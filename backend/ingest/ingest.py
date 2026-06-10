import os
import json
import boto3
import uuid
import logging
from datetime import datetime, UTC

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sagemaker_runtime_client = boto3.client('sagemaker-runtime')
s3_vectors_client = boto3.client('s3vectors')

VECTOR_BUCKET      = os.environ["VECTOR_BUCKET"]
SAGEMAKER_ENDPOINT = os.environ["SAGEMAKER_ENDPOINT"]
INDEX_NAME         = "financial-research"


def get_embeddings(text: str) -> list[float]:
    """Call SageMaker endpoint to convert text to vector."""
    if len(text) > 300:
        text = text[:300]
        print(f"Truncated to 300 chars for embedding")

    logger.info(f"Calling SageMaker endpoint: {SAGEMAKER_ENDPOINT}")

    response = sagemaker_runtime_client.invoke_endpoint(
        EndpointName = SAGEMAKER_ENDPOINT,
        Body         = json.dumps({"inputs": text}),
        ContentType  = 'application/json'
    )

    result = json.loads(response['Body'].read())

    # When input is string: result shape is [N, 384]
    # result[0] = first token vector of size 384
    # Mean pool across all token vectors
    token_embeddings = result[0]  # ← changed from result[0][0]
    num_tokens       = len(token_embeddings)
    vector_size      = len(token_embeddings[0])

    logger.info(f"num_tokens: {num_tokens}, vector_size: {vector_size}")

    vector = [
        sum(token_embeddings[t][i] for t in range(num_tokens)) / num_tokens
        for i in range(vector_size)
    ]

    logger.info(f"Final vector size: {len(vector)}")
    return vector

def lambda_handler(event, context):
    """
    Main Lambda handler.
    Accepts POST with JSON body: {"content": "text", "topic": "label"}
    """

    logger.info(f"Received event: {event}")

    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid JSON body'})
        }

    content = body.get('content', '').strip()
    topic   = body.get('topic', 'general')

    if not content:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'content field is required'})
        }

    logger.info(f"Generating embedding for topic: {topic}")
    vector = get_embeddings(content)

    vector_id = str(uuid.uuid4())

    s3_vectors_client.put_vectors(
    vectorBucketName=VECTOR_BUCKET,
    indexName=INDEX_NAME,
    vectors=[
        {
            "key":  vector_id,
            "data": {"float32": vector},
            "metadata": {
                # Truncate content for metadata (2048 byte limit)
                # Full content stored in embedding — metadata is for filtering
                "content":   content[:500],
                "topic":     topic[:200],
                "timestamp": datetime.now(UTC).isoformat(),
                "source":    "alex-researcher"
            }
        }
    ]
)

    logger.info(f"Stored vector {vector_id} for topic: {topic}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message":   "Successfully ingested",
            "vector_id": vector_id,
            "topic":     topic
        })
    }
