'use client'
import { useState, useRef, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import Navbar from '@/components/Navbar'
import { Brain, Send, Loader2, User, Zap, Search } from 'lucide-react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Message {
  role:    'user' | 'alex'
  content: string
  time:    string
  mode?:   'fast' | 'deep'
}

export default function ResearchPage() {
  const searchParams = useSearchParams()
  const initialQ     = searchParams.get('q') || ''

  const [messages, setMessages] = useState<Message[]>([{
    role:    'alex',
    content: 'Hello! I\'m Alex, your AI financial research assistant.\n\n⚡ **Fast Mode** — Price, news, and analysis in 45 seconds.\n\n🔍 **Deep Mode** — SEC filings, insider trading, earnings transcripts in 3-4 minutes.\n\nAsk me anything about stocks, markets, or investment topics.',
    time:    ''
  }])

  const [input,    setInput]    = useState(initialQ)
  const [loading,  setLoading]  = useState(false)
  const [deepMode, setDeepMode] = useState(false)
  const [mounted,  setMounted]  = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (initialQ) handleSubmit(null, initialQ)
  }, [])

  function getTime() {
    return mounted ? new Date().toLocaleTimeString() : ''
  }

  async function handleSubmit(
    e: React.FormEvent | null,
    overrideInput?: string
  ) {
    if (e) e.preventDefault()
    const question = overrideInput || input
    if (!question.trim() || loading) return

    const mode = deepMode ? 'deep' : 'fast'

    setMessages(prev => [...prev, {
      role:    'user',
      content: question,
      time:    getTime(),
      mode
    }])
    setInput('')
    setLoading(true)

    const loadingMsg = deepMode
      ? 'Alex is reading SEC filings and official documents... (3-4 minutes)'
      : 'Alex is researching... (30-60 seconds)'

    setMessages(prev => [...prev, {
      role:    'alex',
      content: `⏳ ${loadingMsg}`,
      time:    getTime(),
      mode
    }])

    try {
      const endpoint = deepMode ? '/api/research/deep' : '/api/research'
      const response = await axios.post(
        endpoint,
        { topic: question },
        { timeout: 300000 }
      )

      setMessages(prev => [
        ...prev.slice(0, -1),
        {
          role:    'alex',
          content: response.data.result || 'Research complete.',
          time:    getTime(),
          mode
        }
      ])

    } catch (error: any) {
      const errMsg = deepMode
        ? 'Deep research encountered an error. SEC filings may be temporarily unavailable.'
        : 'Research encountered an error. Please ensure the researcher service is running.'

      setMessages(prev => [
        ...prev.slice(0, -1),
        {
          role:    'alex',
          content: errMsg,
          time:    getTime(),
          mode
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  const markdownComponents = {
    h1: ({children}: any) => (
      <h1 className="text-lg font-bold text-white mb-2 mt-1">{children}</h1>
    ),
    h2: ({children}: any) => (
      <h2 className="text-base font-bold text-white mb-2 mt-3 pb-1 border-b border-gray-700">{children}</h2>
    ),
    h3: ({children}: any) => (
      <h3 className="text-sm font-semibold text-blue-400 mb-1 mt-2">{children}</h3>
    ),
    p: ({children}: any) => (
      <p className="mb-2 text-gray-200 leading-relaxed">{children}</p>
    ),
    ul: ({children}: any) => (
      <ul className="mb-3 space-y-1.5">{children}</ul>
    ),
    ol: ({children}: any) => (
      <ol className="mb-3 space-y-1.5 list-decimal list-inside">{children}</ol>
    ),
    li: ({children}: any) => (
      <li className="flex gap-2 text-gray-300 text-sm">
        <span className="text-blue-400 mt-0.5 flex-shrink-0">•</span>
        <span>{children}</span>
      </li>
    ),
    strong: ({children}: any) => (
      <strong className="text-white font-semibold">{children}</strong>
    ),
    em: ({children}: any) => (
      <em className="text-gray-300 italic">{children}</em>
    ),
    hr: () => (
      <hr className="border-gray-700 my-4" />
    ),
    blockquote: ({children}: any) => (
      <blockquote className="border-l-2 border-blue-400 pl-3 text-gray-400 italic my-3 bg-blue-500/5 py-2 rounded-r">
        {children}
      </blockquote>
    ),
    code: ({children}: any) => (
      <code className="bg-gray-800 text-blue-300 px-1.5 py-0.5 rounded text-xs font-mono">
        {children}
      </code>
    ),
    table: ({children}: any) => (
      <div className="overflow-x-auto my-3 rounded-lg border border-gray-700">
        <table className="w-full text-sm border-collapse">
          {children}
        </table>
      </div>
    ),
    thead: ({children}: any) => (
      <thead className="bg-gray-800/80">
        {children}
      </thead>
    ),
    tbody: ({children}: any) => (
      <tbody className="divide-y divide-gray-800">
        {children}
      </tbody>
    ),
    tr: ({children}: any) => (
      <tr className="hover:bg-gray-800/40 transition">
        {children}
      </tr>
    ),
    th: ({children}: any) => (
      <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
        {children}
      </th>
    ),
    td: ({children}: any) => (
      <td className="px-4 py-2.5 text-gray-200">
        {children}
      </td>
    ),
  }

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-6 flex flex-col">

        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          <Brain className="text-blue-400" size={20} />
          <h1 className="font-semibold text-white">Research Chat</h1>
          <span className="ml-auto text-xs text-gray-500">
            Powered by AWS Bedrock Nova Pro
          </span>
        </div>

        {/* Mode Toggle */}
        <div className="flex items-center gap-3 mb-4 p-3
                        bg-gray-900 border border-gray-800 rounded-xl">
          <span className="text-xs text-gray-500 font-medium">
            Mode:
          </span>

          <button
            onClick={() => setDeepMode(false)}
            className={`flex items-center gap-1.5 px-3 py-1.5
                        rounded-lg text-xs font-medium transition ${
              !deepMode
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            <Zap size={12} />
            Fast
          </button>

          <button
            onClick={() => setDeepMode(true)}
            className={`flex items-center gap-1.5 px-3 py-1.5
                        rounded-lg text-xs font-medium transition ${
              deepMode
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/20'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            <Search size={12} />
            Deep
          </button>

          <span className="text-xs text-gray-600 ml-1">
            {deepMode
              ? '🔍 SEC filings + insider trading (3-4 min)'
              : '⚡ Price + news + analysis (45 sec)'
            }
          </span>
        </div>

        {/* Suggested Questions */}
        {messages.length === 1 && (
          <div className="mb-4 grid grid-cols-2 gap-2">
            {(deepMode ? [
              'Analyze NVDA SEC 10-K for hidden risks',
              'Show AAPL insider trading activity',
              'Find MSFT 8-K material events',
              'TSLA insider trades last 90 days',
            ] : [
              'Should I buy NVDA before earnings?',
              'What is happening with AI stocks today?',
              'Compare NVDA vs AMD for next quarter',
              'How is Fed rate affecting tech stocks?',
            ]).map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => handleSubmit(null, suggestion)}
                className="text-left p-3 bg-gray-900 hover:bg-gray-800
                           border border-gray-800 hover:border-gray-600
                           rounded-xl text-gray-400 text-xs transition"
              >
                "{suggestion}"
              </button>
            ))}
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 space-y-4 overflow-y-auto mb-4 min-h-0">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 ${
                msg.role === 'user' ? 'justify-end' : ''
              }`}
            >
              {msg.role === 'alex' && (
                <div className={`w-8 h-8 rounded-full flex items-center
                                 justify-center flex-shrink-0 mt-1 ${
                  msg.mode === 'deep'
                    ? 'bg-purple-600'
                    : 'bg-blue-600'
                }`}>
                  <Brain size={16} className="text-white" />
                </div>
              )}

              <div className={`max-w-[85%] p-4 ${
                msg.role === 'user'
                  ? 'bg-blue-600 rounded-2xl rounded-tr-sm'
                  : 'bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-sm'
              }`}>

                {/* Mode badge */}
                {msg.role === 'alex' && msg.mode && i > 0 && (
                  <div className="mb-3">
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                      msg.mode === 'deep'
                        ? 'bg-purple-500/20 text-purple-400'
                        : 'bg-blue-500/20 text-blue-400'
                    }`}>
                      {msg.mode === 'deep' ? '🔍 Deep Research' : '⚡ Fast Research'}
                    </span>
                  </div>
                )}

                <div className={`text-sm leading-relaxed ${
                  msg.role === 'user' ? 'text-white' : 'text-gray-200'
                }`}>
                  {msg.role === 'user' ? (
                    <span>{msg.content}</span>
                  ) : (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={markdownComponents}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  )}
                </div>

                {msg.time && (
                  <div className="text-xs text-gray-600 mt-2">
                    {msg.time}
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-gray-700
                                flex items-center justify-center
                                flex-shrink-0 mt-1">
                  <User size={16} className="text-gray-300" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center
                               justify-center flex-shrink-0 mt-1 ${
                deepMode ? 'bg-purple-600' : 'bg-blue-600'
              }`}>
                <Brain size={16} className="text-white" />
              </div>
              <div className="bg-gray-900 border border-gray-800
                              rounded-2xl rounded-tl-sm p-4">
                <div className="flex items-center gap-2
                                text-gray-400 text-sm">
                  <Loader2 size={14} className="animate-spin" />
                  {deepMode
                    ? 'Reading SEC EDGAR filings... (3-4 minutes)'
                    : 'Researching markets... (30-60 seconds)'
                  }
                </div>
                {deepMode && (
                  <div className="mt-1.5 text-xs text-gray-600">
                    Browsing official SEC EDGAR documents
                  </div>
                )}
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="flex gap-3">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder={deepMode
              ? 'Ask for SEC filing analysis, insider trades, 8-K events...'
              : 'Ask about any stock, market trend, or investment topic...'
            }
            disabled={loading}
            className="flex-1 bg-gray-900 border border-gray-700
                       rounded-xl px-4 py-3 text-white text-sm
                       placeholder-gray-500 focus:outline-none
                       focus:border-blue-500 transition
                       disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className={`px-4 py-3 disabled:opacity-50 disabled:cursor-not-allowed
                        rounded-xl transition flex items-center
                        gap-2 text-white text-sm font-medium ${
              deepMode
                ? 'bg-purple-600 hover:bg-purple-500'
                : 'bg-blue-600 hover:bg-blue-500'
            }`}
          >
            {loading
              ? <Loader2 size={16} className="animate-spin" />
              : <Send size={16} />
            }
          </button>
        </form>

        <p className="text-xs text-gray-600 text-center mt-3">
          {deepMode
            ? 'Deep mode reads official SEC EDGAR filings — allow 3-4 minutes'
            : 'Fast mode uses live market data — results in 30-60 seconds'
          }
        </p>

      </main>
    </div>
  )
}