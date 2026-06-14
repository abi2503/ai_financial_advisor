"""
Run a single Trading Floor debater agent for Alex chat handoffs.
Uses yfinance + news (same tools as researcher) and Nova for specialist reply.
"""
from __future__ import annotations

import asyncio
import logging

from debater_registry import DebaterAgent, get_debater

logger = logging.getLogger(__name__)


async def fetch_ticker_context(ticker: str) -> str:
    """Fetch live ticker metrics via yfinance (researcher tool stack)."""
    import time as time_mod

    def _fetch() -> str:
        import yfinance as yf
        t = ticker.upper().strip()
        stock = yf.Ticker(t)
        info  = stock.info or {}
        price = info.get("currentPrice") or info.get("regularMarketPrice") or "N/A"
        name  = info.get("longName") or t
        lines = [
            f"{name} ({t})",
            f"Price: ${price}" if price != "N/A" else "Price: N/A",
            f"Market Cap: {info.get('marketCap', 'N/A')}",
            f"P/E: {info.get('trailingPE', 'N/A')}",
            f"Forward P/E: {info.get('forwardPE', 'N/A')}",
            f"52W High/Low: {info.get('fiftyTwoWeekHigh', 'N/A')} / {info.get('fiftyTwoWeekLow', 'N/A')}",
            f"Revenue Growth: {info.get('revenueGrowth', 'N/A')}",
            f"Profit Margin: {info.get('profitMargins', 'N/A')}",
            f"Sector: {info.get('sector', 'N/A')}",
            f"Analyst Rating: {info.get('recommendationKey', 'N/A')}",
            f"Target Price: {info.get('targetMeanPrice', 'N/A')}",
        ]
        try:
            hist = stock.history(period="3mo")
            if not hist.empty:
                lines.append(f"3M Return: {((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100:.1f}%")
        except Exception:
            pass
        return "\n".join(str(x) for x in lines)

    return await asyncio.to_thread(_fetch)


def build_debater_prompt(agent: DebaterAgent, query: str, ticker: str | None, market_ctx: str) -> str:
    ticker_line = f"\nFOCUS TICKER: {ticker}\n" if ticker else ""
    return f"""You are {agent.name}, {agent.title} on the Alex AI Trading Floor.

BACKGROUND: {agent.background}
YOUR LENS: {agent.expertise}
{ticker_line}
LIVE MARKET DATA:
{market_ctx}

User question: {query}

Instructions:
- Answer in first person as {agent.name} using clear markdown
- Apply your specialist lens — cite exact numbers from the data above
- 3-4 concise paragraphs; bullets welcome for key evidence
- This is research analysis, NOT a trade recommendation — no explicit buy/sell orders
- If data is missing, say what you'd need and give qualitative analysis
- Sign off: — **{agent.name}**, {agent.title}"""


async def run_debater_handoff(agent_id: str, query: str, ticker: str | None) -> tuple[str, str]:
    """Returns (market_context, prompt) for streaming."""
    agent = get_debater(agent_id)
    if not agent:
        raise ValueError(f"Unknown debater: {agent_id}")

    market_ctx = "General macro / market context — no single ticker specified."
    if ticker:
        market_ctx = await fetch_ticker_context(ticker)

    prompt = build_debater_prompt(agent, query, ticker, market_ctx)
    return market_ctx, prompt
