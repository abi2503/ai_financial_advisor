#!/usr/bin/env python3
"""P1 — Query router tests (CI-safe static + unit)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "researcher"))

from query_router import classify_query, routing_steps  # noqa: E402

PASSED = FAILED = 0


def ok(name: str):
    global PASSED
    PASSED += 1
    print(f"  ✅ {name}")


def fail(name: str, detail: str = ""):
    global FAILED
    FAILED += 1
    print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


def test_fast_route():
    print("\n── P1 fast routes ──")
    cases = [
        ("What is NVDA trading at?", "fast"),
        ("Brief AAPL outlook", "fast"),
        ("NVDA price today", "fast"),
    ]
    for q, expected in cases:
        d = classify_query(q)
        if d.route == expected:
            ok(f'"{q[:30]}..." → {d.route}')
        else:
            fail(q, f"expected {expected}, got {d.route}")


def test_deep_mcp():
    print("\n── P1 deep MCP ──")
    cases = [
        "Analyze NVDA SEC 10-K filing risks",
        "Show AAPL insider trading from EDGAR",
    ]
    for q in cases:
        d = classify_query(q)
        if d.route == "deep" and d.deep_kind == "mcp":
            ok(f'MCP: "{q[:35]}..."')
        else:
            fail(q, f"route={d.route} kind={d.deep_kind}")


def test_deep_parallel():
    print("\n── P1 deep parallel (was multi-agent) ──")
    cases = [
        "Compare NVDA vs AMD for AI chips",
        "Should I buy NVDA or AMD?",
    ]
    for q in cases:
        d = classify_query(q)
        if d.route == "deep" and d.deep_kind == "parallel":
            ok(f'parallel: "{q[:35]}..."')
        else:
            fail(q, f"route={d.route} kind={d.deep_kind}")


def test_chat_route():
    print("\n── P1 conversation ──")
    cases = [
        "Hello!",
        "Who are you?",
        "What can Alex do?",
        "tell me about bonds",
        "what is a government bond?",
        "what is inflation",
        "How is the Fed affecting tech?",
    ]
    for q in cases:
        d = classify_query(q)
        if d.route == "chat":
            ok(f'chat: "{q}"')
        else:
            fail(q, f"got {d.route}")


def test_debater_handoff():
    print("\n── P1 debater handoff ──")
    cases = [
        ("What's the RSI on NVDA?", "zara", "debater"),
        ("NVDA growth outlook and revenue momentum", "marcus", "debater"),
        ("Is TSLA overvalued bear case", "victoria", "debater"),
        ("How will Fed rate hikes affect AAPL?", "reid", "debater"),
        ("NVDA portfolio risk and position sizing", "elena", "debater"),
    ]
    for q, expected_agent, expected_route in cases:
        d = classify_query(q)
        if d.route == expected_route and d.debater == expected_agent:
            ok(f'"{q[:40]}" → {d.debater}')
        else:
            fail(q, f"route={d.route} debater={d.debater}")

    # Bare price → fast not debater
    d = classify_query("NVDA price today")
    if d.route == "fast":
        ok("NVDA price today → fast (not debater)")
    else:
        fail("NVDA price today", f"got {d.route}")


def test_policy_flag():
    print("\n── P1 policy guardrail ──")
    flagged = [
        "I want to short stocks agggresively",
        "I want to short stocks aggressively",
        "how do I short TSLA aggressively",
        "yolo all my savings into options",
    ]
    for q in flagged:
        d = classify_query(q)
        if d.route == "chat" and d.intent == "policy_flag":
            ok(f'flagged: "{q[:40]}"')
        else:
            fail(q, f"route={d.route} intent={d.intent}")

    allowed = [
        "what is short selling",
        "explain how shorting works",
    ]
    for q in allowed:
        d = classify_query(q)
        if d.intent != "policy_flag":
            ok(f'education ok: "{q}"')
        else:
            fail(q, "should not be policy_flag")


def test_off_topic():
    print("\n── P1 off-topic redirect ──")
    cases = [
        ("What's the weather in NYC?", "off_topic"),
        ("tell me about blackholes?", "off_topic"),
        ("explain quantum physics", "off_topic"),
    ]
    for q, expected_intent in cases:
        d = classify_query(q)
        if d.route == "chat" and d.intent == expected_intent:
            ok(f'"{q[:35]}" → chat {expected_intent}')
        else:
            fail(q, f"route={d.route} intent={d.intent}")


def test_chat_with_stale_context():
    print("\n── P1 chat ignores stale session context ──")
    stale = "USER: How is the Fed affecting tech stocks?\nALEX: Tech stocks are sensitive..."
    d = classify_query("Hey Alex?", stale)
    if d.route == "chat":
        ok('"Hey Alex?" → chat despite Fed context')
    else:
        fail("Hey Alex?", f"got {d.route} kind={d.deep_kind}")
    if not d.entities:
        ok("no hallucinated entities on greeting")
    else:
        fail("entities", str(d.entities))


def test_routing_steps():
    print("\n── P1 routing steps ──")
    d = classify_query("Compare NVDA vs AMD")
    steps = routing_steps(d)
    if steps and "Deep Research" in " ".join(steps):
        ok("steps mention Deep Research")
    else:
        fail("routing_steps", str(steps))


def test_follow_up_context():
    print("\n── P1 follow-up context ──")
    nvda_ctx = (
        "ALEX: **Nvidia (NVDA)** is poised for potential growth with a strong analyst consensus.\n"
        "USER: analyze nvda"
    )
    d = classify_query("give its PE ratio", nvda_ctx)
    if d.route == "fast" and d.entities and d.entities[0] == "NVDA":
        ok('"give its PE ratio" → fast NVDA from context')
    else:
        fail("give its PE ratio", f"route={d.route} entities={d.entities}")

    mu_ctx = (
        "ALEX: **Micron Technology (MU)** — Deep Research | June 15, 2026\n"
        "Options flow data indicates bullish sentiment among investors.\n"
        "USER: SEC filing details about micron"
    )
    d2 = classify_query("what is its market sentiment?", mu_ctx)
    if d2.route == "fast" and d2.entities and d2.entities[0] == "MU":
        ok('"what is its market sentiment?" → fast MU after Micron research')
    else:
        fail("market sentiment follow-up", f"route={d2.route} entities={d2.entities}")

    # PE must not be mistaken for a ticker
    d2 = classify_query("give its PE ratio", "")
    if d2.route == "chat":
        ok('"give its PE ratio" without context → chat (not PE ticker)')
    else:
        fail("PE without context", f"route={d2.route} entities={d2.entities}")

    amd_ctx = (
        "ALEX: **AMD — Insider Trading (Form 4) | June 13, 2026**\n"
        "Accession Number: 0000002488-26-000109\n"
        "Transaction details sourced from SEC EDGAR.\n"
        "USER: insider trade details for AMD"
    )
    d3 = classify_query("are there any other details I can know?", amd_ctx)
    if d3.route == "deep" and d3.deep_kind == "mcp" and d3.entities and d3.entities[0] == "AMD":
        ok('"any other details?" after AMD Form 4 → deep MCP with AMD')
    else:
        fail("AMD insider vague follow-up", f"route={d3.route} kind={d3.deep_kind} entities={d3.entities}")
    if d3.research_scope == "filing_form4":
        ok("AMD insider follow-up → filing_form4 scope")
    else:
        fail("AMD insider scope", f"got {d3.research_scope}")

    from query_router import enrich_follow_up_query
    enriched, scope = enrich_follow_up_query("are there any other details I can know?", amd_ctx)
    if enriched and "AMD" in enriched and scope and scope.scope == "filing_form4":
        ok("enrich_follow_up_query expands vague insider follow-up")
    else:
        fail("enrich_follow_up_query", f"topic={enriched} scope={getattr(scope, 'scope', scope)}")


def test_micron_sec_entities():
    print("\n── P1 company name → ticker ──")
    d = classify_query("SEC filing details about micron")
    if d.route == "deep" and "MU" in d.entities:
        ok("micron SEC → deep with MU entity")
    else:
        fail("micron SEC", f"route={d.route} entities={d.entities}")
    if d.research_scope == "sec_full":
        ok("broad SEC query → sec_full scope")
    else:
        fail("micron SEC scope", f"got {d.research_scope}")


def test_research_scope():
    print("\n── P1 scoped deep research ──")
    from query_router import infer_research_scope

    cases = [
        ("tell me about 10k filings for NVDA", "filing_10k", ["10-K"], False, False),
        ("show me the 8-K for TSLA", "filing_8k", ["8-K"], False, False),
        ("SEC filing details about micron", "sec_full", ["10-K", "4"], True, True),
        ("NVDA analyst ratings from MarketBeat", "analyst_only", [], True, False),
    ]
    for q, scope, forms, analyst, options in cases:
        s = infer_research_scope(q)
        ok_scope = s.scope == scope and s.sec_forms == forms
        ok_flags = s.use_analyst_browser == analyst and s.use_options_browser == options
        if ok_scope and ok_flags:
            ok(f'"{q[:35]}..." → {scope}')
        else:
            fail(q, f"scope={s.scope} forms={s.sec_forms} analyst={s.use_analyst_browser}")


def test_sec_conceptual_education():
    print("\n── P1 SEC conceptual education (not deep) ──")
    edu_cases = [
        "diffirence b/w 10k, 8k and 4k filing of a stock?",
        "what is the difference between 10-K and 8-K?",
        "explain Form 4 insider filings",
        "what is a 10-K filing?",
        "compare 10-Q vs 10-K",
        "when do companies file an 8-K?",
        "purpose of SEC Form 4",
    ]
    for q in edu_cases:
        d = classify_query(q)
        if d.route == "chat" and d.intent == "sec_education":
            ok(f'edu: "{q[:40]}..."')
        else:
            fail(q, f"route={d.route} intent={d.intent}")

    # Live SEC data requests must still go deep
    live_cases = [
        ("SEC filing details about micron", "deep"),
        ("tell me about 10k filings for NVDA", "deep"),
        ("show NVDA 8-K from EDGAR", "deep"),
    ]
    for q, expected in live_cases:
        d = classify_query(q)
        if d.route == expected:
            ok(f'live: "{q[:35]}..." → {d.route}')
        else:
            fail(q, f"expected {expected}, got {d.route} intent={d.intent}")


def test_trading_education():
    print("\n── P1 trading education (stop loss, etc.) ──")
    cases = [
        "explain stop loss?",
        "what is a stop loss",
        "explain take profit orders",
        "what is dollar cost averaging",
    ]
    for q in cases:
        d = classify_query(q)
        if d.route == "chat" and d.intent in ("education", "conversation", "sec_education"):
            ok(f'"{q}" → chat {d.intent}')
        elif d.route == "chat" and d.intent == "off_topic":
            fail(q, "should not be off_topic")
        else:
            fail(q, f"route={d.route} intent={d.intent}")


def test_leadership_routing():
    print("\n── P1 leadership / CEO queries ──")
    d = classify_query("CEO of TSLA")
    if d.route == "fast" and d.intent == "leadership" and d.entities and d.entities[0] == "TSLA":
        ok('"CEO of TSLA" → fast leadership with TSLA')
    else:
        fail("CEO of TSLA", f"route={d.route} intent={d.intent} entities={d.entities}")

    d2 = classify_query("who is the CFO of NVDA")
    if d2.route == "fast" and d2.intent == "leadership" and "NVDA" in d2.entities:
        ok('"who is the CFO of NVDA" → fast leadership')
    else:
        fail("CFO NVDA", f"route={d2.route} intent={d2.intent} entities={d2.entities}")

    d3 = classify_query("NVDA price today")
    if d3.route == "fast" and d3.intent == "market_research":
        ok('"NVDA price today" still → market_research (not leadership)')
    else:
        fail("NVDA price", f"route={d3.route} intent={d3.intent}")


def test_llm_finance_gate_unknown_concepts():
    """Obscure finance terms hit LLM gate — no new regex per concept."""
    print("\n── P1 LLM finance gate (unknown concepts) ──")
    from unittest.mock import patch
    import query_router as qr

    with patch.object(qr, "_llm_finance_gate", return_value=(True, "education")):
        for q in ("explain vega", "what is gamma in options", "define theta decay"):
            d = classify_query(q)
            if d.route == "chat" and d.intent == "education":
                ok(f'LLM gate: "{q}" → education')
            else:
                fail(q, f"route={d.route} intent={d.intent}")

    with patch.object(qr, "_llm_finance_gate", return_value=(False, "off_topic")):
        d = classify_query("explain photosynthesis")
        if d.intent == "off_topic":
            ok("LLM gate rejects non-finance")
        else:
            fail("photosynthesis", f"intent={d.intent}")


def main():
    print("🧪 P1 Query Router Tests")
    print("=" * 50)
    test_fast_route()
    test_deep_mcp()
    test_deep_parallel()
    test_chat_route()
    test_debater_handoff()
    test_policy_flag()
    test_off_topic()
    test_chat_with_stale_context()
    test_follow_up_context()
    test_micron_sec_entities()
    test_research_scope()
    test_sec_conceptual_education()
    test_trading_education()
    test_leadership_routing()
    test_llm_finance_gate_unknown_concepts()
    test_routing_steps()
    print("\n" + "=" * 50)
    print(f"📊 {PASSED} passed, {FAILED} failed")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
