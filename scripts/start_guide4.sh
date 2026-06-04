#!/bin/bash
echo "🚀 Starting Guide 4 infrastructure..."
cd terraform/4_researcher
terraform apply -auto-approve
echo ""
echo "⏳ Waiting for ECS to stabilize..."
aws ecs wait services-stable \
  --cluster alex-cluster \
  --services alex-researcher \
  --region us-east-1
echo ""
echo "✅ Ready! Your URL:"
terraform output alb_dns_name