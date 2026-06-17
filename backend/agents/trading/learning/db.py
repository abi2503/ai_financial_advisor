"""Persist trading outcome eval runs to Aurora."""

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


def is_configured() -> bool:
    return bool(CLUSTER_ARN and SECRET_ARN)


def _execute(sql: str, params: list | None = None) -> dict:
    if not is_configured():
        logger.warning("Aurora not configured — skipping trading eval persist")
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
        logger.error(f"Trading eval DB error: {e}")
        raise


def ensure_schema() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS trading_eval_runs (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          gate VARCHAR(50) NOT NULL DEFAULT 'manual',
          horizon_days INT DEFAULT 5,
          trades_evaluated INT DEFAULT 0,
          trades_pending INT DEFAULT 0,
          trades_skipped INT DEFAULT 0,
          overall_accuracy NUMERIC(5,3),
          buy_accuracy NUMERIC(5,3),
          sell_accuracy NUMERIC(5,3),
          hold_neutral_rate NUMERIC(5,3),
          avg_pnl_pct NUMERIC(8,4),
          passed BOOLEAN DEFAULT false,
          report_json JSONB DEFAULT '{}',
          evaluated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "ALTER TABLE agent_performance ADD COLUMN IF NOT EXISTS eval_run_id UUID",
        "ALTER TABLE agent_performance ADD COLUMN IF NOT EXISTS trade_id UUID",
        "ALTER TABLE agent_performance ADD COLUMN IF NOT EXISTS final_action VARCHAR(10)",
        "ALTER TABLE agent_performance ADD COLUMN IF NOT EXISTS return_pct NUMERIC(8,4)",
        "ALTER TABLE agent_performance ADD COLUMN IF NOT EXISTS horizon_days INT DEFAULT 5",
        "ALTER TABLE agent_performance ADD COLUMN IF NOT EXISTS audit_json JSONB DEFAULT '{}'",
        "CREATE INDEX IF NOT EXISTS agent_performance_eval_run_idx ON agent_performance (eval_run_id)",
        "CREATE INDEX IF NOT EXISTS agent_performance_agent_idx ON agent_performance (agent_name, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS simulated_trades_outcome_null_idx ON simulated_trades (executed_at) WHERE outcome IS NULL",
        "CREATE INDEX IF NOT EXISTS trading_eval_runs_at_idx ON trading_eval_runs (evaluated_at DESC)",
    ]
    for sql in statements:
        _execute(sql.strip())


def new_run_id() -> str:
    return str(uuid.uuid4())


def fetch_pending_trades(horizon_days: int = 5, limit: int = 100) -> list[dict[str, Any]]:
    ensure_schema()
    result = _execute(
        """
        SELECT
          id::text, ticker, action, shares, price,
          agent_votes::text, confidence, mode, executed_at::text,
          simulation_id::text, user_id::text
        FROM simulated_trades
        WHERE outcome IS NULL
          AND executed_at <= NOW() - (:min_age::int * INTERVAL '1 day')
        ORDER BY executed_at ASC
        LIMIT :lim
        """,
        [
            {"name": "min_age", "value": {"longValue": int(horizon_days)}},
            {"name": "lim",     "value": {"longValue": int(limit)}},
        ],
    )
    rows = []
    for rec in result.get("records", []):
        rows.append({
            "trade_id":       rec[0].get("stringValue"),
            "ticker":         rec[1].get("stringValue"),
            "action":         rec[2].get("stringValue"),
            "shares":         int(list(rec[3].values())[0] or 0),
            "price":          float(list(rec[4].values())[0] or 0),
            "agent_votes_raw": rec[5].get("stringValue") or "[]",
            "confidence":     float(list(rec[6].values())[0] or 0),
            "mode":           rec[7].get("stringValue"),
            "executed_at":    rec[8].get("stringValue"),
            "simulation_id":  rec[9].get("stringValue"),
            "user_id":        rec[10].get("stringValue"),
        })
    return rows


def count_pending_trades(horizon_days: int = 5) -> int:
    ensure_schema()
    result = _execute(
        """
        SELECT COUNT(*)::int
        FROM simulated_trades
        WHERE outcome IS NULL
          AND executed_at <= NOW() - (:min_age::int * INTERVAL '1 day')
        """,
        [{"name": "min_age", "value": {"longValue": int(horizon_days)}}],
    )
    if not result.get("records"):
        return 0
    return int(list(result["records"][0][0].values())[0] or 0)


def update_trade_outcome(
    trade_id: str,
    outcome: str,
    realized_pnl: float,
    return_pct: float,
) -> None:
    _execute(
        """
        UPDATE simulated_trades
        SET outcome = :outcome,
            realized_pnl = :pnl,
            pnl = :pnl
        WHERE id = :trade_id::uuid
        """,
        [
            {"name": "outcome",   "value": {"stringValue": outcome}},
            {"name": "pnl",       "value": {"doubleValue": float(realized_pnl)}},
            {"name": "trade_id",  "value": {"stringValue": trade_id}},
        ],
    )


