'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import Navbar from '@/components/Navbar'

interface AgentStat {
  agent: string
  calls: number
  input_tokens: number
  output_tokens: number
  total_tokens: number
  total_cost: number
  avg_latency: number
  successes: number
  guardrail_hits: number
  unique_tickers: number
  buy_count: number
  sell_count: number
  hold_count: number
  trim_count: number
}

interface Platform {
  total_cost: number
  total_tokens: number
  total_calls: number
  unique_tickers: number
  total_guardrails: number
}

interface GuardrailLog {
  agent: string
  ticker: string
  action: string
  confidence: number
  reason: string
  created_at: string
}

interface QuerySummary {
  route: string
  count: number
  avg_ms: number
  p50_ms: number
  p95_ms: number
  avg_first_token_ms: number
  input_tokens?: number
  output_tokens?: number
  total_cost?: number
}

interface ResearchTotals {
  input_tokens: number
  output_tokens: number
  total_cost: number
  count: number
}

interface DataSource {
  name: string
  url: string
  latency_ms: number
  success: boolean
  error?: string
}

interface ToolHit {
  name: string
  success: boolean
  error?: string
  latency_ms?: number
}

interface McpHit {
  name: string
  success: boolean
  error?: string
}

interface PassFail {
  tools_passed: number
  tools_failed: number
  apis_passed: number
  apis_failed: number
  mcps_passed: number
  mcps_failed: number
}

interface RecentQuery {
  query_id: string
  query: string
  route: string
  model: string
  total_ms: number
  first_token_ms: number | null
  context_ms: number
  agent_ms: number
  guardrail_ms: number
  tools: ToolHit[]
  mcp_servers: McpHit[]
  data_sources: DataSource[]
  pass_fail: PassFail
  response_chars: number
  success: boolean
  created_at: string
  input_tokens: number
  output_tokens: number
  cost_usd: number
}

interface RagasRun {
  run_id: string
  gate: string
  judge_model: string
  backend: string
  query_count: number
  faithfulness: number
  answer_relevancy: number
  context_precision: number
  context_recall: number
  hallucination_rate: number
  overall_score: number
  passed: boolean
  evaluated_at: string
}

interface RagasAudit {
  id: string
  query: string
  response: string
  ground_truth: string
  faithfulness: number
  answer_relevancy: number
  context_precision: number
  context_recall: number
  hallucination_rate: number
  overall_score: number
  passed: boolean
  gate: string
  contexts: string[]
  audit: Record<string, unknown>
  evaluated_at: string
}

interface RagasThresholds {
  faithfulness: number
  answer_relevancy: number
  hallucination_rate: number
  context_recall: number
}

interface TradingEvalRun {
  run_id: string
  gate: string
  horizon_days: number
  trades_evaluated: number
  trades_pending: number
  trades_skipped: number
  overall_accuracy: number
  buy_accuracy: number
  sell_accuracy: number
  hold_neutral_rate: number
  avg_pnl_pct: number
  passed: boolean
  evaluated_at: string
}

interface TradingLeaderboardRow {
  agent_name: string
  votes: number
  correct_count: number
  scored: number
  accuracy: number
}

interface TradingAuditVote {
  agent_name: string
  action: string
  confidence: number
  correct: boolean | null
  outcome?: string
}

interface TradingAudit {
  trade_id: string
  ticker: string
  final_action: string
  outcome: string
  realized_pnl: number
  return_pct: number
  evaluated_at: string
  agent_votes: TradingAuditVote[]
}

const AGENT_COLORS: Record<string, string> = {
  'marcus chen':       '#22c55e',
  'victoria sterling': '#ef4444',
  'zara patel':        '#3b82f6',
  'reid morrison':     '#f97316',
  'elena vasquez':     '#a855f7',
}

const AGENT_LABELS: Record<string, string> = {
  'marcus chen':       'Marcus',
  'victoria sterling': 'Victoria',
  'zara patel':        'Zara',
  'reid morrison':     'Reid',
  'elena vasquez':     'Elena',
}

const ROUTE_COLORS: Record<string, string> = {
  chat:         'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  fast:         'bg-blue-500/20 text-blue-400 border-blue-500/30',
  stream:       'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  deep:         'bg-purple-500/20 text-purple-400 border-purple-500/30',
  'deep-stream':'bg-purple-500/20 text-purple-400 border-purple-500/30',
  debater:      'bg-pink-500/20 text-pink-400 border-pink-500/30',
  multi:        'bg-orange-500/20 text-orange-400 border-orange-500/30',
}

/** Display label for route tags on observe cards */
const ROUTE_LABELS: Record<string, string> = {
  chat: 'chat observability',
}

function routeLabel(route: string) {
  return ROUTE_LABELS[route] || route
}

function costLabel(usd: number) {
  if (usd <= 0) return '$0.000000'
  if (usd < 0.0001) return `$${usd.toFixed(6)}`
  if (usd < 0.01) return `$${usd.toFixed(5)}`
  return `$${usd.toFixed(4)}`
}

