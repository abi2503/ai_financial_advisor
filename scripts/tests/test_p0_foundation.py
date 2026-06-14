#!/usr/bin/env python3
"""
P0 Foundation Tests — run after every P0 change (and before starting P1).

Layers:
  1. Static code checks  — no AWS required (always run in CI)
  2. Unit checks         — pure Python helpers
  3. Aurora schema live  — requires AWS creds + Aurora (skip if unavailable)

Usage:
  python3 scripts/tests/test_p0_foundation.py           # static + unit (+ live if AWS)
  python3 scripts/tests/test_p0_foundation.py --static  # CI-safe, no AWS
  python3 scripts/tests/test_p0_foundation.py --live   # include Aurora schema checks

Exit code: 0 = all run tests passed, 1 = failure
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "backend" / "ingest"))
sys.path.insert(0, str(ROOT / "backend" / "researcher"))

PASSED = 0
FAILED = 0
SKIPPED = 0


def ok(name: str, detail: str = ""):
    global PASSED
    PASSED += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  ✅ {name}{suffix}")


def fail(name: str, detail: str = ""):
    global FAILED
    FAILED += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  ❌ {name}{suffix}")


def skip(name: str, detail: str = ""):
    global SKIPPED
    SKIPPED += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  ⏭️  {name}{suffix}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


# ── Layer 1: Static code checks ───────────────────────────────────────────────

def test_context_service_static():
    print("\n── P0.1 context_service.py (static) ──")
    src = read("backend/researcher/context_service.py")

    bad_patterns = [
        ("LECT messages",        r"\bLECT\s+messages"),
        ("portfolio_stocks",     r"portfolio_stocks"),
        ("result[ecords]",       r"result\[ecords\]"),
        ("resul'records'",       r"resul'records'"),
        ("userd param",          r"def get_prior_research\(query: str, userd:"),
    ]
    for label, pattern in bad_patterns:
        if re.search(pattern, src):
            fail(label, "regression detected")
        else:
            ok(label)

    good_patterns = [
        ("SELECT messages",      r"SELECT\s+cs\.messages|SELECT messages FROM chat_sessions"),
        ("portfolios table",     r"FROM portfolios p"),
        ("user_id filter RAG",   r"u\.clerk_id = :user_id"),
        ("parse_field_number",   r"def _parse_field_number"),
    ]
    for label, pattern in good_patterns:
        if re.search(pattern, src):
            ok(label)
        else:
            fail(label, "expected pattern missing")


def test_orchestrator_static():
    print("\n── P0.7 orchestrator.py (static) ──")
    src = read("backend/agents/trading/core/orchestrator.py")

    if "MessageGroupId" in src:
        fail("no MessageGroupId", "FIFO-only param on standard queue")
    else:
        ok("no MessageGroupId on SQS send")

    if re.search(r"sqs\.send_message\s*\(", src):
        ok("sqs.send_message present")
    else:
        fail("sqs.send_message", "missing")


def test_ingest_static():
    print("\n── P0.3 ingest_pgvector.py (static) ──")
    src = read("backend/ingest/ingest_pgvector.py")

    for col in ("session_id", "chunk_index", "chunk_type", "user_id"):
        if col in src:
            ok(f"ingest column {col}")
        else:
            fail(f"ingest column {col}", "missing from handler")

    if "_resolve_db_user_id" in src:
        ok("_resolve_db_user_id helper")
    else:
        fail("_resolve_db_user_id", "missing")


def test_deep_routes_static():
    print("\n── P0.4 deep API routes (static) ──")
    for path in (
        "frontend/app/api/research/deep/route.ts",
        "frontend/app/api/research/deep/stream/route.ts",
        "frontend/app/api/research/stream/route.ts",
    ):
        src = read(path)
        if "user_id" in src and "session_id" in src:
            ok(f"{path.split('/')[-2]}/route passes identity")
        else:
            fail(f"{path}", "missing user_id or session_id")


def test_research_route_static():
    print("\n── P0.4 research route + multi-agent (static) ──")
    src = read("frontend/app/api/research/route.ts")
    checks = [
        ("simple ECS session_id from body", r"body\.session_id"),
        ("multi planner user_id",           r"user_id:\s*userId"),
        ("multi planner session_id",        r"session_id:\s*sessionId"),
    ]
    for label, pattern in checks:
        if re.search(pattern, src):
            ok(label)
        else:
            fail(label, "expected pattern missing")


def test_planner_reporter_static():
    print("\n── P0.4 planner + reporter identity (static) ──")
    planner = read("backend/agents/planner.py")
    reporter = read("backend/agents/reporter.py")
    tools = read("backend/researcher/tools.py")
    ctx = read("backend/researcher/context_service.py")

    if '"session_id"' in planner and '"user_id"' in planner:
        ok("planner SQS message includes identity")
    else:
        fail("planner identity", "missing user_id/session_id in SQS message")

    if re.search(r"def store_report\([^)]*clerk_id", reporter):
        ok("reporter store_report passes identity")
    else:
        fail("reporter store_report", "missing clerk_id/session_id")
    if re.search(r"call_ecs_research\([^)]*session_id", reporter):
        ok("reporter ECS call passes session_id")
    else:
        fail("reporter ECS", "missing session_id")

    if "get_tracker" in tools and '"session_id"' in tools:
        ok("tools ingest uses latency tracker identity")
    else:
        fail("tools ingest identity", "missing tracker wiring")

    if re.search(r"u\.clerk_id = :user_id", ctx) and "JOIN users u" in ctx:
        ok("chat_sessions scoped by user_id")
    else:
        fail("chat_sessions scoping", "missing user join in queries")


def test_aurora_warmup_static():
    print("\n── P0.5-9 aurora_warmup.py (static) ──")
    src = read("scripts/aurora_warmup.py")

    required = [
        "agent_observations",
        "research_vectors.user_id",
        "simulated_trades.target_price",
        "chat_sessions unique index",
        "scout_candidates",
        "query_latency_metrics",
        "trading_floor_intelligence",
    ]
    for item in required:
        if item.replace(".", " ").split()[0] in src or item in src:
            ok(f"warmup includes {item}")
        else:
            fail(f"warmup missing {item}")


# ── Layer 2: Unit checks ──────────────────────────────────────────────────────

def test_parse_field_number():
    print("\n── P0 unit: _parse_field_number ──")
    from context_service import _parse_field_number

    cases = [
        ({"doubleValue": 1.5}, 1.5),
        ({"stringValue": "42.5"}, 42.5),
        ({"longValue": 10}, 10.0),
        (None, 0.0),
    ]
    for field, expected in cases:
        got = _parse_field_number(field)
        if abs(got - expected) < 0.001:
            ok(f"parse {field} → {got}")
        else:
            fail(f"parse {field}", f"expected {expected}, got {got}")


# ── Layer 3: Aurora live schema ───────────────────────────────────────────────

CLUSTER_ARN = os.environ.get(
    "DB_CLUSTER_ARN",
    "arn:aws:rds:us-east-1:381491881089:cluster:alex-aurora",
)
SECRET_ARN = os.environ.get(
    "DB_SECRET_ARN",
    "arn:aws:secretsmanager:us-east-1:381491881089:secret:alex/aurora/credentials-2HP8fm",
)
DB_NAME = os.environ.get("DB_NAME", "alex_db")


def _aws_available() -> bool:
    try:
        import boto3
        boto3.client("sts", region_name="us-east-1").get_caller_identity()
        return True
    except Exception:
        return False


def _execute_sql(sql: str) -> dict:
    import boto3
    rds = boto3.client("rds-data", region_name="us-east-1")
    return rds.execute_statement(
        resourceArn=CLUSTER_ARN,
        secretArn=SECRET_ARN,
        database=DB_NAME,
        sql=sql,
    )


def test_aurora_schema_live():
    print("\n── P0 Aurora schema (live) ──")

    if not _aws_available():
        skip("Aurora live tests", "no AWS credentials")
        return

    table_checks = [
        "agent_observations",
        "scout_candidates",
        "rl_weights",
        "trading_events",
        "session_metadata",
        "rag_attributions",
        "query_latency_metrics",
        "trading_floor_intelligence",
        "quant_snapshots",
        "ragas_evaluations",
    ]
    for table in table_checks:
        try:
            r = _execute_sql(f"SELECT 1 FROM {table} LIMIT 1")
            ok(f"table {table} reachable")
        except Exception as e:
            fail(f"table {table}", str(e)[:60])

    column_sql = """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'research_vectors'
          AND column_name IN ('user_id','session_id','chunk_index','query','chunk_type')
    """
    try:
        r = _execute_sql(column_sql)
        cols = {row[0]["stringValue"] for row in r.get("records", [])}
        expected = {"user_id", "session_id", "chunk_index", "query", "chunk_type"}
        if expected.issubset(cols):
            ok("research_vectors P0 columns", ", ".join(sorted(cols)))
        else:
            fail("research_vectors columns", f"missing {expected - cols}")
    except Exception as e:
        fail("research_vectors column check", str(e)[:60])

    trade_cols_sql = """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'simulated_trades'
          AND column_name IN ('target_price','stop_loss','realized_pnl','outcome','trigger')
    """
    try:
        r = _execute_sql(trade_cols_sql)
        cols = {row[0]["stringValue"] for row in r.get("records", [])}
        expected = {"target_price", "stop_loss", "realized_pnl", "outcome", "trigger"}
        if expected.issubset(cols):
            ok("simulated_trades P0 columns")
        else:
            fail("simulated_trades columns", f"missing {expected - cols}")
    except Exception as e:
        fail("simulated_trades column check", str(e)[:60])

    index_sql = """
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'chat_sessions'
          AND indexname = 'chat_sessions_user_session_uidx'
    """
    try:
        r = _execute_sql(index_sql)
        if r.get("records"):
            ok("chat_sessions unique index")
        else:
            fail("chat_sessions unique index", "not found")
    except Exception as e:
        fail("chat_sessions index check", str(e)[:60])


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="P0 foundation tests")
    parser.add_argument("--static", action="store_true", help="Static + unit only (CI)")
    parser.add_argument("--live",   action="store_true", help="Include Aurora live checks")
    args = parser.parse_args()

    run_live = args.live or (not args.static)

    print("🧪 Alex P0 Foundation Tests")
    print("=" * 50)

    test_context_service_static()
    test_orchestrator_static()
    test_ingest_static()
    test_deep_routes_static()
    test_research_route_static()
    test_planner_reporter_static()
    test_aurora_warmup_static()
    test_parse_field_number()

    if run_live:
        test_aurora_schema_live()
    else:
        skip("Aurora live tests", "use --live or default to enable")

    print("\n" + "=" * 50)
    print(f"📊 Results: {PASSED} passed, {FAILED} failed, {SKIPPED} skipped")

    if FAILED:
        print("❌ P0 tests FAILED")
        sys.exit(1)
    print("✅ P0 tests PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
