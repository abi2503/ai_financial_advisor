#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo ""
echo "🚀 Starting Alex AI Development Session"
echo "========================================"
echo "$(date)"
echo ""

if [ -f ".env" ]; then
  set -a
  source <(grep -v '^#' .env | sed 's/ *= */=/g')
  set +a
else
  echo "❌ .env not found"
  exit 1
fi

REGION=${DEFAULT_AWS_REGION:-us-east-1}
SM_ENDPOINT="alex-embedding"
SM_CONFIG="alex-embedding-config"
SM_MODEL="alex-embedding-model"

# Set or append a KEY=VALUE in an env file (macOS + Linux compatible)
set_env_var() {
  local file="$1" key="$2" value="$3"
  touch "$file"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "s|^${key}=.*|${key}=${value}|" "$file"
    else
      sed -i "s|^${key}=.*|${key}=${value}|" "$file"
    fi
  else
    echo "${key}=${value}" >> "$file"
  fi
}

sm_status() {
  aws sagemaker describe-endpoint \
    --endpoint-name "$SM_ENDPOINT" \
    --region "$REGION" \
    --query "EndpointStatus" \
    --output text 2>/dev/null || echo "NOT_FOUND"
}

cleanup_sagemaker() {
  local status
  status=$(sm_status)
  if [ "$status" = "NOT_FOUND" ]; then
    return 0
  fi

  echo "  🧹 Cleaning SageMaker ($status)..."
  aws sagemaker delete-endpoint --endpoint-name "$SM_ENDPOINT" --region "$REGION" 2>/dev/null || true

  for i in $(seq 1 36); do
    status=$(sm_status)
    if [ "$status" = "NOT_FOUND" ]; then
      echo "  ✅ Endpoint deleted"
      break
    fi
    echo "  ⏳ Deleting endpoint... ($status, ${i}/36)"
    sleep 10
  done

  aws sagemaker delete-endpoint-config --endpoint-config-name "$SM_CONFIG" --region "$REGION" 2>/dev/null || true
  aws sagemaker delete-model --model-name "$SM_MODEL" --region "$REGION" 2>/dev/null || true
  sleep 5
}

# Resolve ALB URL from Terraform output or live AWS state
get_alb_url() {
  local url
  url=$(cd terraform/4_researcher && terraform output -raw alb_dns_name 2>/dev/null || echo "")
  if [ -n "$url" ] && [ "$url" != "None" ]; then
    echo "$url"
    return
  fi
  local dns
  dns=$(aws elbv2 describe-load-balancers \
    --region "$REGION" \
    --query "LoadBalancers[?contains(LoadBalancerName, 'alex')].DNSName | [0]" \
    --output text 2>/dev/null || echo "")
  if [ -n "$dns" ] && [ "$dns" != "None" ]; then
    echo "http://${dns}"
  fi
}

# Sync ECS endpoints into .env and frontend/.env.local
update_env_from_ecs() {
  local alb_url="$1"
  local ecr_url="${2:-}"

  if [ -z "$alb_url" ] || [ "$alb_url" = "None" ]; then
    echo "  ⚠️  No ALB URL — skipping env update"
    return 0
  fi

  set_env_var ".env" "ECS_SERVICE_URL" "$alb_url"
  echo "  ✅ .env ECS_SERVICE_URL=$alb_url"

  if [ -n "$ecr_url" ] && [ "$ecr_url" != "None" ]; then
    set_env_var ".env" "ECR_REPOSITORY_URL" "$ecr_url"
    echo "  ✅ .env ECR_REPOSITORY_URL=$ecr_url"
  fi

  set_env_var "frontend/.env.local" "ECS_URL" "$alb_url"
  set_env_var "frontend/.env.local" "NEXT_PUBLIC_ECS_URL" "$alb_url"
  echo "  ✅ frontend/.env.local ECS_URL + NEXT_PUBLIC_ECS_URL updated"
}

