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

echo "🔨 Building Docker image..."
DOCKER_BUILDKIT=1 docker build \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  -t alex-researcher:latest \
  .

echo "🏷️  Tagging image..."
docker tag alex-researcher:latest "${ECR_URL}:latest"

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

echo "✅ Image pushed successfully!"

# Step 1 — Scale to zero (kills current container)
aws ecs update-service \
  --cluster alex-cluster \
  --service alex-researcher \
  --desired-count 0 \
  --region us-east-1 > /dev/null

echo "⏳ Waiting for container to stop..."
sleep 15

# Step 2 — Scale back up (forces fresh pull)
aws ecs update-service \
  --cluster alex-cluster \
  --service alex-researcher \
  --desired-count 1 \
  --force-new-deployment \
  --region us-east-1 > /dev/null

# Check task started AFTER your last push
aws ecs describe-services \
  --cluster alex-cluster \
  --services alex-researcher \
  --region us-east-1 \
  --query "services[0].deployments"