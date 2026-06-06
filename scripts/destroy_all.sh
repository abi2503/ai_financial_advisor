#!/bin/bash
set -e

echo "🔴 Destroying all Alex infrastructure..."
echo "This will destroy ALL resources. Are you sure? (yes/no)"
read confirm
if [ "$confirm" != "yes" ]; then
  echo "Cancelled."
  exit 0
fi

cd "$(dirname "$0")/.."

echo "1/7 Destroying Guide 6 agents..."
cd terraform/6_agents && terraform destroy -auto-approve > /dev/null && cd ../..
echo "✅ Guide 6 destroyed"

echo "2/7 Destroying Guide 4 ECS..."
cd terraform/4_researcher && terraform destroy -auto-approve > /dev/null && cd ../..
echo "✅ Guide 4 destroyed"

echo "3/7 Destroying Guide 5 Aurora..."
cd terraform/5_database && terraform destroy -auto-approve > /dev/null && cd ../..
echo "✅ Guide 5 destroyed"

echo "4/7 Destroying Guide 3 Ingest..."
cd terraform/3_ingestion && terraform destroy -auto-approve > /dev/null && cd ../..
echo "✅ Guide 3 destroyed"

echo "5/7 Destroying Guide 2 SageMaker..."
cd terraform/2_sagemaker && terraform destroy -auto-approve > /dev/null && cd ..✅ Guide 2 destroyed"

echo "6/7 Destroying Guide 1 IAM..."
cd terraform/1_permissions && terraform destroy -auto-approve > /dev/null && cd ../..
echo "✅ Guide 1 destroyed"

echo "7/7 Destroying Guide 0 VPC..."
cd terraform/0_vpc && terraform destroy -auto-approve > /dev/null && cd ../..
echo "✅ Guide 0 destroyed"

echo ""
echo "✅ Everything destroyed. AWS bill: $0/day"
