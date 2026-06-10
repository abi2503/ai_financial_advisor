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
MAX_ATTEMPTS=10
ATTEMPT=1
PUSH_SUCCESS=false

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    if docker push "${ECR_URL}:latest"; then
        PUSH_SUCCESS=true
        break
    else
        echo "Push failed — attempt $ATTEMPT of $MAX_ATTEMPTS. Retrying in 15s..."
        ATTEMPT=$((ATTEMPT + 1))
        sleep 15
    fi
done

if [ "$PUSH_SUCCESS" = false ]; then
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

echo "⏳ Waiting for container to stop..."
aws ecs wait services-stable \
  --cluster alex-cluster \
  --services alex-researcher \
  --region $REGION

# Scale back up — forces fresh pull
echo "🚀 Starting new container..."
aws ecs update-service \
  --cluster alex-cluster \
  --service alex-researcher \
  --desired-count 1 \
  --force-new-deployment \
  --region $REGION > /dev/null

echo "⏳ Waiting for new container to be healthy..."
aws ecs wait services-stable \
  --cluster alex-cluster \
  --services alex-researcher \
  --region $REGION

# Get ALB URL
ALB_URL=$(aws elbv2 describe-load-balancers \
  --names alex-alb \
  --region $REGION \
  --query "LoadBalancers[0].DNSName" \
  --output text)

echo ""
echo "✅ Deployed! ALB: http://${ALB_URL}"
echo ""

# Update SSM FIRST — so Next.js gets new URL immediately
echo "📝 Updating SSM Parameter..."
aws ssm put-parameter \
  --name "/alex/ecs_url" \
  --value "http://${ALB_URL}" \
  --type "String" \
  --overwrite \
  --region $REGION > /dev/null
echo "✅ SSM updated: http://${ALB_URL}"

# Update frontend .env.local
if [ -f "../../frontend/.env.local" ]; then
  sed -i '' \
    "s|NEXT_PUBLIC_ECS_URL=.*|NEXT_PUBLIC_ECS_URL=http://${ALB_URL}|" \
    ../../frontend/.env.local
  sed -i '' \
    "s|ECS_URL=.*|ECS_URL=http://${ALB_URL}|" \
    ../../frontend/.env.local
  echo "✅ Updated frontend/.env.local"
fi

# Update root .env
if [ -f "../../.env" ]; then
  sed -i '' \
    "s|ECS_SERVICE_URL=.*|ECS_SERVICE_URL=http://${ALB_URL}|" \
    ../../.env
  echo "✅ Updated .env"
fi

# Test health
echo "🏥 Testing health..."
HEALTH=$(curl -s "http://${ALB_URL}/health")
echo $HEALTH | python3 -m json.tool

if echo $HEALTH | grep -q '"status": "healthy"'; then
  echo "✅ Service is healthy!"
else
  echo "⚠️  Service may not be healthy — checking logs..."
  aws logs tail /ecs/alex-researcher \
    --region $REGION \
    --since 5m \
    --format short
fi

# Show deployment status
echo ""
echo "📊 Deployment status:"
aws ecs describe-services \
  --cluster alex-cluster \
  --services alex-researcher \
  --region $REGION \
  --query "services[0].deployments" \
  --output table

echo ""
echo "🎉 Deploy complete!"
echo "   ALB:  http://${ALB_URL}"
echo "   SSM:  /alex/ecs_url updated"
echo "   Next: restart frontend to pick up new URL"