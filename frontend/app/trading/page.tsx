'use client'

import { useState, useEffect, useCallback } from 'react'
import { useUser } from '@clerk/nextjs'
import Link from 'next/link'

interface AgentVote {
  agent: string
  action: string
  confidence: number
  opening: string
  reasoning: string
  evidence: string[]
}

interface Trade {
  ticker: string
  action: string
  confidence: number
  price: number
  shares: number
  total_value: number
  rationale: string
  agent_debate: AgentVote[]
  mode: string
  executed_at: string
}

interface Position {
  ticker: string
  shares: number
  avg_cost: number
  current_price: number
  current_value: number
  pnl: number
  pnl_pct: number
  last_action: string
}

interface Simulation {
  total_pnl: number
  total_trades: number
  win_count: number
  current_value: number
  mode: string
}

const AGENTS: Record<string, { color: string; label: string; title: string; bg: string; border: string; text: string }> = {
  marcus:   { color: '#22c55e', label: 'Marcus',   title: 'Bull Analyst',     bg: 'bg-green-950',  border: 'border-green-700',  text: 'text-green-400'  },
  victoria: { color: '#ef4444', label: 'Victoria', title: 'Bear Analyst',     bg: 'bg-red-950',    border: 'border-red-700',    text: 'text-red-400'    },
  zara:     { color: '#3b82f6', label: 'Zara',     title: 'Quant Strategist', bg: 'bg-blue-950',   border: 'border-blue-700',   text: 'text-blue-400'   },
  reid:     { color: '#f97316', label: 'Reid',     title: 'Macro Strategist', bg: 'bg-orange-950', border: 'border-orange-700', text: 'text-orange-400' },
  elena:    { color: '#a855f7', label: 'Elena',    title: 'Risk Manager',     bg: 'bg-purple-950', border: 'border-purple-700', text: 'text-purple-400' },
}

const ACTION_COLORS: Record<string, string> = {
  BUY:  'text-green-400 bg-green-950 border-green-700',
  SELL: 'text-red-400 bg-red-950 border-red-700',
  HOLD: 'text-yellow-400 bg-yellow-950 border-yellow-700',
  TRIM: 'text-orange-400 bg-orange-950 border-orange-700',
}

