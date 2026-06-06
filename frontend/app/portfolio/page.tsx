'use client'
import { useState } from 'react'
import Navbar from '@/components/Navbar'
import { Plus, TrendingUp, TrendingDown, X } from 'lucide-react'

const samplePortfolio = [
  { ticker: 'NVDA', company: 'NVIDIA Corporation', shares: 20, price: 847.23, change: 2.3,  gain: 30.2, insight: '3 bullish signals. Blackwell shipments ahead of schedule.', risk: 'low' },
  { ticker: 'AAPL', company: 'Apple Inc.',          shares: 30, price: 189.45, change: -0.8, gain: 8.3,  insight: 'Supply chain concern flagged in recent analyst notes.',     risk: 'medium' },
  { ticker: 'TSLA', company: 'Tesla Inc.',           shares: 15, price: 245.67, change: 1.1,  gain: 17.4, insight: 'Q2 deliveries beat estimates by 3%. No risk signals.',      risk: 'low' },
]

const riskColors: Record<string, string> = {
  low:    'text-green-400 bg-green-400/10',
  medium: 'text-yellow-400 bg-yellow-400/10',
  high:   'text-red-400 bg-red-400/10',
}

export default function PortfolioPage() {
  const [showAdd, setShowAdd] = useState(false)
  const [ticker,  setTicker]  = useState('')
  const [company, setCompany] = useState('')
  const totalValue = samplePortfolio.reduce((sum, s) => sum + s.shares * s.price, 0)

  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar />
      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">My Portfolio</h1>
            <p className="text-gray-400 text-sm mt-1">Total Value: ${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}</p>
          </div>
          <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white text-sm transition">
            <Plus size={16} /> Add Stock
          </button>
        </div>

        <div className="space-y-4">
          {samplePortfolio.map((stock) => (
            <div key={stock.ticker} className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-600 transition">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-bold text-white text-lg">{stock.ticker}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${riskColors[stock.risk]}`}>{stock.risk} risk</span>
                  </div>
                  <div className="text-gray-400 text-sm">{stock.company}</div>
                </div>
                <div className="text-right">
                  <div className="text-white font-semibold">${stock.price.toFixed(2)}</div>
                  <div className={`flex items-center gap-1 text-sm justify-end ${stock.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {stock.change >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                    {stock.change >= 0 ? '+' : ''}{stock.change}%
                  </div>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-gray-800 text-xs text-gray-500">
                {stock.shares} shares • +{stock.gain}% total gain • ${(stock.shares * stock.price).toLocaleString()}
              </div>
              <div className="mt-3 p-3 bg-blue-500/5 border border-blue-500/10 rounded-lg">
                <div className="text-xs text-blue-400 font-medium mb-1">🤖 Alex</div>
                <div className="text-xs text-gray-300">{stock.insight}</div>
              </div>
            </div>
          ))}
        </div>

        {showAdd && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md mx-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-white">Add Stock to Portfolio</h3>
          <button onClick={() => setShowAdd(false)}><X size={18} className="text-gray-400 hover:text-white" /></button>
              </div>
              <div className="space-y-3">
                <input value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())} placeholder="Ticker (e.g. NVDA)" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500" />
                <input value={company} onChange={e => setCompany(e.target.value)} placeholder="Company name" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500" />
                <button onClick={() => setShowAdd(false)} className="w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-lg text-white text-sm font-medium transition">Add to Portfolio</button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
