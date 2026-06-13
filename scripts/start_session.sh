#!/bin/bash
set -e
cd "$(dirname "$0")/.."

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

echo "🔐 Step 0: IAM trust policies..."
aws iam update-assume-role-policy \
  --role-name alex-sagemaker-role \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"sagemaker.amazonaws.com"},"Action":"sts:AssumeRole"}]}' 2>/dev/null && \
  echo "  ✅ Trust policy verified" || echo "  ⚠️  Trust policy skipped"

echo ""
echo "🧠 Step 1: SageMaker..."
SM_STATUS=$(aws sagemaker describe-endpoint \
  --endpoint-name alex-embedding \
  --region $REGION \
  --query "EndpointStatus" \
  --output text 2>/dev/null || echo "NOT_FOUND")
echo "  Status: $SM_STATUS"

if [ "$SM_STATUS" = "InService" ]; then
  echo "  ✅ SageMaker running"
elif [ "$SM_STATUS" = "Creating" ] || [ "$SM_STATUS" = "Updating" ]; then
  echo "  ⏳ Waiting for SageMaker..."
  aws sagemaker wait endpoint-in-service --endpoint-name alex-embedding --region $REGION
  echo "  ✅ SageMaker ready"
else
  echo "  ⚠️  Recreating SageMaker via Terraform..."
  cd terraform/2_sagemaker
  terraform state rm aws_sagemaker_endpoint.embedding_endpoint 2>/dev/null || true
  terraform state rm aws_sagemaker_endpoint_configuration.embedding_config 2>/dev/null || true
  terraform state rm aws_sagemaker_model.embedding_model 2>/dev/null || true
  aws sagemaker delete-endpoint --endpoint-name alex-embedding --region $REGION 2>/dev/null || true
  aws sagemaker delete-endpoint-config --endpoint-config-name alex-embedding-config --region $REGION 2>/dev/null || true
  aws sagemaker delete-model --model-name alex-embedding-model --region $REGION 2>/dev/null || true
  sleep 20
  terraform apply -auto-approve -compact-warnings 2>&1 | tail -3
  cd ../..
  echo "  ⏳ Waiting for SageMaker InService..."
  aws sagemaker wait endpoint-in-service --endpoint-name alex-embedding --region $REGION
  echo "  ✅ SageMaker ready"
fi

echo ""
echo "🐳 Step 2: ECS + ALB..."
ALB_COUNT=$(aws elbv2 describe-load-balancers \
  --region $REGION \
  --query "length(LoadBalancers)" \
  --output text 2>/dev/null || echo "0")
ECS_RUNNING=$(aws ecs describe-services \
  --cluster alex-cluster --services alex-researcher \
  --region $REGION \
  --query "services[0].runningCount" \
  --output text 2>/dev/null || echo "0")

if [ "$ECS_RUNNING" != "0" ] && [ "$ALB_COUNT" != "0" ]; then
  echo "  ✅ ECS running ($ECS_RUNNING tasks)"
else
  echo "  ⚠️  Recreating ECS via Terraform..."
  cd terraform/4_researcher
  terraform apply -auto-approve -compact-warnings 2>&1 | tail -3
  cd ../..
  aws ecs update-service --cluster alex-cluster --service alex-researcher \
    --desired-count 1 --force-new-deployment --region $REGION > /dev/null 2>&1 || true
  echo "  ✅ ECS starting"

  # Capture new endpoints from Terraform and write to env files immediately
  ALB_URL=$(get_alb_url)
  ECR_URL=$(cd terraform/4_researcher && terraform output -raw ecr_repository_url 2>/dev/null || echo "")
  echo ""
  echo "  📝 Updating env files with new ECS endpoints..."
  update_env_from_ecs "$ALB_URL" "$ECR_URL"
fi

echo ""
echo "🔗 Step 3: SSM + env config..."
ALB_URL=$(get_alb_url)
if [ ! -z "$ALB_URL" ] && [ "$ALB_URL" != "None" ]; then
  aws ssm put-parameter --name "/alex/ecs_url" --value "$ALB_URL" \
    --type "String" --overwrite --region $REGION > /dev/null 2>&1
  echo "  ✅ ALB: $ALB_URL"
  echo "  📝 Syncing .env and frontend/.env.local..."
  update_env_from_ecs "$ALB_URL"
  aws lambda update-function-configuration \
    --function-name alex-ops-agent --region $REGION \
    --environment "Variables={DB_CLUSTER_ARN=arn:aws:rds:us-east-1:381491881089:cluster:alex-aurora,DB_SECRET_ARN=arn:aws:secretsmanager:us-east-1:381491881089:secret:alex/aurora/credentials-2HP8fm,DB_NAME=alex_db,ALERT_EMAIL=abhishek.suresh2503@gmail.com,FROM_EMAIL=abhishek.suresh2503@gmail.com,DAILY_COST_THRESHOLD=10.0,AUTONOMOUS_MODE=false,ALB_URL=$ALB_URL}" \
    > /dev/null 2>&1 && echo "  ✅ Ops Agent updated" || true
fi

echo ""
echo "🗄️  Step 4: Aurora warm-up..."
python3 scripts/aurora_warmup.py

echo ""
echo "🏥 Step 5: Health check..."
sleep 5
ALB_URL=$(aws ssm get-parameter --name "/alex/ecs_url" \
  --region $REGION --query "Parameter.Value" --output text 2>/dev/null || echo "")
if [ ! -z "$ALB_URL" ]; then
  HEALTH=$(curl -s --max-time 15 $ALB_URL/health 2>/dev/null | \
    python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("status","unknown"))' 2>/dev/null || echo "starting")
  echo "  ECS: $HEALTH"
fi
SM_FINAL=$(aws sagemaker describe-endpoint --endpoint-name alex-embedding \
  --region $REGION --query "EndpointStatus" --output text 2>/dev/null || echo "unknown")
echo "  SageMaker: $SM_FINAL"
FRONTEND=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
  "https://ai-financial-advisor-t6kt-abi2503s-projects.vercel.app" 2>/dev/null || echo "000")
echo "  Frontend: HTTP $FRONTEND"

echo ""
echo "========================================"
echo "✅ Session ready!"
echo "  ALB: ${ALB_URL:-not available}"
echo "  Stop: bash scripts/stop_session.sh"
echo "===================================="
