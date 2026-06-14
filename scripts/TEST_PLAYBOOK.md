# Alex Test Playbook

> **Use after every addition.** Agent runs automated tests + deploy; **you oversee** the frontend steps below.
> Reply `Pass` or `Fail` at each checkpoint before moving on.

---

## Layer 1 — Automated (agent runs)

```bash
# Always (CI-safe)
./scripts/test_p0.sh --static

# After P0 / schema / context_service / ingest / deep routes
./scripts/test_p0.sh

# After trading changes
./scripts/test_trading.sh

# After RAG / ingest quality changes
python3 scripts/tests/test_ragas.py
```

**Gate:** All automated tests must pass before frontend testing.

---

## Layer 2 — Deploy (agent runs if backend changed)

| Change | Command |
|--------|---------|
| Researcher / context_service | `cd backend/researcher && bash deploy.sh` |
| Ingest / pgvector | `bash scripts/deploy_ingest.sh` |
| Trading orchestrator / debate | `bash scripts/deploy_trading.sh` |

**Gate:** ECS `/health` returns `"status": "healthy"`.

---

## Layer 3 — Frontend (you oversee)

### Phase 0 — Prep

**Step 0.1** — Start frontend:
```bash
cd frontend && npm run dev
```
**Pass:** Terminal shows `Ready` and `http://localhost:3000` (or `3001`).

**Step 0.2** — Wake Aurora (run at start of every session):
```bash
python3 scripts/aurora_warmup.py
```
**Pass:** `✅ Aurora connected` (may take 15–60s if auto-paused).

**Step 0.3** — (Optional) Backend health:
```bash
curl -s http://alex-alb-1582546453.us-east-1.elb.amazonaws.com/health | python3 -m json.tool
```
**Pass:** `"status": "healthy"`

**Step 0.4** — Sign in at localhost → land on `/dashboard` with your name.

**Checkpoint 0** — Pass/Fail for 0.1, 0.2, and 0.4.

---

### Phase 1 — Dashboard

**Step 1.1** — Scroll to **Your Portfolio Research**.
**Pass:** NVDA / ASML cards with headline, sentiment, digest.
**Proves:** `portfolio_digests` + user join; `context_service` SQL fixes.

**Step 1.2** — Cost snapshot visible (any dollar amount OK).
**Pass:** Section renders without error.

**Checkpoint 1** — Pass/Fail for 1.1 and 1.2.

---

### Phase 2 — Fast Research (~60 sec)

**Step 2.1** — Go to `/research`, **Fast** mode (blue toggle).

**Step 2.2** — Send: `Brief NVDA outlook`
**Pass:** Streams answer in ~60s with price table + news.
**Fail:** 503, Unauthorized, or hang >2 min.
**Proves:** ECS researcher deployed and responding.

**Checkpoint 2** — Pass/Fail + time taken.

---

### Phase 3 — Deep Research (3–5 min)

**Step 3.1** — Toggle **Deep** mode (purple).

**Step 3.2** — Send: `Analyze NVDA SEC filings and recent insider activity`
**Pass:** Reasoning steps appear; answer in 3–5 min with SEC/insider content.
**Fail:** 500 in <30s or empty response.
**Proves:** P0 `user_id` + `session_id` through `/api/research/deep/stream`.

**Checkpoint 3** — Pass/Fail (slow is OK; errors are not).

---

### Phase 4 — Trading Floor (~90 sec)

**Step 4.1** — Go to `/trading`. **Pass:** Page loads, **▶ Run Analysis** visible.

**Step 4.2** — Click **Run Analysis**.
**Pass:** Button → "Analyzing…"; tickers queued (ASML, NVDA).
**Proves:** Orchestrator deploy (no MessageGroupId bug).

**Step 4.3** — Wait ~90s, refresh if needed.
**Pass:** Trades or agent debate cards appear.
**Partial:** Queued but no trades — wait 60s more.

**Step 4.4** — If nothing queued: check `/portfolio` has holdings, retry.

**Checkpoint 4** — Pass/Fail; note queued tickers and trades.

---

## Scorecard

| Step | What | Pass? | Notes |
|------|------|-------|-------|
| 0.3 | Sign in → dashboard | | |
| 1.1 | Portfolio digest cards | | |
| 1.2 | Cost snapshot | | |
| 2.2 | Fast NVDA research | | |
| 3.2 | Deep NVDA SEC research | | |
| 4.2 | Run Analysis queues | | |
| 4.3 | Trades / debate appear | | |

---

## Phase-specific additions (append as we build)

| Phase | Extra frontend step |
|-------|---------------------|
| **Observe** | `/observe` → Research tab shows P50/P95 + expandable query rows (tools, MCP, APIs) |
| **P1** | Single chat input auto-routes fast/deep — no manual toggle |
| **P2** | Follow-up question uses prior context ("What about their P/E?") |
| **P3** | Deep stream saved in History; ingest shows `user_id` in DB |
| **P4** | Simulation P&L updates after trade |
| **P17** | `/observe` shows RAGAS scores |

---

## If something fails

Paste checkpoint + what you saw. Agent runs targeted diagnostics:

```bash
./scripts/test_p0.sh --full      # foundation + orchestrator
./scripts/test_trading.sh        # full debate pipeline
bash scripts/health_check.sh     # all services
```