wait_for_ecs() {
  local running=0
  for i in $(seq 1 30); do
    running=$(aws ecs describe-services \
      --cluster alex-cluster --services alex-researcher \
      --region "$REGION" \
      --query "services[0].runningCount" \
      --output text 2>/dev/null || echo "0")
    if [ "$running" = "None" ] || [ "$running" = "null" ] || [ -z "$running" ]; then
      running=0
    fi
    if [ "$running" -ge 1 ]; then
      echo "  ✅ ECS running ($running tasks)"
      return 0
    fi
    echo "  ⏳ ECS starting... (${i}/30)"
    sleep 15
  done
  echo "  ⚠️  ECS not healthy after 7.5 min — check ECS console"
  return 1
}

ensure_ecr_image() {
  if aws ecr describe-images \
    --repository-name alex-researcher \
    --image-ids imageTag=latest \
    --region "$REGION" > /dev/null 2>&1; then
    echo "  ✅ ECR image exists"
    return 0
  fi

  echo "  ⚠️  No ECR image — building and pushing researcher container..."
  if ! (cd backend/researcher && bash deploy.sh); then
    echo "  ❌ Researcher Docker deploy failed"
    return 1
  fi
  cd "$ROOT"
  return 0
}

wait_for_health() {
  local alb_url="$1"
  local health="starting"
  for i in $(seq 1 18); do
    health=$(curl -s --max-time 15 "$alb_url/health" 2>/dev/null | \
      python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("status","starting"))' 2>/dev/null || echo "starting")
    if [ "$health" = "healthy" ] || [ "$health" = "ok" ]; then
      echo "  ECS: $health"
      return 0
    fi
    echo "  ⏳ ECS health: $health (${i}/18)"
    sleep 10
  done
  echo "  ECS: $health (may still be warming up)"
  return 0
}

ecs_service_active() {
  local status
  status=$(aws ecs describe-services \
    --cluster alex-cluster --services alex-researcher \
    --region "$REGION" \
    --query "services[0].status" \
    --output text 2>/dev/null || echo "MISSING")
  [ "$status" = "ACTIVE" ]
}

resume_ecs() {
  ensure_ecr_image || return 1
  echo "  ▶️  Scaling ECS to 1 (middle lean resume)..."
  aws ecs update-service \
    --cluster alex-cluster \
    --service alex-researcher \
    --desired-count 1 \
    --force-new-deployment \
    --region "$REGION" > /dev/null
  wait_for_ecs || true
}

echo "🔐 Step 0: IAM + SageMaker role (Terraform)..."
cd terraform/2_sagemaker
terraform apply -auto-approve -compact-warnings \
  -target=aws_iam_role.sagemaker_role \
  -target=aws_iam_role_policy_attachment.sagemaker_full_access \
  -target=aws_iam_role_policy_attachment.sagemaker_bedrock_access \
  -target=aws_iam_role_policy_attachment.sagemaker_cloudwatch_access
cd "$ROOT"
echo "  ⏳ Waiting 20s for IAM propagation..."
sleep 20
echo "  ✅ SageMaker IAM role ready"

echo ""
echo "🧠 Step 1: SageMaker endpoint..."
SM_STATUS=$(sm_status)
echo "  Status: $SM_STATUS"

if [ "$SM_STATUS" = "InService" ]; then
  echo "  ✅ SageMaker running"
elif [ "$SM_STATUS" = "Creating" ] || [ "$SM_STATUS" = "Updating" ]; then
  echo "  ⏳ Waiting for SageMaker..."
  aws sagemaker wait endpoint-in-service --endpoint-name "$SM_ENDPOINT" --region "$REGION"
  echo "  ✅ SageMaker ready"
