"""
Alex Query Router — classifies user queries into fast / deep / chat.

Routing philosophy:
  chat  — greetings, financial education, general Q&A (like a normal chatbot)
  fast  — live data: specific tickers, prices, news, trading outlook
  deep  — SEC/MCP filings, multi-ticker comparisons
  Off-topic (weather, recipes, code) → chat with off_topic intent (polite block)
"""
from __future__ import annotations

import json
import logging
import re
from typing import Literal, Optional

import boto3
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
REGION = __import__("os").environ.get("AWS_REGION", "us-east-1")

ROUTER_MODEL = __import__("os").environ.get(
    "ROUTER_BEDROCK_MODEL", "us.amazon.nova-lite-v1:0"
)

RouteName   = Literal["fast", "deep", "chat", "debater"]
DeepKind    = Literal["mcp", "parallel"]

MCP_SIGNALS = [
    "sec", "10-k", "10k", "10-q", "10q", "filing", "edgar", "insider",
    "proxy statement", "annual report", "quarterly report", "8-k", "8k",
    "s-1", "form 4", "executive compensation", "risk factors",
    "analyst rating", "price target", "options flow",
]

PARALLEL_SIGNALS = [
    "compare", " vs ", "versus", " vs.", "which is better",
    "difference between", "contrast", "side by side", "pick between",
    "choose between", "better buy", "both ",
]

CHAT_SIGNALS = [
    "hello", "hi ", "hi!", "hey", "thanks", "thank you", "who are you",
    "what can you do", "what do you do", "help me", "good morning",
    "good afternoon", "good evening", "bye", "goodbye", "how are you",
    "what is alex", "introduce yourself",
]

OFF_TOPIC_SIGNALS = [
    "weather", "recipe", "cook me", "movie", "netflix", "song lyrics",
    "football score", "basketball game", "write python", "write code",
    "javascript function", "homework help", "solve this equation",
    "dating advice", "relationship advice",
    "blackhole", "black hole", "quantum physics", "solar system",
    "celebrity", "tv show", "video game",
]

EDU_FRAME = re.compile(
    r"\b(tell me about|what is|what are|how do|how does|explain|describe|define|can you explain)\b",
    re.I,
)

FINANCE_TOPIC_PATTERNS = [
    r"\b(bonds?|treasur|fixed income|stocks?|equit(y|ies)|etfs?|mutual funds?)\b",
    r"\b(inflation|interest rates?|diversif|asset allocation|portfolio)\b",
    r"\b(options?|futures?|derivatives?|dividends?|yield curve|credit rating)\b",
    r"\b(bull market|bear market|recession|monetary policy|fiscal policy|fed|federal reserve)\b",
    r"\b(pe ratio|p/e|market cap|valuation|fundamental analysis|technical analysis)\b",
    r"\b(401k|ira|roth|retirement planning|compound interest)\b",
    r"\b(invest(ing|ment)?|trading|forex|crypto|bitcoin|ethereum|hedge fund)\b",
    r"\b(s&p|nasdaq|dow jones|wall street|ipo|merger|acquisition)\b",
]

LIVE_RESEARCH_SIGNALS = [
    "price", "trading at", "stock price", "share price", "quote", "trading today",
    "right now", "latest news", "news on", "earnings", "outlook", "should i buy",
    "should i sell", "research on", "analyze ", "brief ", "update on", "what is happening",
    "how is .* doing", "performance of",
]

# Actionable / risky trading intent — flag, do not research or advise
POLICY_FLAG_PATTERNS: list[tuple[str, str]] = [
    (r"\b(i want|i wanna|i'm going|going to|want to|help me)\b.*\bshort\b", "risky_short_intent"),
    (r"\bhow\s+(do|can|should)\s+i\s+short\b", "actionable_short_advice"),
    (r"\bshort\b.*\b(aggress|yolo|all[\s-]?in|heavily|maximum|max out)\b", "aggressive_shorting"),
    (r"\baggress(ive|ively)\b.*\b(short|trade|bet|invest|leverage|position)\b", "aggressive_trading"),
    (r"\b(yolo|ape\s+in|go\s+all\s+in|bet\s+everything)\b", "reckless_trading"),
    (r"\b(pump\s+and\s+dump|manipulate\s+the\s+market|insider\s+tip)\b", "market_manipulation"),
    (r"\b(guaranteed\s+return|get\s+rich\s+quick|risk[\s-]?free\s+profit)\b", "fraudulent_claims"),
    (r"\b(all\s+my\s+(savings|money|portfolio)|mortgage\s+my\s+house)\b", "reckless_capital"),
    (r"\b(leverage|margin).{0,30}\b(max|100%|everything|aggress)\b", "excessive_leverage"),
    (r"\b(front\s*run|launder|tax\s+evasion|illegal\s+trade)\b", "illegal_activity"),
]


