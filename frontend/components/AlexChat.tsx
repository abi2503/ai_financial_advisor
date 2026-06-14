'use client'

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Brain, Send, Loader2, User, ChevronDown, ChevronUp } from 'lucide-react'
import { useChat } from '@/context/ChatContext'
import AlexMarkdown, { renderMarkdownStreaming } from '@/components/AlexMarkdown'

export type ChatMode = 'fast' | 'deep' | 'chat' | 'debater'

export interface DebaterInfo {
  id:        string
  name:      string
  title:     string
  expertise: string
}

export interface ChatMessage {
  role:       'user' | 'alex'
  content:    string
  time:       string
  mode?:      ChatMode
  debater?:   DebaterInfo
  streaming?: boolean
  reasoning?: string[]
  latencyMs?: number
}

const WELCOME: ChatMessage = {
  role: 'alex',
  content: "Hello! I'm Alex, your AI financial assistant.\n\nAsk me anything about markets — I'll pick the right path:\n\n💬 **Chat** — bonds, inflation, investing basics\n\n🤝 **Debater Handoff** — Marcus (growth), Zara (quant), Reid (macro), Victoria (bear), Elena (risk)\n\n⚡ **Fast Research** — live prices & news (~60s)\n\n🔍 **Deep Research** — SEC filings, comparisons (3–5 min)",
  time: '',
}

function formatElapsed(ms: number): string {
  const s = ms / 1000
  return s < 10 ? s.toFixed(1) : String(Math.round(s))
}

function statusWithElapsed(base: string, elapsedMs: number): string {
  const clean = base.replace(/ \(\d+(\.\d+)?s\)$/, '')
  return `${clean} (${formatElapsed(elapsedMs)}s)`
}

function modeLabel(mode?: ChatMode, debater?: DebaterInfo) {
  if (mode === 'debater' && debater) return `🤝 ${debater.name}`
  if (mode === 'deep')  return '🔍 Deep Research'
  if (mode === 'chat')  return '💬 Chat'
  return '⚡ Fast Research'
}

function modeColor(mode?: ChatMode) {
  if (mode === 'debater') return 'bg-amber-500/20 text-amber-400'
  if (mode === 'deep')  return 'bg-purple-500/20 text-purple-400'
  if (mode === 'chat')  return 'bg-gray-500/20 text-gray-300'
  return 'bg-blue-500/20 text-blue-400'
}

/** Reasoning card only for Deep Research / multi-agent — not chat or fast */
function showReasoningCard(mode?: ChatMode) {
  return mode === 'deep'
}

function visibleReasoning(mode: ChatMode | undefined, steps: string[]) {
  return showReasoningCard(mode) ? steps : []
}

function StreamingText({
  content,
  onGrow,
}: {
  content: string
  onGrow?: () => void
}) {
  const ref = React.useRef<HTMLDivElement>(null)
  const rafRef = React.useRef<number | null>(null)
  const lastRendered = React.useRef('')

  useEffect(() => {
    if (content === lastRendered.current) return

    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = requestAnimationFrame(() => {
      if (!ref.current) return
      ref.current.innerHTML = renderMarkdownStreaming(content) +
        '<span style="display:inline-block;width:2px;height:16px;background:#60a5fa;margin-left:2px;animation:pulse 1s infinite"></span>'
      lastRendered.current = content
      rafRef.current = null
      onGrow?.()
    })

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [content, onGrow])

  return <div ref={ref} className="text-sm leading-relaxed" />
}

function HandoffBanner({ debater }: { debater: DebaterInfo }) {
  return (
    <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2">
      <p className="text-xs text-amber-400 font-medium">
        🤝 Delegating to <span className="text-amber-300">{debater.name}</span> — {debater.title}
      </p>
      <p className="text-xs text-gray-500 mt-1">{debater.expertise}</p>
    </div>
  )
}

function ReasoningSteps({ steps, streaming, mode, collapsed, onToggle }: {
  steps: string[]; streaming: boolean; mode?: ChatMode
  collapsed: boolean; onToggle: () => void
}) {
  if (!steps.length) return null
  const purple = mode === 'deep'
  const border = purple ? 'border-purple-500/20' : mode === 'chat' ? 'border-gray-600' : 'border-blue-500/20'
  const accent = purple ? 'text-purple-400' : mode === 'chat' ? 'text-gray-400' : 'text-blue-400'
  const bg     = purple ? 'bg-purple-500/5' : mode === 'chat' ? 'bg-gray-800/50' : 'bg-blue-500/5'

  return (
    <div className={`mb-3 rounded-lg border ${border} ${bg}`}>
      <button onClick={onToggle} className="w-full flex items-center justify-between px-3 py-2">
        <span className={`text-xs font-medium ${accent}`}>
          {streaming ? 'Alex is thinking...' : `Reasoning (${steps.length} steps)`}
        </span>
        {collapsed ? <ChevronDown size={12} className="text-gray-500" /> : <ChevronUp size={12} className="text-gray-500" />}
      </button>
      {!collapsed && (
        <div className="px-3 pb-3 space-y-1">
          {steps.map((s, i) => (
            <div key={i} className="text-xs text-gray-400 leading-relaxed">{s}</div>
          ))}
        </div>
      )}
    </div>
  )
}

async function syncSession(sessionId: string, messages: ChatMessage[]) {
  try {
    await fetch('/api/alex/session', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        session_id: sessionId,
        messages:   messages.filter(m => m.role && m.content).slice(-30),
      }),
    })
  } catch { /* non-fatal */ }
}