else
  echo "  ⚠️  Recreating SageMaker ($SM_STATUS)..."
  cleanup_sagemaker
  cd terraform/2_sagemaker
  terraform state rm aws_sagemaker_endpoint.embedding_endpoint 2>/dev/null || true
  terraform state rm aws_sagemaker_endpoint_configuration.embedding_config 2>/dev/null || true
  terraform state rm aws_sagemaker_model.embedding_model 2>/dev/null || true
  if ! terraform apply -auto-approve -compact-warnings; then
    echo "  ❌ SageMaker terraform apply failed"
    exit 1
  fi
  cd "$ROOT"
  echo "  ⏳ Waiting for SageMaker InService (up to 15 min)..."
  if ! aws sagemaker wait endpoint-in-service --endpoint-name "$SM_ENDPOINT" --region "$REGION"; then
    FAIL_REASON=$(aws sagemaker describe-endpoint --endpoint-name "$SM_ENDPOINT" --region "$REGION" \
      --query "FailureReason" --output text 2>/dev/null || echo "unknown")
    echo "  ❌ SageMaker failed: $FAIL_REASON"
    exit 1
  fi
  echo "  ✅ SageMaker ready"
fi

echo ""
echo "🐳 Step 2: ECS + ALB..."
ECS_RUNNING=$(aws ecs describe-services \
  --cluster alex-cluster --services alex-researcher \
  --region "$REGION" \
  --query "services[0].runningCount" \
  --output text 2>/dev/null || echo "0")
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --region "$REGION" \
  --query "LoadBalancers[?contains(LoadBalancerName, 'alex')].DNSName | [0]" \
  --output text 2>/dev/null || echo "None")

if [ "$ECS_RUNNING" = "None" ] || [ "$ECS_RUNNING" = "null" ] || [ -z "$ECS_RUNNING" ]; then
  ECS_RUNNING=0
fi

if ecs_service_active && [ -n "$ALB_DNS" ] && [ "$ALB_DNS" != "None" ]; then
  if [ "$ECS_RUNNING" -ge 1 ]; then
    echo "  ✅ ECS already running ($ECS_RUNNING tasks)"
  else
    resume_ecs || true
  fi
elif [ -n "$ALB_DNS" ] && [ "$ALB_DNS" != "None" ]; then
  echo "  ⚠️  ECS service missing — creating via Terraform..."
  cd terraform/4_researcher
  if ! terraform apply -auto-approve -compact-warnings; then
    echo "  ❌ ECS terraform apply failed"
    exit 1
  fi
  cd "$ROOT"
  resume_ecs || true
  ALB_URL=$(get_alb_url)
  ECR_URL=$(cd terraform/4_researcher && terraform output -raw ecr_repository_url 2>/dev/null || echo "")
  echo ""
  echo "  📝 Updating env files with ECS endpoints..."
  update_env_from_ecs "$ALB_URL" "$ECR_URL"
else
  echo "  ⚠️  No ALB found — full ECS Terraform apply..."
  cd terraform/4_researcher
  if ! terraform apply -auto-approve -compact-warnings; then
    echo "  ❌ ECS terraform apply failed"
    exit 1
  fi
  cd "$ROOT"
  resume_ecs || true
  ALB_URL=$(get_alb_url)
  ECR_URL=$(cd terraform/4_researcher && terraform output -raw ecr_repository_url 2>/dev/null || echo "")
  echo ""
  echo "  📝 Updating env files with new ECS endpoints..."
  update_env_from_ecs "$ALB_URL" "$ECR_URL"
fi

# Ensure ECR image exists when service is active but image was deleted
if ecs_service_active; then
  if ! aws ecr describe-images --repository-name alex-researcher --image-ids imageTag=latest --region "$REGION" > /dev/null 2>&1; then
    resume_ecs || true
  fi
fi

