#!/usr/bin/env python3
"""
Alex AI — Vector Store Migration Script
Switches between S3 Vectors and pgvector on Aurora

Usage:
  python3 scripts/migrate_vectors.py --to pgvector    # Switch to Aurora
  python3 scripts/migrate_vectors.py --to s3vectors   # Switch back
  python3 scripts/migrate_vectors.py --status         # Current backend
  python3 scripts/migrate_vectors.py --sync           # Copy S3→Aurora
"""
import os
import sys
import json
import boto3
import argparse
import subprocess
from datetime import datetime, timezone

# ============================================
# Config
# ============================================
REGION          = "us-east-1"
CLUSTER_ARN     = "arn:aws:rds:us-east-1:381491881089:cluster:alex-aurora"
SECRET_ARN      = "arn:aws:secretsmanager:us-east-1:381491881089:secret:alex/aurora/credentials-2HP8fm"
DB_NAME         = "alex_db"
VECTOR_BUCKET   = "alex-vectors-381491881089"
INGEST_API      = "https://bmzmoxxehh.execute-api.us-east-1.amazonaws.com/prod/ingest"
INGEST_API_KEY  = "7h5IOpLsxU1CGoSE5AqQY6guMlqPcP113LxVqNUu"
SSM_BACKEND_KEY = "/alex/vector_backend"
LAMBDA_NAME     = "alex-ingest"

rds = boto3.client('rds-data', region_name=REGION)
ssm = boto3.client('ssm',      region_name=REGION)
lmb = boto3.client('lambda',   region_name=REGION)

UTC = timezone.utc


def execute_sql(sql: str, params: list = None) -> dict:
    kwargs = {
        "resourceArn": CLUSTER_ARN,
        "secretArn":   SECRET_ARN,
        "database":    DB_NAME,
        "sql":         sql,
    }
    if params:
        kwargs["parameters"] = params
    return rds.execute_statement(**kwargs)


def get_current_backend() -> str:
    try:
        r = ssm.get_parameter(Name=SSM_BACKEND_KEY)
        return r["Parameter"]["Value"]
    except Exception:
        return "s3vectors"


def set_backend(backend: str):
    ssm.put_parameter(
        Name      = SSM_BACKEND_KEY,
        Value     = backend,
        Type      = "String",
        Overwrite = True
    )
    print(f"  ✅ SSM {SSM_BACKEND_KEY} = {backend}")


def update_lambda_env(backend: str):
    try:
        config = lmb.get_function_configuration(FunctionName=LAMBDA_NAME)
        env    = config.get("Environment", {}).get("Variables", {})
        env["VECTOR_BACKEND"] = backend
        env["DB_CLUSTER_ARN"] = CLUSTER_ARN
        env["DB_SECRET_ARN"]  = SECRET_ARN
        env["DB_NAME"]        = DB_NAME
        lmb.update_function_configuration(
            FunctionName = LAMBDA_NAME,
            Environment  = {"Variables": env}
        )
        print(f"  ✅ Lambda {LAMBDA_NAME} → VECTOR_BACKEND={backend}")
    except Exception as e:
        print(f"  ⚠️  Lambda update failed: {e}")


def test_pgvector() -> bool:
    try:
        execute_sql("SELECT COUNT(*) FROM research_vectors")
        return True
    except Exception as e:
        print(f"  ❌ pgvector test failed: {e}")
        return False


