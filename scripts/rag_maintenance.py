#!/usr/bin/env python3
"""
RAG maintenance: cleanup junk vectors + re-ingest Micron as chunked embeddings.

Usage:
  python3 scripts/rag_maintenance.py --cleanup-debug
  python3 scripts/rag_maintenance.py --reingest-micron
  python3 scripts/rag_maintenance.py --all
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

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
MU_TOPIC    = "Micron Technology (MU) — Deep Research Jun 2026"

rds   = boto3.client("rds-data", region_name=REGION)
lmb   = boto3.client("lambda", region_name=REGION)

# Reuse chunking logic from ingest package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "ingest"))
from rag_utils import chunk_content  # noqa: E402


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
                time.sleep(10 * (i + 1))
            else:
                raise
    raise RuntimeError("SQL failed")


def val(row, idx: int):
    f = row[idx]
    for k in ("stringValue", "longValue", "doubleValue"):
        if k in f:
            return f[k]
    return None


def step_banner(n: int, title: str) -> None:
    print(f"\n{'='*60}\nSTEP {n}: {title}\n{'='*60}")


def cleanup_debug_vectors() -> int:
    step_banner(1, "Delete debug / junk vectors")
    count_r = sql("""
        SELECT COUNT(*)::bigint FROM research_vectors
        WHERE topic ILIKE '%debug test%'
           OR topic ILIKE 'Report: final test%'
           OR content ILIKE '%Research Report: Debug Test%'
    """)
    before = int(val(count_r["records"][0], 0) or 0)
    print(f"  Rows to delete: {before}")
    if before == 0:
        print("  ✅ Nothing to clean")
        return 0

    sql("""
        DELETE FROM research_vectors
        WHERE topic ILIKE '%debug test%'
           OR topic ILIKE 'Report: final test%'
           OR content ILIKE '%Research Report: Debug Test%'
    """)
    print(f"  ✅ Deleted {before} junk vectors")
    return before


def fetch_micron_source() -> tuple[str, str] | None:
    step_banner(2, "Fetch latest Micron (MU) research from Aurora")
    r = sql("""
        SELECT topic, content
        FROM research_vectors
        WHERE topic ILIKE '%Micron%'
           OR content ILIKE '%Micron Technology (MU)%'
        ORDER BY created_at DESC
        LIMIT 1
    """)
    if not r.get("records"):
        print("  ❌ No Micron content found — run deep research on MU first")
        return None
    row = r["records"][0]
    topic   = val(row, 0) or MU_TOPIC
    content = val(row, 1) or ""
    print(f"  Topic: {topic}")
    print(f"  Content length: {len(content)} chars")
    return topic, content


def delete_old_micron() -> int:
    count_r = sql("""
        SELECT COUNT(*)::bigint FROM research_vectors
        WHERE topic ILIKE '%Micron%'
           OR content ILIKE '%Micron Technology (MU)%'
    """)
    n = int(val(count_r["records"][0], 0) or 0)
    if n:
        sql("""
            DELETE FROM research_vectors
            WHERE topic ILIKE '%Micron%'
               OR content ILIKE '%Micron Technology (MU)%'
        """)
    print(f"  Removed {n} old Micron row(s)")
    return n


def invoke_ingest(topic: str, content: str) -> dict:
    payload = {
        "path":       "/ingest",
        "httpMethod": "POST",
        "body":       json.dumps({
            "content": content,
            "topic":   topic,
            "source":  "rag-maintenance",
            "query":   "SEC filing details about micron",
            "chunk_type": "deep_research",
        }),
    }
    resp = lmb.invoke(
        FunctionName="alex-ingest",
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode(),
    )
    raw  = json.loads(resp["Payload"].read())
    body = json.loads(raw.get("body", "{}"))
    if raw.get("statusCode", 200) >= 400:
        raise RuntimeError(body.get("error") or raw)
    return body


def reingest_micron() -> int:
    src = fetch_micron_source()
    if not src:
        return 0

    topic, content = src
    step_banner(3, "Remove old Micron vectors")
    delete_old_micron()

    chunks = chunk_content(content)
    step_banner(4, f"Re-ingest Micron as {len(chunks)} chunked vector(s)")
    for i, c in enumerate(chunks):
        print(f"  Chunk {i + 1}/{len(chunks)} — {len(c)} chars")

    body = invoke_ingest(MU_TOPIC, content)
    n    = body.get("chunks") or len(body.get("vector_ids") or [])
    print(f"  ✅ Ingested {n} chunk(s) — ids: {body.get('vector_ids', [body.get('vector_id')])}")
    return n


def verify_search(query: str = "Micron MU SEC filing memory chip risks") -> None:
    step_banner(5, f"Verify semantic search — \"{query}\"")
    payload = {
        "path":       "/search",
        "httpMethod": "POST",
        "body":       json.dumps({"query": query, "top_k": 5}),
    }
    resp = lmb.invoke(
        FunctionName="alex-ingest",
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode(),
    )
    raw  = json.loads(resp["Payload"].read())
    body = json.loads(raw.get("body", "{}"))
    results = body.get("results", [])
    print(f"  Status: {raw.get('statusCode')}  Count: {len(results)}")
    for i, hit in enumerate(results, 1):
        print(f"  #{i} score={hit.get('score')} topic={hit.get('topic')}")
        print(f"      {(hit.get('content') or '')[:120]}…")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleanup-debug", action="store_true")
    parser.add_argument("--reingest-micron", action="store_true")
    parser.add_argument("--verify", action="store_true", help="Run search verification")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if not any([args.cleanup_debug, args.reingest_micron, args.verify, args.all]):
        parser.print_help()
        sys.exit(1)

    if args.all or args.cleanup_debug:
        cleanup_debug_vectors()
    if args.all or args.reingest_micron:
        reingest_micron()
    if args.all or args.verify:
        verify_search()

    total = sql("SELECT COUNT(*)::bigint FROM research_vectors")
    mu    = sql("SELECT COUNT(*)::bigint FROM research_vectors WHERE topic ILIKE '%Micron%'")
    print(f"\n📊 Total vectors: {val(total['records'][0], 0)}")
    print(f"📊 Micron vectors: {val(mu['records'][0], 0)}")


if __name__ == "__main__":
    main()
