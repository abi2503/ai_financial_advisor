"""
Test Aurora database operations.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent.parent / '.env')

import db

print("Testing Aurora database operations...")
print("=" * 50)

# Test 1 — Create user
print("\n1. Creating test user...")
user = db.create_user(
    clerk_id="test_clerk_123",
    email="test@alex.ai",
    name="Test User"
)
print(f"   ✅ User created: {user['id']}")

# Test 2 — Save research session
print("\n2. Saving research session...")
session = db.save_research_session(
    user_id=user['id'],
    topic="NVIDIA AI chips 2026",
    result="NVIDIA dominates with 80% market share...",
    vector_id="test-vector-id-123"
)
print(f"   ✅ Session saved: {session['id']}")

# Test 3 — Get research history
print("\n3. Getting research history...")
history = db.get_research_history(user['id'])
print(f"   ✅ Found {len(history)} sessions")
for h in history:
    print(f"      - {h['topic']} ({h['created_at'][:10]})")

# Test 4 — Add to portfolio
print("\n4. Adding to portfolio...")
stock = db.add_to_portfolio(user['id'], "NVDA", "NVIDIA Corporation")
print(f"   ✅ Added {stock['ticker']} to portfolio")

# Test 5 — Get portfolio
print("\n5. Getting portfolio...")
portfolio = db.get_portfolio(user['id'])
print(f"   ✅ Portfolio has {len(portfolio)} stocks")
for s in portfolio:
    print(f"      - {s['ticker']}: {s['company']}")

# Test 6 — Save preferences
print("\n6. Saving preferences...")
prefs = db.save_preferences(
    user_id=user['id'],
    risk_tolerance="aggressive",
    sectors=["technology", "semiconductors"]
)
print(f"   ✅ Preferences saved")

print("\n" + "=" * 50)
print("✅ All database tests passed!")