def test_s3vectors() -> bool:
    try:
        result = subprocess.run([
            "curl", "-s", "-X", "POST",
            f"{INGEST_API.replace('/ingest', '/search')}",
            "-H", "Content-Type: application/json",
            "-H", f"x-api-key: {INGEST_API_KEY}",
            "-d", json.dumps({"query": "test", "top_k": 1})
        ], capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        return "results" in data
    except Exception as e:
        print(f"  ❌ S3 Vectors test failed: {e}")
        return False


def count_pgvector() -> int:
    try:
        r = execute_sql("SELECT COUNT(*) FROM research_vectors")
        return r["records"][0][0]["longValue"]
    except Exception:
        return 0


def sync_s3_to_pgvector():
    print("\n  Syncing S3 Vectors → pgvector...")
    topics = [
        "NVIDIA analysis", "Apple analysis", "Tesla analysis",
        "Microsoft analysis", "stock market", "SEC filing",
        "financial research", "earnings", "crypto", "Fed rate"
    ]
    synced = 0
    seen   = set()
    for topic in topics:
        try:
            result = subprocess.run([
                "curl", "-s", "-X", "POST",
                f"{INGEST_API.replace('/ingest', '/search')}",
                "-H", "Content-Type: application/json",
                "-H", f"x-api-key: {INGEST_API_KEY}",
                "-d", json.dumps({"query": topic, "top_k": 10})
            ], capture_output=True, text=True, timeout=30)
            data    = json.loads(result.stdout)
            results = data.get("results", [])
            for r in results:
                vid = r.get("id")
                if vid in seen:
                    continue
                seen.add(vid)
                content   = r.get("content", "")
                topic_str = r.get("topic", "")
                source    = r.get("source", "alex-researcher")
                if not content or not topic_str:
                    continue
                try:
                    execute_sql(
                        """
                        INSERT INTO research_vectors (topic, content, source)
                        VALUES (:topic, :content, :source)
                        ON CONFLICT DO NOTHING
                        """,
                        [
                            {"name": "topic",   "value": {"stringValue": topic_str[:200]}},
                            {"name": "content", "value": {"stringValue": content[:5000]}},
                            {"name": "source",  "value": {"stringValue": source}},
                        ]
                    )
                    synced += 1
                except Exception as e:
                    print(f"    ⚠️  Skip {topic_str[:30]}: {e}")
        except Exception as e:
            print(f"    ⚠️  Search failed for {topic}: {e}")
    print(f"  ✅ Synced {synced} vectors to pgvector")
    return synced


def wait_for_lambda():
    print("  Waiting for Lambda to be ready...")
    lam     = boto3.client("lambda", region_name=REGION)
    waiter  = lam.get_waiter('function_updated')
    waiter.wait(FunctionName=LAMBDA_NAME)
    print("  ✅ Lambda ready")


def deploy_pgvector_lambda():
    """Deploy pgvector version of ingest Lambda with Aurora retry logic"""
    wait_for_lambda()

    pgvector_code = '''
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
'''

    import shutil
    import zipfile

    pgvector_path = "backend/ingest/ingest_pgvector.py"
    with open(pgvector_path, "w") as f:
        f.write(pgvector_code)

    os.makedirs("backend/ingest/tmp_pgvector", exist_ok=True)
    shutil.copy(pgvector_path, "backend/ingest/tmp_pgvector/ingest.py")

    zip_path = "backend/ingest/lambda_pgvector.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk("backend/ingest/tmp_pgvector"):
            for file in files:
                fp   = os.path.join(root, file)
                arcn = os.path.relpath(fp, "backend/ingest/tmp_pgvector")
                zf.write(fp, arcn)

    shutil.rmtree("backend/ingest/tmp_pgvector")

    lam = boto3.client("lambda", region_name=REGION)
    with open(zip_path, "rb") as f:
        lam.update_function_code(
            FunctionName = LAMBDA_NAME,
            ZipFile      = f.read()
        )
    print("  ✅ pgvector Lambda deployed")


def deploy_s3vectors_lambda():
    """Redeploy original S3 Vectors Lambda"""
    wait_for_lambda()
    result = subprocess.run(
        ["bash", "backend/ingest/package.sh"],
        capture_output=True, text=True
    )
    lam = boto3.client("lambda", region_name=REGION)
    with open("backend/ingest/lambda_function.zip", "rb") as f:
        lam.update_function_code(
            FunctionName = LAMBDA_NAME,
            ZipFile      = f.read()
        )
    print("  ✅ S3 Vectors Lambda redeployed")


def migrate_to_pgvector():
    print("\n🔄 Migrating to pgvector (Aurora)")
    print("=" * 40)

    print("\nStep 1: Testing pgvector connection...")
    if not test_pgvector():
        print("  ❌ pgvector not ready")
        sys.exit(1)
    print("  ✅ pgvector ready")

    print("\nStep 2: Syncing existing data...")
    synced = sync_s3_to_pgvector()

    print("\nStep 3: Updating Lambda environment...")
    update_lambda_env("pgvector")

    print("\nStep 4: Updating SSM parameter...")
    set_backend("pgvector")

    print("\nStep 5: Deploying pgvector Lambda...")
    deploy_pgvector_lambda()

    print("\n" + "=" * 40)
    print("✅ Migration to pgvector complete!")
    print(f"   Vectors synced: {synced}")
    print(f"   Cost saving:    ~$350/month")
    print(f"\n   To stop billing delete S3 Vectors:")
    print(f"   aws s3 rb s3://{VECTOR_BUCKET} --force")


def migrate_to_s3vectors():
    print("\n🔄 Migrating back to S3 Vectors")
    print("=" * 40)

    print("\nStep 1: Testing S3 Vectors...")
    if not test_s3vectors():
        print("  ❌ S3 Vectors not accessible")
        sys.exit(1)
    print("  ✅ S3 Vectors ready")

    print("\nStep 2: Updating Lambda environment...")
    update_lambda_env("s3vectors")

    print("\nStep 3: Updating SSM parameter...")
    set_backend("s3vectors")

    print("\nStep 4: Deploying S3 Vectors Lambda...")
    deploy_s3vectors_lambda()

    print("\n" + "=" * 40)
    print("✅ Migration back to S3 Vectors complete!")
    print(f"   ⚠️  Note: S3 Vectors costs ~$350/month baseline")


def show_status():
    backend = get_current_backend()
    print("\n📊 Vector Store Status")
    print("=" * 40)
    print(f"  Current backend: {backend}")
    if backend == "pgvector":
        count = count_pgvector()
        print(f"  Vectors stored:  {count}")
        print(f"  Cost:            ~$0/month idle")
    else:
        print(f"  S3 Vectors:      {VECTOR_BUCKET}")
        print(f"  Cost:            ~$350/month baseline")
    print("\n  Switch commands:")
    print("  python3 scripts/migrate_vectors.py --to pgvector")
    print("  python3 scripts/migrate_vectors.py --to s3vectors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alex AI Vector Store Migration")
    parser.add_argument("--to",     choices=["pgvector", "s3vectors"])
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--sync",   action="store_true")
    args = parser.parse_args()

    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

    if args.status:
        show_status()
    elif args.sync:
        sync_s3_to_pgvector()
    elif args.to == "pgvector":
        migrate_to_pgvector()
    elif args.to == "s3vectors":
        migrate_to_s3vectors()
    else:
        show_status()