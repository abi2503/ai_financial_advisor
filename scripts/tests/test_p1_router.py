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
    test_routing_steps()
    print("\n" + "=" * 50)
    print(f"📊 {PASSED} passed, {FAILED} failed")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
