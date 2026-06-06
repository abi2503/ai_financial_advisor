#!/bin/bash
set -e

echo "🚀 Deploying all Alex infrastructure..."

cd "$(dirname "$0")/.."

echo "1/7 Deploying Guide 0 VPC..."
cd terraform/0_vpc && terraform apply -auto-approve > /dev/null && cd ../..
echo "✅ VPC ready"

echo "2/7 Deploying Guide 1 IAM..."
cd terraform/1_permissions && terraform apply -auto-approve > /dev/null && cd ../..
echo "✅ IAM ready"

echo "3/7 Deploying Guide 2 SageMaker..."
cd terraform/2_sagemaker && terraform apply -auto-approve > /dev/null && cd ../..
echo "✅ SageMaker ready"

echo "4/7 Deploying Guide 3 Ingest..."
cd terraform/3_ingestion && terraform apply -auto-approve > /dev/null && cd ../..
echo "✅ Ingest pipeline ready"

echo "5/7 Deploying Guide 5 Aurora..."
cd terraform/5_database && terraform apply -auto-approve > /dev/null && cd ../..
echo "✅ Aurora ready"

echo "6/7 Deploying Guide 6 Agents..."
cd terraform/6_agents && terraform apply -auto-approve > /dev/null && cd ../..
echo "✅ Agents ready"

echo  Guide 4 ECS..."
cd terraform/4_researcher && terraform apply -auto-approve > /dev/null && cd ../..
echo "✅ ECS ready"

# Get outputs
echo ""
echo "📋 Key URLs:"
echo "  ECS: $(cd terraform/4_researcher && terraform output -raw alb_dns_name 2>/dev/null)"
echo "  API: $(cd terraform/3_ingestion && terraform output -raw api_endpoint 2>/dev/null)"
echo ""
echo "✅ Everything deployed!"
echo ""
echo "Next steps:"
echo "  1. Push Docker image: cd backend/researcher && bash deploy.sh"
echo "  2. Force ECS update:  aws ecs update-service --cluster alex-cluster --service alex-researcher --force-new-deployment --region us-east-1"
echo "  3. Run frontend:      cd frontend && npm run dev"