def insert_agent_performance(row: dict[str, Any]) -> None:
    week_of = (row.get("executed_at") or "")[:10] or None
    _execute(
        """
        INSERT INTO agent_performance (
          eval_run_id, trade_id, agent_name, ticker, action, confidence,
          outcome, pnl_pct, correct, week_of, final_action, return_pct,
          horizon_days, audit_json
        ) VALUES (
          :eval_run_id::uuid, :trade_id::uuid, :agent_name, :ticker, :action, :confidence,
          :outcome, :pnl_pct, :correct, :week_of::date, :final_action, :return_pct,
          :horizon_days, :audit_json::jsonb
        )
        """,
        [
            {"name": "eval_run_id",   "value": {"stringValue": row["eval_run_id"]}},
            {"name": "trade_id",      "value": {"stringValue": row["trade_id"]}},
            {"name": "agent_name",    "value": {"stringValue": row["agent_name"]}},
            {"name": "ticker",        "value": {"stringValue": row["ticker"]}},
            {"name": "action",        "value": {"stringValue": row["action"]}},
            {"name": "confidence",    "value": {"doubleValue": float(row.get("confidence") or 0)}},
            {"name": "outcome",       "value": {"stringValue": row["outcome"]}},
            {"name": "pnl_pct",       "value": {"doubleValue": float(row.get("return_pct") or 0)}},
            {"name": "correct",       "value": {"booleanValue": row["correct"]} if row.get("correct") is not None else {"isNull": True}},
            {"name": "week_of",       "value": {"stringValue": week_of or "1970-01-01"}},
            {"name": "final_action",  "value": {"stringValue": row.get("final_action") or ""}},
            {"name": "return_pct",    "value": {"doubleValue": float(row.get("return_pct") or 0)}},
            {"name": "horizon_days",  "value": {"longValue": int(row.get("horizon_days") or 5)}},
            {"name": "audit_json",    "value": {"stringValue": json.dumps(row.get("audit", {}))}},
        ],
    )


def save_eval_run(run_id: str, gate: str, summary: dict[str, Any], audits: list[dict[str, Any]]) -> None:
    ensure_schema()
    _execute(
        """
        INSERT INTO trading_eval_runs (
          id, gate, horizon_days, trades_evaluated, trades_pending, trades_skipped,
          overall_accuracy, buy_accuracy, sell_accuracy, hold_neutral_rate,
          avg_pnl_pct, passed, report_json
        ) VALUES (
          :run_id::uuid, :gate, :horizon_days, :evaluated, :pending, :skipped,
          :overall, :buy_acc, :sell_acc, :hold_rate,
          :avg_pnl, :passed, :report_json::jsonb
        )
        """,
        [
            {"name": "run_id",       "value": {"stringValue": run_id}},
            {"name": "gate",         "value": {"stringValue": gate}},
            {"name": "horizon_days", "value": {"longValue":   int(summary.get("horizon_days", 5))}},
            {"name": "evaluated",    "value": {"longValue":   int(summary.get("trades_evaluated", 0))}},
            {"name": "pending",      "value": {"longValue":   int(summary.get("trades_pending", 0))}},
            {"name": "skipped",      "value": {"longValue":   int(summary.get("trades_skipped", 0))}},
            {"name": "overall",      "value": {"doubleValue": float(summary["overall_accuracy"])}},
            {"name": "buy_acc",      "value": {"doubleValue": float(summary["buy_accuracy"])}},
            {"name": "sell_acc",     "value": {"doubleValue": float(summary["sell_accuracy"])}},
            {"name": "hold_rate",    "value": {"doubleValue": float(summary["hold_neutral_rate"])}},
            {"name": "avg_pnl",      "value": {"doubleValue": float(summary["avg_pnl_pct"])}},
            {"name": "passed",       "value": {"booleanValue": bool(summary["passed"])}},
            {"name": "report_json",  "value": {"stringValue": json.dumps({"audits": audits})}},
        ],
    )


def insert_trading_event(user_id: str | None, event_type: str, ticker: str, payload: dict) -> None:
    if not user_id:
        return
    try:
        _execute(
            """
            INSERT INTO trading_events (user_id, event_type, ticker, payload)
            SELECT id, :event_type, :ticker, :payload::jsonb
            FROM users WHERE id = :user_id::uuid
            """,
            [
                {"name": "user_id",     "value": {"stringValue": user_id}},
                {"name": "event_type",  "value": {"stringValue": event_type}},
                {"name": "ticker",      "value": {"stringValue": ticker or ""}},
                {"name": "payload",     "value": {"stringValue": json.dumps(payload)}},
            ],
        )
    except Exception as e:
        logger.warning(f"trading_events insert skipped: {e}")
