'use client'
import { useState, useEffect } from 'react'
import Navbar from '@/components/Navbar'
import { Plus, TrendingUp, X, Loader2, Brain } from 'lucide-react'
import axios from 'axios'

interface Stock {
  id:       string
  ticker:   string
  company:  string
  added_at: string
}

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState<Stock[]>([])
  const [loading,   setLoading]   = useState(true)
  const [showAdd,   setShowAdd]   = useState(false)
  const [ticker,    setTicker]    = useState('')
  const [company,   setCompany]   = useState('')
  const [adding,    setAdding]    = useState(false)
  const [error,     setError]     = useState('')

  useEffect(() => {
    async function init() {
      try {
        await axios.post('/api/users/sync')
        console.log('User synced to Aurora')
      } catch (err) {
        console.error('Sync error:', err)
      }
      fetchPortfolio()
    }
    init()
  }, [])

  async function fetchPortfolio() {
    try {
      setLoading(true)
      const res = await axios.get('/api/portfolio')
      setPortfolio(res.data.portfolio || [])
    } catch (err: any) {
      console.error('Portfolio fetch error:', err)
      setError('Failed to load portfolio')
    } finally {
      setLoading(false)
    }
  }

  async function handleAddStock() {
    if (!ticker || !company) return
    setAdding(true)
    try {
      await axios.post('/api/portfolio', { ticker, company })
      await fetchPortfolio()
      setTicker('')
      setCompany('')
      setShowAdd(false)
    } catch (err: any) {
      console.error('Add stock error:', err)
      setError('Failed to add stock')
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

  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar />
      <main className="max-w-4xl mx-auto px-6 py-8">

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">My Portfolio</h1>
            <p className="text-gray-400 text-sm mt-1">
              {loading ? 'Loading...' : `${portfolio.length} stocks tracked`}
            </p>
          </div>
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white text-sm transition"
          >
            <Plus size={16} /> Add Stock
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            {error}
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
            <p className="text-gray-500 mb-4">No stocks tracked yet</p>
            <button
              onClick={() => setShowAdd(true)}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg text-white text-sm transition"
            >
              Add your first stock
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {portfolio.map((stock) => (
              <div
                key={stock.id}
                className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-600 transition"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <span className="font-bold text-white text-lg">
                        {stock.ticker}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400">
                        tracked
                      </span>
                    </div>
                    <div className="text-gray-400 text-sm">{stock.company}</div>
                    <div className="text-gray-600 text-xs mt-1">
                      Added {new Date(stock.added_at).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => window.location.href = `/research?q=Analyze ${stock.ticker} ${stock.company}`}
                      className="px-3 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 rounded-lg text-xs transition"
                    >
                      Research →
                    </button>
                    <button
                      onClick={() => handleRemove(stock.ticker)}
                      className="p-2 hover:bg-red-500/10 rounded-lg transition"
                    >
                      <X size={16} className="text-gray-500 hover:text-red-400" />
                    </button>
                  </div>
                </div>

                <div className="mt-3 p-3 bg-blue-500/5 border border-blue-500/10 rounded-lg">
                  <div className="text-xs text-blue-400 font-medium mb-1">
                    🤖 Alex
                  </div>
                  <div className="text-xs text-gray-400">
                    Click Research → to get Alex's latest analysis on {stock.ticker}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {showAdd && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md mx-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-white">Add Stock</h3>
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
                <input
                  value={company}
                  onChange={e => setCompany(e.target.value)}
                  placeholder="Company name (e.g. NVIDIA Corporation)"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
                />
                <button
                  onClick={handleAddStock}
                  disabled={adding || !ticker || !company}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-white text-sm font-medium transition flex items-center justify-center gap-2"
                >
                  {adding
                    ? <><Loader2 size={14} className="animate-spin" /> Adding...</>
                    : 'Add to Portfolio'
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