#!/bin/bash
# P0 Foundation smoke test — run after every P0-related change.
# Usage:
#   ./scripts/test_p0.sh           # static + unit + Aurora schema
#   ./scripts/test_p0.sh --static  # CI-safe (no AWS)
#   ./scripts/test_p0.sh --full    # + trading orchestrator SQS smoke
set -e
cd "$(dirname "$0")/.."

MODE="${1:---live}"

echo "════════════════════════════════════════"
echo "  Alex P0 Foundation Test Suite"
echo "════════════════════════════════════════"

echo ""
echo "Step 1: Python syntax check (P0 files)..."
python3 -m py_compile \
  backend/researcher/context_service.py \
  backend/researcher/tools.py \
  backend/ingest/ingest_pgvector.py \
  backend/agents/trading/core/orchestrator.py \
  backend/agents/planner.py \
  backend/agents/reporter.py \
  scripts/aurora_warmup.py \
  scripts/tests/test_p0_foundation.py
echo "  ✅ Syntax OK"

echo ""
echo "Step 2: P0 foundation tests..."
if [ "$MODE" = "--static" ]; then
  python3 scripts/tests/test_p0_foundation.py --static
else
  python3 scripts/tests/test_p0_foundation.py --live
fi

if [ "$MODE" = "--full" ]; then
  echo ""
  echo "Step 3: Trading orchestrator SQS smoke (optional)..."
  REGION="${AWS_REGION:-us-east-1}"
  USER_ID="${TEST_USER_ID:-user_3EjDRkfojIp599preEYnkjMESKu}"

  aws lambda invoke \
    --function-name alex-trading-orchestrator \
    --region "$REGION" \
    --payload "{\"trigger\":\"manual\",\"user_id\":\"$USER_ID\",\"force\":true}" \
    --cli-binary-format raw-in-base64-out \
    /tmp/p0_orch_result.json > /dev/null

  TASKS=$(python3 -c "import json; d=json.load(open('/tmp/p0_orch_result.json')); print(d.get('tasks_queued', d.get('body','')))" 2>/dev/null || echo "")
  echo "  Orchestrator response: $TASKS"

  MSGS=$(aws sqs get-queue-attributes \
    --queue-url "https://sqs.us-east-1.amazonaws.com/381491881089/alex-trading-queue" \
    --attribute-names ApproximateNumberOfMessages \
    --region "$REGION" \
    --query "Attributes.ApproximateNumberOfMessages" \
    --output text 2>/dev/null || echo "?")

  echo "  SQS messages queued: $MSGS"
  if [ "$MSGS" != "0" ] && [ "$MSGS" != "?" ]; then
    echo "  ✅ Orchestrator queued tasks (no MessageGroupId error)"
  else
    echo "  ⚠️  No messages in queue — check portfolio holdings or orchestrator logs"
  fi
fi

echo ""
echo "════════════════════════════════════════"
echo "  ✅ P0 test suite complete"
echo "════════════════════════════════════════"
