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
  fast:   'bg-blue-500/20 text-blue-400 border-blue-500/30',
  stream: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  deep:   'bg-purple-500/20 text-purple-400 border-purple-500/30',
  multi:  'bg-orange-500/20 text-orange-400 border-orange-500/30',
}

function msLabel(ms: number) {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
  return `${ms}ms`
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
  const [tab, setTab]               = useState<'research' | 'trading'>('research')
  const [agents, setAgents]         = useState<AgentStat[]>([])
  const [platform, setPlatform]     = useState<Platform | null>(null)
  const [guardrails, setGuardrails] = useState<GuardrailLog[]>([])
  const [querySummary, setQuerySummary] = useState<QuerySummary[]>([])
  const [recentQueries, setRecentQueries] = useState<RecentQuery[]>([])
  const [expanded, setExpanded]     = useState<string | null>(null)
  const [loading, setLoading]       = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const res  = await fetch('/api/observe')
      const data = await res.json()
      setAgents(data.agents || [])
      setPlatform(data.platform)
      setGuardrails(data.guardrails || [])
      setQuerySummary(data.querySummary || [])
      setRecentQueries(data.recentQueries || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  useEffect(() => {
    if (tab !== 'research') return
    const id = setInterval(fetchData, 30000)
    return () => clearInterval(id)
  }, [tab, fetchData])

  const maxCost = Math.max(...agents.map(a => a.total_cost), 0.0001)

  if (loading) {
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
              Per-query latency, tools, MCP servers, and API sources — last 7 days
            </p>
          </div>
          <button onClick={() => { setLoading(true); fetchData() }}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-white border border-gray-700 rounded-lg">
            ↻ Refresh
          </button>
        </div>
        <div className="max-w-7xl mx-auto px-4 flex gap-1 pb-0">
          {(['research', 'trading'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition ${
                tab === t
                  ? 'border-indigo-500 text-white bg-gray-900'
                  : 'border-transparent text-gray-500 hover:text-gray-300'
              }`}>
              {t === 'research' ? '🧠 Research Queries' : '📈 Trading Floor'}
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">

        {/* ── RESEARCH TAB ── */}
        {tab === 'research' && (
          <>
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
                        {s.route}
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
                            {q.route}
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
      </div>
    </div>
  )
}
