# Alex AI — Startup Strategy & Monetization Plan

> **Status:** PARKED — strategic planning document  
> **Created:** June 13, 2026  
> **Technical companion:** `Alex_Master_Implementation_Plan.md`  
> **Product:** AI financial intelligence platform with conversational research, autonomous agent trading simulation, and quant intelligence

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [What Alex Is (Product Positioning)](#what-alex-is)
3. [The Problem We Solve](#the-problem-we-solve)
4. [Competitive Landscape](#competitive-landscape)
5. [Revenue Models](#revenue-models)
6. [Startup Ideas (7 Paths)](#startup-ideas)
7. [Recommended Launch Strategy](#recommended-launch-strategy)
8. [Unit Economics & Cost Structure](#unit-economics--cost-structure)
9. [Pricing Tiers (Proposed)](#pricing-tiers-proposed)
10. [Go-to-Market Plan](#go-to-market-plan)
11. [Regulatory & Compliance](#regulatory--compliance)
12. [Moat & Defensibility](#moat--defensibility)
13. [Fundraising Narrative](#fundraising-narrative)
14. [12-Month Roadmap to Revenue](#12-month-roadmap-to-revenue)
15. [Risks & Mitigations](#risks--mitigations)

---

## Executive Summary

Alex is not a brokerage and not a robo-advisor. It is an **AI-native financial intelligence layer** that sits on top of a user's portfolio and gives them:

- Institutional-quality research on demand (conversational, remembered, sourced)
- A transparent multi-agent trading floor that paper-trades and explains every decision
- Quant intelligence (charts, indicators, macro) via MCP-connected data sources
- Collective debate memory that learns which agents are right over time

**The money is not in executing trades for users.** The money is in **selling intelligence, transparency, and time saved** to investors who currently pay for Bloomberg ($24k/yr), Koyfin ($300/yr), Seeking Alpha ($240/yr), and financial advisors (1% AUM) — and still feel uninformed.

**Recommended first revenue path:** B2C subscription ($19–49/mo) targeting active retail investors, launched after MVP (Sprints 1–3, ~3 weeks of engineering).

---

## What Alex Is

```
┌─────────────────────────────────────────────────────────────┐
│  ALEX = Your Personal AI Hedge Fund Research Team             │
│                                                             │
│  🧠 Ask anything → intelligent answer (fast or deep)        │
│  📊 Quant charts + indicators on demand                     │
│  🏛️ 6 agents debate your holdings every 2 hours             │
│  📈 Paper simulation shows what agents would have done        │
│  🧬 Memory — Alex remembers every conversation & debate       │
│  🔍 Full transparency — see every agent argument, not a black box │
└─────────────────────────────────────────────────────────────┘
```

### What Alex Is NOT

| Not this | Why |
|----------|-----|
| A brokerage (Robinhood, IBKR) | We don't execute real trades (yet) — avoids SEC broker-dealer registration |
| A robo-advisor (Wealthfront, Betterment) | We don't manage money or give personalized investment advice |
| A signal service ("buy NVDA now!") | We show reasoning, not blind tips — reduces liability |
| ChatGPT with a finance skin | We have live market data, agent debates, portfolio memory, quant MCP |

### One-Line Pitch

> **"Alex is the AI research team and trading floor you can't afford to hire — transparent, remembered, and always watching your portfolio."**

---

## The Problem We Solve

### For Retail Investors ($10k–$500k portfolios)

| Pain | Current workaround | Cost | Alex solution |
|------|-------------------|------|---------------|
| "Should I buy NVDA?" — no one to ask | Reddit, Twitter, ChatGPT | Free but unreliable | Alex researches with live data + memory |
| No time to read 10-K filings | Skip them, buy on hype | Opportunity cost | Deep research agent + SEC MCP |
| Don't know if portfolio is performing well | Check once a month | Anxiety | 2h autonomous research + simulation comparison |
| Financial advisors cost 1% AUM | Pay $1,000/yr on $100k | $500–5,000/yr | Alex Pro at $29/mo = $348/yr |
| Black-box AI answers | Trust blindly | Risk | Full agent debate transparency |

### For Active Traders / FIRE Community

| Pain | Alex solution |
|------|---------------|
| Information overload — 50 tabs open | Single chat, auto-routed to fast/deep |
| No systematic process | 6-agent debate = structured bull/bear/quant/risk |
| Can't backtest intuition | Paper simulation with full replay |
| Forget why they bought something | Session RAG + trading floor intelligence memory |

### For RIAs / Small Fund Managers (B2B, later)

| Pain | Alex solution |
|------|---------------|
| Junior analysts cost $80k+/yr | Alex researches 24/7 at marginal cost |
| Client questions need fast answers | White-label Alex chat per client portfolio |
| Compliance requires reasoning documentation | Every agent vote logged in vector store |

---

## Competitive Landscape

| Competitor | What they do | Price | Alex advantage |
|------------|-------------|-------|----------------|
| **ChatGPT / Claude** | General AI, no live data | $20/mo | Live market data, portfolio-aware, agent debates, memory |
| **Perplexity Finance** | Search + summarize news | Free–$20/mo | Deeper SEC research, quant indicators, trading simulation |
| **Koyfin** | Charts + fundamentals dashboard | $0–$300/yr | Conversational + autonomous agents + debate transparency |
| **Seeking Alpha** | Crowdsourced stock analysis | $240/yr | AI agents with quant data, not human bloggers |
| **TradingView** | Charts + social ideas | $0–$360/yr | AI interprets charts + connects to portfolio + simulates trades |
| **Composer** | AI-driven trading strategies | $30/mo + fees | More transparent (see agent debates), paper sim first |
| **Magnifi** | AI search for ETFs/stocks | $14/mo | Deeper single-stock research, multi-agent, quant MCP |
| **Bloomberg Terminal** | Institutional everything | $24,000/yr | 1/100th the price, 80% of what retail needs |
| **Human RIA** | Personalized advice | 0.5–1% AUM | 10x cheaper, always available, full transparency |

### Alex's Unique Wedge

1. **Multi-agent debate transparency** — no competitor shows 5 agents arguing bull vs bear with quant evidence
2. **Collective debate memory** (`trading_floor_intelligence`) — agents learn from past debates
3. **Simulation vs reality comparison** — "agents would have done better today"
4. **Unified intelligence** — chat + research + quant + trading in one memory graph

---

## Revenue Models

### Model 1: B2C Subscription (Primary — recommended launch)

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | 5 Alex queries/day, 1 portfolio ticker, manual trading analysis |
| **Pro** | $29/mo | Unlimited queries, full portfolio, autonomous 2h research, simulation |
| **Quant** | $49/mo | Pro + chart rendering, options flow, technical indicators, priority deep research |
| **Team** | $99/mo | Quant + 3 seats, shared watchlists, API access (limited) |

**Rationale:** Retail investors already pay $14–30/mo for inferior AI finance tools (Magnifi, Composer). Alex offers more depth.

**Target:** 1,000 paying users × $29/mo = **$29,000 MRR** ($348k ARR)

---

### Model 2: B2B API — "Alex Intelligence API"

Sell the intelligence layer to fintech apps, neobanks, and RIAs.

| API Product | Price | Buyer |
|-------------|-------|-------|
| Research API | $0.05/query | Fintech apps needing stock research |
| Debate API | $0.10/ticker analysis | Trading platforms wanting agent opinions |
| Quant Snapshot API | $0.02/snapshot | Charting apps needing indicators |
| Portfolio Digest API | $500/mo flat | RIAs with 50+ client portfolios |

**Rationale:** Every fintech app wants AI finance features but can't build multi-agent infrastructure. Alex becomes the intelligence backend.

**Target:** 10 B2B customers × $500/mo = **$5,000 MRR**

---

### Model 3: White-Label for RIAs

RIA pays $200–500/mo per advisor seat. Alex runs behind their brand:
- Client-facing chat: "Ask [Firm Name] AI about your portfolio"
- Auto-generated client research memos (hedge fund style)
- Compliance-friendly audit trail (every agent vote in vector store)

**Rationale:** 15,000+ RIAs in the US, each with 50–200 clients. One RIA replacing one junior analyst ($80k/yr) pays for itself 13x over.

**Target:** 20 RIAs × $300/mo = **$6,000 MRR**

---

### Model 4: Affiliate / Referral Revenue

| Partner | Commission | Integration |
|---------|-------------|-------------|
| Brokerage referral (IBKR, Alpaca) | $50–200 per funded account | "Execute this trade" → deep link to broker |
| Premium data upsell (Polygon, Unusual Whales) | Revenue share | Quant tier includes premium data |
| Financial education courses | 30% affiliate | Alex recommends based on knowledge gaps |

**Rationale:** Non-intrusive monetization. Alex says "here's the analysis" not "buy now through our broker."

**Target:** 50 referrals/mo × $100 = **$5,000/mo** (at scale)

---

### Model 5: Data & Intelligence Licensing

Anonymized, aggregated intelligence products:

| Product | Buyer | Price |
|---------|-------|-------|
| Agent Sentiment Index | Quant funds, media | $1,000–5,000/mo |
| Sector Debate Digest | Financial newsletters | $500/mo |
| Retail Positioning Report | Institutional investors | $2,000/mo |

**Rationale:** Aggregate agent votes across users → "72% of Alex agents are bullish on AI sector this week." Unique data no one else has.

**Target:** 3 data customers × $2,000/mo = **$6,000 MRR** (Year 2+)

---

### Model 6: Premium Simulation ("Alex Prop Desk")

Gamified paper trading league:

| Feature | Price |
|---------|-------|
| Join monthly simulation league | $9/mo |
| Compete against other users' agent configs | — |
| Winner gets Pro subscription credit | — |
| Leaderboard + agent accuracy rankings | — |

**Rationale:** Trading competitions are proven (eToro, Public.com). Alex's agent debates make it educational, not gambling.

---

### Model 7: Enterprise — Family Offices & Small Funds

Custom deployment on their AWS account:

| Package | Price | Includes |
|---------|-------|----------|
| Alex Enterprise | $2,000–10,000/mo | Private deployment, custom agents, their data sources |
| On-premise option | $50,000 setup + $5,000/mo | VPC-isolated, compliance audit trail |

**Rationale:** Family offices ($5M–100M AUM) want AI but can't use public ChatGPT with portfolio data.

---

## Startup Ideas

### Idea 1: "AI Research Team for Retail" (Recommended MVP → Launch)

**What:** B2C subscription. Alex researches your portfolio every 2 hours, answers any question, shows agent debates.

**Why it wins:** Clear value prop, low regulatory risk (research, not advice), fast to market.

| Metric | Estimate |
|--------|----------|
| Time to launch | 3–4 weeks (MVP) |
| CAC (organic/Reddit/X) | $5–15 |
| LTV (12-mo retention 60%) | $210 |
| LTV/CAC | 14–42x |
| Break-even users | ~150 Pro subscribers |
| AWS cost per user/mo | $2–5 (see unit economics) |
| Gross margin | 85–90% |

---

### Idea 2: "Transparent AI Trading Floor" (Differentiation play)

**What:** Lead with the 6-agent debate simulation. "Watch AI agents argue about your stocks."

**Why it wins:** Viral potential — debate replays are shareable content. Nobody else shows this.

| GTM | Post debate replay clips on X/Reddit/YouTube |
| Monetization | Free to watch, Pro to run on your portfolio |
| Viral hook | "My AI agents voted 4-1 to SELL NVDA — here's why" |

---

### Idea 3: "Alex for Advisors" (B2B, higher ARPU)

**What:** White-label Alex for RIAs. Client-facing chat + auto research memos.

**Why it wins:** RIAs have budget, need compliance trail, can't build this themselves.

| Metric | Estimate |
|--------|----------|
| Time to launch | 8–10 weeks (needs compliance review) |
| ARPU | $300/advisor/mo |
| Sales cycle | 2–4 weeks |
| Break-even | 20 advisors |

---

### Idea 4: "Quant Intelligence API" (Developer-first)

**What:** Sell MCP-connected quant data + agent analysis as API.

**Why it wins:** Every fintech startup needs this; building multi-agent infra is 6+ months.

| Comparable | Polygon.io ($199/mo), Alpha Vantage ($50/mo) |
| Alex edge | Agent interpretation included, not just raw data |

---

### Idea 5: "AI Portfolio Coach" (Consumer subscription)

**What:** Position Alex as a coach, not an advisor. "Learn to think like a hedge fund analyst."

**Why it wins:** Educational framing reduces regulatory risk. Appeals to FIRE/learning community.

| Feature | Coach framing |
|---------|--------------|
| Agent debates | "See how professionals analyze stocks" |
| Simulation | "Practice without risking real money" |
| Quant charts | "Learn to read technical indicators" |
| Memory | "Build your investment thesis over time" |

---

### Idea 6: "Agent Sentiment Data Product" (B2B data, Year 2)

**What:** Aggregate anonymized agent votes → sentiment indices by sector/ticker.

**Why it wins:** Unique data asset. No one publishes "what AI agents think" at scale.

| Product | Example output |
|---------|---------------|
| Alex AI Sentiment Index | "NVDA: 78% agent bullishness (n=1,200 debates)" |
| Sector Rotation Signal | "Agents rotating from tech to energy this week" |
| Contrarian Alert | "Agents unanimously bullish — contrarian flag" |

---

### Idea 7: "Alex Prop League" (Gamification + community)

**What:** Monthly paper trading competition using Alex agents. Users customize agent weights and compete.

**Why it wins:** Community + retention + viral loops. TradingView meets fantasy football.

| Revenue | $9/mo league entry, sponsorships, Pro upsell |

---

## Recommended Launch Strategy

### Phase 1: Build + Validate (Month 1–2)

```
Week 1–3:  MVP (Sprints 1–3 from Master Plan)
Week 4:    Private beta — 20 users from network
Week 5–6:  Iterate on feedback, add quant Tier 1 (P13)
Week 7–8:  Public beta launch — Free tier live
```

### Phase 2: Monetize (Month 3–4)

```
Launch Pro tier ($29/mo) via Stripe
Content marketing: debate replay clips on X/Reddit
Target: 100 paying users
Add trading floor intelligence (P14) as Pro feature
```

### Phase 3: Grow (Month 5–8)

```
Launch Quant tier ($49/mo) with Polygon data
Quant chart embeds in chat
Referral program (1 month free per referral)
Target: 500 paying users
Explore RIA white-label conversations
```

### Phase 4: Scale (Month 9–12)

```
B2B API beta
Agent Sentiment Index prototype
Target: 1,000 paying users + 5 B2B pilots
Consider seed fundraise ($500k–1M) if metrics support
```

---

## Unit Economics & Cost Structure

### Current AWS Costs (from your live deployment)

| Service | Daily cost (observed) | Monthly est. |
|---------|----------------------|--------------|
| Aurora Serverless | ~$0.10 | ~$3 |
| ECS Researcher (when running) | ~$0.15 | ~$4.50 |
| Lambda (all agents) | ~$0.05 | ~$1.50 |
| Bedrock (Nova Pro/Lite) | ~$0.30 | ~$9 |
| SageMaker embedding | ~$0.05 | ~$1.50 |
| SQS + EventBridge + S3 | ~$0.02 | ~$0.60 |
| API Gateway | ~$0.01 | ~$0.30 |
| **Total (dev session)** | **~$0.40/day** | **~$12/mo** |

### Projected Cost Per Active User (at scale)

| Users | AWS infra/mo | Bedrock AI/mo | Data APIs/mo | Total/mo | Cost/user |
|-------|-------------|---------------|-------------|----------|-----------|
| 100 | $50 | $200 | $50 | $300 | $3.00 |
| 1,000 | $200 | $1,500 | $200 | $1,900 | $1.90 |
| 10,000 | $800 | $12,000 | $1,000 | $13,800 | $1.38 |

### Cost Drivers Per User Action

| Action | Bedrock cost | Data API cost | Total |
|--------|-------------|---------------|-------|
| Fast Alex query | ~$0.01–0.03 | $0 (yfinance) | ~$0.02 |
| Deep Alex query | ~$0.05–0.15 | ~$0.01 | ~$0.08 |
| Trading debate (6 agents) | ~$0.10–0.20 | ~$0.02 | ~$0.15 |
| Portfolio research (per stock) | ~$0.05–0.10 | ~$0.01 | ~$0.07 |
| Quant chart render | ~$0.01 | ~$0.005 | ~$0.015 |

### Pro User Economics ($29/mo)

```
Revenue:                    $29.00/mo
AWS + AI cost (30 queries,  −$3.00/mo
  2 debates/day, research):
Data APIs (Polygon):        −$0.50/mo (amortized)
Stripe fees (2.9%):          −$0.84/mo
─────────────────────────────────────
Gross profit:               $24.66/mo (85% margin)
```

### Break-Even Analysis

| Scenario | Fixed costs/mo | Variable cost/user | Price | Break-even users |
|----------|---------------|-------------------|-------|-----------------|
| Solo founder | $500 (tools, data) | $3 | $29 | **20 Pro users** |
| Small team (2) | $15,000 | $3 | $29 | **580 Pro users** |
| With office | $30,000 | $3 | $29 | **1,160 Pro users** |

**You break even at ~20 paying users as a solo founder.** This is highly achievable.

---

## Pricing Tiers (Proposed)

### Free Tier — "Alex Lite"

| Feature | Limit |
|---------|-------|
| Alex chat queries | 5/day |
| Portfolio tickers | 1 |
| Trading analysis | Manual only (1/day) |
| Research memory | Session only (no cross-session) |
| Agent debates visible | Last 1 only |
| Quant charts | No |

**Purpose:** Acquisition funnel. Show value, upsell to Pro.

### Pro Tier — $29/mo — "Alex Pro"

| Feature | Included |
|---------|----------|
| Unlimited Alex chat | ✅ Auto-routed fast/deep |
| Full portfolio | ✅ Unlimited tickers |
| Autonomous research | ✅ Every 2h per stock |
| Paper trading simulation | ✅ Full replay |
| Agent debates | ✅ Full history + transparency |
| Session memory | ✅ Cross-session RAG |
| Trading floor intelligence | ✅ Debate memory search |
| Daily digest email | ✅ |

### Quant Tier — $49/mo — "Alex Quant"

| Feature | Included |
|---------|----------|
| Everything in Pro | ✅ |
| Chart rendering in chat | ✅ Candlestick + indicators |
| Technical indicators | ✅ RSI, MACD, BB, ATR |
| Options flow data | ✅ Put/call, unusual activity |
| Macro dashboard | ✅ FRED: rates, CPI, yields |
| Priority deep research | ✅ Faster ECS allocation |
| IV rank + volatility | ✅ |

### Team Tier — $99/mo — "Alex Desk"

| Feature | Included |
|---------|----------|
| Everything in Quant | ✅ |
| 3 seats | ✅ |
| Shared watchlists | ✅ |
| API access | 1,000 calls/mo |
| Export research memos | ✅ PDF |
| Priority support | ✅ |

---

## Go-to-Market Plan

### Channel 1: Content-Led Growth (Primary, $0 CAC)

| Content type | Platform | Example |
|-------------|----------|---------|
| Debate replay clips | X, Reddit r/stocks, r/investing | "My 6 AI agents debated NVDA — bull won 4-2" |
| Alex answers | YouTube Shorts, TikTok | "I asked AI if Jensen Huang's GTC speech means buy NVDA" |
| Simulation results | Blog, newsletter | "Alex simulation beat my portfolio by 3.2% this month" |
| Quant chart analysis | X, StockTwits | Auto-generated chart + Alex commentary image |

### Channel 2: Community Seeding

| Community | Approach |
|-----------|----------|
| r/algotrading, r/stocks, r/financialindependence | Genuine value posts, not spam |
| X finance (#fintwit) | Daily agent sentiment summaries |
| Discord investing servers | Free tier for members |
| Product Hunt launch | Target #1 Product of the Day |

### Channel 3: Partnerships (Month 3+)

| Partner type | Deal |
|-------------|------|
| Finance YouTubers (10k–100k subs) | Free Pro for review video |
| Newsletter writers (Substack) | Embed Alex research in newsletter |
| Brokerage API partners | "Analyze with Alex" button |

### Channel 4: Paid Acquisition (Month 6+, if unit economics work)

| Channel | Target CAC | Expected conversion |
|---------|-----------|-------------------|
| Google Ads ("AI stock research") | $10–20 | 5–10% to Pro |
| X Ads (finance targeting) | $8–15 | 3–5% to Pro |
| Reddit Ads (r/stocks) | $5–10 | 5–8% to Pro |

Only scale paid when LTV/CAC > 5x confirmed.

---

## Regulatory & Compliance

### What Alex Can Say (Safe)

- "Here's what the data shows about NVDA"
- "My agents debated and 4/6 voted bullish"
- "The simulation would have bought 5 shares"
- "RSI is 68, historically overbought territory"
- "This is research and education, not financial advice"

### What Alex Must NOT Say (Guardrailed)

- "You should buy NVDA now"
- "Guaranteed 20% returns"
- "Put your life savings in..."
- "I recommend you sell everything"
- Personalized advice without RIA registration

### Regulatory Positioning

| Classification | Applies? | Action |
|---------------|----------|--------|
| Investment Adviser (SEC) | **No** — if we provide research/education, not personalized advice | Disclaimer on every response |
| Broker-Dealer | **No** — we don't execute trades | Paper simulation only |
| Financial data provider | **Low risk** | Terms of service |
| AI disclosure | **Yes** — SEC AI guidance 2024 | "Generated by AI agents" label |

### Required Legal (before paid launch)

| Item | Cost | Timeline |
|------|------|----------|
| Terms of Service + Privacy Policy | $500–1,500 (legal template) | Week 1 |
| "Not financial advice" disclaimer | Built into guardrails (P10) | Engineering |
| GDPR/CCPA compliance | Clerk handles auth; add data export | Week 2 |
| RIA review (if pursuing B2B) | $2,000–5,000 | Month 3+ |

---

## Moat & Defensibility

| Moat | How it builds over time |
|------|------------------------|
| **Debate intelligence memory** | More debates → better agent weights → better analysis → more users → more debates |
| **Per-user RAG graph** | Each user's Alex knows their portfolio, history, preferences — switching cost increases |
| **Agent accuracy tracking** | RL weights create proven track record — "Marcus is 72% accurate on tech stocks" |
| **Quant MCP infrastructure** | Hard to replicate multi-agent + MCP + vector + simulation stack |
| **Collective sentiment data** | Aggregated agent votes become unique data product |
| **Network effects** | Prop league + leaderboards + shared agent configs |

---

## Fundraising Narrative

### If Raising Seed ($500k–$1.5M)

**Thesis:** AI is democratizing financial tools, but current solutions are either too shallow (ChatGPT) or too expensive (Bloomberg). Alex is the AI-native research platform for the 100M+ global retail investors with $10k–$500k portfolios.

**Traction targets for fundraise:**
- 500+ paying users ($15k MRR)
- 60%+ monthly retention
- 10+ debate analyses per user per week
- Documented agent accuracy track record

**Use of funds:**
| Allocation | % | Purpose |
|-----------|---|---------|
| Engineering | 50% | 2 engineers × 12 months |
| Data APIs | 15% | Polygon, Finnhub, premium sources |
| GTM | 25% | Content, partnerships, Product Hunt |
| Legal/compliance | 10% | RIA review, terms, B2B contracts |

**Comparable raises:**
- Composer (AI trading): $3.5M seed
- Magnifi (AI finance search): $8M Series A
- Koyfin (finance dashboard): Bootstrapped to $5M ARR

---

## 12-Month Roadmap to Revenue

| Month | Engineering | Business | Revenue target |
|-------|------------|----------|---------------|
| 1 | MVP (Sprints 1–3) | Private beta (20 users) | $0 |
| 2 | Quant + debate memory (P13, P14) | Public beta, content creation | $0 |
| 3 | Pro tier launch (Stripe) | Product Hunt, Reddit launch | $500 MRR (20 users) |
| 4 | RL + observability | YouTuber partnerships | $2,000 MRR (70 users) |
| 5 | Scout + sentinel agents | Referral program | $5,000 MRR (170 users) |
| 6 | Quant tier launch ($49) | Paid ads test ($500 budget) | $10,000 MRR (300 users) |
| 7 | B2B API beta | 3 RIA pilot conversations | $12,000 MRR |
| 8 | White-label demo | First RIA contract | $15,000 MRR |
| 9 | Agent Sentiment Index | Data product pilot | $18,000 MRR |
| 10 | Mobile-responsive PWA | Team tier launch | $22,000 MRR |
| 11 | Prop league beta | Community growth | $25,000 MRR |
| 12 | Enterprise package | Seed fundraise or profitability | $30,000 MRR ($360k ARR) |

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| SEC/regulatory action | High | Research-only positioning, disclaimers, no trade execution, guardrails |
| AI hallucination on financial data | High | Live data via MCP (not LLM memory), source citations, confidence scores |
| Users expect guaranteed returns | Medium | Simulation labeled "paper trading", no performance promises |
| AWS/Bedrock costs spike at scale | Medium | Per-user rate limits, query caching, quant_snapshots TTL |
| Competition from ChatGPT finance | Medium | Depth moat: debates, simulation, memory, quant — ChatGPT won't build this |
| Low willingness to pay | Medium | Free tier proves value; target active investors who already pay for tools |
| Data API costs eat margin | Low | Tier 1 free sources for Free/Pro; premium data only on Quant tier |
| Key person risk (solo founder) | Medium | Document everything (these plan docs), modular architecture |

---

## Summary: How Alex Makes Money in Trading

**Alex does not make money BY trading.** Alex makes money by selling the **intelligence, transparency, and infrastructure** that helps users trade (or invest) better:

```
┌────────────────────────────────────────────────────────────┐
│  WHERE THE MONEY IS                                        │
│                                                            │
│  1. Subscription — users pay for AI research team          │
│  2. Quant tier — users pay for charts, indicators, flow     │
│  3. B2B API — fintechs pay for agent intelligence           │
│  4. White-label — RIAs pay for client-facing AI            │
│  5. Data licensing — institutions pay for agent sentiment    │
│  6. Affiliates — broker referrals (non-intrusive)           │
│  7. Gamification — prop league entry fees                   │
│                                                            │
│  WHERE THE MONEY IS NOT                                      │
│                                                            │
│  ✗ Executing trades (requires broker-dealer license)        │
│  ✗ Managing money (requires RIA registration)               │
│  ✗ Selling stock tips (liability + low retention)           │
│  ✗ Guaranteed returns (illegal)                             │
└────────────────────────────────────────────────────────────┘
```

**Fastest path to first dollar:** Launch Pro at $29/mo after MVP, target 20 users from Reddit/X finance communities. Break-even at 20 users. $29k MRR at 1,000 users.

---

## Document Index

| Document | Purpose |
|----------|---------|
| `Startup.md` | **This file** — business strategy, monetization, costs |
| `Alex_Master_Implementation_Plan.md` | Unified technical implementation (P0–P14) |
| `Alex_AI_2.0.md` | Conversational AI architecture |
| `Alex_Trading_Floor_2.0.md` | Trading simulation architecture |

---

*Review with technical plans in `Alex_Master_Implementation_Plan.md`. Approve business direction before building paid tiers.*
