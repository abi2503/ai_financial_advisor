"""
Trading floor outcome-based evaluation.

Scores simulated_trades against forward price movement (default 5d horizon),
attributes correctness to each agent vote, persists to agent_performance.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from learning.db import (
    count_pending_trades,
    fetch_pending_trades,
    insert_agent_performance,
    insert_trading_event,
    is_configured,
    new_run_id,
    save_eval_run,
    update_trade_outcome,
)
from learning.scoring import aggregate_accuracy, compute_realized_pnl, score_action

logger = logging.getLogger(__name__)

HORIZON_DAYS = int(os.environ.get("TRADING_EVAL_HORIZON_DAYS", "5"))
MIN_AGE_DAYS = int(os.environ.get("TRADING_EVAL_MIN_AGE_DAYS", "1"))
PASS_ACCURACY = float(os.environ.get("TRADING_EVAL_PASS_ACCURACY", "0.50"))
MIN_TRADES_FOR_PASS = int(os.environ.get("TRADING_EVAL_MIN_TRADES", "1"))


@dataclass
class EvalRunResult:
    run_id:            str
    gate:              str
    horizon_days:      int
    passed:            bool
    trades_evaluated:  int
    trades_pending:    int
    trades_skipped:    int
    overall_accuracy:  float
    buy_accuracy:      float
    sell_accuracy:     float
    hold_neutral_rate: float
    avg_pnl_pct:       float
    audits:            list[dict[str, Any]] = field(default_factory=list)
    leaderboard:       list[dict[str, Any]] = field(default_factory=list)
    evaluated_at:      str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_agent_votes(raw: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        return []
    return [v for v in data if isinstance(v, dict)]


def _fetch_exit_price(ticker: str, executed_at: str, horizon_days: int) -> tuple[float | None, float | None]:
    """Return (exit_price, return_pct) at horizon; None if not mature or no data."""
    try:
        import yfinance as yf
    except ImportError as e:
        raise RuntimeError("yfinance required for trading outcome eval") from e

    entry_dt = datetime.fromisoformat(executed_at.replace("Z", "+00:00"))
    if entry_dt.tzinfo is None:
        entry_dt = entry_dt.replace(tzinfo=timezone.utc)

    target_dt = entry_dt + timedelta(days=horizon_days)
    now = datetime.now(timezone.utc)
    if target_dt > now:
        return None, None

    start = (entry_dt - timedelta(days=2)).strftime("%Y-%m-%d")
    end = (target_dt + timedelta(days=5)).strftime("%Y-%m-%d")
    hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
    if hist.empty:
        return None, None

    hist = hist.reset_index()
    hist["date"] = hist["Date"].dt.tz_localize(None)
    target_naive = target_dt.replace(tzinfo=None)
    hist["delta"] = (hist["date"] - target_naive).abs()
    row = hist.sort_values("delta").iloc[0]
    exit_price = float(row["Close"])
    return exit_price, None


def evaluate_trade(trade: dict[str, Any], horizon_days: int) -> dict[str, Any] | None:
    entry_price = float(trade.get("price") or 0)
    if entry_price <= 0:
        return None

    exit_price, _ = _fetch_exit_price(trade["ticker"], trade["executed_at"], horizon_days)
    if exit_price is None:
        return None

    return_pct = round((exit_price - entry_price) / entry_price * 100, 4)
    final_action = (trade.get("action") or "HOLD").upper()
    outcome, correct, score = score_action(final_action, return_pct)
    realized_pnl = compute_realized_pnl(final_action, trade.get("shares", 0), entry_price, exit_price)

    agent_rows = []
    for vote in _parse_agent_votes(trade.get("agent_votes_raw", "[]")):
        agent_action = (vote.get("action") or "HOLD").upper()
        a_outcome, a_correct, a_score = score_action(agent_action, return_pct)
        agent_rows.append({
            "record_type": "agent",
            "agent_name":  (vote.get("agent") or vote.get("agent_name") or "unknown").lower(),
            "action":      agent_action,
            "confidence":  float(vote.get("confidence") or 0),
            "outcome":     a_outcome,
            "correct":     a_correct,
            "score":       a_score,
            "return_pct":  return_pct,
        })

    trade_row = {
        "record_type":  "trade",
        "trade_id":     trade["trade_id"],
        "ticker":       trade["ticker"],
        "action":       final_action,
        "outcome":      outcome,
        "correct":      correct,
        "score":        score,
        "return_pct":   return_pct,
        "entry_price":  entry_price,
        "exit_price":   exit_price,
        "realized_pnl": realized_pnl,
        "confidence":   trade.get("confidence"),
        "mode":         trade.get("mode"),
        "executed_at":  trade.get("executed_at"),
        "agent_votes":  agent_rows,
        "audit": {
            "method":       "outcome_based_price_horizon",
            "horizon_days": horizon_days,
            "entry_price":  entry_price,
            "exit_price":   exit_price,
        },
    }
    return trade_row


def _build_leaderboard(audits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    for audit in audits:
        for vote in audit.get("agent_votes", []):
            name = vote.get("agent_name", "unknown")
            if name not in stats:
                stats[name] = {"agent_name": name, "votes": 0, "correct": 0, "scored": 0}
            stats[name]["votes"] += 1
            if vote.get("correct") is not None:
                stats[name]["scored"] += 1
                if vote["correct"]:
                    stats[name]["correct"] += 1

    board = []
    for name, s in stats.items():
        acc = round(s["correct"] / max(s["scored"], 1), 3)
        board.append({**s, "accuracy": acc})
    return sorted(board, key=lambda x: x["accuracy"], reverse=True)


def run_evaluation(
    gate: str = "manual",
    horizon_days: int = HORIZON_DAYS,
    min_age_days: int = MIN_AGE_DAYS,
    persist: bool = True,
    report_path: str | None = "scripts/tests/trading_eval_report.json",
) -> EvalRunResult:
    run_id = new_run_id()
    pending_total = count_pending_trades(horizon_days) if is_configured() else 0
    trades = fetch_pending_trades(horizon_days) if is_configured() else []

    print("\n📈 Alex Trading Outcome Evaluation")
    print("=" * 50)
    print(f"Gate:          {gate}")
    print(f"Horizon:       {horizon_days}d")
    print(f"Pending trades:{pending_total}")
    print(f"Run ID:        {run_id}")
    print("=" * 50)

    audits: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []
    skipped = 0

    for trade in trades:
        print(f"\nEvaluating {trade['ticker']} {trade['action']} @ ${trade['price']:.2f}...")
        result = evaluate_trade(trade, horizon_days)
        if not result:
            skipped += 1
            print("  ⏭ skipped (immature or missing price data)")
            continue

        print(f"  {horizon_days}d return: {result['return_pct']:+.2f}% → {result['outcome']}")
        audits.append(result)
        aggregate_rows.append(result)
        aggregate_rows.extend(result.get("agent_votes", []))

        if persist and is_configured():
            update_trade_outcome(
                trade["trade_id"],
                result["outcome"],
                result["realized_pnl"],
                result["return_pct"],
            )
            for vote in result.get("agent_votes", []):
                insert_agent_performance({
                    "eval_run_id":  run_id,
                    "trade_id":     trade["trade_id"],
                    "agent_name":   vote["agent_name"],
                    "ticker":       trade["ticker"],
                    "action":       vote["action"],
                    "confidence":   vote["confidence"],
                    "outcome":      vote["outcome"],
                    "correct":      vote["correct"],
                    "return_pct":   result["return_pct"],
                    "final_action": result["action"],
                    "horizon_days": horizon_days,
                    "executed_at":  trade.get("executed_at"),
                    "audit":        result["audit"],
                })
            insert_trading_event(
                trade.get("user_id"),
                "outcome_evaluated",
                trade["ticker"],
                {"run_id": run_id, "outcome": result["outcome"], "return_pct": result["return_pct"]},
            )

    summary = aggregate_accuracy(aggregate_rows)
    leaderboard = _build_leaderboard(audits)
    passed = (
        len(audits) >= MIN_TRADES_FOR_PASS
        and summary["overall_accuracy"] >= PASS_ACCURACY
    )

    evaluated_at = datetime.now(timezone.utc).isoformat()
    full_summary = {
        **summary,
        "horizon_days":     horizon_days,
        "trades_evaluated": len(audits),
        "trades_pending":   max(pending_total - len(audits) - skipped, 0),
        "trades_skipped":   skipped,
        "passed":           passed,
    }

    print("\n" + "=" * 50)
    print("📊 OUTCOME SUMMARY")
    print(f"  Evaluated:        {len(audits)}")
    print(f"  Skipped:          {skipped}")
    print(f"  Agent accuracy:   {summary['overall_accuracy']:.3f}  (gate ≥ {PASS_ACCURACY})")
    print(f"  BUY accuracy:     {summary['buy_accuracy']:.3f}")
    print(f"  SELL accuracy:    {summary['sell_accuracy']:.3f}")
    print(f"  HOLD neutral:     {summary['hold_neutral_rate']:.3f}")
    print(f"  Avg return:       {summary['avg_pnl_pct']:+.2f}%")
    print(f"  PASSED:           {'✅ YES' if passed else '❌ NO'}")
    if leaderboard:
        print("\n  Agent leaderboard:")
        for row in leaderboard:
            print(f"    {row['agent_name']:12} {row['accuracy']*100:5.1f}% ({row['correct']}/{row['scored']} scored)")
    print("=" * 50)

    result = EvalRunResult(
        run_id=run_id,
        gate=gate,
        horizon_days=horizon_days,
        passed=passed,
        trades_evaluated=len(audits),
        trades_pending=full_summary["trades_pending"],
        trades_skipped=skipped,
        overall_accuracy=summary["overall_accuracy"],
        buy_accuracy=summary["buy_accuracy"],
        sell_accuracy=summary["sell_accuracy"],
        hold_neutral_rate=summary["hold_neutral_rate"],
        avg_pnl_pct=summary["avg_pnl_pct"],
        audits=audits,
        leaderboard=leaderboard,
        evaluated_at=evaluated_at,
    )

    if persist:
        if is_configured():
            save_eval_run(run_id, gate, full_summary, audits)
            print(f"  ✅ Saved to Aurora (run_id={run_id})")
        else:
            print("  ⚠️  Aurora not configured — skipped persist")

    if report_path and not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        root = Path(__file__).resolve().parents[4]
        out = root / report_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"summary": full_summary, **result.to_dict()}, indent=2, default=str))
        print(f"  Report: {out}")

    return result


def lambda_handler(event, context):
    """AWS Lambda entry — daily or manual outcome eval."""
    gate = (event or {}).get("gate", "scheduled")
    horizon = int((event or {}).get("horizon_days", HORIZON_DAYS))
    result = run_evaluation(gate=gate, horizon_days=horizon, persist=True)
    body = result.to_dict()
    status = 200 if result.passed or result.trades_evaluated == 0 else 422
    return {"statusCode": status, "body": json.dumps(body)}
