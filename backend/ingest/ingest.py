import os
import json
import boto3
import uuid
import logging
from datetime import datetime, UTC

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sagemaker_runtime_client = boto3.client('sagemaker-runtime')
s3_vectors_client        = boto3.client('s3vectors')

VECTOR_BUCKET      = os.environ["VECTOR_BUCKET"]
SAGEMAKER_ENDPOINT = os.environ["SAGEMAKER_ENDPOINT"]
INDEX_NAME         = "financial-research"


def get_embeddings(text: str) -> list[float]:
    """
    Call SageMaker endpoint to convert text to vector.
    Max 512 tokens — truncate to 300 chars to be safe.
    """
    if len(text) > 300:
        text = text[:300]
        print(f"Truncated to 300 chars for embedding")

    logger.info(f"Calling SageMaker endpoint: {SAGEMAKER_ENDPOINT}")

    response = sagemaker_runtime_client.invoke_endpoint(
        EndpointName = SAGEMAKER_ENDPOINT,
        Body         = json.dumps({"inputs": text}),
        ContentType  = 'application/json'
    )

    result           = json.loads(response['Body'].read())
    token_embeddings = result[0]
    num_tokens       = len(token_embeddings)
    vector_size      = len(token_embeddings[0])

    logger.info(f"num_tokens: {num_tokens}, vector_size: {vector_size}")

    vector = [
        sum(token_embeddings[t][i] for t in range(num_tokens)) / num_tokens
        for i in range(vector_size)
    ]

    logger.info(f"Final vector size: {len(vector)}")
    return vector


def handle_ingest(body: dict) -> dict:
    """
    Ingest a document into S3 Vectors.
    Requires: content, topic
    """
    content = body.get('content', '').strip()
    topic   = body.get('topic', 'general')

    if not content:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'content field is required'})
        }

    logger.info(f"Generating embedding for topic: {topic}")
    vector    = get_embeddings(content)
    vector_id = str(uuid.uuid4())

    s3_vectors_client.put_vectors(
        vectorBucketName = VECTOR_BUCKET,
        indexName        = INDEX_NAME,
        vectors=[{
            "key":  vector_id,
            "data": {"float32": vector},
            "metadata": {
                "content":   content[:500],
                "topic":     topic[:200],
                "timestamp": datetime.now(UTC).isoformat(),
                "source":    "alex-researcher"
            }
        }]
    )

    logger.info(f"Stored vector {vector_id} for topic: {topic}")
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message':   'Successfully ingested',
            'vector_id': vector_id,
            'topic':     topic
        })
    }


def handle_search(body: dict) -> dict:
    """
    Search S3 Vectors using semantic similarity.
    Requires: query
    Optional: top_k (default 5)

    Why semantic search:
      User searches "NVIDIA earnings"
      Finds: "NVDA Q4 analysis", "Jensen Huang AI chips"
      Not just keyword matching — meaning-based
    """
    query = body.get('query', '').strip()
    top_k = int(body.get('top_k', 5))

    if not query:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'query field is required'})
        }

    logger.info(f"Searching for: {query} (top_k={top_k})")

    # Embed the query using same model as documents
    query_vector = get_embeddings(query)

    # Search S3 Vectors
    response = s3_vectors_client.query_vectors(
        vectorBucketName = VECTOR_BUCKET,
        indexName        = INDEX_NAME,
        queryVector      = {"float32": query_vector},
        topK             = top_k,
        returnMetadata   = True,
        returnDistance   = True,
    )

    results = []
    for match in response.get('vectors', []):
        metadata = match.get('metadata', {})
        results.append({
            'id':        match.get('key', ''),
            'score':     round(1 - match.get('distance', 1), 4),
            'topic':     metadata.get('topic', ''),
            'content':   metadata.get('content', ''),
            'timestamp': metadata.get('timestamp', ''),
            'source':    metadata.get('source', '')
        })

    logger.info(f"Found {len(results)} results for: {query}")
    return {
        'statusCode': 200,
        'body': json.dumps({
            'query':   query,
            'results': results,
            'count':   len(results)
        })
    }


def lambda_handler(event, context):
    """
    Main Lambda handler.
    Routes to ingest or search based on path.

    POST /ingest → store document in S3 Vectors
    POST /search → semantic search S3 Vectors
    """
    logger.info(f"Received event: {event}")

    path   = event.get('path', '/ingest')
    method = event.get('httpMethod', 'POST')

    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers':    {'Content-Type': 'application/json'},
            'body':       json.dumps({'error': 'Invalid JSON body'})
        }

    # Route to correct handler
    if path == '/search' and method == 'POST':
        result = handle_search(body)
    elif path == '/ingest' and method == 'POST':
        result = handle_ingest(body)
    else:
        result = {
            'statusCode': 404,
            'body': json.dumps({'error': f'Unknown path: {path}'})
        }

    # Add CORS headers
    result['headers'] = {
        'Content-Type':                'application/json',
        'Access-Control-Allow-Origin': '*'
    }

    return result