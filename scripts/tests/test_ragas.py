#!/usr/bin/env python3
"""
Alex RAGAS evaluation — CLI entrypoint.

Uses official RAGAS library + Bedrock LLM judge.
Results → Aurora (ragas_eval_runs + ragas_evaluations) + ragas_report.json

Usage:
  python3 scripts/tests/test_ragas.py
  python3 scripts/tests/test_ragas.py --smoke
  python3 scripts/tests/test_ragas.py --gate ci --no-persist

Requires:
  pip install -r backend/researcher/requirements-eval.txt
  AWS credentials + ALEX_SEARCH_API in .env
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "researcher"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / "researcher" / ".env")

from eval.ragas_runner import run_evaluation  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Alex RAGAS evaluation")
    parser.add_argument("--gate", default="manual", help="manual | ci | weekly | observe")
    parser.add_argument("--smoke", action="store_true", help="Run 3 queries only")
    parser.add_argument("--no-persist", action="store_true", help="Skip Aurora write")
    args = parser.parse_args()

    result = run_evaluation(
        gate=args.gate,
        smoke=args.smoke,
        persist=not args.no_persist,
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
