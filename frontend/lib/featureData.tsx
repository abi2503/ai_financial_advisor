import {
  TrendingUp, Brain, Shield, Zap, BarChart2, Clock,
  Telescope, Users, MessageSquare, CloudCog, ClipboardCheck,
  LineChart, Activity,
} from 'lucide-react'

export type FeatureItem = {
  icon: React.ReactNode
  badge: string
  title: string
  desc: string
  ai: string[]
  stack: string[]
  href: string
  accent: string
  theme: 'blue' | 'amber' | 'indigo' | 'emerald' | 'cyan' | 'green' | 'purple' | 'red' | 'orange' | 'yellow'
  shipped?: string
}

/** Shipped June 17, 2026 — eval frameworks, observe expansions, market data & charts */
export const TODAY_FEATURES: FeatureItem[] = [
  {
    icon:   <ClipboardCheck className="text-cyan-400" size={24} />,
    badge:  'Jun 17',
    title:  'RAGAS Eval (LLM Judge)',
    desc:   'Official RAGAS library with Bedrock Nova judge — faithfulness, relevancy, context recall, hallucination gates on research RAG',
    ai:     ['RAGAS metrics', 'LLM-as-judge', 'faithfulness gate', 'context audit'],
    stack:  ['ragas 0.1.21', 'Bedrock Nova Lite', 'pgvector search', 'Aurora'],
    href:   '/observe',
    accent: 'border-cyan-500/30 bg-cyan-500/5',
    theme:  'cyan',
    shipped: '2026-06-17',
  },
  {
    icon:   <Activity className="text-emerald-400" size={24} />,
    badge:  'Jun 17',
    title:  'Trading Outcome Eval',
    desc:   'Scores paper trades vs 5-day forward price — attributes BUY/SELL/HOLD accuracy per agent with leaderboard and trade audits',
    ai:     ['outcome scoring', 'agent attribution', 'P&L horizon', 'accuracy leaderboard'],
    stack:  ['alex-trade-evaluator λ', 'yfinance', 'agent_performance', 'EventBridge'],
    href:   '/observe',
    accent: 'border-emerald-500/30 bg-emerald-500/5',
    theme:  'emerald',
    shipped: '2026-06-17',
  },
  {
    icon:   <LineChart className="text-violet-400" size={24} />,
    badge:  'Jun 17',
    title:  'Holdings Breakdown Chart',
    desc:   'Donut-style portfolio allocation on /charts — top tickers plus Others bucket with side table',
    ai:     ['portfolio viz'],
    stack:  ['Recharts', 'Aurora portfolios', 'Clerk auth'],
    href:   '/charts',
    accent: 'border-violet-500/30 bg-violet-500/5',
    theme:  'purple',
    shipped: '2026-06-17',
  },
  {
    icon:   <TrendingUp className="text-yellow-400" size={24} />,
    badge:  'Jun 17',
    title:  'Live Market Overview',
    desc:   '“How did markets do today?” returns real Dow, S&P, NASDAQ, and sector ETF moves — no placeholder X%',
    ai:     ['market overview tool', 'fast route', 'indices + sectors'],
    stack:  ['yfinance', 'query router', 'Nova Lite', 'ECS researcher'],
    href:   '/research',
    accent: 'border-yellow-500/30 bg-yellow-500/5',
    theme:  'yellow',
    shipped: '2026-06-17',
  },
  {
    icon:   <Telescope className="text-indigo-400" size={24} />,
    badge:  'Jun 17',
    title:  'Observe — RAGAS & Outcome Tabs',
    desc:   'Three-tab observability: research queries, trading floor ops, and RAGAS eval with run history and per-query audits',
    ai:     ['eval scorecard', 'eval trend', 'trade audits', 'run eval buttons'],
    stack:  ['Next.js API', 'Aurora ragas_eval_runs', 'trading_eval_runs', 'Lambda proxy'],
    href:   '/observe',
    accent: 'border-indigo-500/30 bg-indigo-500/5',
    theme:  'indigo',
    shipped: '2026-06-17',
  },
]

export const SHIP_DATE_LABEL = 'June 17, 2026'

