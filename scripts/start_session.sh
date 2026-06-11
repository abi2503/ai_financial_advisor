#!/bin/bash
# ============================================
# Alex AI — Start Development Session
# ============================================
set -e
cd "$(dirname "$0")/.."

echo ""
echo "🚀 Starting Alex AI Development Session"
echo "========================================"
echo "$(date)"
echo ""

# Load env vars
if [ -f ".env" ]; then
  set -a
  source <(grep -v '^#' .env | sed 's/ *= */=/g')
  set +a
else
  echo "❌ .env not found"
  exit 1
fi

REGION=${DEFAULT_AWS_REGION:-us-east-1}

# ============================================
# Step 1 — SageMaker
# ============================================
echo "🧠 Starting SageMaker embedding endpoint..."

# Check if endpoint already exists and is InService
SM_STATUS=$(aws sagemaker describe-endpoint \
  --endpoint-name alex-embedding \
  --region $REGION \
  --query "EndpointStatus" \
  --output text 2>/dev/null || echo "NOT_FOUND")

echo "  Current status: $SM_STATUS"

if [ "$SM_STATUS" = "InService" ]; then
  echo "  ✅ SageMaker already running — skipping"

elif [ "$SM_STATUS" = "Creating" ] || [ "$SM_STATUS" = "Updating" ]; then
  echo "  ⏳ SageMaker is starting — waiting..."
  aws sagemaker wait endpoint-in-service \
    --endpoint-name alex-embedding \
    --region $REGION
  echo "  ✅ SageMaker ready"

elif [ "$SM_STATUS" = "Deleting" ]; then
  echo "  ⏳ SageMaker is deleting — waiting..."
  aws sagemaker wait endpoint-deleted \
    --endpoint-name alex-embedding \
    --region $REGION 2>/dev/null || true
  echo "  Recreating SageMaker..."
  cd terraform/2_sagemaker
  terraform apply -auto-approve -compact-warnings 2>&1 | tail -3
  cd ../..
  aws sagemaker wait endpoint-in-service \
    --endpoint-name alex-embedding \
    --region $REGION
  echo "  ✅ SageMaker ready"

elif [ "$SM_STATUS" = "Failed" ]; then
  echo "  ⚠️  Endpoint failed — cleaning and recreating..."
  # Clean terraform state
  cd terraform/2_sagemaker
  terraform state rm aws_sagemaker_endpoint.embedding_endpoint 2>/dev/null || true
  # Import existing if it exists
  terraform import aws_sagemaker_endpoint.embedding_endpoint alex-embedding 2>/dev/null || true
  terraform apply -auto-approve -compact-warnings 2>&1 | tail -3
  cd ../..
  echo "  ✅ SageMaker recreated"

else
  # NOT_FOUND — create fresh
  echo "  Creating SageMaker endpoint..."
  cd terraform/2_sagemaker

  # Clean stale state first
  terraform state rm aws_sagemaker_endpoint.embedding_endpoint 2>/dev/null || true
  terraform state rm aws_sagemaker_endpoint_configuration.embedding_config 2>/dev/null || true
  terraform state rm aws_sagemaker_model.embedding_model 2>/dev/null || true

  terraform apply -auto-approve -compact-warnings 2>&1 | tail -5

  cd ../..

  echo "  ⏳ Waiting for endpoint to be InService..."
  aws sagemaker wait endpoint-in-service \
    --endpoint-name alex-embedding \
    --region $REGION
  echo "  ✅ SageMaker ready"
fi

# ============================================
# Step 2 — ECS Infrastructure
# ============================================
echo ""
echo "🐳 Starting ECS infrastructure..."

ECS_STATUS=$(aws ecs describe-services \
  --cluster alex-cluster \
  --services alex-researcher \
  --region $REGION \
  --query "services[0].status" \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$ECS_STATUS" = "ACTIVE" ]; then
  RUNNING=$(aws ecs describe-services \
    --cluster alex-cluster \
    --services alex-researcher \
    --region $REGION \
    --query "services[0].runningCount" \
    --output text)
  echo "  ✅ ECS already running ($RUNNING tasks)"
else
  cd terraform/4_researcher
  terraform apply -auto-approve -compact-warnings 2>&1 | tail -3
  cd ../..
  echo "  ✅ ECS infrastructure ready"

  # Deploy latest image
  echo ""
  echo "📦 Deploying researcher image..."
  cd backend/researcher
  bash deploy.sh
  cd ../..
fi

# ============================================
# Step 3 — Update SSM with ALB URL
# ============================================
echo ""
echo "🔗 Updating SSM with ALB URL..."
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names alex-alb \
  --region $REGION \
  --query "LoadBalancers[0].DNSName" \
  --output text 2>/dev/null)

if [ ! -z "$ALB_DNS" ] && [ "$ALB_DNS" != "None" ]; then
  aws ssm put-parameter \
    --name "/alex/ecs_url" \
    --value "http://${ALB_DNS}" \
    --type "String" \
    --overwrite \
    --region $REGION > /dev/null
  echo "  ✅ ALB: http://${ALB_DNS}"
fi

# ============================================
# Step 4 — Health Check
# ============================================
echo ""
echo "🏥 Quick health check..."

sleep 5
ALB=$(aws ssm get-parameter \
  --name "/alex/ecs_url" \
  --region $REGION \
  --query "Parameter.Value" \
  --output text 2>/dev/null)

if [ ! -z "$ALB" ]; then
  HEALTH=$(curl -s --max-time 10 $ALB/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "starting")
  echo "  ECS Health: $HEALTH"
fi

SM_FINAL=$(aws sagemaker describe-endpoint \
  --endpoint-name alex-embedding \
  --region $REGION \
  --query "EndpointStatus" \
  --output text 2>/dev/null)
echo "  SageMaker:  $SM_FINAL"

# ============================================
# Done
# ============================================
echo ""
echo "========================================"
echo "✅ Session ready!"
echo ""
echo "Next steps:"
echo "  cd frontend && npm run dev"
echo ""
echo "Test streaming:"
echo "  curl -s -X POST \$ALB/research/stream \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"topic\": \"NVDA analysis\"}' \\"
echo "    --no-buffer --max-time 180"
echo ""
echo "💰 Stop when done:"
echo "  bash scripts/stop_session.sh"
echo "========================================"