function msLabel(ms: number) {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
  return `${ms}ms`
}

function scorePct(v: number) {
  return `${Math.round(v * 100)}%`
}

function metricColor(value: number, threshold: number, higherIsBetter = true) {
  const ok = higherIsBetter ? value >= threshold : value <= threshold
  if (ok) return 'text-green-400'
  if (higherIsBetter ? value >= threshold * 0.9 : value <= threshold * 1.2) return 'text-yellow-400'
  return 'text-red-400'
}

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`text-xs px-2 py-1 rounded border ${
      ok ? 'bg-green-950 border-green-800 text-green-400' : 'bg-red-950 border-red-800 text-red-400'
    }`}>
      {ok ? '✓' : '✗'} {label}
    </span>
  )
}

function StageBar({ label, ms, total }: { label: string; ms: number; total: number }) {
  const pct = total > 0 ? Math.max(2, (ms / total) * 100) : 0
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-16 text-gray-500 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-1.5">
        <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="w-12 text-right text-gray-400">{msLabel(ms)}</span>
    </div>
  )
}

export default function ObservePage() {
  const [tab, setTab]               = useState<'research' | 'trading' | 'ragas'>('research')
  const [agents, setAgents]         = useState<AgentStat[]>([])
  const [platform, setPlatform]     = useState<Platform | null>(null)
  const [guardrails, setGuardrails] = useState<GuardrailLog[]>([])
  const [querySummary, setQuerySummary] = useState<QuerySummary[]>([])
  const [recentQueries, setRecentQueries] = useState<RecentQuery[]>([])
  const [researchTotals, setResearchTotals] = useState<ResearchTotals | null>(null)
  const [expanded, setExpanded]     = useState<string | null>(null)
  const [loading, setLoading]       = useState(true)

  const [ragasLatest, setRagasLatest]       = useState<RagasRun | null>(null)
  const [ragasTrend, setRagasTrend]         = useState<RagasRun[]>([])
  const [ragasAudits, setRagasAudits]       = useState<RagasAudit[]>([])
  const [ragasThresholds, setRagasThresholds] = useState<RagasThresholds>({
    faithfulness: 0.88, answer_relevancy: 0.85, hallucination_rate: 0.08, context_recall: 0.70,
  })
  const [selectedRunId, setSelectedRunId]   = useState<string | null>(null)
  const [ragasExpanded, setRagasExpanded]   = useState<string | null>(null)
  const [ragasLoading, setRagasLoading]     = useState(false)
  const [ragasRunning, setRagasRunning]     = useState(false)
  const [ragasError, setRagasError]         = useState<string | null>(null)

  const [tradingEvalLatest, setTradingEvalLatest] = useState<TradingEvalRun | null>(null)
  const [tradingEvalTrend, setTradingEvalTrend]   = useState<TradingEvalRun[]>([])
  const [tradingLeaderboard, setTradingLeaderboard] = useState<TradingLeaderboardRow[]>([])
  const [tradingAudits, setTradingAudits]         = useState<TradingAudit[]>([])
  const [tradingEvalPending, setTradingEvalPending] = useState(0)
  const [tradingEvalLoading, setTradingEvalLoading] = useState(false)
  const [tradingEvalRunning, setTradingEvalRunning] = useState(false)
  const [tradingEvalError, setTradingEvalError]   = useState<string | null>(null)
  const [tradingEvalExpanded, setTradingEvalExpanded] = useState<string | null>(null)
  const [selectedTradingRunId, setSelectedTradingRunId] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const res  = await fetch('/api/observe')
      const data = await res.json()
      setAgents(data.agents || [])
      setPlatform(data.platform)
      setGuardrails(data.guardrails || [])
      setQuerySummary(data.querySummary || [])
      setRecentQueries(data.recentQueries || [])
      setResearchTotals(data.researchTotals || null)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchRagas = useCallback(async (runId?: string | null) => {
    setRagasLoading(true)
    setRagasError(null)
    try {
      const qs = runId ? `?run_id=${encodeURIComponent(runId)}` : ''
      const res  = await fetch(`/api/observe/ragas${qs}`)
      const data = await res.json()
      setRagasLatest(data.latest || null)
      setRagasTrend(data.trend || [])
      setRagasAudits(data.audits || [])
      setRagasThresholds(data.thresholds || {
        faithfulness: 0.88, answer_relevancy: 0.85, hallucination_rate: 0.08, context_recall: 0.70,
      })
      setSelectedRunId(data.selected_run_id || null)
    } catch (err) {
      console.error(err)
      setRagasError('Failed to load RAGAS eval data')
    } finally {
      setRagasLoading(false)
    }
  }, [])

  const runRagasEval = useCallback(async (smoke = false) => {
    setRagasRunning(true)
    setRagasError(null)
    try {
      const res = await fetch('/api/observe/ragas/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ smoke }),
      })
      const data = await res.json()
      if (!res.ok) {
        setRagasError(data.error || 'RAGAS eval failed')
        return
      }
      await fetchRagas(data.run_id)
    } catch (err) {
      console.error(err)
      setRagasError('RAGAS eval request failed')
    } finally {
      setRagasRunning(false)
    }
  }, [fetchRagas])

  const fetchTradingEval = useCallback(async (runId?: string | null) => {
    setTradingEvalLoading(true)
    setTradingEvalError(null)
    try {
      const qs = runId ? `?run_id=${encodeURIComponent(runId)}` : ''
      const res = await fetch(`/api/observe/trading-eval${qs}`)
      const data = await res.json()
      setTradingEvalLatest(data.latest || null)
      setTradingEvalTrend(data.trend || [])
      setTradingLeaderboard(data.leaderboard || [])
      setTradingAudits(data.audits || [])
      setTradingEvalPending(data.pending_mature_trades || 0)
      setSelectedTradingRunId(data.selected_run_id || null)
    } catch (err) {
      console.error(err)
      setTradingEvalError('Failed to load outcome eval data')
    } finally {
      setTradingEvalLoading(false)
    }
  }, [])

  const runTradingEval = useCallback(async () => {
    setTradingEvalRunning(true)
    setTradingEvalError(null)
    try {
      const res = await fetch('/api/observe/trading-eval/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ horizon_days: 5 }),
      })
      const data = await res.json()
      if (!res.ok) {
        setTradingEvalError(data.error || 'Outcome eval failed')
        return
      }
      await fetchTradingEval(data.run_id)
    } catch (err) {
      console.error(err)
      setTradingEvalError('Outcome eval request failed')
    } finally {
      setTradingEvalRunning(false)
    }
  }, [fetchTradingEval])

  useEffect(() => { fetchData() }, [fetchData])

  useEffect(() => {
    if (tab !== 'research') return
    const id = setInterval(fetchData, 30000)
    return () => clearInterval(id)
  }, [tab, fetchData])

  useEffect(() => {
    if (tab === 'ragas') fetchRagas(selectedRunId)
  }, [tab, fetchRagas, selectedRunId])

  useEffect(() => {
    if (tab === 'trading') fetchTradingEval(selectedTradingRunId)
  }, [tab, fetchTradingEval, selectedTradingRunId])

  const maxCost = Math.max(...agents.map(a => a.total_cost), 0.0001)

  if (loading && tab !== 'ragas') {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading Observability...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <Navbar />
      <div className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">🔭 Alex Observability</h1>
            <p className="text-xs text-gray-500 mt-0.5">
              Per-query latency, LLM tokens, AWS Bedrock cost, tools & APIs — last 7 days
            </p>
          </div>
          <button onClick={() => {
            if (tab === 'ragas') { setRagasLoading(true); fetchRagas(selectedRunId) }
            else if (tab === 'trading') { setTradingEvalLoading(true); fetchTradingEval(selectedTradingRunId) }
            else { setLoading(true); fetchData() }
          }}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-white border border-gray-700 rounded-lg">
            ↻ Refresh
          </button>
        </div>
        <div className="max-w-7xl mx-auto px-4 flex gap-1 pb-0">
          {([
            { id: 'research' as const, label: '🧠 Research Queries' },
            { id: 'trading' as const,  label: '📈 Trading Floor' },
            { id: 'ragas' as const,    label: '📋 RAGAS Eval' },
          ]).map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition ${
                tab === t.id
                  ? 'border-indigo-500 text-white bg-gray-900'
                  : 'border-transparent text-gray-500 hover:text-gray-300'
              }`}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">

        {/* ── RESEARCH TAB ── */}
        {tab === 'research' && (
          <>
            {/* LLM cost summary */}
            {researchTotals && researchTotals.count > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                  <p className="text-xs text-gray-500 uppercase">Queries (7d)</p>
                  <p className="text-2xl font-bold text-white mt-1">{researchTotals.count}</p>
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                  <p className="text-xs text-gray-500 uppercase">Input tokens</p>
                  <p className="text-2xl font-bold text-cyan-400 mt-1">{researchTotals.input_tokens.toLocaleString()}</p>
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                  <p className="text-xs text-gray-500 uppercase">Output tokens</p>
                  <p className="text-2xl font-bold text-blue-400 mt-1">{researchTotals.output_tokens.toLocaleString()}</p>
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                  <p className="text-xs text-gray-500 uppercase">AWS Bedrock cost</p>
                  <p className="text-2xl font-bold text-green-400 mt-1">{costLabel(researchTotals.total_cost)}</p>
                  <p className="text-xs text-gray-600 mt-1">Nova Lite/Pro list pricing</p>
                </div>
              </div>
            )}

            {/* Speed summary by route */}
            <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">
              Query Response Speed (7d)
            </h3>
            {querySummary.length === 0 ? (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center mb-8">
                <p className="text-4xl mb-3">📊</p>
                <p className="text-gray-400 text-sm">No research queries logged yet.</p>
                <p className="text-gray-600 text-xs mt-2">
                  Ask Alex something on <Link href="/research" className="text-blue-400 hover:underline">/research</Link> — metrics appear here automatically.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
                {querySummary.map(s => (
                  <div key={s.route} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-xs px-2 py-0.5 rounded border font-medium ${ROUTE_COLORS[s.route] || 'bg-gray-800 text-gray-400'}`}>
                        {routeLabel(s.route)}
                      </span>
                      <span className="text-xs text-gray-600">{s.count} queries</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <p className="text-gray-500">P50</p>
                        <p className="text-white font-bold">{msLabel(s.p50_ms)}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">P95</p>
                        <p className="text-yellow-400 font-bold">{msLabel(s.p95_ms)}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Avg total</p>
                        <p className="text-indigo-400">{msLabel(s.avg_ms)}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">First token</p>
                        <p className="text-cyan-400">{s.avg_first_token_ms ? msLabel(s.avg_first_token_ms) : '—'}</p>
                      </div>
                      {(s.total_cost ?? 0) > 0 && (
                        <div className="col-span-2">
                          <p className="text-gray-500">Route cost</p>
                          <p className="text-green-400">{costLabel(s.total_cost || 0)}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Recent queries */}
            <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">
              Recent Queries — validate each Alex response
            </h3>
            <div className="space-y-2 mb-8">
              {recentQueries.length === 0 ? (
                <p className="text-gray-600 text-sm">No queries yet.</p>
              ) : recentQueries.map(q => (
                <div key={q.query_id} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                  <button
                    className="w-full text-left p-4 hover:bg-gray-800/40 transition"
                    onClick={() => setExpanded(expanded === q.query_id ? null : q.query_id)}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className={`text-xs px-2 py-0.5 rounded border ${ROUTE_COLORS[q.route] || 'bg-gray-800 text-gray-400'}`}>
                            {routeLabel(q.route)}
                          </span>
                          <span className={`text-xs ${q.success ? 'text-green-400' : 'text-red-400'}`}>
                            {q.success ? '✓ success' : '✗ failed'}
                          </span>
                          {q.model && (
                            <span className="text-xs text-gray-600 truncate">{q.model.split('/').pop()}</span>
                          )}
                        </div>
                        <p className="text-sm text-white truncate">{q.query}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(q.created_at).toLocaleString()} · {q.response_chars.toLocaleString()} chars
                        </p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-lg font-bold text-indigo-400">{msLabel(q.total_ms)}</p>
                        {q.first_token_ms && (
                          <p className="text-xs text-cyan-400">1st token {msLabel(q.first_token_ms)}</p>
                        )}
                        {(q.cost_usd > 0 || q.input_tokens > 0) && (
                          <p className="text-xs text-green-400 mt-0.5">{costLabel(q.cost_usd)}</p>
                        )}
                      </div>
                    </div>
                  </button>

                  {expanded === q.query_id && (
                    <div className="px-4 pb-4 border-t border-gray-800 pt-3 space-y-4">
                      {/* Pass/fail summary */}
                      {q.pass_fail && (
                        <div className="flex flex-wrap gap-2 text-xs">
                          <span className="text-gray-500">Calls:</span>
                          <StatusBadge ok={q.pass_fail.tools_failed === 0}
                            label={`Tools ${q.pass_fail.tools_passed}/${q.pass_fail.tools_passed + q.pass_fail.tools_failed}`} />
                          <StatusBadge ok={q.pass_fail.apis_failed === 0}
                            label={`APIs ${q.pass_fail.apis_passed}/${q.pass_fail.apis_passed + q.pass_fail.apis_failed}`} />
                          {(q.pass_fail.mcps_passed + q.pass_fail.mcps_failed) > 0 && (
                            <StatusBadge ok={q.pass_fail.mcps_failed === 0}
                              label={`MCP ${q.pass_fail.mcps_passed}/${q.pass_fail.mcps_passed + q.pass_fail.mcps_failed}`} />
                          )}
                        </div>
                      )}

                      {/* LLM statistics */}
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">LLM statistics (AWS Bedrock)</p>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                          <div className="bg-gray-800/50 rounded-lg p-3">
                            <p className="text-gray-500">Input tokens</p>
                            <p className="text-cyan-400 font-bold text-sm">{q.input_tokens.toLocaleString()}</p>
                          </div>
                          <div className="bg-gray-800/50 rounded-lg p-3">
                            <p className="text-gray-500">Output tokens</p>
                            <p className="text-blue-400 font-bold text-sm">{q.output_tokens.toLocaleString()}</p>
                          </div>
                          <div className="bg-gray-800/50 rounded-lg p-3">
                            <p className="text-gray-500">Total tokens</p>
                            <p className="text-white font-bold text-sm">{(q.input_tokens + q.output_tokens).toLocaleString()}</p>
                          </div>
                          <div className="bg-gray-800/50 rounded-lg p-3">
                            <p className="text-gray-500">Cost / query</p>
                            <p className="text-green-400 font-bold text-sm">{costLabel(q.cost_usd)}</p>
                          </div>
                        </div>
                        {q.model && (
                          <p className="text-xs text-gray-600 mt-2">Model: {q.model.replace('bedrock/', '')}</p>
                        )}
                      </div>

                      {/* Stage breakdown */}
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Latency breakdown</p>
                        <div className="space-y-1.5">
                          <StageBar label="Context" ms={q.context_ms} total={q.total_ms} />
                          <StageBar label="Agent"   ms={q.agent_ms}   total={q.total_ms} />
                          <StageBar label="Guard"   ms={q.guardrail_ms} total={q.total_ms} />
                        </div>
                      </div>

                      {/* Tools */}
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Tools used</p>
                        {q.tools.length === 0 ? (
                          <p className="text-xs text-gray-600">None recorded</p>
                        ) : (
                          <div className="space-y-1.5">
                            {q.tools.map(t => (
                              <div key={t.name} className="flex items-center justify-between gap-2">
                                <StatusBadge ok={t.success} label={`🔧 ${t.name}`} />
                                <span className="text-xs text-gray-500">
                                  {t.latency_ms ? msLabel(t.latency_ms) : ''}
                                  {t.error && !t.success && (
                                    <span className="text-red-400 ml-2 truncate max-w-[200px] inline-block align-bottom" title={t.error}>
                                      {t.error}
                                    </span>
                                  )}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* MCP servers */}
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">MCP servers</p>
                        {q.mcp_servers.length === 0 ? (
                          <p className="text-xs text-gray-600">None (fast mode)</p>
                        ) : (
                          <div className="flex flex-wrap gap-1.5">
                            {q.mcp_servers.map(m => (
                              <StatusBadge key={m.name} ok={m.success} label={`🔌 ${m.name}`} />
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Data source APIs */}
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Data sources / APIs hit</p>
                        {q.data_sources.length === 0 ? (
                          <p className="text-xs text-gray-600">None recorded</p>
                        ) : (
                          <div className="space-y-1">
                            {q.data_sources.map((api, i) => (
                              <div key={i} className={`flex items-center justify-between text-xs rounded px-2 py-1.5 ${
                                api.success ? 'bg-gray-800/50' : 'bg-red-950/40 border border-red-900/50'
                              }`}>
                                <span className={api.success ? 'text-green-300' : 'text-red-300'}>
                                  {api.success ? '✓' : '✗'} 🌐 {api.name}
                                </span>
                                {api.url && <span className="text-gray-600 truncate max-w-xs ml-2">{api.url}</span>}
                                <span className="text-gray-500 shrink-0 ml-2">
                                  {api.latency_ms > 0 ? msLabel(api.latency_ms) : ''}
                                </span>
                              </div>
                            ))}
                            {q.data_sources.some(a => !a.success && a.error) && (
                              <p className="text-xs text-red-400 mt-1">
                                {q.data_sources.filter(a => !a.success && a.error).map(a => `${a.name}: ${a.error}`).join(' · ')}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}

        {/* ── TRADING TAB ── */}
        {tab === 'trading' && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
              {[
                { label: 'Total Cost (7d)',  value: `$${(platform?.total_cost || 0).toFixed(4)}`, color: 'text-green-400' },
                { label: 'Total Tokens',     value: (platform?.total_tokens || 0).toLocaleString(), color: 'text-indigo-400' },
                { label: 'Total Calls',      value: String(platform?.total_calls || 0), color: 'text-blue-400' },
                { label: 'Tickers Analyzed', value: String(platform?.unique_tickers || 0), color: 'text-purple-400' },
                { label: 'Guardrail Hits',   value: String(platform?.total_guardrails || 0), color: platform?.total_guardrails ? 'text-yellow-400' : 'text-gray-400' },
              ].map(stat => (
                <div key={stat.label} className="bg-gray-900 rounded-xl border border-gray-800 p-3 text-center">
                  <p className="text-xs text-gray-500 mb-1">{stat.label}</p>
                  <p className={`text-lg font-bold ${stat.color}`}>{stat.value}</p>
                </div>
              ))}
            </div>

            {/* Outcome-based eval */}
            <div className="mb-8 bg-gray-900 border border-gray-800 rounded-xl p-5">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
                    Outcome Eval — Paper Trade Accuracy
                  </h3>
                  <p className="text-xs text-gray-600 mt-1">
                    Scores BUY/SELL/HOLD/TRIM vs {tradingEvalLatest?.horizon_days ?? 5}d forward price — per agent attribution
                  </p>
                </div>
                <button
                  onClick={runTradingEval}
                  disabled={tradingEvalRunning}
                  className="px-3 py-1.5 text-sm bg-emerald-700 hover:bg-emerald-600 rounded-lg text-white disabled:opacity-50">
                  {tradingEvalRunning ? 'Scoring…' : `Run eval${tradingEvalPending > 0 ? ` (${tradingEvalPending} ready)` : ''}`}
                </button>
              </div>

              {tradingEvalError && (
                <div className="mb-3 p-2 bg-red-950 border border-red-800 rounded text-xs text-red-300">
                  {tradingEvalError}
                </div>
              )}

              {tradingEvalLoading ? (
                <p className="text-sm text-gray-500">Loading outcome eval…</p>
              ) : !tradingEvalLatest ? (
                <p className="text-sm text-gray-500">
                  No outcome evals yet. Run debates on <Link href="/trading" className="text-blue-400">/trading</Link>, wait 5+ days, then run eval.
                </p>
              ) : (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-6 gap-2 mb-4">
                    <div className="bg-gray-800/50 rounded-lg p-3">
                      <p className="text-xs text-gray-500">Gate</p>
                      <p className={`font-bold ${tradingEvalLatest.passed ? 'text-green-400' : 'text-red-400'}`}>
                        {tradingEvalLatest.passed ? 'PASS' : 'FAIL'}
                      </p>
                    </div>
                    {[
                      ['Agent accuracy', tradingEvalLatest.overall_accuracy, 0.5],
                      ['BUY accuracy', tradingEvalLatest.buy_accuracy, 0.5],
                      ['SELL accuracy', tradingEvalLatest.sell_accuracy, 0.5],
                      ['Avg return', tradingEvalLatest.avg_pnl_pct / 100, 0],
                      ['Trades scored', tradingEvalLatest.trades_evaluated, 1],
                    ].map(([label, v, thresh]) => (
                      <div key={String(label)} className="bg-gray-800/50 rounded-lg p-3">
                        <p className="text-xs text-gray-500">{label}</p>
                        <p className={`font-bold ${
                          label === 'Trades scored' ? 'text-white' :
                          metricColor(v as number, thresh as number)
                        }`}>
                          {label === 'Trades scored' ? String(v) : label === 'Avg return' ? `${(v as number).toFixed(2)}%` : scorePct(v as number)}
                        </p>
                      </div>
                    ))}
                  </div>

                  {tradingLeaderboard.length > 0 && (
                    <div className="mb-4">
                      <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Agent leaderboard (last run)</p>
                      <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                        {tradingLeaderboard.map(row => {
                          const color = AGENT_COLORS[row.agent_name] || '#6b7280'
                          const label = AGENT_LABELS[row.agent_name] || row.agent_name
                          return (
                            <div key={row.agent_name} className="bg-gray-800/40 rounded-lg p-2 text-xs">
                              <div className="flex items-center gap-1.5 mb-1">
                                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                                <span className="text-white font-medium">{label}</span>
                              </div>
                              <p className={metricColor(row.accuracy, 0.5)}>{scorePct(row.accuracy)}</p>
                              <p className="text-gray-600">{row.correct_count}/{row.scored} correct</p>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {tradingAudits.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs font-semibold text-gray-500 uppercase">Trade audits</p>
                      {tradingAudits.slice(0, 8).map(a => (
                        <div key={a.trade_id} className="border border-gray-800 rounded-lg overflow-hidden">
                          <button
                            onClick={() => setTradingEvalExpanded(tradingEvalExpanded === a.trade_id ? null : a.trade_id)}
                            className="w-full text-left px-3 py-2 flex justify-between items-center hover:bg-gray-800/50 text-sm">
                            <span>
                              <span className="text-white font-medium">{a.ticker}</span>
                              <span className="text-gray-500 ml-2">{a.final_action}</span>
                              <span className={`ml-2 text-xs ${a.outcome === 'correct' || a.outcome === 'partial' ? 'text-green-400' : a.outcome === 'neutral' ? 'text-gray-400' : 'text-red-400'}`}>
                                {a.outcome} · {a.return_pct >= 0 ? '+' : ''}{a.return_pct.toFixed(2)}%
                              </span>
                            </span>
                            <span className="text-gray-600 text-xs">{tradingEvalExpanded === a.trade_id ? '▲' : '▼'}</span>
                          </button>
                          {tradingEvalExpanded === a.trade_id && (
                            <div className="px-3 pb-3 border-t border-gray-800 pt-2 space-y-1">
                              {a.agent_votes.map(v => (
                                <div key={v.agent_name} className="flex justify-between text-xs">
                                  <span className="text-gray-400">{AGENT_LABELS[v.agent_name] || v.agent_name}: {v.action}</span>
                                  {v.correct === null ? (
                                    <span className="text-gray-500">neutral</span>
                                  ) : (
                                    <StatusBadge ok={v.correct} label={v.correct ? 'correct' : 'wrong'} />
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">Agent Cost Breakdown</h3>
                <div className="space-y-3">
                  {agents.length === 0 ? (
                    <div className="text-center py-12 text-gray-600">
                      <p className="text-sm">No trading observations yet. Run analysis on <Link href="/trading" className="text-blue-400">/trading</Link>.</p>
                    </div>
                  ) : agents.map(agent => {
                    const color = AGENT_COLORS[agent.agent] || '#6b7280'
                    const label = AGENT_LABELS[agent.agent] || agent.agent
                    const successRate = agent.calls > 0 ? Math.round((agent.successes / agent.calls) * 100) : 0
                    return (
                      <div key={agent.agent} className="bg-gray-900 rounded-xl border border-gray-800 p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                            <span className="font-semibold text-white">{label}</span>
                            <span className="text-xs text-gray-500">{agent.calls} calls</span>
                          </div>
                          <span className="text-sm font-bold text-green-400">${agent.total_cost.toFixed(5)}</span>
                        </div>
                        <div className="w-full bg-gray-800 rounded-full h-2 mb-3">
                          <div className="h-2 rounded-full" style={{ width: `${(agent.total_cost / maxCost) * 100}%`, backgroundColor: color }} />
                        </div>
                        <div className="grid grid-cols-4 gap-2 text-xs">
                          <div><p className="text-gray-500">Tokens</p><p className="text-gray-300">{agent.total_tokens.toLocaleString()}</p></div>
                          <div><p className="text-gray-500">Latency</p><p className="text-gray-300">{Math.round(agent.avg_latency)}ms</p></div>
                          <div><p className="text-gray-500">Success</p><p className="text-gray-300">{successRate}%</p></div>
                          <div><p className="text-gray-500">Guardrails</p><p className={agent.guardrail_hits > 0 ? 'text-yellow-400' : 'text-gray-300'}>{agent.guardrail_hits}</p></div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">Guardrail Activity</h3>
                {guardrails.length === 0 ? (
                  <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 text-center">
                    <p className="text-sm text-gray-400">✅ No guardrails triggered.</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {guardrails.map((g, i) => (
                      <div key={i} className="bg-yellow-950 border border-yellow-800 rounded-lg p-3">
                        <div className="flex justify-between text-sm">
                          <span className="font-medium text-yellow-300">{AGENT_LABELS[g.agent] || g.agent}</span>
                          <span className="text-xs text-gray-500">{new Date(g.created_at).toLocaleString()}</span>
                        </div>
                        <p className="text-xs text-gray-400 mt-1">{g.ticker}: {g.action} — {g.reason}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* ── RAGAS EVAL TAB ── */}
        {tab === 'ragas' && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
              <div>
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
                  RAGAS Evaluation — LLM-as-Judge (Bedrock)
                </h3>
                <p className="text-xs text-gray-600 mt-1">
                  Faithfulness, answer relevancy, context recall/precision — audited per query
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => runRagasEval(true)}
                  disabled={ragasRunning}
                  className="px-3 py-1.5 text-sm border border-gray-700 rounded-lg text-gray-300 hover:text-white disabled:opacity-50">
                  {ragasRunning ? 'Running…' : 'Smoke (3q)'}
                </button>
                <button
                  onClick={() => runRagasEval(false)}
                  disabled={ragasRunning}
                  className="px-3 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-500 rounded-lg text-white disabled:opacity-50">
                  {ragasRunning ? 'Running eval…' : 'Run full eval'}
                </button>
              </div>
            </div>

            {ragasError && (
              <div className="mb-4 p-3 bg-red-950 border border-red-800 rounded-lg text-sm text-red-300">
                {ragasError}
              </div>
            )}

            {ragasLoading ? (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
                <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <p className="text-gray-400 text-sm">Loading RAGAS eval history…</p>
              </div>
            ) : !ragasLatest ? (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
                <p className="text-4xl mb-3">📋</p>
                <p className="text-gray-400 text-sm">No RAGAS evaluations yet.</p>
                <p className="text-gray-600 text-xs mt-2">Run a smoke or full eval to populate scorecard and audits.</p>
              </div>
            ) : (
              <>
                {/* Gate + scorecard */}
                <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
                  <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 md:col-span-1">
                    <p className="text-xs text-gray-500 uppercase">Gate</p>
                    <p className={`text-lg font-bold mt-1 ${ragasLatest.passed ? 'text-green-400' : 'text-red-400'}`}>
                      {ragasLatest.passed ? 'PASS' : 'FAIL'}
                    </p>
                    <p className="text-xs text-gray-600 mt-1">{ragasLatest.gate}</p>
                  </div>
                  {[
                    { key: 'faithfulness', label: 'Faithfulness', thresh: ragasThresholds.faithfulness, higher: true },
                    { key: 'answer_relevancy', label: 'Relevancy', thresh: ragasThresholds.answer_relevancy, higher: true },
                    { key: 'context_recall', label: 'Ctx recall', thresh: ragasThresholds.context_recall, higher: true },
                    { key: 'hallucination_rate', label: 'Hallucination', thresh: ragasThresholds.hallucination_rate, higher: false },
                    { key: 'overall_score', label: 'Overall', thresh: 0.85, higher: true },
                  ].map(m => {
                    const v = ragasLatest[m.key as keyof RagasRun] as number
                    return (
                      <div key={m.key} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                        <p className="text-xs text-gray-500 uppercase">{m.label}</p>
                        <p className={`text-2xl font-bold mt-1 ${metricColor(v, m.thresh, m.higher)}`}>
                          {scorePct(v)}
                        </p>
                        <p className="text-xs text-gray-600 mt-1">
                          target {m.higher ? '≥' : '≤'} {scorePct(m.thresh)}
                        </p>
                      </div>
                    )
                  })}
                </div>

                <p className="text-xs text-gray-600 mb-4">
                  Latest run {new Date(ragasLatest.evaluated_at).toLocaleString()} ·
                  judge {ragasLatest.judge_model?.replace('us.', '') || 'nova-lite'} ·
                  {ragasLatest.query_count} queries · backend {ragasLatest.backend}
                </p>

                {/* Trend */}
                {ragasTrend.length > 1 && (
                  <div className="mb-8">
                    <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">Score trend</h3>
                    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 overflow-x-auto">
                      <div className="flex gap-3 min-w-max">
                        {ragasTrend.map(r => (
                          <button
                            key={r.run_id}
                            onClick={() => setSelectedRunId(r.run_id)}
                            className={`text-left p-3 rounded-lg border min-w-[120px] transition ${
                              selectedRunId === r.run_id
                                ? 'border-indigo-500 bg-indigo-950/30'
                                : 'border-gray-800 hover:border-gray-700'
                            }`}>
                            <p className="text-xs text-gray-500">{new Date(r.evaluated_at).toLocaleDateString()}</p>
                            <p className={`text-sm font-bold ${r.passed ? 'text-green-400' : 'text-red-400'}`}>
                              {scorePct(r.overall_score)}
                            </p>
                            <p className="text-xs text-gray-600">{r.gate}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Per-query audits */}
                <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">
                  Per-query audits
                </h3>
                <div className="space-y-3">
                  {ragasAudits.map(a => (
                    <div key={a.id} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                      <button
                        onClick={() => setRagasExpanded(ragasExpanded === a.id ? null : a.id)}
                        className="w-full text-left p-4 flex items-start justify-between gap-4 hover:bg-gray-800/50">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-xs px-2 py-0.5 rounded border ${
                              a.passed
                                ? 'bg-green-950 border-green-800 text-green-400'
                                : 'bg-red-950 border-red-800 text-red-400'
                            }`}>
                              {a.passed ? 'PASS' : 'FAIL'}
                            </span>
                            <span className="text-xs text-gray-600">{scorePct(a.overall_score)} overall</span>
                          </div>
                          <p className="text-sm text-white truncate">{a.query}</p>
                        </div>
                        <span className="text-gray-500 text-xs shrink-0">{ragasExpanded === a.id ? '▲' : '▼'}</span>
                      </button>

                      {ragasExpanded === a.id && (
                        <div className="px-4 pb-4 border-t border-gray-800 pt-4 space-y-4">
                          <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
                            {[
                              ['Faithfulness', a.faithfulness, ragasThresholds.faithfulness, true],
                              ['Relevancy', a.answer_relevancy, ragasThresholds.answer_relevancy, true],
                              ['Ctx precision', a.context_precision, 0.7, true],
                              ['Ctx recall', a.context_recall, ragasThresholds.context_recall, true],
                              ['Hallucination', a.hallucination_rate, ragasThresholds.hallucination_rate, false],
                            ].map(([label, v, t, higher]) => (
                              <div key={String(label)} className="bg-gray-800/50 rounded-lg p-2">
                                <p className="text-gray-500">{label}</p>
                                <p className={`font-bold ${metricColor(v as number, t as number, higher as boolean)}`}>
                                  {scorePct(v as number)}
                                </p>
                              </div>
                            ))}
                          </div>

                          <div>
                            <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Generated answer</p>
                            <p className="text-sm text-gray-300 whitespace-pre-wrap">{a.response}</p>
                          </div>

                          <div>
                            <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Ground truth</p>
                            <p className="text-sm text-gray-400">{a.ground_truth}</p>
                          </div>

                          <div>
                            <p className="text-xs font-semibold text-gray-500 uppercase mb-1">
                              Retrieved contexts ({a.contexts.length})
                            </p>
                            {a.contexts.length === 0 ? (
                              <p className="text-xs text-red-400">No context retrieved — search may have failed</p>
                            ) : (
                              <div className="space-y-2">
                                {a.contexts.map((c, i) => (
                                  <p key={i} className="text-xs text-gray-500 bg-gray-800/40 rounded p-2 line-clamp-3">
                                    {c}
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>

                          <div>
                            <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Judge audit</p>
                            <pre className="text-xs text-gray-500 bg-gray-800/40 rounded p-2 overflow-x-auto">
                              {JSON.stringify(a.audit, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}
