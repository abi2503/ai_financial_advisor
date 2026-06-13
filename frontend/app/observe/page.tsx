'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'

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

export default function ObservePage() {
  const [agents, setAgents]       = useState<AgentStat[]>([])
  const [platform, setPlatform]   = useState<Platform | null>(null)
  const [guardrails, setGuardrails] = useState<GuardrailLog[]>([])
  const [loading, setLoading]     = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/observe')
      const data = await res.json()
      setAgents(data.agents || [])
      setPlatform(data.platform)
      setGuardrails(data.guardrails || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

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
      <div className="border-b border-gray-800 bg-gray-900/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/trading" className="text-gray-500 hover:text-gray-300 text-sm">← Trading Floor</Link>
            <div>
              <h1 className="text-lg font-bold text-white">🔭 Alex Observability</h1>
              <p className="text-xs text-gray-500">Cost, tokens, latency & guardrails per agent — last 7 days</p>
            </div>
          </div>
          <button onClick={fetchData} className="p-1.5 text-gray-500 hover:text-gray-300">↻</button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Platform stats */}
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

        {/* Monthly forecast */}
        <div className="mb-6 p-4 bg-indigo-950 border border-indigo-800 rounded-xl">
          <p className="text-sm text-indigo-300">
            <span className="font-bold">Monthly forecast:</span>{' '}
            ${((platform?.total_cost || 0) / 7 * 30).toFixed(2)} based on current usage
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Agent breakdown */}
          <div>
            <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">Agent Cost Breakdown</h3>
            <div className="space-y-3">
              {agents.length === 0 ? (
                <div className="text-center py-12 text-gray-600">
                  <p className="text-4xl mb-3">🔭</p>
                  <p className="text-sm">No observations yet. Run a trading analysis first.</p>
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
                      <div>
                        <p className="text-gray-500">Tokens</p>
                        <p className="text-gray-300 font-medium">{agent.total_tokens.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Avg Latency</p>
                        <p className="text-gray-300 font-medium">{Math.round(agent.avg_latency)}ms</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Success</p>
                        <p className="text-gray-300 font-medium">{successRate}%</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Guardrails</p>
                        <p className={agent.guardrail_hits > 0 ? 'text-yellow-400 font-medium' : 'text-gray-300 font-medium'}>{agent.guardrail_hits}</p>
                      </div>
                    </div>
                    {/* Action distribution */}
                    <div className="mt-3 flex gap-1 h-1.5 rounded-full overflow-hidden">
                      {agent.buy_count > 0 && <div className="bg-green-500" style={{ flex: agent.buy_count }} title={`BUY: ${agent.buy_count}`} />}
                      {agent.sell_count > 0 && <div className="bg-red-500" style={{ flex: agent.sell_count }} title={`SELL: ${agent.sell_count}`} />}
                      {agent.hold_count > 0 && <div className="bg-yellow-500" style={{ flex: agent.hold_count }} title={`HOLD: ${agent.hold_count}`} />}
                      {agent.trim_count > 0 && <div className="bg-orange-500" style={{ flex: agent.trim_count }} title={`TRIM: ${agent.trim_count}`} />}
                    </div>
                    <div className="mt-1 flex gap-3 text-xs text-gray-500">
                      <span>BUY {agent.buy_count}</span>
                      <span>SELL {agent.sell_count}</span>
                      <span>HOLD {agent.hold_count}</span>
                      <span>TRIM {agent.trim_count}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Guardrails + info */}
          <div>
            <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">Guardrail Activity</h3>
            {guardrails.length === 0 ? (
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 text-center">
                <p className="text-2xl mb-2">✅</p>
                <p className="text-sm text-gray-400">No guardrails triggered. All agents operating within limits.</p>
              </div>
          ) : (
              <div className="space-y-2">
                {guardrails.map((g, i) => (
                  <div key={i} className="bg-yellow-950 border border-yellow-800 rounded-lg p-3">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium text-yellow-300">{AGENT_LABELS[g.agent] || g.agent}</span>
                      <span className="text-xs text-gray-500">{new Date(g.created_at).toLocaleString()}</span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">{g.ticker}: {g.action} ({g.confidence}%) — {g.reason}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-4 p-4 bg-gray-900 rounded-xl border border-gray-800">
              <p className="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wider">Active Guardrails</p>
              <div className="space-y-1.5 text-xs text-gray-500">
                <p>• Confidence capped at 95% (no overconfidence)</p>
                <p>• Confidence floored at 10% (no zero-conviction)</p>
                <p>• Action must be BUY/SELL/HOLD/TRIM</p>
                <p>• Max position size: 50% of portfolio</p>
              </div>
            </div>

            <div className="mt-4 p-4 bg-gray-900 rounded-xl border border-gray-800">
              <p className="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wider">Model Pricing (per 1K tokens)</p>
              <div className="space-y-1.5 text-xs text-gray-500">
                <p>Nova Pro: $0.0008 in / $0.0032 out</p>
                <p>Nova Lite: $0.00006 in / $0.00024 out</p>
                <p className="text-indigo-400 mt-2">Elena uses Nova Lite — ~13x cheaper</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