class RouteDecision(BaseModel):
    route:      RouteName
    deep_kind:  Optional[DeepKind] = None
    intent:     str = "general"
    entities:   list[str] = Field(default_factory=list)
    reasoning:  str = ""
    confidence: float = 0.8
    uses_mcp:   bool = False
    debater:    Optional[str] = None


NON_TICKER_WORDS = frozenset({
    "USA", "NYC", "LA", "SF", "DC", "UK", "EU", "US", "AM", "PM",
    "CEO", "CFO", "CTO", "COO", "IPO", "ETF", "GDP", "FDA", "AI",
    "IT", "HR", "PR", "TV", "PC", "API", "USD", "EUR", "GBP",
    "JPY", "SEC", "LLC", "INC", "THE", "AND", "FOR", "NOT", "ALL",
})

# Lowercase words after "about/on/for" that are not tickers
_ABOUT_WORD_STOP = frozenset({
    "bonds", "bond", "stock", "stocks", "market", "rates", "yield",
    "yields", "inflation", "recession", "fed", "the", "your", "my",
    "how", "what", "why", "when", "where", "them", "this", "that",
})


def _extract_tickers(text: str) -> list[str]:
    found = list(re.findall(r"\b[A-Z]{2,5}\b", text))
    # "tell about tsla" — lowercase tickers after about/on/for
    for m in re.finditer(
        r"\b(?:about|on|for|with|regarding)\s+([a-z]{2,5})\b",
        text.lower(),
    ):
        word = m.group(1)
        if word not in _ABOUT_WORD_STOP:
            found.append(word.upper())
    return list(dict.fromkeys(t for t in found if t not in NON_TICKER_WORDS))


def _entities_from_query(query: str, raw: list[str] | None) -> list[str]:
    tickers = set(_extract_tickers(query))
    if not tickers:
        return []
    return [e for e in (raw or []) if e in tickers] or list(tickers)


def _has_finance_topic(query: str) -> bool:
    lower = query.lower()
    return any(re.search(p, lower) for p in FINANCE_TOPIC_PATTERNS)


def _has_educational_frame(query: str) -> bool:
    return bool(EDU_FRAME.search(query))


def _is_policy_flag(query: str) -> tuple[bool, str]:
    """Detect actionable risky trading / harmful financial intent."""
    lower = query.lower()

    # Conceptual education — not flagged
    if re.search(
        r"\b(what is|what are|explain|tell me about|how does|define)\b.{0,40}\b(short selling|shorting|short sell)\b",
        lower,
    ):
        return False, ""
    if re.search(r"\b(what is|explain)\b.{0,20}\bshorting\b", lower):
        return False, ""

    for pattern, reason in POLICY_FLAG_PATTERNS:
        if re.search(pattern, lower, re.I):
            return True, reason
    return False, ""


def _is_off_topic(query: str) -> bool:
    lower = query.lower()
    # Explicit off-topic signals win even if a city acronym looks like a ticker
    if any(o in lower for o in OFF_TOPIC_SIGNALS):
        return not _has_finance_topic(query)
    if _has_finance_topic(query):
        return False
    if _extract_tickers(query):
        return False
    finance_anchor = [
        "stock", "bond", "market", "invest", "fed", "trade", "fund", "portfolio",
        "earnings", "sec", "ticker", "equity", "etf", "inflation", "rate",
    ]
    if any(f in lower for f in finance_anchor):
        return False
    if _has_educational_frame(query):
        return True
    return False


def _is_social_query(query: str) -> bool:
    q     = query.strip()
    lower = q.lower()
    if _extract_tickers(q):
        return False
    if len(q) > 100:
        return False
    if re.match(r"^(hi|hey|hello|yo|thanks|thank you|good morning|good afternoon|good evening|bye|goodbye)\b", lower, re.I):
        return True
    if re.search(r"\b(who are you|what can you do|what do you do|how are you|what is alex)\b", lower):
        return True
    if any(s in lower for s in CHAT_SIGNALS) and len(q) < 80:
        return True
    return False


def _is_educational_finance(query: str) -> bool:
    if _is_policy_flag(query)[0]:
        return False
    if _extract_tickers(query):
        return False
    lower = query.lower()
    if any(s in lower for s in MCP_SIGNALS):
        return False
    if any(s in lower for s in PARALLEL_SIGNALS) and "difference between" in lower:
        if not re.search(r"\b[A-Z]{2,5}\b.*\b[A-Z]{2,5}\b", query):
            return _has_finance_topic(query)
    return _has_finance_topic(query)


