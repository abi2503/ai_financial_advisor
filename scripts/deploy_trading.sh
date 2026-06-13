#!/bin/bash
set -e
cd "$(dirname "$0")/.."

BUCKET="twin-terraform-state-381491881089"
REGION="us-east-1"
TEMP="/tmp/trading_deploy"

echo "Packaging Trading Floor..."
rm -rf $TEMP && mkdir -p $TEMP

# Copy trading package
cp -r backend/agents/trading/* $TEMP/

# Install Linux-compatible binaries for Lambda
pip install yfinance boto3 \
  --target $TEMP/ \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --quiet 2>/dev/null

find $TEMP -name "*.pyc" -delete 2>/dev/null || true
find $TEMP -name "*.zip" -delete 2>/dev/null || true

cd $TEMP && zip -r /tmp/trading_package.zip . > /dev/null && cd -
SIZE=$(ls -lh /tmp/trading_package.zip | awk '{print $5}')
echo "Size: $SIZE"

# Upload to S3
echo "Uploading to S3..."
aws s3 cp /tmp/trading_package.zip s3://$BUCKET/lambdas/trading_package.zip --region $REGION
echo "  OK uploaded to S3"

# Deploy orchestrator from S3
echo "Deploying alex-trading-orchestrator..."
aws lambda update-function-code \
  --function-name alex-trading-orchestrator \
  --s3-bucket $BUCKET \
  --s3-key lambdas/trading_package.zip \
  --region $REGION > /dev/null
aws lambda wait function-updated --function-name alex-trading-orchestrator --region $REGION
aws lambda update-function-configuration \
  --function-name alex-trading-orchestrator \
  --handler core.orchestrator.lambda_handler \
  --region $REGION > /dev/null
aws lambda wait function-updated --function-name alex-trading-orchestrator --region $REGION
echo "  OK orchestrator deployed"

# Deploy debate agent from S3
echo "Deploying alex-debate-agent..."
aws lambda update-function-code \
  --function-name alex-debate-agent \
  --s3-bucket $BUCKET \
  --s3-key lambdas/trading_package.zip \
  --region $REGION > /dev/null
aws lambda wait function-updated --function-name alex-debate-agent --region $REGION
aws lambda update-function-configuration \
  --function-name alex-debate-agent \
  --handler core.debate_agent.lambda_handler \
  --region $REGION > /dev/null
aws lambda wait function-updated --function-name alex-debate-agent --region $REGION
echo "  OK debate agent deployed"

echo ""
echo "Trading Floor deployed!"
