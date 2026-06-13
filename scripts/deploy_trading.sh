#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "Packaging Trading Floor..."

TEMP="/tmp/trading_deploy"
rm -rf $TEMP && mkdir -p $TEMP
cp -r backend/agents/trading/* $TEMP/
pip install yfinance pydantic boto3 --target $TEMP/ --quiet 2>/dev/null
find $TEMP -name "*.pyc" -delete 2>/dev/null || true
find $TEMP -name "*.zip" -delete 2>/dev/null || true
cd $TEMP && zip -r /tmp/trading_package.zip . > /dev/null && cd -
echo "Size: $(ls -lh /tmp/trading_package.zip | awk '{print $5}')"

echo "Deploying alex-trading-orchestrator..."
aws lambda update-function-code --function-name alex-trading-orchestrator --zip-file fileb:///tmp/trading_package.zip --region us-east-1 > /dev/null
aws lambda wait function-updated --function-name alex-trading-orchestrator --region us-east-1
echo "  OK orchestrator deployed"

echo "Deploying alex-debate-agent..."
aws lambda update-function-code --function-name alex-debate-agent --zip-file fileb:///tmp/trading_package.zip --region us-east-1 > /dev/null
aws lambda wait function-updated --function-name alex-debate-agent --region us-east-1
echo "  OK debate agent deployed"

echo "Trading Floor deployed!"
