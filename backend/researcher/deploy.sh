#!/bin/bash
set -e

source ../../.env

REGION=${DEFAULT_AWS_REGION:-us-east-1}
ACCOUNT_ID=${AWS_ACCOUNT_ID}
ECR_URL="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/alex-researcher"

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin \
  "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "🔨 Building Docker image (linux/amd64 for ECS)..."
docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  -t alex-researcher:amd64 \
  --load \
  .

echo "🏷️  Tagging image..."
docker tag alex-researcher:amd64 "${ECR_URL}:latest"

echo "📤 Pushing to ECR..."
MAX_ATTEMPTS=5
ATTEMPT=1

until docker push "${ECR_URL}:latest" || [ $ATTEMPT -eq $MAX_ATTEMPTS ]; do
    echo "Push failed — attempt $ATTEMPT of $MAX_ATTEMPTS. Retrying..."
    ATTEMPT=$((ATTEMPT + 1))
    sleep 5
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "❌ Push failed after $MAX_ATTEMPTS attempts"
    exit 1
fi

echo "✅ Image pushed!"

# Scale to zero — kills current container
echo "⏳ Stopping current container..."
aws ecs update-service \
  --cluster alex-cluster \
  --service alex-researcher \
  --desired-count 0 \
  --region $REGION > /dev/null

sleep 15

# Scale back up — forces fresh pull of new image
echo "🚀 Starting new container..."
aws ecs update-service \
  --cluster alex-cluster \
  --service alex-researcher \
  --desired-count 1 \
  --force-new-deployment \
  --region $REGION > /dev/null

sleep 10

# Get ALB URL and update .env.local automatically
ALB_URL=$(aws elbv2 describe-load-balancers \
  --names alex-alb \
  --region $REGION \
  --query "LoadBalancers[0].DNSName" \
  --output text)

echo ""
echo "✅ Deployed! ALB: http://${ALB_URL}"
echo ""

# Auto-update frontend .env.local
if [ -f "../../frontend/.env.local" ]; then
  sed -i '' \
    "s|NEXT_PUBLIC_ECS_URL=.*|NEXT_PUBLIC_ECS_URL=http://${ALB_URL}|" \
    ../../frontend/.env.local
  sed -i '' \
    "s|ECS_URL=.*|ECS_URL=http://${ALB_URL}|" \
    ../../frontend/.env.local
  echo "✅ Updated frontend/.env.local with new ALB URL"
fi

sleep 60

# Test health
echo "🏥 Testing health..."
curl -s "http://${ALB_URL}/health" | python3 -m json.tool

# Show deployment status
echo ""
echo "📊 Deployment status:"
aws ecs describe-services \
  --cluster alex-cluster \
  --services alex-researcher \
  --region $REGION \
  --query "services[0].deployments" \
  --output table