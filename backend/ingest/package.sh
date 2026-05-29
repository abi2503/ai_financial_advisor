#!/bin/bash
cd backend/ingest
pip install boto3 -t ./package
cp ingest.py ./package/
cd package
zip -r ../lambda_function.zip .
cd ..
rm -rf package
echo "✅ Lambda packaged successfully"