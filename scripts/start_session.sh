#!/bin/bash
# ============================================
# Alex AI — Start Development Session
# Run this at the START of every session
# Spins up SageMaker + ECS + updates SSM
# Usage: bash scripts/start_session.sh
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
  echo "❌ .env not found — run from project root"
  exit 1
fi

REGION=${DEFAULT_AWS_REGION:-us-east-1}

# ============================================
# Step 1 — SageMaker Endpoint
# ============================================
echo "🧠 Starting SageMaker embedding endpoint..."
cd terraform/2_sagemaker
terraform apply -auto-approve -compact-warnings 2>&1 | tail -3
SM_STATUS=$(aws sagemaker describe-endpoint \
  --endpoint-name alex-embedding \
  --region $REGION \
  --query "EndpointStatus" \
  --output text 2>/dev/null)
echo "  ✅ SageMaker: $SM_STATUS"
cd ../..

# ============================================
# Step 2 — ECS Infrastructure
# ============================================
echo ""
echo "🐳 Starting ECS infrastructure..."
cd terraform/4_researcher
terraform apply -auto-approve -compact-warnings 2>&1 | tail -3
echo "  ✅ ECS infrastructure ready"
cd ../..

# ============================================
# Step 3 — Deploy Researcher Image
# ============================================
echo ""
echo "📦 Deploying researcher agent..."
cd backend/researcher
bash deploy.sh
cd ../..

# ============================================
# Step 4 — Verify Health
# ============================================
echo ""
echo "🏥 Running health check..."
bash scripts/health_check.sh

# ============================================
# Step 5 — Start Frontend Reminder
# ============================================
echo ""
echo "========================================"
echo "✅ Session ready!"
echo ""
echo "Next steps:"
echo "  cd frontend && npm run dev"
echo ""
echo "Test scripts:"
echo "  python3 scripts/tests/test_edgar.py"
echo "  bash scripts/tests/test_fast_research.sh"
echo ""
echo "💰 Remember to stop when done:"
echo "  bash scripts/stop_session.sh"
echo "  Saves \$4.83/day"
echo "========================================"