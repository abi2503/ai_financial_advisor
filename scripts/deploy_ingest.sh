#!/bin/bash
# Deploy alex-ingest Lambda (pgvector backend with P0 user_id/session_id columns)
set -e
cd "$(dirname "$0")/.."

REGION="${DEFAULT_AWS_REGION:-us-east-1}"
TEMP="backend/ingest/tmp_pgvector"
ZIP="backend/ingest/lambda_pgvector.zip"

echo "📦 Packaging alex-ingest (pgvector)..."
rm -rf "$TEMP" "$ZIP"
mkdir -p "$TEMP"

pip install boto3 \
  --target "$TEMP" \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --quiet 2>/dev/null

cp backend/ingest/ingest_pgvector.py "$TEMP/ingest.py"
cp backend/ingest/rag_utils.py "$TEMP/rag_utils.py"
find "$TEMP" -name "*.pyc" -delete 2>/dev/null || true

(cd "$TEMP" && zip -r "../lambda_pgvector.zip" . > /dev/null)
rm -rf "$TEMP"
SIZE=$(ls -lh "$ZIP" | awk '{print $5}')
echo "  Size: $SIZE"

echo "🚀 Deploying alex-ingest..."
aws lambda update-function-code \
  --function-name alex-ingest \
  --zip-file "fileb://$ZIP" \
  --region "$REGION" > /dev/null
aws lambda wait function-updated --function-name alex-ingest --region "$REGION"
echo "✅ alex-ingest deployed (handler: ingest.lambda_handler, backend: pgvector)"
