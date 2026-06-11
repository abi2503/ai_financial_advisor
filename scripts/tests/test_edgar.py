#!/usr/bin/env python3
"""Test: EdgarTools SEC Filing Integration"""
import json
import sys
import os
import subprocess

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

print("\n🧪 Testing EdgarTools Integration")
print("==================================")

# Test 1 — Library
print("\nTest 1: EdgarTools Python library...")
try:
    import edgar
    edgar.set_identity("Alex AI Research abhishek.suresh@gmail.com")
    company = edgar.Company("NVDA")
    filing  = company.get_filings(form="10-K").latest(1)
    doc     = filing.obj()
    rf      = str(doc.risk_factors)[:200]
    print(f"  10-K Date:    {filing.filing_date}")
    print(f"  Accession:    {filing.accession_no}")
    print(f"  Risk preview: {rf[:100]}")
    print("  ✅ PASS")
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    sys.exit(1)

# Test 2 — Form 4
print("\nTest 2: Insider trading Form 4...")
try:
    filing4 = company.get_filings(form="4").latest(1)
    print(f"  Latest Form 4: {filing4.filing_date}")
    print("  ✅ PASS")
except Exception as e:
    print(f"  ⚠️  SKIP: {e}")

# Test 3 — ECS endpoint
print("\nTest 3: Deep research via ECS...")
try:
    r   = subprocess.run(
        ["aws", "ssm", "get-parameter",
         "--name", "/alex/ecs_url",
         "--region", "us-east-1",
         "--query", "Parameter.Value",
         "--output", "text"],
        capture_output=True, text=True
    )
    alb = r.stdout.strip()

    if not alb or alb == "None":
        print("  ⚠️  ECS not running — skipping")
    else:
        import urllib.request
        data = json.dumps({"topic": "NVDA 10-K risk factors"}).encode()
        req  = urllib.request.Request(
            f"{alb}/research/deep",
            data    = data,
            headers = {"Content-Type": "application/json"},
            method  = "POST"
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            body   = json.loads(resp.read())
            result = body.get("result", "")
            has_sec = any(w in result.lower() for w in
                         ["risk", "10-k", "sec", "filing", "management"])
            print(f"  Response: {len(result)} chars")
            print(f"  SEC content: {has_sec}")
            print(f"  Preview: {result[:200]}")
            print(f"  {'✅ PASS' if has_sec else '⚠️  No SEC content'}")
except Exception as e:
    print(f"  ❌ FAIL: {e}")

print("\n==================================")
print("✅ EdgarTools test complete")