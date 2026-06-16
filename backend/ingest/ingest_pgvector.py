
import os
import sys
import json
import time
import boto3
import uuid
import logging
from datetime import datetime, timezone
from botocore.exceptions import ClientError

from rag_utils import chunk_content

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


def _resolve_db_user_id(clerk_id: str) -> str | None:
    """Map Clerk ID → Aurora users.id UUID for scoped vectors."""
    if not clerk_id:
        return None
    try:
        resp = execute_with_retry(
            "SELECT id::text FROM users WHERE clerk_id = :clerk_id LIMIT 1",
            [{"name": "clerk_id", "value": {"stringValue": clerk_id}}],
        )
        rows = resp.get("records", [])
        if rows:
            return rows[0][0].get("stringValue")
    except Exception as e:
        logger.warning(f"Could not resolve user_id for {clerk_id}: {e}")
    return None


def get_embeddings(text: str, retries: int = 5) -> list:
    """Generate embeddings via SageMaker all-MiniLM-L6-v2 (with throttle retry)."""
    if len(text) > 300:
        text = text[:300]
    last_err = None
    for attempt in range(retries):
        try:
            response         = sagemaker_runtime.invoke_endpoint(
                EndpointName = SAGEMAKER_ENDPOINT,
                Body         = json.dumps({"inputs": text}),
                ContentType  = "application/json"
            )
            result           = json.loads(response["Body"].read())
            token_embeddings = result[0]
            num_tokens       = len(token_embeddings)
            vector_size      = len(token_embeddings[0])
            return [
                sum(token_embeddings[t][i] for t in range(num_tokens)) / num_tokens
                for i in range(vector_size)
            ]
        except ClientError as e:
            last_err = e
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("ThrottlingException", "ServiceUnavailable") and attempt < retries - 1:
                wait = min(8, 2 ** attempt)
                logger.warning(f"SageMaker throttle — retry {attempt + 1}/{retries} in {wait}s")
                time.sleep(wait)
                continue
            raise
    raise last_err or RuntimeError("embedding failed")


def _insert_vector(body: dict, content: str, chunk_index: int) -> str:
    topic        = body.get("topic", "general")
    session_id   = (body.get("session_id") or "")[:36]
    clerk_id     = body.get("user_id") or body.get("clerk_id") or ""
    db_user_id   = _resolve_db_user_id(clerk_id) if clerk_id else None
    query_text   = (body.get("query") or "")[:500]
    chunk_type   = (body.get("chunk_type") or "document")[:30]

    vector     = get_embeddings(content)
    vector_id  = str(uuid.uuid4())
    vector_str = "[" + ",".join(str(v) for v in vector) + "]"

    params = [
        {"name": "id",          "value": {"stringValue": vector_id}},
        {"name": "topic",       "value": {"stringValue": topic[:200]}},
        {"name": "content",     "value": {"stringValue": content[:5000]}},
        {"name": "embedding",   "value": {"stringValue": vector_str}},
        {"name": "source",      "value": {"stringValue": body.get("source", "alex-researcher")[:100]}},
        {"name": "session_id",  "value": {"stringValue": session_id}},
        {"name": "chunk_index", "value": {"longValue":   chunk_index}},
        {"name": "query",       "value": {"stringValue": query_text}},
        {"name": "chunk_type",  "value": {"stringValue": chunk_type}},
    ]
    if db_user_id:
        params.append({"name": "user_id", "value": {"stringValue": db_user_id}})

    user_col = ", user_id" if db_user_id else ""
    user_val = ", :user_id::uuid" if db_user_id else ""

    execute_with_retry(
        f"""
        INSERT INTO research_vectors
          (id, topic, content, embedding, source, session_id, chunk_index, query, chunk_type{user_col})
        VALUES
          (:id::uuid, :topic, :content, :embedding::vector, :source, :session_id, :chunk_index, :query, :chunk_type{user_val})
        """,
        params,
    )
    return vector_id


def handle_ingest_pgvector(body: dict) -> dict:
    content = body.get("content", "").strip()
    topic   = body.get("topic", "general")
    if not content:
        return {"statusCode": 400, "body": json.dumps({"error": "content required"})}

    chunks = chunk_content(content)
    logger.info(f"Ingesting to pgvector: {topic} — {len(chunks)} chunk(s)")

    vector_ids = []
    for i, chunk in enumerate(chunks):
        if i > 0:
            time.sleep(0.25)  # gentle pacing for SageMaker serverless
        vid = _insert_vector(body, chunk, chunk_index=i)
        vector_ids.append(vid)
        logger.info(f"Stored chunk {i + 1}/{len(chunks)} → {vid}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message":    "Successfully ingested",
            "vector_id":  vector_ids[0],
            "vector_ids": vector_ids,
            "chunks":     len(chunks),
            "topic":      topic,
            "backend":    "pgvector",
        }),
    }


def handle_search_pgvector(body: dict) -> dict:
    query = body.get("query", "").strip()
    top_k = int(body.get("top_k", 5))
    if not query:
        return {"statusCode": 400, "body": json.dumps({"error": "query required"})}

    try:
        logger.info(f"Searching pgvector: {query}")
        query_vector = get_embeddings(query)
        vector_str   = "[" + ",".join(str(v) for v in query_vector) + "]"

        response = execute_with_retry(
            """
            SELECT id::text, topic, content, source, created_at::text, score
            FROM (
                SELECT
                    id, topic, content, source, created_at,
                    (1 - (embedding <=> :query_vec::vector)) AS score
                FROM research_vectors
                WHERE embedding IS NOT NULL
                  AND topic NOT ILIKE '%debug test%'
            ) ranked
            ORDER BY score DESC
            LIMIT :top_k
            """,
            [
                {"name": "query_vec", "value": {"stringValue": vector_str}},
                {"name": "top_k",     "value": {"longValue": top_k}},
            ],
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
                "backend": "pgvector",
            }),
        }
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "ClientError")
        logger.error(f"Search failed ({code}): {e}")
        return {
            "statusCode": 503,
            "body": json.dumps({
                "error":   f"Embedding service busy ({code}) — retry shortly",
                "query":   query,
                "results": [],
                "count":   0,
                "backend": "pgvector",
            }),
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error":   str(e)[:200],
                "query":   query,
                "results": [],
                "count":   0,
                "backend": "pgvector",
            }),
        }


def lambda_handler(event, context):
    logger.info(f"Backend: {VECTOR_BACKEND}")
    path   = (event.get("path") or event.get("rawPath") or "/ingest").split("?")[0]
    if not path.startswith("/"):
        path = "/" + path
    # API Gateway stage paths: /prod/search → /search
    for part in ("/prod", "/dev", "/staging"):
        if path.startswith(part + "/"):
            path = path[len(part):]
    method = event.get("httpMethod", "POST")

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers":    {"Content-Type": "application/json"},
            "body":       json.dumps({"error": "Invalid JSON"}),
        }

    try:
        if path.endswith("/search") and method == "POST":
            result = handle_search_pgvector(body)
        elif path.endswith("/ingest") and method == "POST":
            result = handle_ingest_pgvector(body)
        else:
            result = {
                "statusCode": 404,
                "body":       json.dumps({"error": f"Unknown path: {path}"}),
            }
    except Exception as e:
        logger.exception("Unhandled error")
        result = {
            "statusCode": 500,
            "body":       json.dumps({"error": str(e)[:200]}),
        }

    result["headers"] = {
        "Content-Type":                "application/json",
        "Access-Control-Allow-Origin": "*",
    }
    return result
