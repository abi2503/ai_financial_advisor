'use client'
import { useState, useEffect } from 'react'
import Navbar from '@/components/Navbar'
import { Plus, TrendingUp, TrendingDown, X, Loader2, RefreshCw } from 'lucide-react'
import axios from 'axios'
import Link from 'next/link'

interface Stock {
  id:             string
  ticker:         string
  company:        string
  shares:         number
  purchase_price: number
  asset_class:    string
  sector:         string
  notes:          string
  added_at:       string
}

interface Price {
  price:     string
  change:    string
  changePct: string
  high:      string
  low:       string
  volume:    number
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

const riskColors: Record<string, string> = {
  high:    'text-red-400 bg-red-400/10',
  medium:  'text-yellow-400 bg-yellow-400/10',
  low:     'text-green-400 bg-green-400/10',
  unknown: 'text-gray-400 bg-gray-400/10',
}

export default function PortfolioPage() {
  const [portfolio,     setPortfolio]     = useState<Stock[]>([])
  const [prices,        setPrices]        = useState<Record<string, Price>>({})
  const [loading,       setLoading]       = useState(true)
  const [pricesLoading, setPricesLoading] = useState(false)
  const [showAdd,       setShowAdd]       = useState(false)
  const [ticker,        setTicker]        = useState('')
  const [shares,        setShares]        = useState('')
  const [purchasePrice, setPurchasePrice] = useState('')
  const [assetClass,    setAssetClass]    = useState('stocks')
  const [adding,        setAdding]        = useState(false)
  const [error,         setError]         = useState('')
  const [lastUpdated,   setLastUpdated]   = useState<string>('')
  const [showEdit,    setShowEdit]    = useState(false)
  const [editStock,   setEditStock]   = useState<Stock | null>(null)
  const [editShares,  setEditShares]  = useState('')
  const [editPrice,   setEditPrice]   = useState('')
  const [updating,    setUpdating]    = useState(false)
  useEffect(() => {
    async function init() {
      try {
        await axios.post('/api/users/sync')
      } catch (err) {
        console.error('Sync error:', err)
      }
      await fetchPortfolio()
    }
    init()
  }, [])

  async function fetchPortfolio() {
    try {
      setLoading(true)
      const res    = await axios.get('/api/portfolio')
      const stocks = res.data.portfolio || []
      setPortfolio(stocks)
      if (stocks.length > 0) {
        await fetchPrices(stocks.map((s: Stock) => s.ticker))
      }
    } catch (err: any) {
      console.error('Portfolio fetch error:', err)
      setError('Failed to load portfolio')
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

  async function handleUpdateStock() {
    if (!editStock) return
    setUpdating(true)
    try {
      await axios.patch('/api/portfolio', {
        ticker:         editStock.ticker,
        shares:         parseFloat(editShares) || 0,
        purchase_price: parseFloat(editPrice) || 0,
      })
      await fetchPortfolio()
      setShowEdit(false)
      setEditStock(null)
    } catch (err) {
      setError('Failed to update position')
    } finally {
      setUpdating(false)
    }
  }
  
  function openEdit(stock: Stock) {
    setEditStock(stock)
    setEditShares(stock.shares.toString())
    setEditPrice(stock.purchase_price.toString())
    setShowEdit(true)
  }

  async function handleAddStock() {
    if (!ticker) return
    setAdding(true)
    try {
      await axios.post('/api/portfolio', {
        ticker,
        shares:         parseFloat(shares) || 0,
        purchase_price: parseFloat(purchasePrice) || 0,
        asset_class:    assetClass,
      })
      await fetchPortfolio()
      setTicker('')
      setShares('')
      setPurchasePrice('')
      setAssetClass('stocks')
      setShowAdd(false)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to add stock')
    } finally {
      setAdding(false)
    }
  }

  async function handleRemove(tickerToRemove: string) {
    try {
      await axios.delete('/api/portfolio', {
        data: { ticker: tickerToRemove }
      })
      await fetchPortfolio()
    } catch (err) {
      console.error('Remove error:', err)
    }
  }

  const totalValue = portfolio.reduce((sum, stock) => {
    const price  = parseFloat(prices[stock.ticker]?.price || '0')
    const qty    = stock.shares || 0
    return sum + (price * qty)
  }, 0)

  const totalCost = portfolio.reduce((sum, stock) => {
    return sum + (stock.shares * stock.purchase_price)
  }, 0)

  const totalGainDollar = totalValue - totalCost
  const totalGainPct = totalCost > 0
    ? (((totalValue - totalCost) / totalCost) * 100).toFixed(2)
    : null

  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar />
      <main className="max-w-4xl mx-auto px-6 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">My Portfolio</h1>
            <p className="text-gray-400 text-sm mt-1">
              {loading ? 'Loading...' : (
                <>
                  {portfolio.length} positions
                  {totalValue > 0 && (
                    <>
                      <span className="mx-2 text-gray-600">·</span>
                      <span className="text-white font-semibold">
                        ${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                      <span className="text-gray-500 text-xs ml-1">market value</span>
                    </>
                  )}
                  {totalCost > 0 && (
                    <>
                      <span className="mx-2 text-gray-600">·</span>
                      <span className="text-gray-300">
                        ${totalCost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                      <span className="text-gray-500 text-xs ml-1">cost basis</span>
                    </>
                  )}
                  {totalGainPct && (
                    <span className={`ml-2 text-sm font-medium ${parseFloat(totalGainPct) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {parseFloat(totalGainPct) >= 0 ? '+' : ''}${totalGainDollar.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      {' '}({parseFloat(totalGainPct) >= 0 ? '+' : ''}{totalGainPct}%)
                    </span>
                  )}
                </>
              )}
              {lastUpdated && (
                <span className="text-gray-600 ml-2">
                  · Updated {lastUpdated}
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchPrices(portfolio.map(s => s.ticker))}
              disabled={pricesLoading || portfolio.length === 0}
              className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-400 transition disabled:opacity-50"
              title="Refresh prices"
            >
              <RefreshCw
                size={16}
                className={pricesLoading ? 'animate-spin' : ''}
              />
            </button>
            <button
              onClick={() => setShowAdd(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white text-sm transition"
            >
              <Plus size={16} /> Add Position
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        {!loading && portfolio.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {[
              { label: 'Total Holding', value: `$${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, sub: 'shares × current price', color: 'text-white' },
              { label: 'Cost Basis', value: `$${totalCost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, sub: 'shares × avg cost', color: 'text-gray-300' },
              { label: 'Total P&L', value: `${totalGainDollar >= 0 ? '+' : ''}$${totalGainDollar.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, sub: 'market − cost', color: totalGainDollar >= 0 ? 'text-green-400' : 'text-red-400' },
              { label: 'Return', value: totalGainPct ? `${parseFloat(totalGainPct) >= 0 ? '+' : ''}${totalGainPct}%` : '—', sub: 'portfolio gain/loss', color: totalGainPct && parseFloat(totalGainPct) >= 0 ? 'text-green-400' : 'text-red-400' },
            ].map(stat => (
              <div key={stat.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <p className="text-xs text-gray-500 mb-1">{stat.label}</p>
                <p className={`text-xl font-bold ${stat.color}`}>{stat.value}</p>
                <p className="text-xs text-gray-600 mt-1">{stat.sub}</p>
              </div>
            ))}
          </div>
        )}

        {!loading && portfolio.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden mb-6">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-500 uppercase tracking-wider">
                    <th className="text-left p-3">Ticker</th>
                    <th className="text-right p-3">Shares</th>
                    <th className="text-right p-3">Avg Cost</th>
                    <th className="text-right p-3">Price</th>
                    <th className="text-right p-3">Total Holding</th>
                    <th className="text-right p-3">Cost Basis</th>
                    <th className="text-right p-3">P&L</th>
                    <th className="text-right p-3">Return</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.map(stock => {
                    const price = prices[stock.ticker]
                    const currentPrice = parseFloat(price?.price || '0')
                    const marketValue = stock.shares * currentPrice
                    const costBasis = stock.shares * stock.purchase_price
                    const pnl = marketValue - costBasis
                    const pnlPct = costBasis > 0 ? (pnl / costBasis) * 100 : 0
                    const up = pnl >= 0
                    if (stock.shares <= 0) return null
                    return (
                      <tr key={stock.id} className="border-b border-gray-800/50">
                        <td className="p-3 font-bold text-white">{stock.ticker}</td>
                        <td className="p-3 text-right text-gray-300">{stock.shares}</td>
                        <td className="p-3 text-right text-gray-400">${stock.purchase_price.toFixed(2)}</td>
                        <td className="p-3 text-right text-gray-300">{price ? `$${currentPrice.toFixed(2)}` : '—'}</td>
                        <td className="p-3 text-right text-white font-medium">{price ? `$${marketValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}</td>
                        <td className="p-3 text-right text-gray-400">${costBasis.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td className={`p-3 text-right font-medium ${up ? 'text-green-400' : 'text-red-400'}`}>{price ? `${up ? '+' : ''}$${pnl.toFixed(2)}` : '—'}</td>
                        <td className={`p-3 text-right font-medium ${up ? 'text-green-400' : 'text-red-400'}`}>{price && costBasis > 0 ? `${up ? '+' : ''}${pnlPct.toFixed(1)}%` : '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
                <tfoot>
                  <tr className="bg-gray-950 border-t border-blue-800/40">
                    <td colSpan={4} className="p-3 font-semibold text-blue-300">Portfolio Total</td>
                    <td className="p-3 text-right font-bold text-white">${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="p-3 text-right font-bold text-gray-300">${totalCost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className={`p-3 text-right font-bold ${totalGainDollar >= 0 ? 'text-green-400' : 'text-red-400'}`}>{totalGainDollar >= 0 ? '+' : ''}${totalGainDollar.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className={`p-3 text-right font-bold ${totalGainPct && parseFloat(totalGainPct) >= 0 ? 'text-green-400' : 'text-red-400'}`}>{totalGainPct ? `${parseFloat(totalGainPct) >= 0 ? '+' : ''}${totalGainPct}%` : '—'}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={24} className="animate-spin text-blue-400" />
            <span className="ml-3 text-gray-400">Loading portfolio...</span>
          </div>
        ) : portfolio.length === 0 ? (
          <div className="text-center py-20">
            <TrendingUp size={32} className="mx-auto mb-3 text-gray-600" />
            <p className="text-gray-500 mb-4">No positions yet</p>
            <button
              onClick={() => setShowAdd(true)}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg text-white text-sm transition"
            >
              Add your first position
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {portfolio.map((stock) => {
              const price     = prices[stock.ticker]
              const isUp      = price ? parseFloat(price.changePct) >= 0 : null
              const riskLevel = price
                ? Math.abs(parseFloat(price.changePct)) > 3 ? 'high'
                : Math.abs(parseFloat(price.changePct)) > 1 ? 'medium'
                : 'low'
                : 'unknown'

              const currentValue  = stock.shares * parseFloat(price?.price || '0')
              const costBasis     = stock.shares * stock.purchase_price
              const gainLossPct   = costBasis > 0
                ? (((currentValue - costBasis) / costBasis) * 100).toFixed(2)
                : null
              const gainLossDollar = costBasis > 0
                ? (currentValue - costBasis).toFixed(2)
                : null
              const currentPrice  = parseFloat(price?.price || '0')
              const totalValue    = stock.shares * currentPrice
              const ytdGainPct    = costBasis > 0 ? (((currentValue - costBasis) / costBasis) * 100) : 0

              return (
                <div
                  key={stock.id}
                  className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-600 transition"
                >
                  {/* Top row */}
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="font-bold text-white text-lg">
                          {stock.ticker}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-700 text-gray-300">
                          {assetClassEmoji[stock.asset_class] || '📈'} {stock.asset_class}
                        </span>
                        {stock.sector && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400">
                            {stock.sector}
                          </span>
                        )}
                        {price && (
                          <span className={`text-xs px-2 py-0.5 rounded-full ${riskColors[riskLevel]}`}>
                            {riskLevel} volatility
                          </span>
                        )}
                      </div>
                      <div className="text-gray-400 text-sm">{stock.company}</div>
                      <div className="text-gray-600 text-xs mt-0.5">
                        {stock.shares > 0 && `${stock.shares} shares`}
                        {stock.purchase_price > 0 && ` · Avg $${stock.purchase_price.toFixed(2)}`}
                        {stock.shares > 0 && stock.purchase_price > 0 && (
                          <span className="text-gray-500"> · Cost basis ${(stock.shares * stock.purchase_price).toLocaleString()}</span>
                        )}
                      </div>
                    </div>

                    {/* Price */}
                    <div className="text-right mr-4">
                      {pricesLoading && !price ? (
                        <Loader2 size={16} className="animate-spin text-gray-600 ml-auto" />
                      ) : price ? (
                        <>
                          <div className="text-white font-bold text-lg">
                            ${price.price}
                          </div>
                          <div className={`flex items-center gap-1 text-sm justify-end ${
                            isUp ? 'text-green-400' : 'text-red-400'
                          }`}>
                            {isUp ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                            {isUp ? '+' : ''}{price.changePct}%
                          </div>
                          <div className="text-gray-600 text-xs">
                            {isUp ? '+' : ''}${price.change} today
                          </div>
                        </>
                      ) : (
                        <div className="text-gray-600 text-xs">Unavailable</div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/research?q=Analyze ${stock.ticker} ${stock.company}`}
                        className="px-3 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 rounded-lg text-xs transition"
                      >
                        Research →
                      </Link>
                      <button
                        onClick={() => openEdit(stock)}
                        className="px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-xs transition"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleRemove(stock.ticker)}
                        className="p-2 hover:bg-red-500/10 rounded-lg transition"
                      >
                        <X size={16} className="text-gray-500 hover:text-red-400" />
                      </button>
                    </div>
                  </div>

                  {/* Price details row */}
                  {price && (
                    <div className="mt-3 pt-3 border-t border-gray-800 grid grid-cols-3 gap-4 text-xs">
                      <div>
                        <span className="text-gray-600">Day High</span>
                        <div className="text-gray-300">${price.high}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">Day Low</span>
                        <div className="text-gray-300">${price.low}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">Volume</span>
                        <div className="text-gray-300">
                          {price.volume
                            ? (price.volume / 1e6).toFixed(1) + 'M'
                            : 'N/A'
                          }
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Position P&L row */}
                  {stock.shares > 0 && price && (
                    <div className="mt-2 pt-2 border-t border-gray-800 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                      <div>
                        <span className="text-gray-600">Market Value</span>
                        <div className="text-white font-medium">
                          ${currentValue.toLocaleString('en-US', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                          })}
                        </div>
                        <div className="text-gray-600">{stock.shares} × ${currentPrice.toFixed(2)}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">Cost Basis</span>
                        <div className="text-gray-300">
                          ${costBasis.toLocaleString('en-US', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                          })}
                        </div>
                        <div className="text-gray-600">{stock.shares} × ${stock.purchase_price.toFixed(2)}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">P&L</span>
                        <div className={
                          parseFloat(gainLossPct || '0') >= 0
                            ? 'text-green-400 font-medium'
                            : 'text-red-400 font-medium'
                        }>
                          {parseFloat(gainLossPct || '0') >= 0 ? '+' : ''}${gainLossDollar}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-600">Return</span>
                        <div className={
                          parseFloat(gainLossPct || '0') >= 0
                            ? 'text-green-400 font-medium'
                            : 'text-red-400 font-medium'
                        }>
                          {parseFloat(gainLossPct || '0') >= 0 ? '+' : ''}{gainLossPct}%
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Alex commentary */}
<div className="mt-3 p-3 bg-blue-500/5 border border-blue-500/10 rounded-lg">
  <div className="text-xs text-blue-400 font-medium mb-2">
    🤖 Alex Commentary
  </div>
  <div className="space-y-1">
    {price ? (
      <>
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500">Today</span>
          <span className={isUp ? 'text-green-400' : 'text-red-400'}>
            {isUp ? '▲' : '▼'} {Math.abs(parseFloat(price.changePct)).toFixed(2)}%
            {isUp ? ' — momentum positive' : ' — under pressure'}
          </span>
        </div>
        {stock.shares > 0 && stock.purchase_price > 0 && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-500">Your position</span>
            <span className={
              parseFloat(price.price) >= stock.purchase_price
                ? 'text-green-400'
                : 'text-red-400'
            }>
              {parseFloat(price.price) >= stock.purchase_price ? '▲' : '▼'}
              {(((parseFloat(price.price) - stock.purchase_price) /
                stock.purchase_price) * 100).toFixed(1)}% from cost
            </span>
          </div>
        )}
        <div className="text-xs text-gray-500 mt-1 pt-1 border-t border-gray-800">
          {isUp
            ? `${stock.ticker} showing strength — consider researching catalysts`
            : `${stock.ticker} declining — research for risk assessment`
          }
        </div>
      </>
    ) : (
      <div className="text-xs text-gray-500">
        Add position details for personalized commentary
      </div>
    )}
  </div>
</div>
                </div>
              )
            })}
          </div>
        )}

        {/* Add Position Modal */}
        {showAdd && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md mx-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-white">Add Position</h3>
                <button onClick={() => setShowAdd(false)}>
                  <X size={18} className="text-gray-400 hover:text-white" />
                </button>
              </div>
              <div className="space-y-3">
                <input
                  value={ticker}
                  onChange={e => setTicker(e.target.value.toUpperCase())}
                  placeholder="Ticker (e.g. NVDA)"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
                />
                <div className="grid grid-cols-2 gap-3">
                  <input
                    value={shares}
                    onChange={e => setShares(e.target.value)}
                    placeholder="Shares (e.g. 10)"
                    type="number"
                    min="0"
                    step="0.0001"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  />
                  <input
                    value={purchasePrice}
                    onChange={e => setPurchasePrice(e.target.value)}
                    placeholder="Avg cost ($)"
                    type="number"
                    min="0"
                    step="0.01"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <select
                  value={assetClass}
                  onChange={e => setAssetClass(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
                >
                  <option value="stocks">📈 Stocks</option>
                  <option value="etf">📊 ETF</option>
                  <option value="crypto">₿ Crypto</option>
                  <option value="bonds">🏦 Bonds</option>
                  <option value="real_estate">🏠 Real Estate</option>
                  <option value="commodities">🥇 Commodities</option>
                  <option value="cash">💵 Cash</option>
                </select>
                <button
                  onClick={handleAddStock}
                  disabled={adding || !ticker}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-white text-sm font-medium transition flex items-center justify-center gap-2"
                >
                  {adding
                    ? <><Loader2 size={14} className="animate-spin" /> Adding...</>
                    : 'Add Position'
                  }
                </button>
              </div>
            </div>
          </div>
        )}

{showEdit && editStock && (
  <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md mx-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white">
          Update {editStock.ticker} Position
        </h3>
        <button onClick={() => setShowEdit(false)}>
          <X size={18} className="text-gray-400 hover:text-white" />
        </button>
      </div>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">
              Shares held
            </label>
            <input
              value={editShares}
              onChange={e => setEditShares(e.target.value)}
              type="number"
              min="0"
              step="0.0001"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">
              Avg cost ($)
            </label>
            <input
              value={editPrice}
              onChange={e => setEditPrice(e.target.value)}
              type="number"
              min="0"
              step="0.01"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        {/* Preview */}
        {prices[editStock.ticker] && (
          <div className="p-3 bg-gray-800 rounded-lg text-xs space-y-1">
            <div className="flex justify-between text-gray-400">
              <span>Current Price</span>
              <span className="text-white">
                ${prices[editStock.ticker].price}
              </span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Position Value</span>
              <span className="text-white">
                ${(parseFloat(editShares || '0') *
                   parseFloat(prices[editStock.ticker].price)).toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Cost Basis</span>
              <span className="text-white">
                ${(parseFloat(editShares || '0') *
                   parseFloat(editPrice || '0')).toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Gain/Loss</span>
              <span className={
                parseFloat(prices[editStock.ticker].price) >= parseFloat(editPrice || '0')
                  ? 'text-green-400'
                  : 'text-red-400'
              }>
                {(((parseFloat(prices[editStock.ticker].price) -
                    parseFloat(editPrice || '0')) /
                   parseFloat(editPrice || '1')) * 100).toFixed(2)}%
              </span>
            </div>
          </div>
        )}

        <button
          onClick={handleUpdateStock}
          disabled={updating}
          className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-white text-sm font-medium transition flex items-center justify-center gap-2"
        >
          {updating
            ? <><Loader2 size={14} className="animate-spin" /> Updating...</>
            : 'Update Position'
          }
        </button>
      </div>
    </div>
  </div>
)}
      </main>
    </div>
  )
}