function AgentDebateCard({ vote }: { vote: AgentVote }) {
  const [expanded, setExpanded] = useState(false)
  const cfg = AGENTS[vote.agent]
  if (!cfg) return null
  return (
    <div className={`rounded-lg border p-3 ${cfg.bg} ${cfg.border} transition-all`}>
      <div className="flex items-center justify-between cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: cfg.color }} />
          <span className={`font-semibold text-sm ${cfg.text}`}>{cfg.label}</span>
          <span className="text-xs text-gray-500">{cfg.title}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold px-2 py-0.5 rounded border ${ACTION_COLORS[vote.action] || 'text-gray-400'}`}>{vote.action}</span>
          <span className="text-xs text-gray-400">{vote.confidence.toFixed(0)}%</span>
          <div className="w-16 bg-gray-800 rounded-full h-1.5">
            <div className="h-1.5 rounded-full transition-all" style={{ width: `${vote.confidence}%`, backgroundColor: cfg.color }} />
          </div>
          <span className="text-gray-600 text-xs">{expanded ? '▲' : '▼'}</span>
        </div>
      </div>
      {vote.opening && <p className="text-xs text-gray-300 mt-2 italic">&ldquo;{vote.opening}&rdquo;</p>}
      {expanded && (
        <div className="mt-3 space-y-2 border-t border-gray-800 pt-3">
          {vote.reasoning && <p className="text-xs text-gray-300">{vote.reasoning}</p>}
          {vote.evidence?.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Key Evidence:</p>
              <ul className="space-y-0.5">
                {vote.evidence.map((e, i) => (
                  <li key={i} className="text-xs text-gray-400 flex gap-1">
                    <span className={cfg.text}>→</span> {e}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function TradeCard({ trade, isLatest }: { trade: Trade; isLatest: boolean }) {
  const [showDebate, setShowDebate] = useState(isLatest)
  return (
    <div className={`rounded-xl border bg-gray-900 overflow-hidden ${isLatest ? 'border-indigo-600' : 'border-gray-800'}`}>
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold text-white">{trade.ticker}</span>
              {isLatest && <span className="text-xs bg-indigo-600 text-white px-2 py-0.5 rounded-full">Latest</span>}
            </div>
            <p className="text-sm text-gray-400">${trade.price?.toFixed(2)} · {new Date(trade.executed_at || '').toLocaleString()}</p>
          </div>
          <div className="text-right">
            <span className={`text-lg font-bold px-3 py-1 rounded-lg border ${ACTION_COLORS[trade.action] || 'text-gray-400'}`}>{trade.action}</span>
           {trade.shares > 0 && <p className="text-xs text-gray-400 mt-1">{trade.shares} shares · ${trade.total_value?.toFixed(0)}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2 mt-2">
          <span className="text-xs text-gray-500">Confidence:</span>
          <div className="flex-1 bg-gray-800 rounded-full h-1.5">
            <div className="h-1.5 rounded-full bg-indigo-500" style={{ width: `${trade.confidence}%` }} />
          </div>
          <span className="text-xs text-gray-400">{trade.confidence?.toFixed(0)}%</span>
        </div>
        {trade.rationale && (
          <div className="mt-3 p-3 bg-gray-800 rounded-lg">
            <p className="text-xs text-gray-500 mb-1 font-semibold">ALEX DECISION</p>
            <p className="text-sm text-gray-200">{trade.rationale}</p>
          </div>
        )}
        <button onClick={() => setShowDebate(!showDebate)} className="mt-3 text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
          {showDebate ? 'Hide' : 'Show'} Agent Debate ({trade.agent_debate?.length || 0} agents) <span>{showDebate ? '▲' : '▼'}</span>
        </button>
      </div>
      {showDebate && trade.agent_debate?.length > 0 && (
        <div className="border-t border-gray-800 p-4 bg-gray-950">
          <p className="text-xs text-gray-500 mb-3 font-semibold tracking-wider">THE DEBATE</p>
          <div className="space-y-2">
            {trade.agent_debate.map((vote, i) => <AgentDebateCard key={i} vote={vote} />)}
          </div>
        </div>
      )}
    </div>
  )
}

function PositionCard({ position }: { position: Position }) {
  const pos = position.pnl >= 0
  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 p-3">
      <div className="flex justify-between items-start">
        <div>
          <span className="font-bold text-white">{position.ticker}</span>
          <p className="text-xs text-gray-500">{position.shares} shares · avg ${position.avg_cost?.toFixed(2)}</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-semibold text-white">${position.current_value?.toFixed(0)}</p>
          <p className={`text-xs font-medium ${pos ? 'text-green-400' : 'text-red-400'}`}>
            {pos ? '+' : ''}{position.pnl?.toFixed(0)} ({position.pnl_pct?.toFixed(1)}%)
          </p>
        </div>
      </div>
      {position.last_action && (
        <span className={`text-xs px-2 py-0.5 rounded mt-2 inline-block border ${ACTION_COLORS[position.last_action] || 'text-gray-400'}`}>
          Last: {position.last_action}
        </span>
      )}
    </div>
  )
}

export default function TradingPage() {
  const { user } = useUser()
  const [trades, setTrades]         = useState<Trade[]>([])
  const [positions, setPositions]   = useState<Position[]>([])
  const [simulation, setSimulation] = useState<Simulation | null>(null)
  const [enabled, setEnabled]       = useState(true)
  const [loading, setLoading]       = useState(true)
  const [running, setRunning]       = useState(false)
  const [lastRun, setLastRun]       = useState<string | null>(null)
  const [activeTab, setActiveTab]   = useState<'trades' | 'positions'>('trades')

  const fetchData = useCallback(async () => {
    try {
      const [dataRes, toggleRes] = await Promise.all([fetch('/api/trading'), fetch('/api/trading/toggle')])
      const data   = await dataRes.json()
      const toggle = await toggleRes.json()
      setTrades(data.trades || [])
      setPositions(data.positions || [])
      setSimulation(data.simulation)
      setEnabled(toggle.enabled)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const runAnalysis = async () => {
    setRunning(true)
    try {
      const res  = await fetch('/api/trading/run', { method: 'POST' })
      const data = await res.json()
      setLastRun(data.message)
      setTimeout(fetchData, 30000)
    } catch (err) {
      console.error(err)
    } finally {
      setRunning(false)
    }
  }

  const toggleTrading = async () => {
    const newState = !enabled
    setEnabled(newState)
    await fetch('/api/trading/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: newState })
    })
  }

  const totalPnl = simulation?.total_pnl || 0
  const winRate  = simulation?.total_trades ? Math.round((simulation.win_count / simulation.total_trades) * 100) : 0

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading Trading Floor...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="border-b border-gray-800 bg-gray-900/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-gray-500 hover:text-gray-300 text-sm">← Dashboard</Link>
            <div>
              <h1 className="text-lg font-bold text-white">🏛️ Alex Trading Floor</h1>
              <p className="text-xs text-gray-500">6-agent AI debate · Paper trading</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Trading</span>
              <button onClick={toggleTrading} className={`relative w-10 h-5 rounded-full transition-colors ${enabled ? 'bg-indigo-600' : 'bg-gray-700'}`}>
                <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${enabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
              </button>
              <span className={`text-xs font-medium ${enabled ? 'text-indigo-400' : 'text-gray-500'}`}>{enabled ? 'ON' : 'OFF'}</span>
            </div>
            <button onClick={runAnalysis} disabled={running || !enabled}
              className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm rounded-lg font-medium transition-colors flex items-center gap-2">
              {running ? <><div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />Analyzing...</> : '▶ Run Analysis'}
            </button>
            <button onClick={fetchData} className="p-1.5 text-gray-500 hover:text-gray-300">↻</button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          {[
            { label: 'Portfolio Value',  value: `$${(simulation?.current_value || 0).toLocaleString()}`, color: 'text-white' },
            { label: 'Total P&L',        value: `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(0)}`,   color: totalPnl >= 0 ? 'text-green-400' : 'text-red-400' },
            { label: 'Total Trades',     value: String(simulation?.total_trades || 0),                    color: 'text-indigo-400' },
            { label: 'Win Rate',         value: `${winRate}%`,                                            color: 'text-yellow-400' },
            { label: 'Mode',             value: (simulation?.mode || 'neutral').toUpperCase(),            color: 'text-purple-400' },
          ].map(stat => (
            <div key={stat.label} className="bg-gray-900 rounded-xl border border-gray-800 p-3 text-center">
              <p className="text-xs text-gray-500 mb-1">{stat.label}</p>
              <p className={`text-lg font-bold ${stat.color}`}>{stat.value}</p>
            </div>
          ))}
        </div>

        {lastRun && (
          <div className="mb-4 p-3 bg-indigo-950 border border-indigo-800 rounded-lg text-sm text-indigo-300">
            ⚡ {lastRun} — Results appear in ~2 minutes.
          </div>
        )}

        <div className="flex flex-wrap gap-2 mb-6">
          {Object.entries(AGENTS).map(([key, cfg]) => (
            <div key={key} className={`flex items-center gap-1.5 px-2 py-1 rounded-full border text-xs ${cfg.bg} ${cfg.border} ${cfg.text}`}>
              <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: cfg.color }} />
              {cfg.label} · {cfg.title}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              {(['trades', 'positions'] as const).map(tab => (
                <button key={tab} onClick={() => setActiveTab(tab)}
                  className={`text-sm font-medium pb-1 border-b-2 transition-colors capitalize ${activeTab === tab ? 'border-indigo-500 text-white' : 'border-transparent text-gray-500'}`}>
                  {tab} ({tab === 'trades' ? trades.length : positions.length})
                </button>
              ))}
            </div>
            {activeTab === 'trades' && (
              <div className="space-y-4">
                {trades.length === 0 ? (
                  <div className="text-center py-16">
                    <p className="text-4xl mb-3">🏛️</p>
                    <p className="text-lg font-medium text-gray-400">No trades yet</p>
                    <p className="text-sm text-gray-600 mt-1">Click Run Analysis to start the 6-agent debate</p>
                  </div>
                ) : trades.map((trade, i) => <TradeCard key={i} trade={trade} isLatest={i === 0} />)}
              </div>
            )}
            {activeTab === 'positions' && (
              <div className="space-y-2">
                {positions.length === 0 ? (
                  <div className="text-center py-16">
                    <p className="text-4xl mb-3">📊</p>
                    <p className="text-sm text-gray-500">No positions yet</p>
            </div>
                ) : positions.map((pos, i) => <PositionCard key={i} position={pos} />)}
              </div>
            )}
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">Agent Panel</h3>
            <div className="space-y-2">
              {Object.entries(AGENTS).map(([key, cfg]) => (
                <div key={key} className={`rounded-lg border p-3 ${cfg.bg} ${cfg.border}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: cfg.color }} />
                    <span className={`font-semibold text-sm ${cfg.text}`}>{cfg.label}</span>
                  </div>
                  <p className="text-xs text-gray-500">{cfg.title}</p>
                  <div className="mt-2">
                    {trades.slice(0, 3).map((trade, i) => {
                      const vote = trade.agent_debate?.find(v => v.agent === key)
                      if (!vote) return null
                      return (
                        <div key={i} className="flex justify-between text-xs mt-1">
                          <span className="text-gray-500">{trade.ticker}</span>
                          <span className={ACTION_COLORS[vote.action]?.split(' ')[0] || 'text-gray-400'}>{vote.action} {vote.confidence.toFixed(0)}%</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 p-4 bg-gray-900 rounded-xl border border-gray-800">
              <p className="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wider">How It Works</p>
              <div className="space-y-1.5 text-xs text-gray-500">
                <p>① Alex reads your portfolio</p>
                <p>② 5 agents debate each stock in parallel</p>
                <p>③ Weighted vote determines action</p>
                <p>④ Alex synthesizes final decision</p>
                <p>⑤ Trade stored with full rationale</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
