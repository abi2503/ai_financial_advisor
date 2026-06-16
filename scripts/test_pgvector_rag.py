#!/usr/bin/env python3
"""
Step-by-step pgvector + Aurora RAG verification.

Usage:
  python3 scripts/test_pgvector_rag.py              # all steps
  python3 scripts/test_pgvector_rag.py --step 3     # single step
  python3 scripts/test_pgvector_rag.py --search "NVDA earnings risk"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import boto3

REGION      = os.environ.get("AWS_REGION", "us-east-1")
CLUSTER_ARN = os.environ.get(
    "DB_CLUSTER_ARN",
    "arn:aws:rds:us-east-1:381491881089:cluster:alex-aurora",
)
SECRET_ARN  = os.environ.get(
    "DB_SECRET_ARN",
    "arn:aws:secretsmanager:us-east-1:381491881089:secret:alex/aurora/credentials-2HP8fm",
)
DB_NAME     = os.environ.get("DB_NAME", "alex_db")
SAGEMAKER_EP = os.environ.get("SAGEMAKER_ENDPOINT", "alex-embedding")
INGEST_API  = os.environ.get(
    "ALEX_API_ENDPOINT",
    os.environ.get("NEXT_PUBLIC_ALEX_API", ""),
).rstrip("/")
API_KEY     = os.environ.get("ALEX_API_KEY", "")

rds  = boto3.client("rds-data", region_name=REGION)
sage = boto3.client("sagemaker", region_name=REGION)
smrt = boto3.client("sagemaker-runtime", region_name=REGION)
lmb  = boto3.client("lambda", region_name=REGION)
ssm  = boto3.client("ssm", region_name=REGION)


def banner(step: int, title: str) -> None:
    print(f"\n{'='*60}")
    print(f"STEP {step}: {title}")
    print("=" * 60)


def sql(query: str, params: list | None = None, retries: int = 3) -> dict:
    kwargs = {
        "resourceArn": CLUSTER_ARN,
        "secretArn":   SECRET_ARN,
        "database":    DB_NAME,
        "sql":         query,
    }
    if params:
        kwargs["parameters"] = params
    for i in range(retries):
        try:
            return rds.execute_statement(**kwargs)
        except Exception as e:
            if "DatabaseResumingException" in str(e) and i < retries - 1:
                wait = 10 * (i + 1)
                print(f"  ⏳ Aurora resuming — wait {wait}s…")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Aurora query failed")


def val(row, idx: int):
    f = row[idx]
    if "stringValue" in f:
        return f["stringValue"]
    if "longValue" in f:
        return f["longValue"]
    if "doubleValue" in f:
        return f["doubleValue"]
    if "booleanValue" in f:
        return f["booleanValue"]
    if "isNull" in f and f["isNull"]:
        return None
    return None


def step1_aurora_ping() -> bool:
    banner(1, "Aurora DB connectivity")
    r = sql("SELECT 1 AS ok, current_database() AS db, version() AS ver")
    row = r["records"][0]
    print(f"  ✅ Connected to database: {val(row, 1)}")
    print(f"  PostgreSQL: {str(val(row, 2))[:80]}…")
    return True


def step2_pgvector_extension() -> bool:
    banner(2, "pgvector extension")
    r = sql("""
        SELECT extname, extversion
        FROM pg_extension
        WHERE extname = 'vector'
    """)
    if not r.get("records"):
        print("  ❌ pgvector extension NOT installed")
        return False
    row = r["records"][0]
    print(f"  ✅ pgvector installed — version {val(row, 1)}")
    return True


def step3_vector_inventory() -> dict:
    banner(3, "research_vectors inventory")
    stats = sql("""
        SELECT
          COUNT(*)::bigint AS total,
          COUNT(embedding)::bigint AS with_embedding,
          COUNT(*) FILTER (WHERE embedding IS NULL)::bigint AS null_embedding,
          MIN(created_at)::text AS oldest,
          MAX(created_at)::text AS newest
        FROM research_vectors
    """)
    row = stats["records"][0]
    out = {
        "total":          int(val(row, 0) or 0),
        "with_embedding": int(val(row, 1) or 0),
        "null_embedding": int(val(row, 2) or 0),
        "oldest":         val(row, 3),
        "newest":         val(row, 4),
    }
    print(f"  Total rows:        {out['total']}")
    print(f"  With embedding:    {out['with_embedding']}")
    print(f"  NULL embedding:    {out['null_embedding']}")
    print(f"  Date range:        {out['oldest']} → {out['newest']}")

    topics = sql("""
        SELECT topic, COUNT(*)::int AS cnt
        FROM research_vectors
        GROUP BY topic
        ORDER BY cnt DESC
        LIMIT 10
    """)
    print("\n  Top topics:")
    for row in topics.get("records", []):
        print(f"    • {val(row, 0) or '(null)'}: {val(row, 1)} chunks")

    samples = sql("""
        SELECT topic, LEFT(content, 120) AS preview, created_at::text, source
        FROM research_vectors
        ORDER BY created_at DESC
        LIMIT 5
    """)
    print("\n  Latest 5 chunks:")
    for row in samples.get("records", []):
        print(f"    [{val(row, 3)}] {val(row, 0)} @ {val(row, 2)}")
        print(f"      {val(row, 1)}…")

    ok = out["total"] > 0 and out["with_embedding"] > 0
    print(f"\n  {'✅' if ok else '⚠️'} Data {'present' if ok else 'missing or no embeddings'}")
    return out


def step4_backend_config() -> dict:
    banner(4, "Vector backend configuration")
    backend = "unknown"
    try:
        backend = ssm.get_parameter(Name="/alex/vector_backend")["Parameter"]["Value"]
        print(f"  SSM /alex/vector_backend = {backend}")
    except Exception as e:
        print(f"  ⚠️  SSM param missing: {e}")

    try:
        cfg = lmb.get_function_configuration(FunctionName="alex-ingest")
        env = cfg.get("Environment", {}).get("Variables", {})
        print(f"  Lambda alex-ingest VECTOR_BACKEND = {env.get('VECTOR_BACKEND', 'not set')}")
        print(f"  Lambda SAGEMAKER_ENDPOINT          = {env.get('SAGEMAKER_ENDPOINT', 'not set')}")
    except Exception as e:
        print(f"  ⚠️  Lambda config: {e}")

    return {"ssm_backend": backend}


def step5_sagemaker() -> bool:
    banner(5, "SageMaker embedding endpoint")
    try:
        r = sage.describe_endpoint(EndpointName=SAGEMAKER_EP)
        status = r["EndpointStatus"]
        print(f"  Endpoint: {SAGEMAKER_EP}")
        print(f"  Status:   {status}")
        if status != "InService":
            print("  ❌ Endpoint not InService — semantic search will fail until started")
            return False
        print("  ✅ Ready for embeddings (MiniLM 384-dim)")
        return True
    except Exception as e:
        print(f"  ❌ SageMaker check failed: {e}")
        return False


def embed_text(text: str) -> list[float]:
    if len(text) > 300:
        text = text[:300]
    resp = smrt.invoke_endpoint(
        EndpointName=SAGEMAKER_EP,
        Body=json.dumps({"inputs": text}),
        ContentType="application/json",
    )
    tokens = json.loads(resp["Body"].read())[0]
    n, d   = len(tokens), len(tokens[0])
    return [sum(tokens[t][i] for t in range(n)) / n for i in range(d)]


def step6_direct_semantic_search(query: str, top_k: int = 5) -> list[dict]:
    banner(6, f"Direct pgvector semantic search — \"{query}\"")
    print("  6a. Embed query via SageMaker…")
    vec = embed_text(query)
    print(f"      Vector dim: {len(vec)} (first 3: {vec[:3]})")

    vec_str = "[" + ",".join(str(v) for v in vec) + "]"
    print("  6b. Cosine search in Aurora (ORDER BY embedding <=> query)…")
    r = sql(
        """
        SELECT topic, LEFT(content, 200) AS snippet, source,
               created_at::text, ROUND(score::numeric, 4) AS score
        FROM (
            SELECT topic, content, source, created_at,
                   (1 - (embedding <=> :qv::vector)) AS score
            FROM research_vectors
            WHERE embedding IS NOT NULL
        ) ranked
        ORDER BY score DESC
        LIMIT :k
        """,
        [
            {"name": "qv", "value": {"stringValue": vec_str}},
            {"name": "k",  "value": {"longValue":   top_k}},
        ],
    )
    results = []
    records = r.get("records", [])
    if not records:
        print("  ⚠️  No results returned")
        return results

    print(f"\n  Top {len(records)} matches:")
    for i, row in enumerate(records, 1):
        hit = {
            "rank":    i,
            "topic":   val(row, 0),
            "snippet": val(row, 1),
            "source":  val(row, 2),
            "date":    val(row, 3),
            "score":   float(val(row, 4) or 0),
        }
        results.append(hit)
        print(f"\n  #{i}  score={hit['score']:.4f}  topic={hit['topic']}  source={hit['source']}")
        print(f"      {hit['snippet']}…")
        print(f"      ({hit['date']})")

    return results


def step7_api_search(query: str, top_k: int = 5) -> list[dict]:
    banner(7, f"API Gateway semantic search — \"{query}\"")
    if not INGEST_API:
        print("  ⚠️  ALEX_API_ENDPOINT / NEXT_PUBLIC_ALEX_API not set — skip")
        return []
    search_url = INGEST_API.replace("/ingest", "/search")
    print(f"  URL: {search_url}")

    import urllib.request
    req = urllib.request.Request(
        search_url,
        data=json.dumps({"query": query, "top_k": top_k}).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key":    API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"  ❌ API search failed: {e}")
        return []

    results = data.get("results", [])
    print(f"  Backend: {data.get('backend', 'unknown')}")
    print(f"  Count:   {data.get('count', len(results))}")
    for i, hit in enumerate(results, 1):
        print(f"\n  #{i}  score={hit.get('score')}  topic={hit.get('topic')}")
        print(f"      {(hit.get('content') or '')[:200]}…")
    return results


def step8_lambda_invoke_search(query: str, top_k: int = 5) -> list[dict]:
    banner(8, f"alex-ingest Lambda invoke — \"{query}\"")
    payload = {
        "path":       "/search",
        "httpMethod": "POST",
        "body":       json.dumps({"query": query, "top_k": top_k}),
    }
    try:
        resp = lmb.invoke(
            FunctionName="alex-ingest",
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode(),
        )
        raw  = json.loads(resp["Payload"].read())
        body = json.loads(raw.get("body", "{}"))
    except Exception as e:
        print(f"  ❌ Lambda invoke failed: {e}")
        return []

    if raw.get("statusCode", 200) >= 400:
        print(f"  ❌ Lambda error: {body}")
        return []

    results = body.get("results", [])
    print(f"  Backend: {body.get('backend')}")
    print(f"  Count:   {body.get('count', len(results))}")
    for i, hit in enumerate(results, 1):
        print(f"\n  #{i}  score={hit.get('score')}  topic={hit.get('topic')}")
        print(f"      {(hit.get('content') or '')[:200]}…")
    return results


STEPS = {
    1: ("Aurora ping",           lambda **_: step1_aurora_ping()),
    2: ("pgvector extension",    lambda **_: step2_pgvector_extension()),
    3: ("Vector inventory",      lambda **_: step3_vector_inventory()),
    4: ("Backend config",        lambda **_: step4_backend_config()),
    5: ("SageMaker endpoint",    lambda **_: step5_sagemaker()),
}


def main():
    parser = argparse.ArgumentParser(description="pgvector + Aurora RAG step tests")
    parser.add_argument("--step", type=int, help="Run only this step (1-8)")
    parser.add_argument("--search", default="NVDA semiconductor earnings outlook",
                        help="Query for semantic search steps 6-8")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    print(f"Alex pgvector RAG test — {datetime.now(timezone.utc).isoformat()}")

    run = lambda n, fn: fn(query=args.search, top_k=args.top_k) if n >= 6 else fn()

    if args.step:
        if args.step in STEPS:
            STEPS[args.step][1]()
        elif args.step == 6:
            step6_direct_semantic_search(args.search, args.top_k)
        elif args.step == 7:
            step7_api_search(args.search, args.top_k)
        elif args.step == 8:
            step8_lambda_invoke_search(args.search, args.top_k)
        else:
            print(f"Unknown step {args.step} (use 1-8)")
            sys.exit(1)
        return

    # Full run: steps 1-5 always; 6-8 only if SageMaker up
    sage_ok = False
    for n in range(1, 6):
        if n == 5:
            sage_ok = bool(STEPS[n][1]())
        else:
            STEPS[n][1]()

    if sage_ok:
        step6_direct_semantic_search(args.search, args.top_k)
        step8_lambda_invoke_search(args.search, args.top_k)
        if INGEST_API and API_KEY:
            step7_api_search(args.search, args.top_k)
        else:
            banner(7, "API Gateway search (skipped)")
            print("  Set ALEX_API_ENDPOINT + ALEX_API_KEY in .env to test API route")
    else:
        print("\n⚠️  Steps 6-8 skipped — start SageMaker endpoint first:")
        print("   scripts/start_session.sh  (or terraform apply 2_sagemaker)")

    print(f"\n{'='*60}")
    print("DONE — review steps above")
    print("=" * 60)


if __name__ == "__main__":
    main()