def _needs_live_research(query: str) -> bool:
    """Ticker-specific or explicit live market research — not general education."""
    tickers = _extract_tickers(query)
    lower   = query.lower()
    if not tickers:
        return False
    if any(re.search(s, lower) for s in LIVE_RESEARCH_SIGNALS):
        return True
    if re.search(r"\b(nvda|aapl|msft|tsla|amzn|goog|meta)\b", lower):
        return True
    # Bare ticker mention: "tell me about NVDA" → live research
    if len(query) < 60 and tickers:
        return True
    return False


def _regex_route(query: str) -> RouteDecision:
    q       = query.strip()
    lower   = q.lower()
    tickers = _extract_tickers(q)

    if _is_off_topic(q):
        return RouteDecision(
            route="chat", intent="off_topic",
            reasoning="Outside finance — I'll help redirect.",
            confidence=0.95,
        )

    if any(s in lower for s in MCP_SIGNALS):
        return RouteDecision(
            route="deep", deep_kind="mcp", intent="sec_research",
            entities=tickers, uses_mcp=True,
            reasoning="SEC filings / EDGAR / MCP research.",
            confidence=0.92,
        )

    has_parallel = any(s in lower for s in PARALLEL_SIGNALS)
    if has_parallel and len(tickers) >= 2:
        return RouteDecision(
            route="deep", deep_kind="parallel", intent="comparison",
            entities=tickers, uses_mcp=False,
            reasoning="Multi-ticker comparison — Deep Research.",
            confidence=0.9,
        )

    if has_parallel or (len(tickers) >= 2 and ("should i" in lower or " or " in lower)):
        return RouteDecision(
            route="deep", deep_kind="parallel", intent="comparison",
            entities=tickers, uses_mcp=False,
            reasoning="Complex comparison — Deep Research.",
            confidence=0.85,
        )

    if _needs_live_research(q):
        return RouteDecision(
            route="fast", intent="market_research",
            entities=tickers,
            reasoning="Live market data and news — Fast Research.",
            confidence=0.88,
        )

    if _is_educational_finance(q) or _is_social_query(q):
        return RouteDecision(
            route="chat", intent="education",
            reasoning="Financial Q&A — conversational response.",
            confidence=0.9,
        )

    # No ticker, no deep signals → chat (not fast)
    if not tickers:
        return RouteDecision(
            route="chat", intent="conversation",
            reasoning="Conversational financial assistant.",
            confidence=0.85,
        )

    return RouteDecision(
        route="fast", intent="market_research",
        entities=tickers,
        reasoning="Ticker mentioned — Fast Research.",
        confidence=0.7,
    )


def _llm_route(query: str, context_hint: str = "") -> Optional[RouteDecision]:
    try:
        bedrock = boto3.client("bedrock-runtime", region_name=REGION)
        ctx = f"\nRecent context:\n{context_hint[:400]}" if context_hint else ""
        prompt = f"""Classify ONLY this message. Ignore prior topics unless it's a clear follow-up.

Message: "{query}"{ctx}

JSON only:
{{
  "route": "fast|deep|chat",
  "deep_kind": "mcp|parallel|null",
  "intent": "greeting|education|market_research|sec_research|comparison|off_topic|conversation",
  "entities": ["TICKER"],
  "reasoning": "one short sentence",
  "confidence": 0.0-1.0,
  "uses_mcp": false
}}

Rules:
- chat: greetings, "tell me about bonds", financial education, general investing concepts, who are you
- fast: ONLY when user wants LIVE data on a specific stock (price, news, earnings today)
- deep+mcp: SEC, 10-K, EDGAR, insider filings
- deep+parallel: compare 2+ ticker symbols
- chat+off_topic: weather, recipes, coding — not finance at all
- "tell me about bonds" = chat (education), NOT fast
- "NVDA price today" = fast"""

        response = bedrock.invoke_model(
            modelId=ROUTER_MODEL,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": 300, "temperature": 0},
            }),
        )
        result = json.loads(response["body"].read())
        text   = result["output"]["message"]["content"][0]["text"].strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())

        route = data.get("route", "chat")
        if route not in ("fast", "deep", "chat"):
            route = "chat"

        deep_kind = data.get("deep_kind")
        if deep_kind == "null" or not deep_kind:
            deep_kind = None
        if route == "deep" and deep_kind not in ("mcp", "parallel"):
            deep_kind = "mcp" if data.get("uses_mcp") else "parallel"

        return RouteDecision(
            route=route,
            deep_kind=deep_kind if route == "deep" else None,
            intent=data.get("intent", "general"),
            entities=_entities_from_query(query, data.get("entities")),
            reasoning=data.get("reasoning", ""),
            confidence=float(data.get("confidence", 0.8)),
            uses_mcp=bool(data.get("uses_mcp", deep_kind == "mcp")),
        )
    except Exception as e:
        logger.warning(f"LLM router failed: {e}")
        return None


