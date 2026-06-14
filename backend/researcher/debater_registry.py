"""
Debater agent registry — domain matching for Alex handoffs.
Maps queries to Trading Floor specialists (Marcus, Victoria, Zara, Reid, Elena).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DebaterAgent:
    id:         str
    name:       str
    title:      str
    expertise:  str
    background: str
    patterns:   tuple[str, ...]


DEBATERS: dict[str, DebaterAgent] = {
    "marcus": DebaterAgent(
        id="marcus",
        name="Marcus Chen",
        title="Growth Analyst",
        expertise="Revenue growth, earnings momentum, competitive moats, bull-case valuation",
        background="Former Goldman Sachs TMT analyst. Finds the bull case in growth stocks.",
        patterns=(
            r"\b(growth|revenue growth|earnings beat|earnings momentum|moat|TAM|bull case)\b",
            r"\b(forward pe|margin expansion|market share|innovation)\b",
            r"\b(is .+ overpriced|undervalued growth)\b",
        ),
    ),
    "victoria": DebaterAgent(
        id="victoria",
        name="Victoria Sterling",
        title="Short-Side Research Director",
        expertise="Bear cases, overvaluation, short interest, forensic red flags",
        background="Former Citadel short seller. Skeptical of management guidance.",
        patterns=(
            r"\b(bear case|short thesis|overvalued|overpriced|bubble)\b",
            r"\b(short interest|accounting|fraud|red flag|downside risk)\b",
            r"\b(crowded trade|earnings quality|skeptic)\b",
        ),
    ),
    "zara": DebaterAgent(
        id="zara",
        name="Zara Patel",
        title="Quantitative Strategist",
        expertise="RSI, MACD, moving averages, options flow, technical signals",
        background="MIT PhD quant. Pure signals — no opinions without data.",
        patterns=(
            r"\b(rsi|macd|technical|chart|moving average|50.?day|200.?day)\b",
            r"\b(options flow|put.?call|momentum|volume trend|support|resistance)\b",
            r"\b(overbought|oversold|technical outlook|quant signal)\b",
        ),
    ),
    "reid": DebaterAgent(
        id="reid",
        name="Reid Morrison",
        title="Macro Strategist",
        expertise="Fed policy, rates, recession risk, sector rotation, macro cycles",
        background="Former Fed economist. Connects stocks to macro forces.",
        patterns=(
            r"\b(fed|federal reserve|interest rate|yield curve|inflation)\b",
            r"\b(recession|macro|monetary policy|sector rotation|economic cycle)\b",
            r"\b(rate hike|rate cut|treasury|bond yield)\b",
        ),
    ),
    "elena": DebaterAgent(
        id="elena",
        name="Elena Vasquez",
        title="Chief Risk Officer",
        expertise="Position sizing, portfolio risk, drawdown, concentration, stop losses",
        background="BlackRock risk veteran. Position sizing is everything.",
        patterns=(
            r"\b(risk|position size|portfolio risk|concentration|drawdown)\b",
            r"\b(stop loss|hedge|trim|reduce exposure|diversif)\b",
            r"\b(how much should i|allocation|volatility exposure)\b",
        ),
    ),
}


def get_debater(agent_id: str) -> Optional[DebaterAgent]:
    return DEBATERS.get(agent_id)


@dataclass
class DebaterMatch:
    agent_id: str
    ticker:   Optional[str]
    score:    int


def _score_debaters(query: str) -> dict[str, int]:
    lower = query.lower()
    return {
        aid: sum(1 for p in agent.patterns if re.search(p, lower, re.I))
        for aid, agent in DEBATERS.items()
    }


def _is_bare_price_query(query: str) -> bool:
    """'NVDA price today' → fast research, not debater handoff."""
    from query_router import _extract_tickers

    lower = query.lower()
    if not _extract_tickers(query):
        return False
    if not re.search(r"\b(price|trading at|quote|stock price|how much|worth)\b", lower):
        return False
    specialist = sum(_score_debaters(query).values())
    return specialist == 0


def match_debater(query: str) -> Optional[DebaterMatch]:
    """Return best debater handoff if query matches a specialist domain."""
    from query_router import _extract_tickers, _is_policy_flag

    if _is_policy_flag(query)[0]:
        return None
    if _is_bare_price_query(query):
        return None

    scores = _score_debaters(query)
    best_id, best_score = max(scores.items(), key=lambda x: x[1])
    if best_score < 1:
        return None

    tickers = _extract_tickers(query)
    agent   = DEBATERS[best_id]

    # Reid handles macro without a specific ticker
    if best_id == "reid" and best_score >= 1:
        return DebaterMatch(agent_id=best_id, ticker=tickers[0] if tickers else None, score=best_score)

    if not tickers:
        return None

    return DebaterMatch(agent_id=best_id, ticker=tickers[0], score=best_score)