interface AlexChatProps {
  initialQuery?: string
}

export default function AlexChat({ initialQuery = '' }: AlexChatProps) {
  const { sessionId } = useChat()
  const [messages, setMessages]     = useState<ChatMessage[]>([WELCOME])
  const [input, setInput]           = useState(initialQuery)
  const [loading, setLoading]       = useState(false)
  const [status, setStatus]         = useState('')
  const [mounted, setMounted]       = useState(false)
  const [collapsedMap, setCollapsedMap] = useState<Record<number, boolean>>({})
  const [hydrated, setHydrated]     = useState(false)

  const bottomRef        = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const submittedRef     = useRef(false)
  const hasAutoSubmitted = useRef(false)
  const streamRafRef     = useRef<number | null>(null)
  const streamContentRef = useRef('')

  const scrollToBottom = useCallback((smooth: boolean) => {
    const container = scrollContainerRef.current
    if (!container) return
    if (smooth) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
      return
    }
    const nearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 150
    if (nearBottom) {
      container.scrollTop = container.scrollHeight
    }
  }, [])

  const handleStreamGrow = useCallback(() => {
    scrollToBottom(false)
  }, [scrollToBottom])

  useEffect(() => { setMounted(true) }, [])

  useEffect(() => {
    if (!sessionId || hydrated) return
    fetch(`/api/alex/session?session_id=${sessionId}`)
      .then(r => r.json())
      .then(data => {
        if (data.messages?.length > 0) {
          setMessages([WELCOME, ...data.messages.map((m: any) => ({
            role:    m.role,
            content: m.content,
            time:    m.time || '',
            mode:    m.mode || undefined,
          }))])
        }
        setHydrated(true)
      })
      .catch(() => setHydrated(true))
  }, [sessionId, hydrated])

  useEffect(() => {
    const lastMsg = messages[messages.length - 1]
    // Smooth scroll only when a message finishes — not on every streaming token
    if (!lastMsg?.streaming) {
      scrollToBottom(true)
    }
  }, [messages, scrollToBottom])

  useEffect(() => {
    if (initialQuery && !hasAutoSubmitted.current && hydrated) {
      hasAutoSubmitted.current = true
      handleSubmit(null, initialQuery)
    }
  }, [initialQuery, hydrated])

  function getTime() {
    return mounted ? new Date().toLocaleTimeString() : ''
  }

  const persistMessages = useCallback((msgs: ChatMessage[]) => {
    if (sessionId && msgs.length > 1) {
      syncSession(sessionId, msgs.filter(m => m !== WELCOME))
    }
  }, [sessionId])

  async function handleSubmit(e: React.FormEvent | null, override?: string) {
    if (e) e.preventDefault()
    const question = override || input
    if (!question.trim() || loading) return
    if (submittedRef.current) return
    submittedRef.current = true
    setTimeout(() => { submittedRef.current = false }, 1000)

    const userMsg: ChatMessage = { role: 'user', content: question, time: getTime() }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput('')
    setLoading(true)
    setStatus('Routing your question...')

    const reasoningSteps: string[] = []
    let content = ''
    streamContentRef.current = ''
    let mode: ChatMode | undefined
    let alexBubbleAdded = false
    let debaterInfo: DebaterInfo | undefined

    const scheduleStreamUpdate = () => {
      if (streamRafRef.current != null) return
      streamRafRef.current = requestAnimationFrame(() => {
        streamRafRef.current = null
        const snapshot = streamContentRef.current
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (!last || last.role !== 'alex' || !last.streaming) return prev
          if (last.content === snapshot) return prev
          return [
            ...prev.slice(0, -1),
            {
              ...last,
              content: snapshot,
              reasoning: visibleReasoning(mode, reasoningSteps),
            },
          ]
        })
      })
    }

    try {
      const response = await fetch('/api/alex/chat', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body:    JSON.stringify({ query: question, session_id: sessionId }),
      })

      if (!response.ok || !response.body) throw new Error('Chat unavailable')

      const reader  = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith(':') || !line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue
          try {
            const data = JSON.parse(raw)

            if (data.type === 'routing') {
              const r = data.routing || {}
              mode = r.route === 'deep' ? 'deep' : r.route === 'chat' ? 'chat' : r.route === 'debater' ? 'debater' : 'fast'
              if (mode === 'deep' && data.steps) reasoningSteps.push(...data.steps)
              setStatus(data.steps?.[data.steps.length - 1] || 'Researching...')
              if (!alexBubbleAdded) {
                alexBubbleAdded = true
                setMessages(prev => [...prev, {
                  role: 'alex', content: '', time: getTime(), mode, debater: debaterInfo,
                  streaming: true, reasoning: visibleReasoning(mode, reasoningSteps),
                }])
              } else {
                setMessages(prev => [
                  ...prev.slice(0, -1),
                  {
                    role: 'alex', content: '', time: getTime(), mode, debater: debaterInfo,
                    streaming: true, reasoning: visibleReasoning(mode, reasoningSteps),
                  },
                ])
              }
            } else if (data.type === 'handoff') {
              debaterInfo = data.debater
              mode = 'debater'
              if (!alexBubbleAdded) {
                alexBubbleAdded = true
                setMessages(prev => [...prev, {
                  role: 'alex', content: '', time: getTime(), mode: 'debater',
                  debater: debaterInfo, streaming: true, reasoning: [],
                }])
              } else {
                setMessages(prev => [
                  ...prev.slice(0, -1),
                  {
                    role: 'alex', content, time: getTime(), mode: 'debater',
                    debater: debaterInfo, streaming: true, reasoning: [],
                  },
                ])
              }
              setStatus(`Delegating to ${debaterInfo?.name}...`)
            } else if (data.type === 'reasoning') {
              if (!alexBubbleAdded) {
                alexBubbleAdded = true
                mode = mode || 'chat'
                setMessages(prev => [...prev, {
                  role: 'alex', content: '', time: getTime(), mode, streaming: true, reasoning: [],
                }])
              }
              if (mode === 'deep' && !reasoningSteps.includes(data.content)) {
                reasoningSteps.push(data.content)
              }
              setStatus(data.content)
              setMessages(prev => [
                ...prev.slice(0, -1),
                {
                  role: 'alex', content, time: getTime(), mode, debater: debaterInfo,
                  streaming: true, reasoning: visibleReasoning(mode, reasoningSteps),
                },
              ])
            } else if (data.type === 'tick') {
              const last = reasoningSteps[reasoningSteps.length - 1] || 'Working...'
              setStatus(statusWithElapsed(last, data.elapsed_ms))
            } else if (data.type === 'reasoning_done') {
              setStatus('Streaming response...')
            } else if (data.type === 'token') {
              if (!alexBubbleAdded) {
                alexBubbleAdded = true
                mode = mode || 'chat'
                setMessages(prev => [...prev, {
                  role: 'alex', content: '', time: getTime(), mode, streaming: true, reasoning: [],
                }])
              }
              content += data.content
              streamContentRef.current = content
              scheduleStreamUpdate()
            } else if (data.type === 'done') {
              if (streamRafRef.current != null) {
                cancelAnimationFrame(streamRafRef.current)
                streamRafRef.current = null
              }
              if (data.route === 'deep' || data.deep_kind) mode = 'deep'
              if (data.route === 'chat') mode = 'chat'
              if (data.route === 'debater') mode = 'debater'
              const final: ChatMessage = {
                role: 'alex', content, time: getTime(), mode: mode || 'chat', debater: debaterInfo,
                streaming: false, reasoning: visibleReasoning(mode, reasoningSteps), latencyMs: data.latency,
              }
              const all = [...nextMessages, final]
              setMessages(all)
              persistMessages(all)
              setStatus('')
              return
            } else if (data.type === 'error') {
              throw new Error(data.content)
            }
          } catch { /* skip bad lines */ }
        }
      }
    } catch (err: any) {
      const errMsg: ChatMessage = {
        role: 'alex',
        content: `Sorry, something went wrong: ${err.message || 'please try again.'}`,
        time: getTime(), mode: mode || 'chat',
      }
      const all = [...nextMessages, errMsg]
      setMessages(all)
      persistMessages(all)
    } finally {
      setLoading(false)
      setStatus('')
    }
  }

  return (
    <>
      {status && (
        <div className="mb-3 px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-lg flex items-center gap-2">
          <Loader2 size={12} className="animate-spin text-blue-400" />
          <span className="text-xs text-blue-400">{status}</span>
        </div>
      )}

      <div
        ref={scrollContainerRef}
        className="flex-1 space-y-4 overflow-y-auto mb-4 min-h-0"
        style={{ overflowAnchor: 'none' }}
      >
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
            {msg.role === 'alex' && (
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${
                msg.mode === 'debater' ? 'bg-amber-600' : msg.mode === 'deep' ? 'bg-purple-600' : msg.mode === 'chat' ? 'bg-gray-600' : 'bg-blue-600'
              }`}>
                <Brain size={16} className="text-white" />
              </div>
            )}
            <div className={`max-w-[85%] p-4 ${
              msg.role === 'user'
                ? 'bg-blue-600 rounded-2xl rounded-tr-sm'
                : 'bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-sm min-h-[60px]'
            }`}>
              {msg.role === 'alex' && msg.mode && i > 0 && (
                <div className="mb-2 flex items-center gap-2 flex-wrap">
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${modeColor(msg.mode)}`}>
                    {modeLabel(msg.mode, msg.debater)}
                  </span>
                  {msg.streaming && (
                    <span className="text-xs text-gray-500 flex items-center gap-1">
                      <Loader2 size={10} className="animate-spin" /> streaming
                    </span>
                  )}
                  {!msg.streaming && msg.latencyMs != null && msg.latencyMs > 0 && (
                    <span className="text-xs text-gray-500">{msg.latencyMs}s</span>
                  )}
                </div>
              )}
              {msg.role === 'alex' && msg.debater && i > 0 && (
                <HandoffBanner debater={msg.debater} />
              )}
              {msg.role === 'alex' && showReasoningCard(msg.mode) && msg.reasoning && msg.reasoning.length > 0 && i > 0 && (
                <ReasoningSteps
                  steps={msg.reasoning}
                  streaming={msg.streaming ?? false}
                  mode={msg.mode}
                  collapsed={collapsedMap[i] ?? false}
                  onToggle={() => setCollapsedMap(p => ({ ...p, [i]: !p[i] }))}
                />
              )}
              {showReasoningCard(msg.mode) && msg.reasoning && msg.reasoning.length > 0 && msg.content && (
                <div className="border-t border-gray-800 mb-3" />
              )}
              <div className="text-sm leading-relaxed text-gray-200">
                {msg.role === 'user' ? (
                  <span className="text-white">{msg.content}</span>
                ) : msg.streaming ? (
                  <StreamingText content={msg.content} onGrow={handleStreamGrow} />
                ) : (
                  <AlexMarkdown content={msg.content} />
                )}
              </div>
              {msg.time && <div className="text-xs text-gray-600 mt-2">{msg.time}</div>}
            </div>
            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center flex-shrink-0 mt-1">
                <User size={16} className="text-gray-300" />
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} style={{ height: 1, overflowAnchor: 'auto' }} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask about any stock, SEC filings, or say hello..."
          disabled={loading}
          className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-xl text-white transition"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
        </button>
      </form>
      <p className="text-xs text-gray-600 text-center mt-3">
        Alex auto-routes: Chat · Debater Handoff · Fast · Deep Research
      </p>
    </>
  )
}
