'use client'
import { useState, useEffect } from 'react'
import Navbar from '@/components/Navbar'
import Link from 'next/link'
import { Loader2, RefreshCw, BarChart2 } from 'lucide-react'
import axios from 'axios'
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ReferenceLine
} from 'recharts'

interface Stock {
  id:             string
  ticker:         string
  company:        string
  shares:         number
  purchase_price: number
  asset_class:    string
  sector:         string
  added_at:       string
}

interface Price {
  price:     string
  changePct: string
  change:    string
}

const COLORS = [
  '#1e3a5f', '#6b8f71', '#c4a882', '#b87d7d', '#8b2942',
  '#6b5b95', '#e07b39', '#d4a017', '#3d8b5f', '#8b6914',
  '#5c6b8a', '#4a90a4', '#c9b896', '#e891a3', '#9ca3af',
]

const assetClassColors: Record<string, string> = {
  stocks:      '#3b82f6',
  etf:         '#10b981',
  crypto:      '#f59e0b',
  bonds:       '#8b5cf6',
  real_estate: '#06b6d4',
  commodities: '#f97316',
  cash:        '#6b7280',
}

const assetClassEmoji: Record<string, string> = {
  stocks:      '📈',
  etf:         '📊',
  crypto:      '₿',
  bonds:       '🏦',
  real_estate: '🏠',
  commodities: '🥇',
  cash:        '💵',
}

const PieTooltip = ({ active, payload }: any) => {
  if (active && payload?.length) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm">
        <p className="text-white font-medium">{payload[0].name}</p>
        <p className="text-blue-400">
          ${payload[0].value.toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </p>
        <p className="text-gray-400">{payload[0].payload.percent}%</p>
      </div>
    )
  }
  return null
}

const BarTooltip = ({ active, payload }: any) => {
  if (active && payload?.length) {
    const val = payload[0].value
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm">
        <p className="text-white font-medium">{payload[0].payload.ticker}</p>
        <p className={val >= 0 ? 'text-green-400' : 'text-red-400'}>
          {val >= 0 ? '+' : ''}{val.toFixed(2)}% today
        </p>
      </div>
    )
  }
  return null
}

const TOP_HOLDINGS = 13

interface TickerSlice {
  name:    string
  value:   number
  percent: string
  company: string
  shares:  number
}

function buildTickerBreakdown(
  positions: { ticker: string; company: string; value: number; shares: number }[],
  totalValue: number,
): TickerSlice[] {
  const sorted = [...positions]
    .filter(p => p.value > 0)
    .sort((a, b) => b.value - a.value)

  const top       = sorted.slice(0, TOP_HOLDINGS)
  const rest      = sorted.slice(TOP_HOLDINGS)
  const othersVal = rest.reduce((s, p) => s + p.value, 0)

  const pct = (v: number) =>
    totalValue > 0 ? ((v / totalValue) * 100).toFixed(2) : '0.00'

  const data: TickerSlice[] = top.map(p => ({
    name:    p.ticker,
    value:   parseFloat(p.value.toFixed(2)),
    percent: pct(p.value),
    company: p.company,
    shares:  p.shares,
  }))

  if (othersVal > 0) {
    data.push({
      name:    'Others',
      value:   parseFloat(othersVal.toFixed(2)),
      percent: pct(othersVal),
      company: `${rest.length} smaller positions`,
      shares:  0,
    })
  }
  return data
}

const RADIAN = Math.PI / 180

function TickerPieLabel(props: {
  cx?: number; cy?: number; midAngle?: number
  outerRadius?: number; percent?: number; name?: string
}) {
  const { cx = 0, cy = 0, midAngle = 0, outerRadius = 0, percent = 0, name = '' } = props
  if (percent < 0.025) return null
  const radius = outerRadius + 22
  const x  = cx + radius * Math.cos(-midAngle * RADIAN)
  const y  = cy + radius * Math.sin(-midAngle * RADIAN)
  const anchor = x > cx ? 'start' : 'end'
  return (
    <text
      x={x} y={y} fill="#d1d5db" textAnchor={anchor}
      dominantBaseline="central" fontSize={11} fontWeight={500}
    >
      {`${name} ${(percent * 100).toFixed(2)}%`}
    </text>
  )
}

