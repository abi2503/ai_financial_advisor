
import os
import sys
import json
import time
import boto3
import uuid
import logging
from datetime import datetime, timezone

UTC    = timezone.utc
logger = logging.getLogger()
logger.setLevel(logging.INFO)

sagemaker_runtime = boto3.client("sagemaker-runtime")
rds_client        = boto3.client("rds-data", region_name="us-east-1")

SAGEMAKER_ENDPOINT = os.environ["SAGEMAKER_ENDPOINT"]
CLUSTER_ARN        = os.environ["DB_CLUSTER_ARN"]
SECRET_ARN         = os.environ["DB_SECRET_ARN"]
DB_NAME            = os.environ.get("DB_NAME", "alex_db")
VECTOR_BACKEND     = os.environ.get("VECTOR_BACKEND", "pgvector")


def execute_with_retry(sql, parameters=None, retries=3):
    """
    Execute SQL with retry for Aurora cold starts.
    Aurora Serverless v2 at min_capacity=0 auto-pauses.
    DatabaseResumingException = Aurora waking up, wait and retry.
    """
    kwargs = {
        "resourceArn": CLUSTER_ARN,
        "secretArn":   SECRET_ARN,
        "database":    DB_NAME,
        "sql":         sql,
    }
    if parameters:
        kwargs["parameters"] = parameters

    for i in range(retries):
        try:
            return rds_client.execute_statement(**kwargs)
        except Exception as e:
            if "DatabaseResumingException" in str(e) and i < retries - 1:
                wait = 30 * (i + 1)
                logger.info(f"Aurora resuming — waiting {wait}s (attempt {i+1}/{retries})")
                time.sleep(wait)
            else:
                raise

    raise Exception("Aurora failed to resume after maximum retries")


def get_embeddings(text: str) -> list:
    """Generate embeddings via SageMaker all-MiniLM-L6-v2"""
    if len(text) > 300:
        text = text[:300]
    response         = sagemaker_runtime.invoke_endpoint(
        EndpointName = SAGEMAKER_ENDPOINT,
        Body         = json.dumps({"inputs": text}),
        ContentType  = "application/json"
    )
    result           = json.loads(response["Body"].read())
    token_embeddings = result[0]
    num_tokens       = len(token_embeddings)
    vector_size      = len(token_embeddings[0])
    vector = [
        sum(token_embeddings[t][i] for t in range(num_tokens)) / num_tokens
        for i in range(vector_size)
    ]
    return vector


def handle_ingest_pgvector(body: dict) -> dict:
    content = body.get("content", "").strip()
    topic   = body.get("topic", "general")
    if not content:
        return {"statusCode": 400, "body": json.dumps({"error": "content required"})}

    logger.info(f"Ingesting to pgvector: {topic}")
    vector     = get_embeddings(content)
    vector_id  = str(uuid.uuid4())
    vector_str = "[" + ",".join(str(v) for v in vector) + "]"

    execute_with_retry(
        """
        INSERT INTO research_vectors
          (id, topic, content, embedding, source)
        VALUES
          (:id::uuid, :topic, :content, :embedding::vector, :source)
        """,
        [
            {"name": "id",        "value": {"stringValue": vector_id}},
            {"name": "topic",     "value": {"stringValue": topic[:200]}},
            {"name": "content",   "value": {"stringValue": content[:5000]}},
            {"name": "embedding", "value": {"stringValue": vector_str}},
            {"name": "source",    "value": {"stringValue": "alex-researcher"}},
        ]
    )

    logger.info(f"Stored vector {vector_id} in pgvector")
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message":   "Successfully ingested",
            "vector_id": vector_id,
            "topic":     topic,
            "backend":   "pgvector"
        })
    }


def handle_search_pgvector(body: dict) -> dict:
    query = body.get("query", "").strip()
    top_k = int(body.get("top_k", 5))
    if not query:
        return {"statusCode": 400, "body": json.dumps({"error": "query required"})}

    logger.info(f"Searching pgvector: {query}")
    query_vector = get_embeddings(query)
    vector_str   = "[" + ",".join(str(v) for v in query_vector) + "]"

    response = execute_with_retry(
        """
        SELECT
            id::text,
            topic,
            content,
            source,
            created_at::text,
            1 - (embedding <=> :query_vec::vector) AS score
        FROM research_vectors
        ORDER BY embedding <=> :query_vec::vector
        LIMIT :top_k
        """,
        [
            {"name": "query_vec", "value": {"stringValue": vector_str}},
            {"name": "top_k",     "value": {"longValue": top_k}},
        ]
    )

    results = [
        {
            "id":        r[0]["stringValue"],
            "topic":     r[1]["stringValue"],
            "content":   r[2]["stringValue"],
            "source":    r[3]["stringValue"],
            "timestamp": r[4]["stringValue"],
            "score":     round(r[5]["doubleValue"], 4),
        }
        for r in response.get("records", [])
    ]

    logger.info(f"Found {len(results)} results")
    return {
        "statusCode": 200,
        "body": json.dumps({
            "query":   query,
            "results": results,
            "count":   len(results),
            "backend": "pgvector"
        })
    }


def lambda_handler(event, context):
    logger.info(f"Backend: {VECTOR_BACKEND}")
    path   = event.get("path", "/ingest")
    method = event.get("httpMethod", "POST")

    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers":    {"Content-Type": "application/json"},
            "body":       json.dumps({"error": "Invalid JSON"})
        }

    if path == "/search" and method == "POST":
        result = handle_search_pgvector(body)
    elif path == "/ingest" and method == "POST":
        result = handle_ingest_pgvector(body)
    else:
        result = {
            "statusCode": 404,
            "body":       json.dumps({"error": f"Unknown path: {path}"})
        }

    result["headers"] = {
        "Content-Type":                "application/json",
        "Access-Control-Allow-Origin": "*"
    }
    return result
