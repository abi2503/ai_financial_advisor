'use client'
import { useState, useEffect } from 'react'
import Navbar from '@/components/Navbar'
import { Search, Clock, Brain, Loader2 } from 'lucide-react'
import axios from 'axios'

interface HistoryItem {
  id:         string
  topic:      string
  result:     string
  created_at: string
}

const categoryColors: Record<string, string> = {
  stocks:     'bg-blue-500/10 text-blue-400',
  macro:      'bg-purple-500/10 text-purple-400',
  technology: 'bg-green-500/10 text-green-400',
  crypto:     'bg-yellow-500/10 text-yellow-400',
  other:      'bg-gray-500/10 text-gray-400',
}

function guessCategory(topic: string): string {
  const t = topic.toLowerCase()
  if (t.includes('crypto') || t.includes('btc') || t.includes('eth'))    return 'crypto'
  if (t.includes('fed') || t.includes('rate') || t.includes('macro'))    return 'macro'
  if (t.includes('ai') || t.includes('tech') || t.includes('nvidia'))    return 'technology'
  if (t.includes('stock') || t.includes('nyse') || t.includes('nasdaq')) return 'stocks'
  return 'other'
}

export default function HistoryPage() {
  const [history,  setHistory]  = useState<HistoryItem[]>([])
  const [loading,  setLoading]  = useState(true)
  const [search,   setSearch]   = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [error,    setError]    = useState('')

  useEffect(() => {
    async function fetchHistory() {
      try {
        const res = await axios.get('/api/history')
        setHistory(res.data.history || [])
      } catch (err: any) {
        console.error('History error:', err)
        setError('Failed to load history')
      } finally {
        setLoading(false)
      }
    }
    fetchHistory()
  }, [])

  const filtered = history.filter(h =>
    h.topic.toLowerCase().includes(search.toLowerCase()) ||
    h.result.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar />
      <main className="max-w-4xl mx-auto px-6 py-8">

        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white mb-4">
            Research History
          </h1>
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search past research..."
              className="w-full bg-gray-900 border border-gray-700 rounded-xl pl-10 pr-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
            />
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={24} className="animate-spin text-blue-400" />
            <span className="ml-3 text-gray-400">Loading history...</span>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((item) => {
              const category = guessCategory(item.topic)
              const isOpen   = expanded === item.id
              return (
                <div
                  key={item.id}
                  onClick={() => setExpanded(isOpen ? null : item.id)}
                  className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-600 transition cursor-pointer"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${categoryColors[category]}`}>
                          {category}
                        </span>
                        <div className="flex items-center gap-1 text-gray-500 text-xs">
                          <Clock size={11} />
                          {new Date(item.created_at).toLocaleString()}
                        </div>
                      </div>
                      <div className="font-medium text-white text-sm mb-2">
                        "{item.topic}"
                      </div>
                      <div className={`text-gray-400 text-sm leading-relaxed whitespace-pre-wrap ${isOpen ? '' : 'line-clamp-2'}`}>
                        {item.result}
                      </div>
                      {!isOpen && item.result?.length > 150 && (
                        <div className="text-blue-400 text-xs mt-1">
                          Click to expand...
                        </div>
                      )}
                    </div>
                    <Brain size={16} className="text-blue-400 flex-shrink-0 mt-1" />
                  </div>
                </div>
              )
            })}

            {filtered.length === 0 && !loading && (
              <div className="text-center py-12 text-gray-500">
                <Brain size={32} className="mx-auto mb-3 opacity-50" />
                {search
                  ? <p>No research found matching "{search}"</p>
                  : <p>No research history yet. Ask Alex something!</p>
                }
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}