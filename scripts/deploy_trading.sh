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

# Install Linux-compatible binaries for Lambda (Python 3.12 on x86_64)
pip install yfinance boto3 pydantic \
  --target $TEMP/ \
  --platform manylinux2014_x86_64 \
  --python-version 3.12 \
  --implementation cp \
  --only-binary=:all: \
  --quiet 2>/dev/null || {
  echo "Binary install failed — retrying without only-binary for pydantic..."
  pip install yfinance boto3 pydantic \
    --target $TEMP/ \
    --platform manylinux2014_x86_64 \
    --python-version 3.12 \
    --implementation cp \
    --quiet
}

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

# Deploy trade evaluator (outcome-based eval)
if aws lambda get-function --function-name alex-trade-evaluator --region $REGION > /dev/null 2>&1; then
  echo "Deploying alex-trade-evaluator..."
  aws lambda update-function-code \
    --function-name alex-trade-evaluator \
    --s3-bucket $BUCKET \
    --s3-key lambdas/trading_package.zip \
    --region $REGION > /dev/null
  aws lambda wait function-updated --function-name alex-trade-evaluator --region $REGION
  aws lambda update-function-configuration \
    --function-name alex-trade-evaluator \
    --handler learning.trade_evaluator.lambda_handler \
    --region $REGION > /dev/null
  aws lambda wait function-updated --function-name alex-trade-evaluator --region $REGION
  echo "  OK trade evaluator deployed"
else
  echo "  ⏭ alex-trade-evaluator not found — run terraform apply in terraform/9_trading_floor first"
fi

echo ""
echo "Trading Floor deployed!"
