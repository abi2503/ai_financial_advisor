# Run this locally: python test_embedding.py
import boto3
import json

client = boto3.client('sagemaker-runtime', region_name='us-east-1')

response = client.invoke_endpoint(
    EndpointName='alex-embedding',
    Body=json.dumps({"inputs": ["test text"]}),
    ContentType='application/json'
)

result = json.loads(response['Body'].read())

print(f"Type of result:       {type(result)}")
print(f"Length of result:     {len(result)}")
print(f"Type of result[0]:    {type(result[0])}")
print(f"Type of result[0][0]: {type(result[0][0])}")
print(f"Type of result[0][0][0]: {type(result[0][0][0])}")