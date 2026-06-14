import Link from 'next/link'
import { auth } from '@clerk/nextjs/server'
import {
  TrendingUp, Brain, Shield, Zap, BarChart2, Clock,
  Telescope, Users, MessageSquare, CloudCog, Sparkles, ChevronDown,
} from 'lucide-react'

const NEW_FEATURES = [
  {
    icon:  <MessageSquare className="text-blue-400" size={24} />,
    badge: 'New',
    title: 'Unified Alex Chat',
    desc:  'One chat box — Alex auto-routes to Chat, Fast Research, Deep SEC analysis, or specialist Debater handoff. No manual mode toggle. Streaming markdown tables, news links, and smooth scroll UX.',
    href:  '/research',
    accent: 'border-blue-500/30 bg-blue-500/5',
  },
  {
    icon:  <Users className="text-amber-400" size={24} />,
    badge: 'New',
    title: 'Trading Floor',
    desc:  'Five named agents — Marcus, Victoria, Zara, Reid, Elena — debate your holdings in parallel and record every vote. Paper-trades with full bull/bear/risk reasoning visible in the UI.',
    href:  '/trading',
    accent: 'border-amber-500/30 bg-amber-500/5',
  },
  {
    icon:  <Telescope className="text-indigo-400" size={24} />,
    badge: 'New',
    title: 'Observe',
    desc:  'Production AI observability — per-query latency, tool/MCP pass-fail, guardrail hits, and agent token costs. See exactly what Alex did on every prompt, not a black box.',
    href:  '/observe',
    accent: 'border-indigo-500/30 bg-indigo-500/5',
  },
  {
    icon:  <CloudCog className="text-emerald-400" size={24} />,
    badge: 'New',
    title: 'AWS Cost Agent',
    desc:  'Live ops dashboard widget — today, week, and MTD AWS spend with service breakdown and 7-service health score. Cost Explorer data refreshed every 30 minutes on your dashboard.',
    href:  '/dashboard',
    accent: 'border-emerald-500/30 bg-emerald-500/5',
  },
]

const CORE_FEATURES = [
  {
    icon:  <Clock className="text-blue-400" size={24} />,
    title: '24/7 Autonomous Research',
    desc:  'Scheduled workflows generate portfolio digests every 2 hours — no prompting required.',
  },
  {
    icon:  <Brain className="text-purple-400" size={24} />,
    title: 'Per-User Memory (RAG)',
    desc:  'pgvector knowledge base scoped to your sessions — Alex remembers your research history.',
  },
  {
    icon:  <Shield className="text-green-400" size={24} />,
    title: 'Layered Guardrails',
    desc:  'Off-topic blocks, policy flags, and Bedrock safety — every guardrail logged to Observe.',
  },
  {
    icon:  <TrendingUp className="text-yellow-400" size={24} />,
    title: 'Real Market Data',
    desc:  'yfinance live prices, EdgarTools SEC filings, and Playwright MCP for deep web research.',
  },
  {
    icon:  <BarChart2 className="text-red-400" size={24} />,
    title: 'Multi-Agent Pipeline',
    desc:  'Planner → Tagger → Reporter agents coordinate via SQS for parallel comparative analysis.',
  },
  {
    icon:  <Zap className="text-orange-400" size={24} />,
    title: 'Tiered Model Routing',
    desc:  'Nova Lite for chat and fast lookups; Nova Pro for deep research — cost-efficient by design.',
  },
]

