'use client'

import { useCallback, useEffect, useState } from 'react'
import AlexMarkdown from '@/components/AlexMarkdown'

interface OpsData {
  latest:       { date: string; total: number; services: Record<string, number>; digest: string } | null
  weeklyTotal:  number
  mtdTotal:     number
  health:       { service: string; status: string; detail?: string }[]
  healthScore:  number | null
  updatedAt:    string | null
  pollIntervalMs: number
}

function statusColor(status: string) {
  if (status === 'healthy') return 'text-green-400'
  if (status === 'degraded') return 'text-yellow-400'
  return 'text-red-400'
}

function costStatus(today: number) {
  if (today > 10) return { label: '⚠️ Alert', cls: 'bg-red-500/20 text-red-400', dot: 'bg-red-400 animate-pulse' }
  if (today > 5)  return { label: '👀 Monitor', cls: 'bg-yellow-500/20 text-yellow-400', dot: 'bg-yellow-400' }
  return { label: '✅ On Track', cls: 'bg-green-500/20 text-green-400', dot: 'bg-green-400' }
}

function formatUpdated(iso: string | null) {
  if (!iso) return 'Never'
  const d = new Date(iso.includes('T') ? iso : iso.replace(' ', 'T') + 'Z')
  if (isNaN(d.getTime())) return iso
  const mins = Math.round((Date.now() - d.getTime()) / 60000)
  if (mins < 2) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  return d.toLocaleString()
}

export default function OpsCostWidget() {
  const [data, setData]           = useState<OpsData | null>(null)
  const [loading, setLoading]     = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState<string | null>(null)

  const fetchOps = useCallback(async () => {
    try {
      const res  = await fetch('/api/ops', { cache: 'no-store' })
      const json = await res.json()
      setData({
        latest:         json.latest,
        weeklyTotal:    json.weeklyTotal || 0,
        mtdTotal:       json.mtdTotal || 0,
        health:         json.health || [],
        healthScore:    json.healthScore,
        updatedAt:      json.updatedAt || json.ops?.last_run || null,
        pollIntervalMs: json.pollIntervalMs || 1800000,
      })
      return true
    } catch (e) {
      console.error('Ops poll error:', e)
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshNow = useCallback(async () => {
    setRefreshing(true)
    setRefreshError(null)
    try {
      const res  = await fetch('/api/ops', { method: 'POST' })
      const json = await res.json()
      if (!res.ok) {
        setRefreshError(json.error || 'Ops agent run failed')
        return
      }
      await fetchOps()
    } catch (e) {
      console.error('Ops refresh error:', e)
      setRefreshError('Could not reach ops agent — check AWS credentials')
    } finally {
      setRefreshing(false)
    }
  }, [fetchOps])

  useEffect(() => {
    fetchOps()
    const interval = setInterval(fetchOps, 30 * 60 * 1000)
    return () => clearInterval(interval)
  }, [fetchOps])

  if (loading && !data) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mt-6 animate-pulse">
        <div className="h-4 bg-gray-800 rounded w-48 mb-4" />
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-16 bg-gray-800 rounded-lg" />)}
        </div>
      </div>
    )
  }

  const today     = data?.latest?.total || 0
  const week      = data?.weeklyTotal || 0
  const mtd       = data?.mtdTotal || 0
  const services  = Object.entries(data?.latest?.services || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
  const cs        = costStatus(today)
  const digest    = data?.latest?.digest || ''

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mt-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${cs.dot}`} />
          <h2 className="font-semibold text-white">AWS Cost & Ops Monitor</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-1 rounded-full ${cs.cls}`}>{cs.label}</span>
          {data?.healthScore != null && (
            <span className="text-xs px-2 py-1 rounded-full bg-indigo-500/20 text-indigo-400">
              Health {data.healthScore}%
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div className="bg-gray-800 rounded-lg p-3 text-center">
          <div className="text-xs text-gray-500 mb-1">Today</div>
          <div className={`text-lg font-bold ${today > 10 ? 'text-red-400' : 'text-white'}`}>
            ${today.toFixed(2)}
          </div>
          <div className="text-xs text-gray-600">threshold $10</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-3 text-center">
          <div className="text-xs text-gray-500 mb-1">This Week</div>
          <div className="text-lg font-bold text-white">${week.toFixed(2)}</div>
          <div className="text-xs text-gray-600">last 7 days</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-3 text-center">
          <div className="text-xs text-gray-500 mb-1">Month to Date</div>
          <div className="text-lg font-bold text-white">${mtd.toFixed(2)}</div>
          <div className="text-xs text-gray-600">Cost Explorer</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-3 text-center">
          <div className="text-xs text-gray-500 mb-1">Daily Avg</div>
          <div className="text-lg font-bold text-white">
            ${data?.latest ? (week / 7).toFixed(2) : '0.00'}
          </div>
          <div className="text-xs text-gray-600">7-day avg</div>
        </div>
      </div>

      {services.length > 0 && (
        <div className="mb-4">
          <div className="text-xs text-gray-500 mb-2">Top cost drivers today</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {services.map(([svc, amt]) => (
              <div key={svc} className="flex justify-between text-xs bg-gray-800 rounded px-3 py-2">
                <span className="text-gray-400 truncate mr-2">{svc.replace('Amazon ', '').replace('AWS ', '')}</span>
                <span className="text-white font-medium">${amt.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data?.health && data.health.length > 0 && (
        <div className="mb-4">
          <div className="text-xs text-gray-500 mb-2">Platform health</div>
          <div className="flex flex-wrap gap-2">
            {data.health.map(h => (
              <span
                key={h.service}
                className={`text-xs px-2 py-1 rounded-full bg-gray-800 ${statusColor(h.status)}`}
                title={h.detail}
              >
                {h.service}: {h.status}
              </span>
            ))}
          </div>
        </div>
      )}

      {digest && (
        <div className="p-3 bg-gray-800 rounded-lg max-h-56 overflow-y-auto mb-3">
          <div className="text-xs text-gray-500 mb-2">Ops digest</div>
          <AlexMarkdown content={digest} />
        </div>
      )}

      <div className="text-xs text-gray-600 text-center">
        Ops agent updates every 30 min · Last refresh: {formatUpdated(data?.updatedAt || null)}
        {' · '}
        <button
          type="button"
          onClick={refreshNow}
          disabled={refreshing}
          className="text-blue-400 hover:text-blue-300 underline disabled:opacity-50 disabled:cursor-wait"
        >
          {refreshing ? 'Running ops agent…' : 'Refresh now'}
        </button>
        {refreshError && (
          <p className="text-red-400 mt-2">{refreshError}</p>
        )}
      </div>
    </div>
  )
}
