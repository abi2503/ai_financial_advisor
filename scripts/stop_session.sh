#!/bin/bash
echo "🛑 Stopping Guide 4 infrastructure..."

# Scale to 0 first (graceful shutdown)
aws ecs update-service \
  --cluster alex-cluster \
  --service alex-researcher \
  --desired-count 0 \
  --region us-east-1 > /dev/null

echo "⏳ Waiting for tasks to stop..."
sleep 15

# Destroy everything
cd terraform/4_researcher
terraform destroy -auto-approve

echo "✅ All Guide 4 resources destroyed"
echo "💰 No more charges accumulating"