export default async function LandingPage() {
  const { userId } = await auth()

  return (
    <main className="min-h-screen bg-gray-950">

      {/* Navbar */}
      <nav className="border-b border-gray-800 px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Brain className="text-blue-400" size={28} />
          <span className="text-xl font-bold text-white">Alex AI</span>
        </div>
        <div className="flex gap-3">
          {userId ? (
            <Link href="/dashboard" className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white transition">
              Dashboard →
            </Link>
          ) : (
            <>
              <Link href="/sign-in" className="px-4 py-2 text-gray-300 hover:text-white transition">
                Sign In
              </Link>
              <Link href="/sign-up" className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white transition">
                Get Started Free
              </Link>
            </>
          )}
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-6 py-24 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-blue-400 text-sm mb-6">
          <Zap size={14} />
          Autonomous AI Research — Running 24/7
        </div>
        <h1 className="text-5xl font-bold text-white mb-6 leading-tight">
          Bloomberg-level research
          <span className="text-blue-400"> at $50/month</span>
        </h1>
        <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
          Alex researches financial markets, builds a searchable knowledge base, and delivers personalized intelligence automatically.
        </p>
        <div className="flex justify-center">
          {userId ? (
            <Link
              href="/dashboard"
              className="px-8 py-4 bg-blue-600 hover:bg-blue-500 rounded-xl text-white font-semibold text-lg transition"
            >
              Go to Dashboard →
            </Link>
          ) : (
            <Link
              href="/sign-up"
              className="px-8 py-4 bg-blue-600 hover:bg-blue-500 rounded-xl text-white font-semibold text-lg transition"
            >
              Start Free →
            </Link>
          )}
        </div>
        <a
          href="#catalog"
          className="inline-flex items-center gap-1 mt-10 text-sm text-gray-500 hover:text-gray-300 transition"
        >
          Explore the Alex catalog
          <ChevronDown size={16} className="animate-bounce" />
        </a>
      </section>

      {/* New features flashcards */}
      <section id="catalog" className="max-w-6xl mx-auto px-6 py-16 scroll-mt-8">
        <div className="flex items-center justify-center gap-2 mb-3">
          <Sparkles className="text-blue-400" size={18} />
          <span className="text-sm font-medium text-blue-400 uppercase tracking-wider">What&apos;s New</span>
        </div>
        <h2 className="text-3xl font-bold text-white text-center mb-4">
          Latest Alex capabilities
        </h2>
        <p className="text-gray-500 text-center mb-12 max-w-xl mx-auto text-sm">
          Sign in and jump straight in — or scroll through the full feature catalog below.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {NEW_FEATURES.map((f) => (
            <Link
              key={f.title}
              href={userId ? f.href : '/sign-up'}
              className={`group p-6 border rounded-xl transition hover:scale-[1.01] ${f.accent} hover:border-opacity-60`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="p-2 bg-gray-900/80 rounded-lg">{f.icon}</div>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
                  {f.badge}
                </span>
              </div>
              <h3 className="text-white font-semibold text-lg mb-2 group-hover:text-blue-300 transition">
                {f.title}
              </h3>
              <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
              <p className="text-xs text-gray-600 mt-4 group-hover:text-blue-400 transition">
                {userId ? 'Open →' : 'Sign up to access →'}
              </p>
            </Link>
          ))}
        </div>
      </section>

      {/* Core platform catalog */}
      <section id="features" className="max-w-5xl mx-auto px-6 py-20 border-t border-gray-800/60">
        <h2 className="text-2xl font-bold text-white text-center mb-3">
          Core platform
        </h2>
        <p className="text-gray-500 text-center mb-12 text-sm">
          The infrastructure behind every Alex response
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {CORE_FEATURES.map((f) => (
            <div key={f.title} className="p-6 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-600 transition">
              <div className="mb-3">{f.icon}</div>
              <h3 className="text-white font-semibold mb-2">{f.title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA — only show to logged out users */}
      {!userId && (
        <section className="max-w-2xl mx-auto px-6 py-24 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Start your free trial today
          </h2>
          <p className="text-gray-400 mb-8">
            No credit card required. Get access to autonomous financial
            research immediately.
          </p>
          <Link
            href="/sign-up"
            className="px-10 py-4 bg-blue-600 hover:bg-blue-500 rounded-xl text-white font-semibold text-lg transition inline-block"
          >
            Get Started Free →
          </Link>
        </section>
      )}

      {/* Footer */}
      <footer className="border-t border-gray-800 px-6 py-8 text-center text-gray-600 text-sm">
        <p>Alex AI © 2026 — Financial Research Platform</p>
        <p className="mt-1">This platform provides research not financial advice.</p>
      </footer>

    </main>
  )
}