def classify_query(query: str, context_hint: str = "") -> RouteDecision:
    """Regex-first; LLM only when live research is plausible."""
    if not query or not query.strip():
        return RouteDecision(route="chat", intent="empty", reasoning="Empty query.", confidence=1.0)

    rx = _regex_route(query)

    # Hard overrides — never let session context change these
    flagged, flag_reason = _is_policy_flag(query)
    if flagged:
        return RouteDecision(
            route="chat", intent="policy_flag", entities=[],
            reasoning=f"Guardrail: {flag_reason.replace('_', ' ')} — research only, no trading advice.",
            confidence=0.99,
        )
    if _is_off_topic(query) or rx.intent == "off_topic":
        return RouteDecision(
            route="chat", intent="off_topic", entities=[],
            reasoning="Off-topic — guardrail will politely decline.",
            confidence=0.97,
        )
    if _is_social_query(query):
        return RouteDecision(
            route="chat", intent="greeting", entities=[],
            reasoning="Hi! Happy to chat about markets and research.",
            confidence=0.98,
        )

    from debater_registry import match_debater, get_debater

    if _is_educational_finance(query):
        return RouteDecision(
            route="chat", intent="education", entities=[],
            reasoning="I'll explain that conversationally.",
            confidence=0.95,
        )

    dm = match_debater(query)
    if dm:
        agent = get_debater(dm.agent_id)
        entities = [dm.ticker] if dm.ticker else []
        return RouteDecision(
            route="debater", intent="handoff", debater=dm.agent_id,
            entities=entities,
            reasoning=f"Handoff to {agent.name} — {agent.title}" if agent else "Debater handoff",
            confidence=0.93,
        )

    if rx.route == "deep" and rx.confidence >= 0.85:
        return rx

    if _needs_live_research(query):
        hint = context_hint if _looks_like_followup(query) else ""
        decision = _llm_route(query, hint)
        if decision and decision.route == "fast" and _needs_live_research(query):
            decision.entities = _entities_from_query(query, decision.entities)
            return decision
        return rx if rx.route == "fast" else RouteDecision(
            route="fast", intent="market_research",
            entities=_extract_tickers(query),
            reasoning="Live stock research.",
            confidence=0.85,
        )

    # Default: conversational (no ticker / no live research needed)
    if not _extract_tickers(query):
        return RouteDecision(
            route="chat",
            intent=rx.intent if rx.route == "chat" else "conversation",
            entities=[],
            reasoning="Conversational financial assistant.",
            confidence=0.9,
        )

    return rx


def _looks_like_followup(query: str) -> bool:
    lower = query.lower()
    return bool(re.search(
        r"\b(what about|how about|their|those|that stock|same|also|follow up|earlier|you said|previous)\b",
        lower,
    ))


def routing_steps(decision: RouteDecision) -> list[str]:
    steps = ["🔍 Analyzing your question..."]
    if decision.entities:
        steps.append(f"📌 Tickers: {', '.join(decision.entities[:6])}")
    steps.append(f"🧠 Intent: {decision.intent}")
    if decision.intent == "off_topic":
        steps.append("🛡️ Guardrail: off-topic query blocked")
    elif decision.intent == "policy_flag":
        steps.append("🛡️ Guardrail: risky trading intent flagged")
    elif decision.route == "debater":
        from debater_registry import get_debater
        agent = get_debater(decision.debater or "")
        if agent:
            steps.append(f"🤝 Delegating to: {agent.name} — {agent.title}")
            steps.append(f"🎯 Expertise: {agent.expertise}")
        else:
            steps.append("🤝 Delegating to Trading Floor specialist")
    elif decision.route == "fast":
        steps.append("⚡ Routing to: Fast Research (live data)")
    elif decision.route == "deep":
        label = "Deep Research (SEC + MCP)" if decision.deep_kind == "mcp" else "Deep Research (parallel)"
        steps.append(f"🔍 Routing to: {label}")
    else:
        steps.append("💬 Routing to: Conversation")
    if decision.reasoning:
        steps.append(f"💡 {decision.reasoning}")
    return steps
