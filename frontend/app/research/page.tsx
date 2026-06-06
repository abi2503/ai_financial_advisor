'use client'
import { useState, useRef, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import Navbar from '@/components/Navbar'
import { Brain, Send, Loader2, User } from 'lucide-react'
import axios from 'axios'

interface Message {
  role:    'user' | 'alex'
  content: string
  time:    string
}

export default function ResearchPage() {
  const searchParams = useSearchParams()
  const initialQ     = searchParams.get('q') || ''

  const [messages, setMessages] = useState<Message[]>([{
    role:    'alex',
    content: 'Hello! I\'m Alex, your AI financial research assistant. Ask me anything about stocks, markets, or investment topics.',
    time:    new Date().toLocaleTimeString()
  }])
  const [input,   setInput]   = useState(initialQ)
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (initialQ) handleSubmit(null, initialQ)
  }, [])

  async function handleSubmit(e: React.FormEvent | null, overrideInput?: string) {
    if (e) e.preventDefault()
    const question = overrideInput || input
    if (!question.trim() || loading) return

    setMessages(prev => [...prev, {
      role:    'user',
      content: question,
      time:    new Date().toLocaleTimeString()
    }])
    setInput('')
    setLoading(true)

    try {
      const response = await axios.post(
        '/api/research',
        { topic: question },
        { timeout: 120000 }
      )
      setMessages(prev => [...prev, {
        role:    'alex',
        content: response.data.result || 'Research complete.',
        time:    new Date().toLocaleTimeString()
      }])
    } catch (error) {
      setMessages(prev => [...prev, {
        role:    'alex',
        content: 'I encountered an error. Please ensure the researcher service is running.',
        time:    new Date().toLocaleTimeString()
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-6 flex flex-col">

        <div className="flex items-center gap-2 mb-6">
          <Brain className="text-blue-400" size={20} />
          <h1 className="font-semibold text-white">Research Chat</h1>
          <span className="ml-auto text-xs text-gray-500">
            Powered by AWS Bedrock Nova Pro
          </span>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto mb-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
              {msg.role === 'alex' && (
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                  <Brain size={16} className="text-white" />
                </div>
              )}
              <div className={`max-w-[80%] p-4 ${
                msg.role === 'user'
                  ? 'bg-blue-600 rounded-2xl rounded-tr-sm'
                  : 'bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-sm'
              }`}>
                <div className={`text-sm whitespace-pre-wrap leading-relaxed ${
                  msg.role === 'user' ? 'text-white' : 'text-gray-200'
                }`}>
                  {msg.content}
                </div>
                <div className="text-xs text-gray-500 mt-2">{msg.time}</div>
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center flex-shrink-0">
                  <User size={16} className="text-gray-300" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                <Brain size={16} className="text-white" />
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-sm p-4">
                <div className="flex items-center gap-2 text-gray-400 text-sm">
                  <Loader2 size={14} className="animate-spin" />
                  Alex is researching... (30-60 seconds)
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <form onSubmit={handleSubmit} className="flex gap-3">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask about any stock, market trend, or investment topic..."
            disabled={loading}
            className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500 transition disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-xl transition flex items-center gap-2 text-white text-sm font-medium"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </form>

        <p className="text-xs text-gray-600 text-center mt-3">
          Research takes 30-60 seconds. Results stored automatically.
        </p>

      </main>
    </div>
  )
}
