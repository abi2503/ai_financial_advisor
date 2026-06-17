"""Persist RAGAS evaluation runs to Aurora."""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

import boto3

logger = logging.getLogger(__name__)

REGION      = os.environ.get("AWS_REGION", os.environ.get("AWS_REGION_NAME", "us-east-1"))
CLUSTER_ARN = os.environ.get("DB_CLUSTER_ARN", "")
SECRET_ARN  = os.environ.get("DB_SECRET_ARN", "")
DB_NAME     = os.environ.get("DB_NAME", "alex_db")

_rds = boto3.client("rds-data", region_name=REGION)


def _execute(sql: str, params: list | None = None) -> dict:
    if not CLUSTER_ARN or not SECRET_ARN:
        logger.warning("Aurora not configured — skipping RAGAS persist")
        return {}
    try:
        return _rds.execute_statement(
            resourceArn=CLUSTER_ARN,
            secretArn=SECRET_ARN,
            database=DB_NAME,
            sql=sql,
            parameters=params or [],
        )
    except Exception as e:
        logger.error(f"RAGAS DB error: {e}")
        return {}


def is_configured() -> bool:
    return bool(CLUSTER_ARN and SECRET_ARN)


def ensure_ragas_schema() -> None:
    """Idempotent migrations for RAGAS tables."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS ragas_eval_runs (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          gate VARCHAR(50) NOT NULL DEFAULT 'manual',
          judge_model VARCHAR(100),
          backend VARCHAR(50) DEFAULT 'pgvector',
          query_count INT DEFAULT 0,
          faithfulness NUMERIC(4,3),
          answer_relevancy NUMERIC(4,3),
          context_precision NUMERIC(4,3),
          context_recall NUMERIC(4,3),
          hallucination_rate NUMERIC(4,3),
          overall_score NUMERIC(4,3),
          passed BOOLEAN DEFAULT false,
          report_json JSONB DEFAULT '{}',
          evaluated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "ALTER TABLE ragas_evaluations ADD COLUMN IF NOT EXISTS run_id UUID",
        "ALTER TABLE ragas_evaluations ADD COLUMN IF NOT EXISTS ground_truth TEXT",
        "ALTER TABLE ragas_evaluations ADD COLUMN IF NOT EXISTS hallucination_rate NUMERIC(4,3)",
        "ALTER TABLE ragas_evaluations ADD COLUMN IF NOT EXISTS contexts JSONB DEFAULT '[]'",
        "ALTER TABLE ragas_evaluations ADD COLUMN IF NOT EXISTS audit_json JSONB DEFAULT '{}'",
        "CREATE INDEX IF NOT EXISTS ragas_evaluations_run_id_idx ON ragas_evaluations (run_id)",
        "CREATE INDEX IF NOT EXISTS ragas_eval_runs_evaluated_at_idx ON ragas_eval_runs (evaluated_at DESC)",
    ]
    for sql in statements:
        _execute(sql.strip())


def save_eval_run(
    run_id: str,
    gate: str,
    judge_model: str,
    summary: dict[str, Any],
    queries: list[dict[str, Any]],
) -> None:
    ensure_ragas_schema()

    _execute(
        """
        INSERT INTO ragas_eval_runs (
          id, gate, judge_model, backend, query_count,
          faithfulness, answer_relevancy, context_precision, context_recall,
          hallucination_rate, overall_score, passed, report_json
        ) VALUES (
          :run_id::uuid, :gate, :judge_model, :backend, :query_count,
          :faithfulness, :answer_relevancy, :context_precision, :context_recall,
          :hallucination_rate, :overall_score, :passed, :report_json::jsonb
        )
        """,
        [
            {"name": "run_id",             "value": {"stringValue": run_id}},
            {"name": "gate",               "value": {"stringValue": gate}},
            {"name": "judge_model",        "value": {"stringValue": judge_model}},
            {"name": "backend",            "value": {"stringValue": summary.get("backend", "pgvector")}},
            {"name": "query_count",        "value": {"longValue":   int(summary.get("query_count", 0))}},
            {"name": "faithfulness",       "value": {"doubleValue": float(summary["faithfulness"])}},
            {"name": "answer_relevancy",   "value": {"doubleValue": float(summary["answer_relevancy"])}},
            {"name": "context_precision",    "value": {"doubleValue": float(summary["context_precision"])}},
            {"name": "context_recall",       "value": {"doubleValue": float(summary["context_recall"])}},
            {"name": "hallucination_rate", "value": {"doubleValue": float(summary["hallucination_rate"])}},
            {"name": "overall_score",      "value": {"doubleValue": float(summary["overall_score"])}},
            {"name": "passed",             "value": {"booleanValue": bool(summary["passed"])}},
            {"name": "report_json",        "value": {"stringValue": json.dumps({"queries": queries})}},
        ],
    )

    for q in queries:
        _execute(
            """
            INSERT INTO ragas_evaluations (
              run_id, query, response, ground_truth, faithfulness, answer_relevancy,
              context_precision, context_recall, hallucination_rate, overall_score,
              passed, gate, contexts, audit_json
            ) VALUES (
              :run_id::uuid, :query, :response, :ground_truth, :faithfulness, :answer_relevancy,
              :context_precision, :context_recall, :hallucination_rate, :overall_score,
              :passed, :gate, :contexts::jsonb, :audit_json::jsonb
            )
            """,
            [
                {"name": "run_id",             "value": {"stringValue": run_id}},
                {"name": "query",              "value": {"stringValue": q["question"][:4000]}},
                {"name": "response",           "value": {"stringValue": q["answer"][:8000]}},
                {"name": "ground_truth",       "value": {"stringValue": q.get("ground_truth", "")[:4000]}},
                {"name": "faithfulness",       "value": {"doubleValue": float(q["metrics"]["faithfulness"])}},
                {"name": "answer_relevancy",   "value": {"doubleValue": float(q["metrics"]["answer_relevancy"])}},
                {"name": "context_precision",  "value": {"doubleValue": float(q["metrics"]["context_precision"])}},
                {"name": "context_recall",     "value": {"doubleValue": float(q["metrics"]["context_recall"])}},
                {"name": "hallucination_rate", "value": {"doubleValue": float(q["metrics"]["hallucination_rate"])}},
                {"name": "overall_score",      "value": {"doubleValue": float(q["metrics"]["overall_score"])}},
                {"name": "passed",             "value": {"booleanValue": bool(q["metrics"]["passed"])}},
                {"name": "gate",               "value": {"stringValue": gate}},
                {"name": "contexts",           "value": {"stringValue": json.dumps(q.get("contexts", []))[:50000]}},
                {"name": "audit_json",         "value": {"stringValue": json.dumps(q.get("audit", {}))}},
            ],
        )


def new_run_id() -> str:
    return str(uuid.uuid4())