echo ""
echo "🔗 Step 3: SSM + env config..."
ALB_URL=$(get_alb_url)
if [ -n "$ALB_URL" ] && [ "$ALB_URL" != "None" ]; then
  aws ssm put-parameter --name "/alex/ecs_url" --value "$ALB_URL" \
    --type "String" --overwrite --region "$REGION" > /dev/null 2>&1
  echo "  ✅ ALB: $ALB_URL"
  echo "  📝 Syncing .env and frontend/.env.local..."
  update_env_from_ecs "$ALB_URL"
  aws lambda update-function-configuration \
    --function-name alex-ops-agent --region "$REGION" \
    --environment "Variables={DB_CLUSTER_ARN=arn:aws:rds:us-east-1:381491881089:cluster:alex-aurora,DB_SECRET_ARN=arn:aws:secretsmanager:us-east-1:381491881089:secret:alex/aurora/credentials-2HP8fm,DB_NAME=alex_db,ALERT_EMAIL=abhishek.suresh2503@gmail.com,FROM_EMAIL=abhishek.suresh2503@gmail.com,DAILY_COST_THRESHOLD=10.0,AUTONOMOUS_MODE=false,ALB_URL=$ALB_URL}" \
    > /dev/null 2>&1 && echo "  ✅ Ops Agent updated" || true
else
  echo "  ⚠️  No ALB URL available"
fi

echo ""
echo "🗄️  Step 4: Aurora warm-up..."
python3 scripts/aurora_warmup.py

echo ""
echo "🏥 Step 5: Health check..."
if [ -n "$ALB_URL" ] && [ "$ALB_URL" != "None" ]; then
  wait_for_health "$ALB_URL"
fi
SM_FINAL=$(sm_status)
echo "  SageMaker: $SM_FINAL"
FRONTEND=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
  "https://ai-financial-advisor-t6kt-abi2503s-projects.vercel.app" 2>/dev/null || echo "000")
echo "  Frontend: HTTP $FRONTEND"

echo ""
echo "⏰ Step 6: Enable schedulers..."
bash scripts/toggle_eventbridge.sh enable 2>/dev/null || echo "  ⚠️  Portfolio scheduler toggle skipped"
aws ssm put-parameter --name "/alex/trading/enabled" --value "true" \
  --type "String" --overwrite --region "$REGION" > /dev/null 2>&1 && \
  echo "  ✅ Trading floor enabled (SSM)" || echo "  ⚠️  Trading SSM skipped"

if [ -n "$ALB_URL" ] && [ "$ALB_URL" != "None" ]; then
  aws lambda update-function-configuration \
    --function-name alex-reporter --region "$REGION" \
    --environment "Variables={ALEX_API_ENDPOINT=${ALEX_API_ENDPOINT:-},ALEX_API_KEY=${ALEX_API_KEY:-},ECS_URL=$ALB_URL,DB_CLUSTER_ARN=arn:aws:rds:us-east-1:381491881089:cluster:alex-aurora,DB_SECRET_ARN=arn:aws:secretsmanager:us-east-1:381491881089:secret:alex/aurora/credentials-2HP8fm,DB_NAME=alex_db,AWS_REGION_NAME=$REGION,RESULTS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/381491881089/alex-results-queue,FRONTEND_RESULTS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/381491881089/alex-frontend-results}" \
    > /dev/null 2>&1 && echo "  ✅ Reporter Lambda ECS_URL updated" || true
  aws lambda update-function-configuration \
    --function-name alex-scheduler --region "$REGION" \
    --environment "Variables={RESEARCH_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/381491881089/alex-research-queue,PLANNER_FUNCTION=alex-planner,DB_CLUSTER_ARN=arn:aws:rds:us-east-1:381491881089:cluster:alex-aurora,DB_SECRET_ARN=arn:aws:secretsmanager:us-east-1:381491881089:secret:alex/aurora/credentials-2HP8fm,DB_NAME=alex_db,AWS_REGION_NAME=$REGION}" \
    > /dev/null 2>&1 && echo "  ✅ Scheduler Lambda updated" || true
fi

echo ""
echo "========================================"
if [ "$SM_FINAL" = "InService" ] && [ -n "$ALB_URL" ] && [ "$ALB_URL" != "None" ]; then
  echo "✅ Session ready!"
else
  echo "⚠️  Session partially ready — check components above"
fi
echo "  ALB: ${ALB_URL:-not available}"
echo "  SageMaker: $SM_FINAL"
echo "  Stop: bash scripts/stop_session.sh  (middle lean — scales ECS to 0)"
echo "===================================="
