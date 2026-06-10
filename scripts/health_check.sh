#!/bin/bash
# ============================================
# Alex AI — Health Check Script
# Run this at start of every session
# to verify all services are working
# ============================================

source .env

REGION=${DEFAULT_AWS_REGION:-us-east-1}

echo ""
echo "🔍 Alex AI — System Health Check"
echo "=================================="
echo ""

# ============================================
# 1. ECS Researcher
# ============================================
echo "📦 ECS Researcher Agent..."
ECS_STATUS=$(aws ecs describe-services \
  --cluster alex-cluster \
  --services alex-researcher \
  --region $REGION \
  --query "services[0].{Running:runningCount,Desired:desiredCount}" \
  --output json 2>/dev/null)

ECS_RUNNING=$(echo $ECS_STATUS | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['Running'])")
ECS_DESIRED=$(echo $ECS_STATUS | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['Desired'])")

if [ "$ECS_RUNNING" = "$ECS_DESIRED" ] && [ "$ECS_RUNNING" != "0" ]; then
  echo "  ✅ Running ($ECS_RUNNING/$ECS_DESIRED)"
else
  echo "  ❌ Not running ($ECS_RUNNING/$ECS_DESIRED)"
  echo "     Run: cd terraform/4_researcher && terraform apply -auto-approve"
fi

# ============================================
# 2. ALB Health
# ============================================
echo ""
echo "🌐 ALB Health..."
ALB_URL=$(aws elbv2 describe-load-balancers \
  --names alex-alb \
  --region $REGION \
  --query "LoadBalancers[0].DNSName" \
  --output text 2>/dev/null)

if [ "$ALB_URL" = "None" ] || [ -z "$ALB_URL" ]; then
  echo "  ❌ ALB not found — ECS not deployed"
else
  HEALTH=$(curl -s -o /dev/null -w "%{http_code}" \
    http://$ALB_URL/health --max-time 5)
  if [ "$HEALTH" = "200" ]; then
    echo "  ✅ Healthy (http://$ALB_URL)"
  else
    echo "  ❌ Unhealthy (HTTP $HEALTH)"
  fi
fi

# ============================================
# 3. SSM Parameter
# ============================================
echo ""
echo "📝 SSM Parameter..."
SSM_URL=$(aws ssm get-parameter \
  --name "/alex/ecs_url" \
  --region $REGION \
  --query "Parameter.Value" \
  --output text 2>/dev/null)

if [ -z "$SSM_URL" ]; then
  echo "  ❌ SSM parameter missing"
else
  echo "  ✅ $SSM_URL"
fi

# ============================================
# 4. Lambda Functions
# ============================================
echo ""
echo "⚡ Lambda Functions..."
for FUNC in alex-ingest alex-planner alex-tagger alex-reporter alex-scheduler; do
  STATUS=$(aws lambda get-function \
    --function-name $FUNC \
    --region $REGION \
    --query "Configuration.State" \
    --output text 2>/dev/null)
  if [ "$STATUS" = "Active" ]; then
    echo "  ✅ $FUNC"
  else
    echo "  ❌ $FUNC ($STATUS)"
  fi
done

# ============================================
# 5. SQS Queues
# ============================================
echo ""
echo "📬 SQS Queues..."
for QUEUE_URL in $SQS_RESEARCH_QUEUE_URL $SQS_RESULTS_QUEUE_URL $SQS_DLQ_URL; do
  QUEUE_NAME=$(echo $QUEUE_URL | awk -F'/' '{print $NF}')
  MSGS=$(aws sqs get-queue-attributes \
    --queue-url $QUEUE_URL \
    --attribute-names ApproximateNumberOfMessages \
    --region $REGION \
    --query "Attributes.ApproximateNumberOfMessages" \
    --output text 2>/dev/null)
  echo "  ✅ $QUEUE_NAME ($MSGS messages)"
done

# ============================================
# 6. Aurora Database
# ============================================
echo ""
echo "🗄️  Aurora Database..."
DB_STATUS=$(aws rds describe-db-clusters \
  --db-cluster-identifier alex-aurora \
  --region $REGION \
  --query "DBClusters[0].Status" \
  --output text 2>/dev/null)

if [ "$DB_STATUS" = "available" ]; then
  echo "  ✅ Available"
else
  echo "  ⚠️  Status: $DB_STATUS"
fi

# ============================================
# 7. S3 Vectors
# ============================================
echo ""
echo "🔎 S3 Vectors..."
S3V_STATUS=$(aws s3api head-bucket \
  --bucket $VECTOR_BUCKET \
  --region $REGION 2>/dev/null && echo "exists" || echo "missing")

if [ "$S3V_STATUS" = "exists" ]; then
  echo "  ✅ Bucket: $VECTOR_BUCKET"
else
  echo "  ❌ Bucket missing: $VECTOR_BUCKET"
fi

# ============================================
# 8. SageMaker Endpoint
# ============================================
echo ""
echo "🧠 SageMaker Endpoint..."
SM_STATUS=$(aws sagemaker describe-endpoint \
  --endpoint-name $SAGEMAKER_ENDPOINT_NAME \
  --region $REGION \
  --query "EndpointStatus" \
  --output text 2>/dev/null)

if [ "$SM_STATUS" = "InService" ]; then
  echo "  ✅ InService"
else
  echo "  ⚠️  Status: $SM_STATUS"
fi

# ============================================
# 9. Bedrock Guardrail
# ============================================
echo ""
echo "🛡️  Bedrock Guardrail..."
GUARDRAIL_STATUS=$(aws bedrock get-guardrail \
  --guardrail-identifier $BEDROCK_GUARDRAIL_ID \
  --region $REGION \
  --query "status" \
  --output text 2>/dev/null)

if [ "$GUARDRAIL_STATUS" = "READY" ]; then
  echo "  ✅ Ready (ID: $BEDROCK_GUARDRAIL_ID)"
else
  echo "  ⚠️  Status: $GUARDRAIL_STATUS"
fi

# ============================================
# 10. EventBridge Scheduler
# ============================================
echo ""
echo "⏰ EventBridge Scheduler..."
EB_STATUS=$(aws events describe-rule \
  --name alex-research-scheduler \
  --region $REGION \
  --query "State" \
  --output text 2>/dev/null)

if [ "$EB_STATUS" = "ENABLED" ]; then
  echo "  ✅ Enabled (autonomous research active)"
elif [ "$EB_STATUS" = "DISABLED" ]; then
  echo "  ⚠️  Disabled (run toggle_eventbridge.sh enable)"
else
  echo "  ❌ Not found"
fi

# ============================================
# 11. Vercel Frontend
# ============================================
echo ""
echo "🌍 Vercel Frontend..."
VERCEL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  https://ai-financial-advisor-t6kt-abi2503s-projects.vercel.app \
  --max-time 10)

if [ "$VERCEL_STATUS" = "200" ]; then
  echo "  ✅ Live"
else
  echo "  ❌ HTTP $VERCEL_STATUS"
fi

# ============================================
# Summary
# ============================================
echo ""
echo "=================================="
echo "✅ Health check complete!"
echo ""
echo "Quick actions:"
echo "  Start ECS:    cd terraform/4_researcher && terraform apply -auto-approve"
echo "  Deploy image: cd backend/researcher && bash deploy.sh"
echo "  Start dev:    cd frontend && npm run dev"
echo "  Enable cron:  bash scripts/toggle_eventbridge.sh enable"
echo ""