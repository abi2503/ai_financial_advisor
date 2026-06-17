#!/usr/bin/env python3
"""Unit tests for trading outcome scoring rules."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "agents" / "trading"))

from learning.scoring import compute_realized_pnl, score_action  # noqa: E402


def test_buy_correct():
    outcome, correct, score = score_action("BUY", 3.5)
    assert outcome == "correct" and correct is True and score == 1.0


def test_buy_wrong():
    outcome, correct, score = score_action("BUY", -2.0)
    assert outcome == "incorrect" and correct is False and score == -1.0


def test_hold_neutral():
    outcome, correct, score = score_action("HOLD", 0.5)
    assert outcome == "neutral" and correct is None and score == 0.0


def test_sell_correct():
    outcome, correct, _ = score_action("SELL", -4.0)
    assert outcome == "correct" and correct is True


def test_realized_pnl_buy():
    pnl = compute_realized_pnl("BUY", 10, 100.0, 110.0)
    assert pnl == 100.0


if __name__ == "__main__":
    test_buy_correct()
    test_buy_wrong()
    test_hold_neutral()
    test_sell_correct()
    test_realized_pnl_buy()
    print("✅ trading scoring tests passed")
