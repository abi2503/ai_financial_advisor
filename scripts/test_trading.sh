#!/bin/bash
set -e
cd "$(dirname "$0")/.."

USER_ID="user_3EjDRkfojIp599preEYnkjMESKu"
REGION="us-east-1"

echo "Testing Trading Floor..."

echo "1. Waking Aurora..."
python3 scripts/aurora_warmup.py

echo "2. Purging SQS queue..."
aws sqs purge-queue --queue-url https://sqs.us-east-1.amazonaws.com/381491881089/alex-trading-queue --region $REGION 2>/dev/null || true
sleep 3

echo "3. Invoking orchestrator..."
aws lambda invoke --function-name alex-trading-orchestrator --region $REGION --payload '{"trigger":"manual","user_id":"user_3EjDRkfojIp599preEYnkjMESKu","force":true}' --cli-binary-format raw-in-base64-out /tmp/orch_result.json
cat /tmp/orch_result.json | python3 -m json.tool

echo "4. Checking SQS messages..."
aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/381491881089/alex-trading-queue --attribute-names ApproximateNumberOfMessages --region $REGION

echo "5. Waiting 90s for debate agents..."
sleep 90

echo "6. Debate agent logs:"
aws logs filter-log-events --log-group-name /aws/lambda/alex-debate-agent --region $REGION --start-time $(python3 -c "import time; print(int((time.time()-120)*1000))") --query "events[*].message" --output text 2>/dev/null | grep -v "^$" | head -20

echo "7. Checking stored trades..."
python3 - << PYEOF2
import boto3
rds = boto3.client("rds-data", region_name="us-east-1")
r = rds.execute_statement(
    resourceArn="arn:aws:rds:us-east-1:381491881089:cluster:alex-aurora",
    secretArn="arn:aws:secretsmanager:us-east-1:381491881089:secret:alex/aurora/credentials-2HP8fm",
    database="alex_db",
    sql="SELECT ticker, action, confidence, price FROM simulated_trades ORDER BY executed_at DESC LIMIT 5"
)
if r["records"]:
    for row in r["records"]:
        print(f"  {row[0]['stringValue']}: {row[1]['stringValue']} ({row[2]['doubleValue']:.0f}%) @ \${row[3]['doubleValue']:.2f}")
else:
    print("  No trades yet")
PYEOF2

echo "Trading floor test complete!"
