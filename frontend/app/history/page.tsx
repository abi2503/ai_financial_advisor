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

interface SearchResult {
  id:        string
  topic:     string
  content:   string
  timestamp: string
  score:     number
}

export default function HistoryPage() {
  const [history,       setHistory]       = useState<HistoryItem[]>([])
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [loading,       setLoading]       = useState(true)
  const [searching,     setSearching]     = useState(false)
  const [search,        setSearch]        = useState('')
  const [expanded,      setExpanded]      = useState<string | null>(null)
  const [searchMode,    setSearchMode]    = useState(false)

  useEffect(() => { fetchHistory() }, [])

  async function fetchHistory() {
    try {
      const res = await axios.get('/api/history')
      setHistory(res.data.history || [])
    } catch (err) {
      console.error('History error:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!search.trim()) {
      setSearchMode(false)
      return
    }

    setSearching(true)
    setSearchMode(true)

    try {
      // Use semantic search via S3 Vectors
      const res = await axios.post('/api/search', { query: search })
      setSearchResults(res.data.results || [])
    } catch (err) {
      console.error('Search error:', err)
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }

  function clearSearch() {
    setSearch('')
    setSearchMode(false)
    setSearchResults([])
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
    if (t.includes('crypto') || t.includes('btc'))  return 'crypto'
    if (t.includes('fed') || t.includes('macro'))   return 'macro'
    if (t.includes('ai') || t.includes('nvidia'))   return 'technology'
    if (t.includes('stock') || t.includes('nasdaq'))return 'stocks'
    return 'other'
  }

  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar />
      <main className="max-w-4xl mx-auto px-6 py-8">

        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white mb-4">
            Research History
          </h1>

          {/* Search bar */}
          <form onSubmit={handleSearch} className="relative flex gap-2">
            <div className="relative flex-1">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
              />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Semantic search — find research by meaning..."
                className="w-full bg-gray-900 border border-gray-700 rounded-xl pl-10 pr-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
              />
            </div>
            <button
              type="submit"
              disabled={searching}
              className="px-4 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl text-white text-sm transition disabled:opacity-50"
            >
              {searching ? <Loader2 size={16} className="animate-spin" /> : 'Search'}
            </button>
            {searchMode && (
              <button
                type="button"
                onClick={clearSearch}
                className="px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-xl text-gray-400 text-sm transition"
              >
                Clear
              </button>
            )}
          </form>

          {searchMode && (
            <div className="mt-2 text-xs text-blue-400">
              🔍 Semantic search — finding research by meaning, not just keywords
            </div>
          )}
        </div>

        {/* Semantic Search Results */}
        {searchMode && (
          <div className="space-y-3 mb-8">
            <h2 className="text-sm font-medium text-gray-400">
              {searchResults.length} semantic matches for "{search}"
            </h2>
            {searchResults.length === 0 && !searching && (
              <div className="text-center py-8 text-gray-500 text-sm">
                No semantic matches found — try a different query
              </div>
            )}
            {searchResults.map((result) => (
              <div
                key={result.id}
                className="bg-gray-900 border border-blue-500/20 rounded-xl p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-blue-400 text-xs font-medium">
                    {result.topic}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">
                      Score: {(result.score * 100).toFixed(0)}%
                    </span>
                    <span className="text-xs text-gray-600">
                      {new Date(result.timestamp).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <p className="text-gray-300 text-sm line-clamp-3">
                  {result.content}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Regular History */}
        {!searchMode && (
          <>
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 size={24} className="animate-spin text-blue-400" />
                <span className="ml-3 text-gray-400">Loading history...</span>
              </div>
            ) : (
              <div className="space-y-3">
                {history.map((item) => {
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

                {history.length === 0 && (
                  <div className="text-center py-12 text-gray-500">
                    <Brain size={32} className="mx-auto mb-3 opacity-50" />
                    <p>No research history yet. Ask Alex something!</p>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}