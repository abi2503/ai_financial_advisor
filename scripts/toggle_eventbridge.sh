#!/bin/bash

# ============================================
# EventBridge Scheduler Toggle Script
# Controls the auto-research scheduler
# Usage:
#   bash scripts/toggle_eventbridge.sh enable
#   bash scripts/toggle_eventbridge.sh disable
#   bash scripts/toggle_eventbridge.sh status
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../.env" ]; then
  set -a
  source "$SCRIPT_DIR/../.env"
  set +a
fi

SCHEDULE_NAME="alex-auto-research"
REGION=${DEFAULT_AWS_REGION:-us-east-1}

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

case "$1" in

  enable)
    echo "🟢 Enabling EventBridge scheduler..."

    aws scheduler update-schedule \
      --name $SCHEDULE_NAME \
      --state ENABLED \
      --schedule-expression "rate(2 hours)" \
      --flexible-time-window '{"Mode": "OFF"}' \
      --target "$(aws scheduler get-schedule \
        --name $SCHEDULE_NAME \
        --region $REGION \
        --query 'Target' \
        --output json)" \
      --region $REGION > /dev/null

    echo -e "${GREEN}✅ Scheduler ENABLED — Alex will research every 2 hours${NC}"
    echo "💡 Disable when done testing: bash scripts/toggle_eventbridge.sh disable"
    ;;

  disable)
    echo "🔴 Disabling EventBridge scheduler..."

    aws scheduler update-schedule \
      --name $SCHEDULE_NAME \
      --state DISABLED \
      --schedule-expression "rate(2 hours)" \
      --flexible-time-window '{"Mode": "OFF"}' \
      --target "$(aws scheduler get-schedule \
        --name $SCHEDULE_NAME \
        --region $REGION \
        --query 'Target' \
        --output json)" \
      --region $REGION > /dev/null

    echo -e "${RED}✅ Scheduler DISABLED — No automatic research running${NC}"
    echo "💡 Re-enable when needed: bash scripts/toggle_eventbridge.sh enable"
    ;;

  status)
    echo "📊 Checking scheduler status..."

    STATUS=$(aws scheduler get-schedule \
      --name $SCHEDULE_NAME \
      --region $REGION \
      --query 'State' \
      --output text 2>/dev/null)

    if [ $? -ne 0 ]; then
      echo -e "${YELLOW}⚠️  Scheduler not found — has Guide 6 been deployed?${NC}"
      exit 1
    fi

    NEXT_RUN=$(aws scheduler get-schedule \
      --name $SCHEDULE_NAME \
      --region $REGION \
      --query 'NextInvocationTime' \
      --output text 2>/dev/null)

    if [ "$STATUS" == "ENABLED" ]; then
      echo -e "${GREEN}✅ Scheduler: ENABLED${NC}"
      echo "   Next run: $NEXT_RUN"
      echo "   Schedule: Every 2 hours"
    else
      echo -e "${RED}⏸️  Scheduler: DISABLED${NC}"
      echo "   Not running automatically"
    fi
    ;;

  trigger)
    echo "⚡ Manually triggering scheduler NOW..."

    FUNCTION_NAME="alex-scheduler"

    aws lambda invoke \
      --function-name $FUNCTION_NAME \
      --region $REGION \
      --payload '{"source": "manual-trigger", "task": "auto-research"}' \
      --cli-binary-format raw-in-base64-out \
      /tmp/scheduler_response.json > /dev/null

    echo -e "${GREEN}✅ Scheduler triggered manually${NC}"
    echo "Response:"
    cat /tmp/scheduler_response.json
    ;;

  *)
    echo "Usage: bash scripts/toggle_eventbridge.sh [enable|disable|status|trigger]"
    echo ""
    echo "Commands:"
    echo "  enable   → Start auto-research every 2 hours"
    echo "  disable  → Stop auto-research (saves cost)"
    echo "  status   → Check if scheduler is running"
    echo "  trigger  → Manually trigger research right now"
    echo ""
    echo "Cost impact:"
    echo "  ENABLED:  ~\$0.01/day (Lambda invocations)"
    echo "  DISABLED: \$0.00/day"
    ;;

esac