"""
Portfolio research dimensions — shared config for scheduler/planner/reporter.
Each 2-hour cycle rotates through dimensions so every stock gets fresh coverage.
"""
from datetime import datetime, timezone

UTC = timezone.utc

# Fast research (ECS /research) and deep research (ECS /research/deep)
DIMENSIONS = [
    {
        "id":   "news",
        "mode": "fast",
        "label": "Trending News",
        "topic": "Latest trending news, headlines, analyst commentary, and market sentiment for {ticker} ({company})",
    },
    {
        "id":   "price",
        "mode": "fast",
        "label": "Price Action",
        "topic": "Current price action, volume trends, technical indicators, and short-term outlook for {ticker}",
    },
    {
        "id":   "fundamentals",
        "mode": "fast",
        "label": "Fundamentals",
        "topic": "Latest earnings, revenue growth, margins, guidance, and fundamental outlook for {ticker}",
    },
    {
        "id":   "sec",
        "mode": "deep",
        "label": "SEC & Filings",
        "topic": "Recent SEC filings, 10-K/10-Q highlights, insider transactions, and regulatory news for {ticker}",
    },
    {
        "id":   "sector",
        "mode": "fast",
        "label": "Sector Context",
        "topic": "Sector trends, peer comparison, competitive positioning, and industry catalysts for {ticker}",
    },
]


def cycle_index(now=None) -> int:
    """2-hour cycle slot (0-11 per day)."""
    now = now or datetime.now(UTC)
    return (now.hour // 2) % len(DIMENSIONS)


def dimensions_for_cycle(now=None) -> list:
    """
    Pick dimensions for this 2-hour window:
    - Primary: rotating fast/deep dimension
    - Bonus deep SEC every 3rd cycle
    """
    idx  = cycle_index(now)
    dims = [DIMENSIONS[idx]]

    # Every 3rd cycle, also run SEC deep research (if not already primary)
    if idx % 3 == 0 and DIMENSIONS[idx]["id"] != "sec":
        sec = next(d for d in DIMENSIONS if d["id"] == "sec")
        dims.append(sec)

    return dims


def format_topic(dimension: dict, ticker: str, company: str) -> str:
    return dimension["topic"].format(ticker=ticker, company=company or ticker)
