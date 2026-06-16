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
# LLM gate for ambiguous educational queries (avoid growing regex lists)
ROUTER_USE_LLM_GATE = __import__("os").environ.get("ROUTER_USE_LLM_GATE", "true").lower() != "false"

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

# SEC filing terms — used to detect conceptual vs live-data SEC questions
SEC_FILING_PATTERN = re.compile(
    r"\b(10[\s-]?k|8[\s-]?k|10[\s-]?q|form\s*4|(?:4[\s-]?k)(?:\s+filing)?|"
    r"sec\s+filing|edgar|proxy\s+statement|risk\s+factors?)\b",
    re.I,
)

SEC_COMPARE_FRAME = re.compile(
    r"\b(difference|diffirence|diff\b|compare|comparison|versus|contrast|"
    r"b/w|between|what is|what are|what's|explain|define|tell me about|"
    r"how does|how do|when is|why is|purpose of|meaning of|types? of)\b",
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

# Trading / risk concepts — educational "explain stop loss" etc.
INVESTING_EDU_PATTERNS = [
    r"\b(stop[\s-]?loss|take[\s-]?profit|trailing stop|profit target)\b",
    r"\b(limit order|market order|stop order|bracket order|order type)\b",
    r"\b(position sizing|risk management|risk[\s-]?reward|drawdown|volatility)\b",
    r"\b(dollar cost averaging|dca|rebalancing|tax[\s-]?loss harvesting)\b",
    r"\b(support|resistance|moving average|rsi|macd|bollinger)\b",
    r"\b(bullish|bearish|long position|short position|going long|going short)\b",
    r"\b(alpha|beta|sharpe|sortino|standard deviation)\b",
    r"\b(bid[\s-]?ask|spread|slippage|liquidity|volume)\b",
    r"\b(margin call|maintenance margin|pattern day trader)\b",
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
    research_scope: Optional[str] = None  # filing_10k | filing_8k | sec_full | inferred | ...


class ResearchScope(BaseModel):
    """What tools/sections deep research should use — answer only what was asked."""
    scope: str = "inferred"
    sec_forms: list[str] = Field(default_factory=list)
    use_analyst_browser: bool = False
    use_options_browser: bool = False
    include_recommendation: bool = False
    label: str = "Scoped research"


NON_TICKER_WORDS = frozenset({
    "USA", "NYC", "LA", "SF", "DC", "UK", "EU", "US", "AM", "PM",
    "CEO", "CFO", "CTO", "COO", "IPO", "ETF", "GDP", "FDA", "AI",
    "IT", "HR", "PR", "TV", "PC", "API", "USD", "EUR", "GBP",
    "JPY", "SEC", "LLC", "INC", "THE", "AND", "FOR", "NOT", "ALL",
    # Financial metric abbreviations — not stock symbols
    "PE", "EPS", "EBIT", "EBITDA", "ROI", "ROE", "ROA", "YOY", "QOQ",
    "CAGR", "FCF", "EV", "ATH", "ATL", "RSI", "MACD", "YTD", "MTD",
    # Assistant / chat role labels — not tickers
    "ALEX", "USER",
})

# Signals user wants live SEC data on a specific company — not conceptual education
LIVE_SEC_REQUEST = re.compile(
    r"\b(details?\s+(about|for|on)|filing\s+details|analyze|analysis\s+of|"
    r"latest|recent|show\s+me|fetch|get\s+(the|its)|read\s+the|"
    r"risks?\s+(from|in)|research\s+on)\b",
    re.I,
)

# Common company names → tickers (lowercase keys)
COMPANY_ALIASES: dict[str, str] = {
    "micron": "MU", "nvidia": "NVDA", "apple": "AAPL", "microsoft": "MSFT",
    "amazon": "AMZN", "google": "GOOGL", "alphabet": "GOOGL", "meta": "META",
    "tesla": "TSLA", "amd": "AMD", "intel": "INTC", "broadcom": "AVGO",
    "asml": "ASML", "netflix": "NFLX", "palantir": "PLTR", "coinbase": "COIN",
}

METRIC_SIGNALS = re.compile(
    r"\b(pe ratio|p/e|market cap|price|earnings|revenue|dividend|"
    r"52[\s-]?week|analyst|target|valuation|eps|outlook|sentiment|"
    r"news|catalyst|risk|recommendation|bullish|bearish|momentum)\b",
    re.I,
)

# Lowercase words after "about/on/for" that are not tickers
_ABOUT_WORD_STOP = frozenset({
    "bonds", "bond", "stock", "stocks", "market", "rates", "yield",
    "yields", "inflation", "recession", "fed", "the", "your", "my",
    "how", "what", "why", "when", "where", "them", "this", "that",
})


def _extract_tickers(text: str) -> list[str]:
    found = list(re.findall(r"\b[A-Z]{2,5}\b", text))
    # "tell about tsla" — lowercase tickers after about/on/for
    lower = text.lower()
    for m in re.finditer(
        r"\b(?:about|on|for|with|regarding)\s+([a-z]{2,5})\b",
        lower,
    ):
        word = m.group(1)
        if word not in _ABOUT_WORD_STOP:
            found.append(word.upper())
    # Company names: "SEC filing details about micron"
    for name, ticker in COMPANY_ALIASES.items():
        if re.search(rf"\b{re.escape(name)}\b", lower):
            found.append(ticker)
    return list(dict.fromkeys(t for t in found if t not in NON_TICKER_WORDS))


def extract_tickers_from_context(context_hint: str) -> list[str]:
    """Pull tickers from recent ALEX messages — e.g. follow-up after NVDA analysis."""
    if not context_hint:
        return []
    found: list[str] = []
    # Scan ALEX lines only, most recent first
    alex_lines = [
        ln for ln in context_hint.splitlines()
        if ln.strip().upper().startswith("ALEX:")
    ]
    for line in reversed(alex_lines):
        # Strip role prefix — "ALEX:" must not be parsed as ticker ALEX
        content = line.split(":", 1)[-1].strip()
        for m in re.finditer(r"\(([A-Z]{2,5})\)", content):
            sym = m.group(1)
            if sym not in NON_TICKER_WORDS:
                found.append(sym)
        for m in re.finditer(r"\*\*([A-Z]{2,5})\*\*", content):
            sym = m.group(1)
            if sym not in NON_TICKER_WORDS:
                found.append(sym)
        for m in re.finditer(r"\b([A-Z]{2,5})\b", content):
            sym = m.group(1)
            if sym not in NON_TICKER_WORDS:
                found.append(sym)
        if found:
            break
    return list(dict.fromkeys(found))


def _is_vague_continuation(query: str) -> bool:
    """User wants more on the prior topic without naming ticker or subject."""
    return bool(re.search(
        r"\b(any other|more details?|what else|tell me more|anything else|"
        r"other details?|can i know|know more|go deeper|elaborate|expand on that|"
        r"more information|additional details?|anything more)\b",
        query.lower(),
    ))


def _is_contextual_followup(query: str) -> bool:
    return (
        _looks_like_followup(query)
        or _has_pronoun_reference(query)
        or _is_vague_continuation(query)
    )


def _infer_context_topic(context_hint: str) -> str:
    """What the session was last discussing — drives vague follow-up routing."""
    if not context_hint:
        return ""
    content = ""
    for ln in reversed(context_hint.splitlines()):
        if ln.strip().upper().startswith("ALEX:"):
            content = ln.split(":", 1)[-1].lower()
            break
    if re.search(r"\b(insider|form\s*4|form 4)\b", content):
        return "insider"
    if re.search(r"\b(10[\s-]?k|8[\s-]?k|10[\s-]?q|sec filing|edgar)\b", content):
        return "sec"
    if re.search(r"\b(sentiment|options flow|analyst)\b", content):
        return "sentiment"
    if re.search(r"\b(price|trading at|pe ratio|market cap)\b", content):
        return "market"
    return "general"


def _follow_up_route_decision(
    query: str, context_hint: str, entities: list[str],
) -> RouteDecision:
    """Route contextual follow-ups using prior topic — insider → deep Form 4."""
    primary   = entities[0]
    ctx_topic = _infer_context_topic(context_hint)
    if ctx_topic == "insider":
        scope_q = f"{primary} insider Form 4 trading filings additional details"
        scope   = infer_research_scope(scope_q)
        return RouteDecision(
            route="deep", deep_kind="mcp", intent="follow_up",
            entities=entities, uses_mcp=True,
            research_scope=scope.scope,
            reasoning=f"Follow-up on {primary} insider / Form 4 — more EDGAR details.",
            confidence=0.93,
        )
    if ctx_topic == "sec":
        scope_q = f"{primary} SEC filings additional details"
        scope   = infer_research_scope(scope_q)
        return RouteDecision(
            route="deep", deep_kind="mcp", intent="follow_up",
            entities=entities, uses_mcp=True,
            research_scope=scope.scope,
            reasoning=f"Follow-up on {primary} SEC research.",
            confidence=0.92,
        )
    return RouteDecision(
        route="fast", intent="follow_up", entities=entities,
        reasoning=f"Follow-up on {primary} — live research.",
        confidence=0.94,
    )


def enrich_follow_up_query(
    query: str, context_hint: str,
) -> tuple[str, Optional[ResearchScope]]:
    """Turn vague follow-ups into a concrete research topic + optional forced scope."""
    entities = resolve_entities(query, context_hint)
    if not entities or not _is_contextual_followup(query):
        return query, None
    ticker    = entities[0]
    ctx_topic = _infer_context_topic(context_hint)
    if ctx_topic == "insider":
        effective = f"{ticker} additional Form 4 insider trading transactions and details"
        return effective, infer_research_scope(effective)
    if ctx_topic == "sec":
        effective = f"{ticker} additional SEC filing details"
        return effective, infer_research_scope(effective)
    if _is_vague_continuation(query):
        return f"{ticker} {query}", None
    return query, None


def resolve_entities(query: str, context_hint: str = "") -> list[str]:
    """Merge tickers from query and session context for follow-ups."""
    from_query = _extract_tickers(query)
    if from_query:
        return from_query
    if _is_contextual_followup(query):
        return extract_tickers_from_context(context_hint)[:3]
    return []


def infer_research_scope(query: str) -> ResearchScope:
    """
    Decide which tools/sections deep research should use.
    Answer ONLY what the user asked — do not run the full 4-source pipeline by default.
    """
    lower = query.lower()

    # --- Specific SEC form types (highest priority) ---
    if re.search(r"\b10[\s-]?k\b|annual report", lower):
        return ResearchScope(
            scope="filing_10k", sec_forms=["10-K"],
            label="10-K filing only — no analyst/options sections",
        )
    if re.search(r"\b8[\s-]?k\b", lower):
        return ResearchScope(
            scope="filing_8k", sec_forms=["8-K"],
            label="8-K filing only — current events report",
        )
    if re.search(r"\b10[\s-]?q\b|quarterly report", lower):
        return ResearchScope(
            scope="filing_10q", sec_forms=["10-Q"],
            label="10-Q filing only — quarterly report",
        )
    if re.search(r"\bform\s*4\b|insider\s+(trad|buy|sell|activity)|insider trading", lower):
        return ResearchScope(
            scope="filing_form4", sec_forms=["4"],
            label="Form 4 insider trading only",
        )

    # --- Non-SEC deep tools (no SEC unless also requested) ---
    wants_analyst = bool(re.search(
        r"\b(analyst rating|analyst ratings|price target|upgrade|downgrade|marketbeat|consensus)\b",
        lower,
    ))
    wants_options = bool(re.search(
        r"\b(options flow|unusual options|put.?call|unusualwhales)\b",
        lower,
    ))
    wants_sec_broad = bool(re.search(
        r"\b(sec\s+filings?|edgar|sec\s+research|risk factors?|proxy statement|executive compensation)\b",
        lower,
    )) or (
        re.search(r"\bsec\b", lower)
        and re.search(r"\bfiling", lower)
        and not re.search(r"\b10[\s-]?[kq]\b|\b8[\s-]?k\b", lower)
    )

    if wants_analyst and not wants_sec_broad and not wants_options:
        return ResearchScope(
            scope="analyst_only", use_analyst_browser=True,
            label="Analyst ratings only",
        )
    if wants_options and not wants_sec_broad and not wants_analyst:
        return ResearchScope(
            scope="options_only", use_options_browser=True,
            label="Options flow only",
        )

    # --- Broad SEC / full deep research ---
    if wants_sec_broad or re.search(r"\bsec\b.*\b(filing|filings|edgar)\b", lower):
        return ResearchScope(
            scope="sec_full",
            sec_forms=["10-K", "4"],
            use_analyst_browser=True,
            use_options_browser=True,
            include_recommendation=True,
            label="Full SEC + analyst + options deep research",
        )

    # --- Agent infers minimum tools from question keywords ---
    sec_forms: list[str] = []
    if any(s in lower for s in ("risk factor", "md&a", "business summary", "annual")):
        sec_forms.append("10-K")
    if any(s in lower for s in ("insider", "form 4")):
        sec_forms.append("4")
    if any(s in lower for s in ("8-k", "8k", "current report", "material event")):
        sec_forms.append("8-K")
    if any(s in lower for s in ("10-q", "10q", "quarterly")):
        sec_forms.append("10-Q")

    return ResearchScope(
        scope="inferred",
        sec_forms=sec_forms or ["10-K"],
        use_analyst_browser=wants_analyst,
        use_options_browser=wants_options,
        include_recommendation=wants_analyst or wants_options,
        label="Inferred scope — use minimum tools needed for this question",
    )


def deep_reasoning_steps(scope: ResearchScope) -> list[str]:
    """UI reasoning steps matched to actual research scope."""
    steps = ["🔌 Connecting to SEC EDGAR..."] if scope.sec_forms else []
    for form in scope.sec_forms:
        steps.append(f"📄 Fetching {form} filings...")
    if scope.use_analyst_browser:
        steps.append("📊 Reading analyst ratings...")
    if scope.use_options_browser:
        steps.append("📈 Scanning options flow...")
    if not steps:
        steps.append("🧠 Analyzing with available tools...")
    return steps


def _entities_from_query(query: str, raw: list[str] | None) -> list[str]:
    tickers = set(_extract_tickers(query))
    if not tickers:
        return []
    return [e for e in (raw or []) if e in tickers] or list(tickers)


def _has_finance_topic(query: str) -> bool:
    lower = query.lower()
    return any(re.search(p, lower) for p in FINANCE_TOPIC_PATTERNS + INVESTING_EDU_PATTERNS)


def _has_educational_frame(query: str) -> bool:
    return bool(EDU_FRAME.search(query)) or bool(SEC_COMPARE_FRAME.search(query))


def _mentions_sec_filings(query: str) -> bool:
    return bool(SEC_FILING_PATTERN.search(query))


def _is_live_sec_data_request(query: str) -> bool:
    """User wants real EDGAR data for a company — not a definitions question."""
    if _extract_tickers(query):
        return True
    if LIVE_SEC_REQUEST.search(query):
        return True
    lower = query.lower()
    return any(
        re.search(rf"\b{re.escape(name)}\b", lower)
        for name in COMPANY_ALIASES
    )


def _is_sec_conceptual_education(query: str) -> bool:
    """
    Conceptual SEC / filing questions with no ticker → chat, not deep research.

    Examples:
      "difference between 10-K, 8-K, and Form 4"  → True
      "when do companies file an 8-K?"            → True
      "what is a 10-K filing?"                    → True
      "NVDA latest 10-K"                          → False (has ticker)
      "SEC filing details about micron"           → False (company-specific live data)
    """
    if not _mentions_sec_filings(query):
        return False
    return not _is_live_sec_data_request(query)


def _should_llm_finance_gate(query: str) -> bool:
    """
    Ambiguous educational queries regex cannot classify — use Nova Lite once.
    Fast-path patterns (FINANCE_TOPIC / INVESTING_EDU) skip this call.
    """
    if not ROUTER_USE_LLM_GATE:
        return False
    lower = query.lower()
    if any(o in lower for o in OFF_TOPIC_SIGNALS):
        return False
    if _mentions_sec_filings(query) or _is_sec_conceptual_education(query):
        return False
    if _has_finance_topic(query) or _extract_tickers(query):
        return False
    if _has_educational_frame(query):
        return True
    # Short open questions without tickers — "what is vega?"
    if len(query) < 100 and re.search(r"\b(what is|what are|explain|define|how does)\b", lower):
        return True
    return False


def _llm_finance_gate(query: str) -> Optional[tuple[bool, str]]:
    """
    Lightweight finance relevance check — one Nova Lite call.
    Returns (is_finance, intent) or None on failure.
    """
    try:
        bedrock = boto3.client("bedrock-runtime", region_name=REGION)
        prompt = f"""You gate messages for Alex, a FINANCIAL RESEARCH assistant.

Decide if the message is about finance, investing, markets, trading, portfolios, or SEC/regulatory topics.

Finance INCLUDES (non-exhaustive): any investing/trading concept (stop loss, vega, gamma, theta, P/E, bonds, ETFs, Fed policy, 10-K education, options, risk, diversification, retirement accounts).

NOT finance: weather, recipes, sports scores, entertainment, general science, coding homework, relationships, celebrities.

Message: "{query}"

JSON only:
{{"finance": true|false, "intent": "education"|"off_topic"|"conversation", "confidence": 0.0-1.0}}"""

        response = bedrock.invoke_model(
            modelId=ROUTER_MODEL,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": 80, "temperature": 0},
            }),
        )
        result = json.loads(response["body"].read())
        text   = result["output"]["message"]["content"][0]["text"].strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data      = json.loads(text.strip())
        is_finance = bool(data.get("finance", False))
        intent     = data.get("intent", "education" if is_finance else "off_topic")
        if intent not in ("education", "off_topic", "conversation"):
            intent = "education" if is_finance else "off_topic"
        logger.info(f"LLM finance gate: finance={is_finance} intent={intent} q={query[:60]}")
        return is_finance, intent
    except Exception as e:
        logger.warning(f"LLM finance gate failed: {e}")
        return None


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
    if _mentions_sec_filings(query) or _is_sec_conceptual_education(query):
        return False
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
        "filing", "10-k", "10k", "8-k", "8k", "edgar", "insider",
        "stop loss", "stop-loss", "take profit", "margin", "option", "dividend",
    ]
    if any(f in lower for f in finance_anchor):
        return False
    if _has_educational_frame(query):
        # Educational + explicit off-topic signals → block; else let chat/education handle
        if any(o in lower for o in OFF_TOPIC_SIGNALS):
            return True
        return False
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
    if _is_sec_conceptual_education(query):
        return True
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

    if _is_sec_conceptual_education(q):
        return RouteDecision(
            route="chat", intent="sec_education",
            reasoning="Conceptual SEC/filing question — conversational explanation.",
            confidence=0.96,
        )

    if any(s in lower for s in MCP_SIGNALS):
        scope = infer_research_scope(q)
        return RouteDecision(
            route="deep", deep_kind="mcp", intent=scope.scope,
            entities=tickers, uses_mcp=True,
            reasoning=scope.label,
            confidence=0.92,
            research_scope=scope.scope,
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
- chat+education: ANY investing/trading/market concept explained (stop loss, vega, gamma, bonds, P/E, diversification, SEC filing types) — do NOT require exact keyword matches
- chat+off_topic: clearly NOT finance (weather, recipes, physics, coding, sports)
- fast: ONLY when user wants LIVE data on a specific stock (price, news, earnings today)
- deep+mcp: SEC, 10-K, EDGAR, insider filings for a company
- deep+parallel: compare 2+ ticker symbols
- When unsure if finance-related → prefer chat+education over off_topic
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

    if _is_social_query(query):
        return RouteDecision(
            route="chat", intent="greeting", entities=[],
            reasoning="Hi! Happy to chat about markets and research.",
            confidence=0.98,
        )

    # Conceptual SEC education — before LLM gate (regex is authoritative here)
    if _is_sec_conceptual_education(query):
        return RouteDecision(
            route="chat", intent="sec_education", entities=[],
            reasoning="I'll explain SEC filing types conversationally — no live EDGAR fetch.",
            confidence=0.96,
        )

    # Follow-up on prior ticker — before LLM gate
    if context_hint and _is_contextual_followup(query):
        entities = resolve_entities(query, context_hint)
        if entities:
            return _follow_up_route_decision(query, context_hint, entities)

    # LLM finance gate — ambiguous education (vega, stop loss w/o regex, etc.)
    if _should_llm_finance_gate(query):
        gate = _llm_finance_gate(query)
        if gate is not None:
            is_finance, gate_intent = gate
            if not is_finance:
                return RouteDecision(
                    route="chat", intent="off_topic", entities=[],
                    reasoning="Not finance-related (LLM gate).",
                    confidence=0.92,
                )
            return RouteDecision(
                route="chat",
                intent="education" if gate_intent != "conversation" else "conversation",
                entities=[],
                reasoning="Financial concept — conversational explanation (LLM gate).",
                confidence=0.91,
            )
        if _has_educational_frame(query):
            return RouteDecision(
                route="chat", intent="education", entities=[],
                reasoning="Educational question — let Alex answer (gate fallback).",
                confidence=0.75,
            )

    if _is_off_topic(query) or rx.intent == "off_topic":
        return RouteDecision(
            route="chat", intent="off_topic", entities=[],
            reasoning="Off-topic — guardrail will politely decline.",
            confidence=0.97,
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
        use_ctx = _is_contextual_followup(query)
        hint = context_hint if use_ctx else ""
        decision = _llm_route(query, hint)
        entities = resolve_entities(query, context_hint) if use_ctx else _extract_tickers(query)
        if decision and decision.route == "fast" and _needs_live_research(query):
            merged = _entities_from_query(query, decision.entities) or entities
            decision.entities = merged
            return decision
        return rx if rx.route == "fast" else RouteDecision(
            route="fast", intent="market_research",
            entities=entities or _extract_tickers(query),
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


def _has_pronoun_reference(query: str) -> bool:
    """User refers to prior subject without naming a ticker."""
    return bool(re.search(
        r"\b(its|it's|their|they|them|that stock|this stock|the stock|the company|that company|this company)\b",
        query.lower(),
    ))


def _looks_like_followup(query: str) -> bool:
    lower = query.lower()
    return bool(re.search(
        r"\b(what about|how about|their|those|that stock|same|also|follow up|earlier|you said|previous|"
        r"its|it's|this one|that one|the one|give me|show me|and what|what's its|what is its)\b",
        lower,
    )) or _has_pronoun_reference(query)


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
    elif decision.intent == "sec_education":
        steps.append("💬 Routing to: Conversation (SEC concepts)")
    elif decision.reasoning and "LLM gate" in decision.reasoning:
        steps.append("🧠 LLM finance gate: concept recognized")
    elif decision.route == "fast":
        steps.append("⚡ Routing to: Fast Research (live data)")
    elif decision.route == "deep":
        label = "Deep Research (SEC + MCP)" if decision.deep_kind == "mcp" else "Deep Research (parallel)"
        steps.append(f"🔍 Routing to: {label}")
        if decision.research_scope:
            steps.append(f"🎯 Scope: {decision.research_scope.replace('_', ' ')}")
    else:
        steps.append("💬 Routing to: Conversation")
    if decision.reasoning:
        steps.append(f"💡 {decision.reasoning}")
    return steps