export default function ChartsPage() {
  const [portfolio,     setPortfolio]     = useState<Stock[]>([])
  const [prices,        setPrices]        = useState<Record<string, Price>>({})
  const [loading,       setLoading]       = useState(true)
  const [pricesLoading, setPricesLoading] = useState(false)
  const [lastUpdated,   setLastUpdated]   = useState('')

  useEffect(() => { fetchAll() }, [])

  async function fetchAll() {
    try {
      setLoading(true)
      const res    = await axios.get('/api/portfolio')
      const stocks = res.data.portfolio || []
      setPortfolio(stocks)
      if (stocks.length > 0) {
        await fetchPrices(stocks.map((s: Stock) => s.ticker))
      }
    } catch (err) {
      console.error('Charts fetch error:', err)
    } finally {
      setLoading(false)
    }
  }

  async function fetchPrices(tickers: string[]) {
    try {
      setPricesLoading(true)
      const res = await axios.post('/api/portfolio/prices', { tickers })
      setPrices(res.data.prices || {})
      setLastUpdated(new Date().toLocaleTimeString())
    } catch (err) {
      console.error('Prices error:', err)
    } finally {
      setPricesLoading(false)
    }
  }

  const positions = portfolio.map(stock => {
    const price       = parseFloat(prices[stock.ticker]?.price || '0')
    const changePct   = parseFloat(prices[stock.ticker]?.changePct || '0')
    const value       = stock.shares > 0 ? stock.shares * price : price
    const costBasis   = stock.shares * stock.purchase_price
    const gainLossPct = costBasis > 0
      ? (((value - costBasis) / costBasis) * 100)
      : 0
    return { ...stock, currentPrice: price, changePct, value, costBasis, gainLossPct }
  })

  const totalValue = positions.reduce((sum, p) => sum + p.value, 0)

  const assetClassData = Object.entries(
    positions.reduce((acc, p) => {
      const cls = p.asset_class || 'stocks'
      acc[cls]  = (acc[cls] || 0) + p.value
      return acc
    }, {} as Record<string, number>)
  ).map(([name, value]) => ({
    name:    `${assetClassEmoji[name] || '📈'} ${name}`,
    value:   parseFloat(value.toFixed(2)),
    percent: totalValue > 0 ? ((value / totalValue) * 100).toFixed(1) : '0',
    color:   assetClassColors[name] || '#3b82f6'
  }))

  const sectorData = Object.entries(
    positions.reduce((acc, p) => {
      const sec = p.sector || 'Other'
      acc[sec]  = (acc[sec] || 0) + p.value
      return acc
    }, {} as Record<string, number>)
  ).map(([name, value]) => ({
    name,
    value:   parseFloat(value.toFixed(2)),
    percent: totalValue > 0 ? ((value / totalValue) * 100).toFixed(1) : '0'
  }))

  const performanceData = positions
    .filter(p => prices[p.ticker])
    .map(p => ({
      ticker:    p.ticker,
      changePct: parseFloat(p.changePct.toFixed(2)),
      value:     p.value,
    }))
    .sort((a, b) => b.changePct - a.changePct)

  const tickerBreakdown = buildTickerBreakdown(positions, totalValue)

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950">
        <Navbar />
        <div className="flex items-center justify-center py-40">
          <Loader2 size={24} className="animate-spin text-blue-400" />
          <span className="ml-3 text-gray-400">Loading charts...</span>
        </div>
      </div>
    )
  }

  if (portfolio.length === 0) {
    return (
      <div className="min-h-screen bg-gray-950">
        <Navbar />
        <main className="max-w-6xl mx-auto px-6 py-8">
          <div className="text-center py-20">
            <BarChart2 size={32} className="mx-auto mb-3 text-gray-600" />
            <p className="text-gray-500 mb-4">No portfolio positions yet</p>
            <Link
              href="/portfolio"
              className="px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg text-white text-sm transition inline-block"
            >
              Add positions first
            </Link>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar />
      <main className="max-w-6xl mx-auto px-6 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Portfolio Charts</h1>
            <p className="text-gray-400 text-sm mt-1">
              Total Value: ${totalValue.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
              })}
              {lastUpdated && (
                <span className="text-gray-600 ml-2">· Updated {lastUpdated}</span>
              )}
            </p>
          </div>
          <button
            onClick={fetchAll}
            disabled={pricesLoading}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-400 transition"
          >
            <RefreshCw size={16} className={pricesLoading ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {positions.slice(0, 4).map(p => (
            <div key={p.ticker} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-white">{p.ticker}</span>
                <span className={`text-sm font-medium ${
                  p.changePct >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {p.changePct >= 0 ? '+' : ''}{p.changePct.toFixed(2)}%
                </span>
              </div>
              <div className="text-gray-500 text-xs">
                {assetClassEmoji[p.asset_class] || '📈'} {p.asset_class}
              </div>
              <div className="text-white font-medium mt-1">
                ${p.currentPrice.toFixed(2)}
              </div>
              {p.gainLossPct !== 0 && (
                <div className={`text-xs mt-0.5 ${
                  p.gainLossPct >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {p.gainLossPct >= 0 ? '+' : ''}{p.gainLossPct.toFixed(2)}% total
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Holdings Breakdown — per-ticker allocation donut */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
          <div className="flex items-start justify-between mb-2">
            <div>
              <h2 className="font-semibold text-white">Holdings Breakdown</h2>
              <p className="text-gray-500 text-xs mt-1">
                Portfolio weight by ticker · top {TOP_HOLDINGS} shown individually
              </p>
            </div>
            <span className="text-gray-500 text-xs">
              {positions.length} position{positions.length !== 1 ? 's' : ''}
            </span>
          </div>

          <div className="flex flex-col lg:flex-row items-center gap-8">
            <div className="w-full lg:w-1/2">
              <ResponsiveContainer width="100%" height={360}>
                <PieChart>
                  <Pie
                    data={tickerBreakdown}
                    cx="50%"
                    cy="50%"
                    innerRadius={72}
                    outerRadius={118}
                    paddingAngle={1.5}
                    dataKey="value"
                    labelLine={{ stroke: '#4b5563', strokeWidth: 1 }}
                    label={TickerPieLabel}
                  >
                    {tickerBreakdown.map((entry, index) => (
                      <Cell
                        key={entry.name}
                        fill={COLORS[index % COLORS.length]}
                        stroke="#111827"
                        strokeWidth={2}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<PieTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="w-full lg:w-1/2 max-h-80 overflow-y-auto pr-1">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 text-xs border-b border-gray-800">
                    <th className="text-left pb-2 font-medium">Ticker</th>
                    <th className="text-right pb-2 font-medium">Value</th>
                    <th className="text-right pb-2 font-medium">Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {tickerBreakdown.map((row, i) => (
                    <tr
                      key={row.name}
                      className="border-b border-gray-800/60 last:border-0"
                    >
                      <td className="py-2.5">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-2.5 h-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: COLORS[i % COLORS.length] }}
                          />
                          <div>
                            <span className="text-white font-medium">{row.name}</span>
                            {row.name !== 'Others' && row.company && (
                              <p className="text-gray-600 text-xs truncate max-w-[140px]">
                                {row.company}
                              </p>
                            )}
                            {row.name === 'Others' && (
                              <p className="text-gray-600 text-xs">{row.company}</p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-2.5 text-right text-gray-300 tabular-nums">
                        ${row.value.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-2.5 text-right text-white font-medium tabular-nums">
                        {row.percent}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Pie Charts */}
        <div className="grid grid-cols-2 gap-6 mb-6">

          {/* Asset Class */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="font-semibold text-white mb-4">Asset Class Allocation</h2>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={assetClassData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {assetClassData.map((entry, index) => (
                    <Cell
                      key={entry.name}
                      fill={entry.color || COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip content={<PieTooltip />} />
                <Legend
                  formatter={(value, entry: any) => (
                    <span className="text-gray-300 text-xs">
                      {value} ({entry.payload.percent}%)
                    </span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Sector Breakdown */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="font-semibold text-white mb-4">Sector Breakdown</h2>
            {sectorData.filter(s => s.name && s.name !== 'Other').length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={sectorData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {sectorData.map((entry, index) => (
                      <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<PieTooltip />} />
                  <Legend
                    formatter={(value, entry: any) => (
                      <span className="text-gray-300 text-xs">
                        {value} ({entry.payload.percent}%)
                      </span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-500 text-sm flex-col gap-2">
                <BarChart2 size={24} className="opacity-40" />
                <p>Add sectors to positions to see breakdown</p>
                <Link href="/portfolio" className="text-blue-400 text-xs hover:underline">
                  Update positions
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Daily Performance Bar Chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="font-semibold text-white mb-4">Today's Performance</h2>
          {performanceData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart
                data={performanceData}
                margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                <XAxis
                  dataKey="ticker"
                  tick={{ fill: '#9ca3af', fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#9ca3af', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={v => `${v}%`}
                />
                <Tooltip content={<BarTooltip />} />
                <ReferenceLine y={0} stroke="#4b5563" />
                <Bar dataKey="changePct" radius={[4, 4, 0, 0]}>
                  {performanceData.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={entry.changePct >= 0 ? '#10b981' : '#ef4444'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
              Price data loading...
            </div>
          )}
        </div>

      </main>
    </div>
  )
}