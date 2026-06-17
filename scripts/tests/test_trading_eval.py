#!/usr/bin/env python3
"""
Trading floor outcome-based evaluation CLI.

Scores simulated_trades vs forward price movement (default 5d),
attributes correctness to each agent vote, persists to Aurora.

Usage:
  python3 scripts/tests/test_trading_eval.py
  python3 scripts/tests/test_trading_eval.py --gate observe --no-persist
  python3 scripts/tests/test_trading_eval.py --horizon 5

Requires: yfinance, boto3, AWS credentials, DB_CLUSTER_ARN + DB_SECRET_ARN
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "agents" / "trading"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from learning.trade_evaluator import run_evaluation  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Alex trading outcome eval")
    parser.add_argument("--gate", default="manual", help="manual | ci | scheduled | observe")
    parser.add_argument("--horizon", type=int, default=5, help="Forward price horizon in days")
    parser.add_argument("--no-persist", action="store_true", help="Skip Aurora write")
    args = parser.parse_args()

    result = run_evaluation(
        gate=args.gate,
        horizon_days=args.horizon,
        persist=not args.no_persist,
    )
    return 0 if result.passed or result.trades_evaluated == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