export const NEW_FEATURES: FeatureItem[] = [
  {
    icon:   <MessageSquare className="text-blue-400" size={24} />,
    badge:  'New',
    title:  'Unified Alex Chat',
    desc:   'Single interface with automatic routing across chat, research, SEC analysis, and specialist agents',
    ai:     ['intent router', 'tool agents', 'specialist handoff', 'live streaming'],
    stack:  ['Amazon Nova', 'Bedrock SSE', 'yfinance', 'EdgarTools'],
    href:   '/research',
    accent: 'border-blue-500/30 bg-blue-500/5',
    theme:  'blue' as const,
  },
  {
    icon:   <ClipboardCheck className="text-cyan-400" size={24} />,
    badge:  'Eval',
    title:  'RAGAS Quality Gates',
    desc:   'Measure RAG faithfulness and hallucination — block bad researcher deploys with audited benchmarks',
    ai:     ['RAGAS eval', 'LLM judge', 'deploy gate'],
    stack:  ['P17', '/observe', 'test_ragas.py'],
    href:   '/observe',
    accent: 'border-cyan-500/30 bg-cyan-500/5',
    theme:  'cyan' as const,
  },
  {
    icon:   <Users className="text-amber-400" size={24} />,
    badge:  'New',
    title:  'Trading Floor',
    desc:   'Multi-agent debate on portfolio positions with logged votes and simulated trade rationale',
    ai:     ['multi-agent debate', 'bull vs bear votes', 'risk scoring', 'simulated trades'],
    stack:  ['5 LLM personas', 'parallel agents', 'Aurora logs', 'SQS queue'],
    href:   '/trading',
    accent: 'border-amber-500/30 bg-amber-500/5',
    theme:  'amber' as const,
  },
  {
    icon:   <Telescope className="text-indigo-400" size={24} />,
    badge:  'New',
    title:  'Observe',
    desc:   'Query-level observability for latency, tool execution, guardrails, and token usage',
    ai:     ['query tracing', 'tool pass/fail', 'guardrail hits', 'token costs'],
    stack:  ['Aurora metrics', 'CloudWatch', 'per-prompt logs'],
    href:   '/observe',
    accent: 'border-indigo-500/30 bg-indigo-500/5',
    theme:  'indigo' as const,
  },
  {
    icon:   <CloudCog className="text-emerald-400" size={24} />,
    badge:  'New',
    title:  'AWS Cost Agent',
    desc:   'Operational spend and service health on your dashboard, refreshed every 30 minutes',
    ai:     ['ops agent', 'spend digests', 'health checks'],
    stack:  ['Cost Explorer', 'Lambda 30min', 'live dashboard widget'],
    href:   '/dashboard#ops-cost',
    accent: 'border-emerald-500/30 bg-emerald-500/5',
    theme:  'emerald' as const,
  },
]

export const CORE_FEATURES = [
  {
    icon:  <Clock className="text-blue-400" size={24} />,
    title: '24/7 Autonomous Research',
    desc:  'Scheduled portfolio digests every two hours',
    ai:    ['planner agent', 'auto digests', 'sentiment tags'],
    stack: ['EventBridge', 'SQS pipeline', 'Lambda agents'],
    theme: 'blue' as const,
  },
  {
    icon:  <Brain className="text-purple-400" size={24} />,
    title: 'Per-User Memory (RAG)',
    desc:  'Session-scoped vector memory for research continuity',
    ai:    ['RAG memory', 'session context', 'similarity search'],
    stack: ['pgvector', 'SageMaker embeds', 'Aurora'],
    theme: 'purple' as const,
  },
  {
    icon:  <Shield className="text-green-400" size={24} />,
    title: 'Layered Guardrails',
    desc:  'Policy and safety controls with full audit logging',
    ai:    ['policy router', 'Bedrock guardrails', 'block logging'],
    stack: ['regex + LLM gate', 'safety filters'],
    theme: 'green' as const,
  },
  {
    icon:  <TrendingUp className="text-yellow-400" size={24} />,
    title: 'Real Market Data',
    desc:  'Live prices, SEC filings, and tool-augmented web research',
    ai:    ['tool-augmented answers', 'SEC parsing', 'web browse'],
    stack: ['yfinance API', 'EdgarTools', 'Playwright MCP'],
    theme: 'yellow' as const,
  },
  {
    icon:  <BarChart2 className="text-red-400" size={24} />,
    title: 'Multi-Agent Pipeline',
    desc:  'Coordinated planner, tagger, and reporter agents via SQS',
    ai:    ['task split', 'parallel research', 'merge results'],
    stack: ['planner / tagger / reporter', 'map-reduce agents'],
    theme: 'red' as const,
  },
  {
    icon:  <Zap className="text-orange-400" size={24} />,
    title: 'Tiered Model Routing',
    desc:  'Nova Lite for routine queries; Nova Pro for deep analysis',
    ai:    ['auto route pick', 'Nova Lite vs Pro', 'cost-aware'],
    stack: ['query classifier', 'tiered LLMs'],
    theme: 'orange' as const,
  },
]
