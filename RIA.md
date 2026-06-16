# RIA Copilot — Product Report & Alex Architecture Leverage Plan

> **Status:** Strategic product spec — not yet implemented  
> **Created:** June 14, 2026  
> **Product codename:** RIA Copilot (white-label Alex for Registered Investment Advisors)  
> **Companion docs:** `usecases.md` (A2), `Startup.md` (Model 3), `Alex_Master_Implementation_Plan.md`, `Alex_report.md`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The RIA Problem](#2-the-ria-problem)
3. [Product Positioning](#3-product-positioning)
4. [How Alex Architecture Maps to RIA Copilot](#4-how-alex-architecture-maps-to-ria-copilot)
5. [Multi-Tenant Model (Firm → Advisor → Client)](#5-multi-tenant-model-firm--advisor--client)
6. [Feature Set](#6-feature-set)
7. [Compliance & Regulatory Framework](#7-compliance--regulatory-framework)
8. [Implementation Phases on Alex Codebase](#8-implementation-phases-on-alex-codebase)
9. [Infrastructure & Terraform Changes](#9-infrastructure--terraform-changes)
10. [API & Integration Surface](#10-api--integration-surface)
11. [Pricing & Unit Economics](#11-pricing--unit-economics)
12. [Go-to-Market for RIAs](#12-go-to-market-for-rias)
13. [Competitive Landscape](#13-competitive-landscape)
14. [MVP Roadmap (6–8 Weeks)](#14-mvp-roadmap-68-weeks)
15. [Risks & Mitigations](#15-risks--mitigations)
16. [Document Index](#16-document-index)

---

## 1. Executive Summary

**RIA Copilot** is a white-label, agentic AI research platform built on the Alex stack. It lets Registered Investment Advisors and small fund managers:

- Auto-generate **client research memos** every 2 hours (portfolio-aware, sourced)
- Answer client questions via **firm-branded chat** with full audit trail
- Run **multi-agent debates** on holdings and document reasoning for compliance
- Review AI output in an **advisor console** before client delivery (human-in-the-loop)

**One-line pitch:**

> **"RIA Copilot is the junior analyst your firm can't hire — research memos, client Q&A, and compliance-ready reasoning, running on the same agentic engine as Alex."**

### Why build on Alex (not from scratch)

| Alex asset | RIA Copilot reuse | Build new |
|------------|-------------------|-----------|
| ECS researcher + router + RAG | ✅ 90% | White-label UI, firm branding |
| Portfolio scheduler + digests | ✅ 85% | Per-client batching, memo templates |
| 6-agent trading debate | ✅ 70% | Rename personas → investment committee |
| pgvector + session memory | ✅ 95% | Client-scoped isolation |
| Observability + cost agent | ✅ 90% | Firm-level billing dashboard |
| Guardrails (P10) | ✅ 80% | RIA-specific disclaimers, approval gates |
| Clerk auth | ✅ 60% | Firm/advisor/client RBAC |
| Terraform modules 0–9 | ✅ 100% | Optional dedicated tenant VPC (enterprise) |

**Estimated engineering:** 6–8 weeks for MVP on top of Alex MVP (Sprints 1–3 complete).  
**Target ARPU:** $300/advisor/month · **Break-even:** ~20 advisor seats ($6,000 MRR).

---

## 2. The RIA Problem

### Who is the customer

| Segment | AUM range | Clients | Pain intensity |
|---------|-----------|---------|----------------|
| Solo RIA | $20M–$100M | 30–80 | High — advisor does everything |
| Small firm | $100M–$500M | 80–300 | Very high — 2–5 advisors, no research desk |
| Breakaway team | $50M–$200M | 40–120 | High — left wirehouse, lost research support |

~**15,000+ RIAs** in the US (SEC IAPD); majority lack dedicated research staff.

### Acute pains (validated by Startup.md + industry pattern)

| Pain | Current workaround | Cost / risk |
|------|-------------------|-------------|
| **10+ hrs/week** writing client research updates | Manual Bloomberg/Koyfin + Word memos | $80k/yr junior analyst equivalent |
| Client asks "what's happening with my NVDA?" at 9pm | Advisor Googles or ignores until morning | Client satisfaction risk |
| Compliance wants **documented reasoning** for recommendations | Advisor writes notes after the fact | Audit gap, FINRA exposure |
| No systematic bull/bear process | Gut feel + CNBC | Inconsistent advice quality |
| Can't scale personalized touch | Generic quarterly letters | Churn to larger firms |
| ChatGPT with client portfolio data | Compliance violation (no audit, data leakage) | Firm liability |

### What RIAs will pay for

1. **Time back** — memos written while they sleep  
2. **Compliance armor** — every AI output logged with sources and agent votes  
3. **Client experience** — branded portal that feels like a $1B firm  
4. **Not replacing the advisor** — AI as copilot, advisor approves and owns relationship  

---

## 3. Product Positioning

### What RIA Copilot IS

```
┌─────────────────────────────────────────────────────────────────┐
│  RIA COPILOT = White-label Alex for advisory firms               │
│                                                                 │
│  📋 Auto research memos per client portfolio (2h schedule)      │
│  💬 Firm-branded client chat ("Ask [Firm] Intelligence")        │
│  🏛️ Investment committee debate — logged for compliance          │
│  ✅ Advisor approval queue — nothing reaches client unreviewed   │
│  📊 Firm dashboard — all clients, costs, agent accuracy          │
└─────────────────────────────────────────────────────────────────┘
```

### What RIA Copilot IS NOT

| Not this | Why |
|----------|-----|
| Robo-advisor (Wealthfront) | RIA retains discretion; Copilot produces research, not allocation decisions |
| CRM (Redtail, Wealthbox) | Integrates with CRM; does not replace it |
| Portfolio management system (Orion, Tamarac) | Reads holdings via import/API; does not execute trades |
| Replacement for RIA registration | The **human advisor** remains the registered investment adviser |
| Alex B2C with a logo swap | Requires firm tenancy, approval workflows, compliance exports |

### Alex B2C vs RIA Copilot

| Dimension | Alex B2C | RIA Copilot |
|-----------|----------|-------------|
| User | Retail investor | Advisor + end client |
| Branding | Alex | Firm white-label |
| AI output | Direct to user | Advisor review → client (optional auto for low-risk) |
| Compliance | "Not financial advice" | Firm supervises; audit export for SEC/FINRA exams |
| Pricing | $29/mo | $300/advisor/mo |
| Tenancy | `user_id` = investor | `firm_id` → `advisor_id` → `client_id` |
| Scheduler | One portfolio per user | Batch: all clients under firm |

---

## 4. How Alex Architecture Maps to RIA Copilot

### Layer-by-layer mapping

```mermaid
flowchart TB
    subgraph ria_ui [RIA Copilot UI — NEW]
        ADV[Advisor Console]
        CLIENT[Client Portal — white-label]
        APPROVE[Approval Queue]
    end

    subgraph alex_brain [Alex Brain — REUSE]
        ROUTER[Query Router]
        CHAT[Unified Chat SSE]
        RAG[RAG Engine]
        DEEP[Deep Research + MCP]
    end

    subgraph alex_hands [Alex Hands — ADAPT]
        SCHED[EventBridge 2h Scheduler]
        PLANNER[Planner Lambda]
        REPORTER[Reporter Lambda]
        DEBATE[6-Agent Committee]
    end

    subgraph alex_data [Alex Data Plane — EXTEND]
        DIGESTS[(portfolio_digests)]
        VECTORS[(research_vectors)]
        MEMOS[(client_memos — NEW)]
        AUDIT[(compliance_audit_log — NEW)]
    end

    subgraph alex_observe [Alex Observe — REUSE]
        OBS[/observe + firm cost]
        COST[P21 Cost Agent]
        GUARD[Guardrails]
    end

    CLIENT --> ROUTER
    ADV --> APPROVE
    APPROVE --> CLIENT
    ROUTER --> CHAT --> RAG
    SCHED --> PLANNER --> REPORTER --> DIGESTS
    REPORTER --> MEMOS
    DEBATE --> AUDIT
    DIGESTS --> ADV
    MEMOS --> APPROVE
```

### Component reuse matrix

| Alex component | File / module | RIA Copilot role | Change required |
|----------------|---------------|------------------|-----------------|
| **Query router** | `backend/researcher/query_router.py` | Route client vs advisor vs compliance queries | Add `audience: client\|advisor` intent |
| **Unified chat** | `frontend/app/api/alex/chat/route.ts` | Client-facing branded chat | Firm theme + stricter guardrails |
| **RAG engine** | `context_service.py`, `rag_engine.py` | Client-scoped memory | Scope vectors to `client_id` |
| **Portfolio research** | `scheduler.py` → `planner.py` → `reporter.py` | Nightly/2h memo generation per client | Loop clients per firm |
| **Portfolio digests** | `portfolio_digests` table | Raw research cards | Feed memo composer |
| **6-agent debate** | `debate_engine.py`, trading agents | Investment committee simulation | Rebrand agents; paper-only |
| **Trading orchestrator** | `orchestrator.py` | Batch debate per client watchlist | Firm-level queue |
| **Ingest + vectors** | `ingest_pgvector.py` | Memo + chat history retrieval | `firm_id` column |
| **Guardrails** | P10, Bedrock guardrail | Block personalized directives to clients | RIA disclaimer templates |
| **Observability** | `/observe`, `agent_observations` | Firm admin: cost per client, tool failures | Aggregate by `firm_id` |
| **Ops / cost agents** | `ops_agent.py`, P21 cost agent | Per-firm AWS + Bedrock bill-back | Tenant tags in reports |
| **Clerk auth** | `frontend` middleware | Advisor login | Clerk Organizations → `firm_id` |
| **Terraform** | `0_vpc` … `9_trading_floor` | Same AWS footprint | SSM per-firm config (enterprise tier) |

### Alex agents → RIA Investment Committee

Rebrand trading floor personas for advisor-friendly language (same models, same debate engine):

| Alex agent | RIA committee role | Client-facing label |
|------------|-------------------|---------------------|
| Marcus (growth) | Growth / bull case analyst | "Growth Perspective" |
| Victoria (value) | Value / fundamentals analyst | "Fundamentals Perspective" |
| Zara (quant) | Technical & quantitative analyst | "Market Data Perspective" |
| Reid (macro) | Macro & rates strategist | "Economic Context" |
| Elena (risk) | Risk & concentration reviewer | "Risk Review" |
| Scout (discovery) | New idea / drift monitor | "Opportunities Watch" |

**Compliance value:** Debate transcript + votes stored in `trading_floor_intelligence` (P14) = exam-ready reasoning artifact.

---

## 5. Multi-Tenant Model (Firm → Advisor → Client)

### Tenancy hierarchy

```
Firm (RIA legal entity)
  └── Advisor (Clerk org member / seat license)
        └── Client (household / account group)
              └── Portfolios (holdings — 1:N tickers)
                    └── Memos, chats, debates (scoped data)
```

### Schema extensions (new tables)

```sql
-- Firm tenancy
CREATE TABLE firms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(64) UNIQUE NOT NULL,        -- acme-wealth.riacopilot.com
  logo_url TEXT,
  primary_color VARCHAR(7),
  disclaimer_text TEXT NOT NULL,
  auto_publish_memos BOOLEAN DEFAULT false, -- false = advisor approval required
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE firm_advisors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  firm_id UUID REFERENCES firms(id),
  clerk_user_id VARCHAR(255) NOT NULL,
  role VARCHAR(20) DEFAULT 'advisor',       -- admin | advisor | readonly
  seat_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE firm_clients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  firm_id UUID REFERENCES firms(id),
  advisor_id UUID REFERENCES firm_advisors(id),
  display_name VARCHAR(255) NOT NULL,
  external_crm_id VARCHAR(100),             -- Redtail / Wealthbox ID
  clerk_user_id VARCHAR(255),               -- optional client portal login
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Link existing portfolios to firm clients
ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS firm_client_id UUID REFERENCES firm_clients(id);

-- Client research memos (advisor-facing artifact)
CREATE TABLE client_memos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  firm_id UUID NOT NULL,
  firm_client_id UUID NOT NULL,
  memo_date DATE NOT NULL,
  status VARCHAR(20) DEFAULT 'draft',       -- draft | pending_approval | published | rejected
  title TEXT,
  body_markdown TEXT NOT NULL,
  sources JSONB DEFAULT '[]',               -- SEC links, news, data citations
  agent_summary JSONB DEFAULT '{}',         -- committee vote summary
  approved_by UUID REFERENCES firm_advisors(id),
  approved_at TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Compliance audit log (append-only)
CREATE TABLE compliance_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  firm_id UUID NOT NULL,
  actor_type VARCHAR(20) NOT NULL,          -- advisor | client | system
  actor_id VARCHAR(255),
  action VARCHAR(50) NOT NULL,              -- memo_generated | memo_approved | chat_query | debate_run
  resource_type VARCHAR(50),
  resource_id UUID,
  payload JSONB DEFAULT '{}',
  ip_address INET,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Auth model (Clerk Organizations)

| Role | Clerk mapping | Permissions |
|------|---------------|-------------|
| Firm admin | Org admin | Billing, branding, advisor seats, audit export |
| Advisor | Org member | Client CRUD, approve memos, internal chat |
| Client | Optional separate Clerk app / magic link | Read published memos, ask chat (firm-branded) |
| System | Lambda / ECS service role | Scheduler, memo generation |

**Alex today:** `users.clerk_id` → single investor.  
**RIA Copilot:** `firm_advisors.clerk_user_id` + `firm_clients` → isolated client portfolios.

---

## 6. Feature Set

### 6.1 Advisor Console (primary UI)

| Feature | Description | Alex source |
|---------|-------------|-------------|
| **Client list** | All households, AUM, last memo date | Extend `/dashboard` |
| **Memo inbox** | Pending approvals, one-click publish/edit | NEW — `client_memos` |
| **Committee replay** | Watch agent debate for any ticker | `/trading` replay → RIA mode |
| **Internal research chat** | Advisor asks without client guardrails | `/research` Alex chat |
| **Compliance export** | CSV/PDF of audit log date range | NEW — `compliance_audit_log` |
| **Firm observability** | Cost, latency, guardrail hits per firm | `/observe` + `firm_id` filter |

### 6.2 Client Portal (white-label)

| Feature | Description | Alex source |
|---------|-------------|-------------|
| **Branded homepage** | Firm logo, colors, disclaimer | NEW — `firms` config |
| **Published memos** | Hedge-fund-style quarterly + event-driven updates | `client_memos` published only |
| **Ask [Firm] AI** | Client chat with strict guardrails | `AlexChat.tsx` + firm theme |
| **Holdings context** | Chat scoped to their portfolio only | RAG `client_id` scope |
| **No simulation trades** | Optional — hide trading floor from clients | Config flag |

### 6.3 Autonomous pipelines (background)

| Pipeline | Schedule | Output |
|----------|----------|--------|
| **Portfolio memo** | EventBridge 2h (per firm batch) | `client_memos` draft per client |
| **Material news alert** | EventBridge 1h scan | Advisor notification if holding in news |
| **Committee debate** | Daily 6 AM ET per firm | `trading_events` + summary in memo |
| **Digest refresh** | Reuse Alex scheduler | `portfolio_digests` per client ticker |

### 6.4 Human-in-the-loop (compliance differentiator)

```
System generates memo (draft)
        ↓
Advisor reviews in Memo Inbox
        ↓
   ┌────┴────┐
   ▼         ▼
Approve    Edit + Approve
   ↓         ↓
Publish to client portal + audit log entry
```

**Default:** `firms.auto_publish_memos = false` for all pilot firms.

Maps to Alex **P1.5 Dashboard recommendation approval** pattern (`trading_recommendations` → `client_memos`).

### 6.5 CRM integrations (Phase 2)

| CRM | Integration | Value |
|-----|-------------|-------|
| Redtail | OAuth + contact sync | Auto-map `firm_clients.external_crm_id` |
| Wealthbox | API import holdings | Portfolio seed |
| Orion / Tamarac | Holdings file import | CSV → `portfolios` |

MVP: **CSV import** of client holdings (no CRM OAuth).

---

## 7. Compliance & Regulatory Framework

### Division of responsibility

| Party | Responsibility |
|-------|----------------|
| **RIA firm** | Supervises AI output; remains registered investment adviser; client relationship |
| **RIA Copilot (vendor)** | Research automation tool; audit trail; guardrails; SOC 2 (roadmap) |
| **End client** | Receives published materials approved by their advisor |

### Safe outputs (client-facing, post-approval)

- "Your portfolio's largest holding NVDA rose 3% today; here's what our research agents found..."
- "Four of six committee perspectives were constructive on healthcare exposure..."
- "RSI on SPY is 62 — context only, not a recommendation"
- Firm disclaimer on every page and chat response

### Blocked outputs (guardrails — extend Alex P10)

- "You should sell all bonds"
- "Guaranteed returns"
- "Act now before it's too late"
- Personalized allocation commands without advisor review

### Audit trail requirements (SEC / FINRA exam readiness)

| Event | Logged in | Retention |
|-------|-----------|-----------|
| Memo generated | `compliance_audit_log` + `client_memos` | 7 years (configurable) |
| Advisor approval | `compliance_audit_log` + `approved_by` | 7 years |
| Client chat query | `chat_sessions` + `query_latency_metrics` | 7 years |
| Agent debate run | `trading_events` + `agent_observations` | 7 years |
| Guardrail block | `agent_observations.guardrail_hits` | 7 years |
| Data sources used | `rag_attributions`, `data_sources` JSON | 7 years |

### Legal checklist before first RIA pilot

| Item | Owner | Est. cost |
|------|-------|-----------|
| Vendor B2B agreement template | Legal | $2,000–5,000 |
| RIA compliance consultant review | External | $2,000–5,000 |
| Firm-facing disclaimer library | Legal + engineering | Included in P10 |
| Data Processing Agreement (DPA) | Legal | $500–1,500 |
| SOC 2 Type I roadmap | Ops | Year 2 |

**Alex B2C disclaimer is insufficient for B2B** — firm-specific disclaimers required.

---

## 8. Implementation Phases on Alex Codebase

### Phase R0 — Tenancy foundation (Week 1–2)

| # | Task | Alex files to extend |
|---|------|---------------------|
| 1 | DDL: `firms`, `firm_advisors`, `firm_clients`, `client_memos`, `compliance_audit_log` | `scripts/aurora_warmup.py` |
| 2 | Clerk Organizations → `firm_id` on session | `frontend/middleware.ts`, auth helpers |
| 3 | Scope all portfolio queries by `firm_client_id` | `frontend/app/api/portfolio/*` |
| 4 | `POST /api/ria/firms`, `POST /api/ria/clients` | NEW API routes |
| 5 | Static tests | `scripts/tests/test_ria_tenancy.py` |

**Depends on:** Alex P0 complete ✅

---

### Phase R1 — Advisor console + memo pipeline (Week 3–4)

| # | Task | Alex leverage |
|---|------|---------------|
| 1 | Scheduler: loop `firm_clients` not just `users` | `scheduler.py` |
| 2 | Reporter output → `client_memos` draft (not just `portfolio_digests`) | `reporter.py` |
| 3 | Memo inbox UI | NEW `frontend/app/ria/memos/page.tsx` |
| 4 | Approve / reject / edit flow | `compliance_audit_log` writes |
| 5 | Firm branding config page | `firms` table admin UI |

**Depends on:** Alex P3 synthesizer, portfolio research pipeline ✅

---

### Phase R2 — Client portal + white-label chat (Week 5–6)

| # | Task | Alex leverage |
|---|------|---------------|
| 1 | Subdomain or path routing: `/c/[firmSlug]` | Next.js middleware |
| 2 | White-label theme from `firms` row | CSS variables |
| 3 | Client chat — published memos only in RAG context | `AlexChat.tsx`, scope RAG |
| 4 | Stricter client guardrails | P10 extension |
| 5 | Client memo read view (markdown) | Reuse research card components |

**Depends on:** Alex P1 unified chat ✅, P2 RAG

---

### Phase R3 — Committee + compliance export (Week 7–8)

| # | Task | Alex leverage |
|---|------|---------------|
| 1 | Investment committee debate per client watchlist | `9_trading_floor` orchestrator |
| 2 | Debate summary auto-attached to memo | `debate_engine.py` → `client_memos.agent_summary` |
| 3 | Compliance CSV export API | NEW `GET /api/ria/audit/export` |
| 4 | Firm-level `/observe` panel | Filter `agent_observations` by firm |
| 5 | Pilot with 1 RIA (5–10 clients) | Manual onboarding |

**Depends on:** Alex P4 trading, P11 observability

---

### Phase R4 — Enterprise (post-MVP)

- Dedicated VPC per firm (Terraform module `10_ria_enterprise`)
- Orion / Redtail OAuth
- SSO (SAML via Clerk)
- SOC 2 Type I
- Per-firm Bedrock guardrail profiles

---

## 9. Infrastructure & Terraform Changes

**Policy:** All infra via Terraform only (`Alex_report.md` §22.5).

### MVP — no new Terraform modules required

RIA Copilot MVP runs on **existing Alex modules**:

| Module | RIA usage |
|--------|-----------|
| `5_database` | New tables via `aurora_warmup.py` only |
| `6_agents` | Same scheduler; extend Lambda env `MODE=ria` |
| `4_researcher` | Same ECS; router prompt variants per `firm_id` |
| `9_trading_floor` | Committee debates per client batch |

### Optional Terraform additions (Phase R4)

```hcl
# terraform/10_ria_enterprise/main.tf (future)
# - Per-firm S3 prefix for audit exports
# - Per-firm KMS key for client_memos encryption
# - Dedicated EventBridge schedule per firm (large firms)
```

### Scheduler change (application, not new infra)

```python
# scheduler.py — RIA mode
def get_research_users():
    if os.environ.get('DEPLOY_MODE') == 'ria':
        return query_firm_clients_for_scheduled_research()
    return query_retail_users_with_portfolios()
```

Set `DEPLOY_MODE=ria` in Terraform `6_agents` scheduler Lambda env when serving RIA pilots.

---

## 10. API & Integration Surface

### New APIs (RIA Copilot)

| Route | Method | Auth | Purpose |
|-------|--------|------|---------|
| `/api/ria/firms` | GET, POST | Clerk org admin | Firm CRUD + branding |
| `/api/ria/advisors` | GET, POST | Firm admin | Seat management |
| `/api/ria/clients` | GET, POST, PUT | Advisor | Client households |
| `/api/ria/clients/import` | POST | Advisor | CSV holdings upload |
| `/api/ria/memos` | GET | Advisor | Memo inbox (filter by status) |
| `/api/ria/memos/[id]/approve` | POST | Advisor | Publish to client |
| `/api/ria/memos/[id]/reject` | POST | Advisor | Reject with reason |
| `/api/ria/audit/export` | GET | Firm admin | Compliance CSV |
| `/api/ria/chat` | POST (SSE) | Advisor or client | Scoped chat (reuse alex/chat) |
| `/api/ria/observe` | GET | Firm admin | Firm-scoped metrics |

### Reused Alex APIs (unchanged)

| Route | RIA usage |
|-------|-----------|
| `/api/portfolio` | Holdings per `firm_client_id` |
| `/api/portfolio-research` | Digest cards → feed memos |
| `/api/costs` | Firm admin cost view (extend filter) |

### B2B API tier (from Startup.md Model 2)

| Product | Price | RIA use |
|---------|-------|---------|
| Portfolio Digest API | $500/mo flat | Large firms with 50+ clients |
| Debate API | $0.10/ticker | Embed committee in existing tools |

---

## 11. Pricing & Unit Economics

### Recommended pricing

| Tier | Price | Includes |
|------|-------|----------|
| **Pilot** | $199/advisor/mo (3-mo min) | Up to 30 clients, manual CSV import |
| **Professional** | $300/advisor/mo | Up to 100 clients, memo approval, client portal |
| **Firm** | $250/advisor/mo (5+ seats) | Volume discount, firm observability |
| **Enterprise** | Custom | Dedicated VPC, SSO, CRM integrations, SLA |

**Add-ons:** Extra client packs ($50/50 clients), compliance export retention ($100/mo), premium data (Polygon pass-through).

### Unit economics (per advisor seat)

| Item | Monthly |
|------|---------|
| Revenue | $300 |
| AWS + Bedrock (est. 50 clients, moderate use) | $25–40 |
| Support allocation | $20 |
| Gross margin | **~80–85%** |

### Break-even vs junior analyst

| | Junior analyst | RIA Copilot seat |
|--|----------------|------------------|
| Annual cost | ~$80,000 | $3,600 ($300×12) |
| Hours/week on memos | 10–15 | 0 (automated) + 1 hr review |
| Compliance trail | Manual | Automatic |
| **ROI** | — | **~22× cost savings** |

### Firm-level targets

| Milestone | Advisors | MRR |
|-----------|----------|-----|
| Pilot | 3 | $900 |
| Break-even | 20 | $6,000 |
| Year 1 goal | 50 | $15,000 |
| Year 2 goal | 200 | $60,000 |

---

## 12. Go-to-Market for RIAs

### ICP (ideal customer profile)

- SEC-registered RIA, $50M–$500M AUM  
- 1–10 advisors, no in-house research  
- Uses Orion/Tamarac or Excel for holdings  
- Already paying for Koyfin, YCharts, or Bloomberg LP  
- Compliance-conscious (values audit trail)

### Acquisition channels

| Channel | Tactic |
|---------|--------|
| **RIA conferences** | T3, Schwab IMPACT, FPA — demo memo inbox |
| **Compliance consultants** | Referral fee — they recommend tools that log well |
| **Breakaway wirehouse advisors** | "Take Bloomberg-quality research to your new RIA" |
| **LinkedIn / RIA Facebook groups** | Before/after: 10hr memo week → 1hr review week |
| **Custodian partnerships** | Schwab/Fidelity RIA custody — integration marketplace (Year 2) |

### Pilot offer (first 5 firms)

```
90-day pilot: $199/advisor/mo
- We import up to 20 clients free
- Weekly check-in on memo quality
- Compliance export included
- Case study rights (anonymized)
```

### Sales motion

1. **Demo** — show memo generated overnight + approval flow (15 min)  
2. **Pilot** — 5–10 clients, CSV import, 30 days  
3. **Compliance call** — firm's CCO reviews audit export  
4. **Convert** — Professional tier, expand client count  

---

## 13. Competitive Landscape

| Competitor | Offering | Price | RIA Copilot advantage |
|------------|----------|-------|----------------------|
| **ChatGPT / Copilot** | General AI | $20/user/mo | No portfolio scope, no audit, compliance risk |
| **Morningstar Advisor Workstation** | Research + models | $3k+/yr | Not agentic, not conversational, no client portal AI |
| **YCharts** | Charts + reports | $3k–6k/yr | Static reports; no debate, no chat, no scheduler |
| **Nitrogen (Riskalyze)** | Risk profiling | $1.5k+/yr | Risk scores only; no research memos |
| **Holistiplan** | Tax planning | $2k+/yr | Different wedge; complementary |
| **FP Alpha** | AI for planners | Enterprise | Less transparent; no multi-agent debate visible |
| **Zephyr / Orion analytics** | Performance | Bundled | Backend analytics; not client-facing AI |

**RIA Copilot wedge:** Only product combining **autonomous memos + white-label client chat + visible investment committee debate + compliance audit export** on proven agentic infra.

---

## 14. MVP Roadmap (6–8 Weeks)

```
Week 1–2   R0  Tenancy schema + Clerk orgs + client CSV import
Week 3–4   R1  Memo pipeline + advisor inbox + approval flow
Week 5–6   R2  Client portal + white-label chat + firm branding
Week 7–8   R3  Committee summary in memos + audit export + 1 pilot RIA
```

### MVP success criteria

| Metric | Target |
|--------|--------|
| Memo generation | Draft per client every 2h |
| Advisor review time | < 5 min per memo (vs 30+ min to write) |
| Client portal | Published memo + chat live for pilot firm |
| Audit export | CSV with 100% of approve/chat events |
| Guardrail block rate | < 2% false positives on client chat |
| Pilot conversion | 1 of 1 pilot → paid Professional |

### Parallel Alex roadmap dependencies

| Alex phase | Required for RIA MVP |
|------------|---------------------|
| P0 ✅ | Schema, user scoping |
| P1 ✅ | Unified chat |
| P2 | Session RAG (client scope) |
| P3 | Synthesizer quality in memos |
| P10 | Guardrails — client mode |
| P11 | Firm observability panel |
| P14 | Committee memory in memos (nice-to-have MVP) |

---

## 15. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Compliance rejection by CCO | High | Human-in-the-loop default; audit export; legal review before pilot |
| Client confuses AI for advisor | Medium | Firm branding + "AI-assisted research, not advice" on every screen |
| Data leakage across firms | Critical | `firm_id` on every query; integration tests; no cross-firm RAG |
| Memo quality inconsistent | Medium | RAGAS eval (P17); advisor edit before publish |
| CRM integration delays sales | Medium | MVP CSV import; CRM in Phase R4 |
| Advisor fears job replacement | Medium | Position as "junior analyst" not replacement; advisor owns client |
| AWS cost per firm untracked | Low | P21 cost agent with `firm_id` dimension |

---

## 16. Document Index

| Document | Relationship |
|----------|--------------|
| `RIA.md` | **This file** — RIA Copilot product + Alex leverage plan |
| `usecases.md` | A2 startup idea summary |
| `Startup.md` | Model 3 white-label pricing, RIA pain points |
| `Alex_Master_Implementation_Plan.md` | Engineering phases to complete before/during RIA |
| `Alex_Trading_Floor_2.0.md` | Committee debate engine spec |
| `Alex_AI_2.0.md` | Router, RAG, chat spec |
| `Alex_report.md` | Production state, §33 change log |

---

## Summary

**RIA Copilot** is the highest-ARPU extension of Alex (~$300/advisor/mo vs $29 retail) with **~70–95% infrastructure reuse**. The Alex stack already provides the hard parts: scheduled research, multi-agent debate, RAG memory, MCP data, observability, and Terraform-proven AWS deployment.

**What to build new:** Firm tenancy, memo approval workflow, white-label client portal, compliance audit export, and RIA-specific guardrails.

**Recommended path:** Complete Alex MVP (Sprints 1–3) → run R0–R3 in parallel with one pilot RIA → convert to Professional tier → expand to Firm pricing.

---

*Log implementation progress in `Alex_report.md` §33. Infrastructure changes via Terraform only.*
