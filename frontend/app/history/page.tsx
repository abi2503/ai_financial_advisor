'use client'
import { useState } from 'react'
import Navbar from '@/components/Navbar'
import { Search, Clock, Brain } from 'lucide-react'

const sampleHistory = [
  { id: '1', topic: 'Should I add more NVDA before earnings?',   result: 'HOLD current position. Wait for earnings result before adding. Set stop loss at $780.', created_at: '2026-06-06T10:23:00Z', category: 'stocks' },
  { id: '2', topic: 'Federal Reserve interest rate updates',      result: 'Fed holds rates steady. Neutral impact on tech stocks short-term.',                        created_at: '2026-06-06T08:00:00Z', category: 'macro' },
  { id: '3', topic: 'AI Technology sector news',                  result: 'AI infrastructure spending up 67% YoY. NVDA, AMD, TSMC primary beneficiaries.',            created_at: '2026-06-06T08:00:00Z', category: 'technology' },
  { id: '4', topic: 'Cryptocurrency market performance',          result: 'BTC consolidating near $68k. ETH showing relative strength.',                              created_at: '2026-06-06T08:00:00Z', category: 'crypto' },
]

const categoryColors: Record<string, string> = {
  stocks:     'bg-blue-500/10 text-blue-400',
  macro:      'bg-purple-500/10 text-purple-400',
  technology: 'bg-green-500/10 text-green-400',
  crypto:     'bg-yellow-500/10 text-yellow-400',
}

export default function HistoryPage() {
  const [search, setSearch] = useState('')
  const filtered = sampleHistory.filter(h =>
    h.topic.toLowerCase().includes(search.toLowerCase()) ||
    h.result.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar />
      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white mb-4">Research History</h1>
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search past research..." className="w-full bg-gray-900 border border-gray-700 rounded-xl pl-10 pr-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500 transition" />
          </div>
        </div>

        <div className="space-y-3">
          {filtered.map((item) => (
            <div key={item.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-600 transition">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${categoryColors[item.category] || 'bg-gray-700 text-gray-400'}`}>{item.category}</span>
                    <div className="flex items-center gap-1 text-gray-500 text-xs">
                      <Clock size={11} />
                      {new Date(item.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="font-medium text-white text-sm mb-2">"{item.topic}"</div>
                  <div className="text-gray-400 text-sm leading-relaxed line-clamp-2">{item.result}</div>
                </div>
                <Brain size={16} className="text-blue-400 flex-shrink-0 mt-1" />
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <Brain size={32} className="mx-auto mb-3 opacity-50" />
              <p>No research found matching "{search}"</p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
