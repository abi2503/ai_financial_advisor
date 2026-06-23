#!/bin/bash
# ============================================
# Alex AI — Pause Development Session (middle lean)
# Scales ECS to 0 + removes SageMaker endpoint
# Keeps ALB, ECR image, Terraform state
# Saves ~$4.15/day vs full session (~$0.65/day while paused)
#
# Full teardown (destroy ALB/ECS/SageMaker Terraform):
#   FULL_TEARDOWN=1 bash scripts/stop_session.sh
# ============================================
set -e
cd "$(dirname "$0")/.."
source .env

REGION=${DEFAULT_AWS_REGION:-us-east-1}
SM_ENDPOINT="alex-embedding"
SM_CONFIG="alex-embedding-config"
SM_MODEL="alex-embedding-model"

sm_status() {
  aws sagemaker describe-endpoint \
    --endpoint-name "$SM_ENDPOINT" \
    --region "$REGION" \
    --query "EndpointStatus" \
    --output text 2>/dev/null || echo "NOT_FOUND"
}

pause_sagemaker() {
  local status
  status=$(sm_status)
  if [ "$status" = "NOT_FOUND" ]; then
    echo "  ✅ SageMaker already off"
    return 0
  fi

  echo "  🧹 Removing SageMaker endpoint ($status)..."
  aws sagemaker delete-endpoint --endpoint-name "$SM_ENDPOINT" --region "$REGION" 2>/dev/null || true

  for i in $(seq 1 24); do
    status=$(sm_status)
    if [ "$status" = "NOT_FOUND" ]; then
      echo "  ✅ SageMaker endpoint removed (saves ~\$3.10/day)"
      break
    fi
    echo "  ⏳ Waiting for endpoint delete... ($status, ${i}/24)"
    sleep 10
  done

  aws sagemaker delete-endpoint-config --endpoint-config-name "$SM_CONFIG" --region "$REGION" 2>/dev/null || true
  aws sagemaker delete-model --model-name "$SM_MODEL" --region "$REGION" 2>/dev/null || true
}

echo ""
echo "🛑 Pausing Alex AI Development Session (middle lean)"
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
    --region "$REGION" \
    --query 'Target' \
    --output json)" \
  --region "$REGION" > /dev/null 2>&1 || true
echo "  ✅ Scheduler disabled"

echo ""
echo "📈 Disabling trading floor (SSM)..."
aws ssm put-parameter --name "/alex/trading/enabled" --value "false" \
  --type "String" --overwrite --region "$REGION" > /dev/null 2>&1 || true
echo "  ✅ Trading disabled"

if [ "${FULL_TEARDOWN:-0}" = "1" ]; then
  echo ""
  echo "⚠️  FULL_TEARDOWN=1 — destroying ECS + SageMaker via Terraform..."
  cd terraform/4_researcher
  terraform destroy -auto-approve -compact-warnings > /dev/null
  echo "  ✅ ECS + ALB destroyed"
  cd ../2_sagemaker
  terraform destroy -auto-approve -compact-warnings > /dev/null
  echo "  ✅ SageMaker Terraform destroyed"
  cd ../..
else
  echo ""
  echo "🐳 Scaling ECS researcher to 0 (keeping ALB + ECR)..."
  if aws ecs describe-services \
    --cluster alex-cluster --services alex-researcher \
    --region "$REGION" \
    --query "services[0].status" --output text 2>/dev/null | grep -q ACTIVE; then
    aws ecs update-service \
      --cluster alex-cluster \
      --service alex-researcher \
      --desired-count 0 \
      --region "$REGION" > /dev/null
    echo "  ⏳ Waiting for tasks to stop..."
    aws ecs wait services-stable \
      --cluster alex-cluster \
      --services alex-researcher \
      --region "$REGION" 2>/dev/null || true
    echo "  ✅ ECS scaled to 0 (saves ~\$1.30/day)"
  else
    echo "  ⚠️  ECS service not found — already stopped or never created"
  fi

  echo ""
  echo "🧠 Pausing SageMaker embedding endpoint..."
  pause_sagemaker
fi

echo ""
echo "========================================"
echo "✅ Session paused (middle lean)"
echo "💰 Paused cost: ~\$0.65/day (~\$20/mo)"
echo ""
echo "  ALB + ECR:     kept (fast resume, stable URL)"
echo "  ECS tasks:     0"
echo "  SageMaker:     off"
echo "  Schedulers:    off"
echo ""
echo "Resume:  bash scripts/start_session.sh"
echo "Nuke:    FULL_TEARDOWN=1 bash scripts/stop_session.sh"
echo "========================================"
