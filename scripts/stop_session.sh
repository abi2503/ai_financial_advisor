#!/bin/bash
# ============================================
# Alex AI — Stop Development Session
# Run this at the END of every session
# Saves ~$4.83/day
# ============================================
set -e
cd "$(dirname "$0")/.."
source .env

echo ""
echo "🛑 Stopping Alex AI Development Session"
echo "========================================"

# Disable EventBridge
echo ""
echo "⏰ Disabling EventBridge scheduler..."
aws scheduler update-schedule \
  --name alex-auto-research \
  --state DISABLED \
  --schedule-expression "rate(2 hours)" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target "$(aws scheduler get-schedule \
    --name alex-auto-research \
    --region us-east-1 \
    --query 'Target' \
    --output json)" \
  --region us-east-1 > /dev/null 2>&1 || true
echo "  ✅ Scheduler disabled"

# Destroy ECS
echo ""
echo "🐳 Destroying ECS researcher agent..."
cd terraform/4_researcher
terraform destroy -auto-approve -compact-warnings > /dev/null
echo "  ✅ ECS destroyed (saves \$1.73/day)"

# Destroy SageMaker
echo ""
echo "🧠 Destroying SageMaker endpoint..."
cd ../2_sagemaker
terraform destroy -auto-approve -compact-warnings > /dev/null
echo "  ✅ SageMaker destroyed (saves \$3.10/day)"

# Git commit
echo ""
echo "📝 Saving work to GitHub..."
cd ../..
git add .
git commit -m "Auto-save: session end $(date '+%Y-%m-%d %H:%M')" > /dev/null 2>&1 || true
git push origin main > /dev/null 2>&1 || true
echo "  ✅ Code saved to GitHub"

echo ""
echo "========================================"
echo "✅ Session stopped!"
echo "💰 Saving ~\$4.83/day while stopped"
echo ""
echo "Remaining costs while stopped:"
echo "  Aurora Serverless:  ~\$0.00/day"
echo "  S3 Vectors:         ~\$0.10/day"
echo "  CloudWatch:         ~\$0.01/day"
echo "  Lambda:             ~\$0.00/day"
echo "  Total:              ~\$0.11/day"
echo ""
echo "Run start_session.sh to resume"

