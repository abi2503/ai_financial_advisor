"""Outcome scoring rules for trading agent votes and committee decisions."""

from __future__ import annotations

HOLD_NEUTRAL_BAND_PCT = 2.0
TRIM_PARTIAL_SCORE = 0.5


def score_action(action: str, return_pct: float) -> tuple[str, bool | None, float]:
    """
    Score a trade action against forward return.

    Returns: (outcome_label, correct, score)
      outcome_label: correct | incorrect | neutral | partial
      correct: True/False/None (None for neutral HOLD)
      score: -1.0 .. +1.0
    """
    action = (action or "HOLD").upper()
    ret = float(return_pct)

    if action == "BUY":
        if ret > 0:
            return "correct", True, 1.0
        return "incorrect", False, -1.0

    if action == "SELL":
        if ret < 0:
            return "correct", True, 1.0
        return "incorrect", False, -1.0

    if action == "HOLD":
        if abs(ret) <= HOLD_NEUTRAL_BAND_PCT:
            return "neutral", None, 0.0
        return "incorrect", False, -0.5

    if action == "TRIM":
        if ret > 0:
            return "partial", True, TRIM_PARTIAL_SCORE
        if ret < -HOLD_NEUTRAL_BAND_PCT:
            return "correct", True, 0.75
        return "neutral", None, 0.0

    return "neutral", None, 0.0


def compute_realized_pnl(
    action: str,
    shares: int,
    entry_price: float,
    exit_price: float,
) -> float:
    """Paper P&L for a simulated trade over the eval horizon."""
    action = (action or "HOLD").upper()
    shares = int(shares or 0)
    if shares <= 0 or entry_price <= 0 or exit_price <= 0:
        return 0.0

    delta = exit_price - entry_price
    if action == "BUY":
        return round(shares * delta, 2)
    if action == "SELL":
        return round(shares * -delta, 2)
    if action == "TRIM":
        return round(shares * delta * 0.25, 2)
    return 0.0


def aggregate_accuracy(rows: list[dict]) -> dict[str, float]:
    """Summarize accuracy across evaluated trades and agent votes."""
    if not rows:
        return {
            "overall_accuracy": 0.0,
            "buy_accuracy": 0.0,
            "sell_accuracy": 0.0,
            "hold_neutral_rate": 0.0,
            "avg_pnl_pct": 0.0,
        }

    trade_rows = [r for r in rows if r.get("record_type") == "trade"]
    agent_rows = [r for r in rows if r.get("record_type") == "agent"]

    def _acc(subset: list[dict], action_filter: str | None = None) -> float:
        items = subset
        if action_filter:
            items = [r for r in subset if (r.get("action") or "").upper() == action_filter]
        scored = [r for r in items if r.get("correct") is not None]
        if not scored:
            return 0.0
        return round(sum(1 for r in scored if r["correct"]) / len(scored), 3)

    hold_rows = [r for r in trade_rows if (r.get("action") or "").upper() == "HOLD"]
    hold_neutral = [r for r in hold_rows if r.get("outcome") == "neutral"]

    return {
        "overall_accuracy": _acc(agent_rows),
        "buy_accuracy": _acc(trade_rows, "BUY"),
        "sell_accuracy": _acc(trade_rows, "SELL"),
        "hold_neutral_rate": round(len(hold_neutral) / max(len(hold_rows), 1), 3),
        "avg_pnl_pct": round(
            sum(float(r.get("return_pct") or 0) for r in trade_rows) / max(len(trade_rows), 1),
            3,
        ),
    }
