'use client'
import { useState, useRef, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Navbar from '@/components/Navbar'
import { Brain, Send, Loader2, User, Zap, Search, GitBranch, ChevronDown, ChevronUp } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChat } from '@/context/ChatContext'
interface Message {
  role:       'user' | 'alex'
  content:    string
  time:       string
  mode?:      'fast' | 'deep' | 'multi'
  tasks?:     string[]
  tasksDone?: number[]
  streaming?: boolean
  reasoning?: string[]
}

const COMPLEX_PATTERNS = [
  'compare', ' vs ', 'versus', 'should i',
  'or ', 'both', 'which is better',
  'difference between', 'contrast'
]

function isComplexQuery(topic: string): boolean {
  const lower       = topic.toLowerCase()
  const tickerMatch = topic.match(/\b[A-Z]{2,5}\b/g) || []
  const hasMultiple = tickerMatch.length >= 2
  const hasPattern  = COMPLEX_PATTERNS.some(p => lower.includes(p))
  return hasMultiple && hasPattern
}

const markdownComponents = {
  h1:         ({children}: any) => <h1 className="text-lg font-bold text-white mb-2 mt-1">{children}</h1>,
  h2:         ({children}: any) => <h2 className="text-base font-bold text-white mb-2 mt-3 pb-1 border-b border-gray-700">{children}</h2>,
  h3:         ({children}: any) => <h3 className="text-sm font-semibold text-blue-400 mb-1 mt-2">{children}</h3>,
  p:          ({children}: any) => <p className="mb-2 text-gray-200 leading-relaxed">{children}</p>,
  ul:         ({children}: any) => <ul className="mb-3 space-y-1.5">{children}</ul>,
  ol:         ({children}: any) => <ol className="mb-3 space-y-1.5 list-decimal list-inside">{children}</ol>,
  li:         ({children}: any) => (
    <li className="flex gap-2 text-gray-300 text-sm">
      <span className="text-blue-400 mt-0.5 flex-shrink-0">•</span>
      <span>{children}</span>
    </li>
  ),
  strong:     ({children}: any) => <strong className="text-white font-semibold">{children}</strong>,
  em:         ({children}: any) => <em className="text-gray-300 italic">{children}</em>,
  hr:         () => <hr className="border-gray-700 my-4" />,
  code:       ({children}: any) => <code className="bg-gray-800 text-blue-300 px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>,
  blockquote: ({children}: any) => (
    <blockquote className="border-l-2 border-blue-400 pl-3 text-gray-400 italic my-3 bg-blue-500/5 py-2 rounded-r">
      {children}
    </blockquote>
  ),
  table: ({children}: any) => (
    <div className="overflow-x-auto my-3 rounded-lg border border-gray-700">
      <table className="w-full text-sm border-collapse">{children}</table>
    </div>
  ),
  thead: ({children}: any) => <thead className="bg-gray-800/80">{children}</thead>,
  tbody: ({children}: any) => <tbody className="divide-y divide-gray-800">{children}</tbody>,
  tr:    ({children}: any) => <tr className="hover:bg-gray-800/40 transition">{children}</tr>,
  th:    ({children}: any) => <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">{children}</th>,
  td:    ({children}: any) => <td className="px-4 py-2.5 text-gray-200">{children}</td>,
  a:     ({children, href}: any) => (
    <a href={href} target="_blank" rel="noopener noreferrer"
       className="text-blue-400 hover:text-blue-300 underline">
      {children}
    </a>
  ),
}

function ReasoningSteps({
  steps, streaming, mode, collapsed, onToggle
}: {
  steps: string[]; streaming: boolean; mode?: string; collapsed: boolean; onToggle: () => void
}) {
  if (!steps || steps.length === 0) return null

  const borderColor = mode === 'deep' ? 'border-purple-500/20' : mode === 'multi' ? 'border-green-500/20' : 'border-blue-500/20'
  const textColor   = mode === 'deep' ? 'text-purple-400'      : mode === 'multi' ? 'text-green-400'      : 'text-blue-400'
  const bgColor     = mode === 'deep' ? 'bg-purple-500/5'      : mode === 'multi' ? 'bg-green-500/5'      : 'bg-blue-500/5'
  const dotColor    = mode === 'deep' ? 'bg-purple-400'        : mode === 'multi' ? 'bg-green-400'        : 'bg-blue-400'

  return (
    <div className={`mb-3 rounded-lg border ${borderColor} ${bgColor} overflow-hidden`}>
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-white/5 transition"
      >
        <div className="flex items-center gap-2">
          {streaming
            ? <Loader2 size={10} className={`animate-spin ${textColor}`} />
            : <div className={`w-2 h-2 rounded-full ${dotColor}`} />
          }
          <span className={`text-xs font-medium ${textColor}`}>
            {streaming ? 'Alex is thinking...' : `Alex's reasoning (${steps.length} steps)`}
          </span>
        </div>
        {collapsed ? <ChevronDown size={12} className="text-gray-500" /> : <ChevronUp size={12} className="text-gray-500" />}
      </button>

      {!collapsed && (
        <div className="px-3 pb-3 space-y-1.5">
          {steps.map((step, i) => {
            const isComplete = step.startsWith('✅')
            const isWaiting  = step.startsWith('⏳')
            const isError    = step.startsWith('❌')
            const isInfo     = step.startsWith('🔀') || step.startsWith('🧠')
            const isLast     = i === steps.length - 1

            return (
              <div key={i} className="flex items-start gap-2">
                <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5 ${
                  isComplete ? 'bg-green-400' :
                  isWaiting  ? 'bg-yellow-400 animate-pulse' :
                  isError    ? 'bg-red-400' :
                  isInfo     ? 'bg-blue-400' :
                  isLast && streaming ? `${dotColor} animate-pulse` :
                  'bg-gray-600'
                }`} />
                <span className={`text-xs leading-relaxed ${
                  isComplete ? 'text-green-400/80' :
                  isWaiting  ? 'text-yellow-400/80' :
                  isError    ? 'text-red-400/80' :
                  isInfo     ? 'text-blue-400/80' :
                  isLast && streaming ? 'text-gray-300' :
                  'text-gray-500'
                }`}>
                  {step}
                </span>
              </div>
            )
          })}
          {streaming && (
            <div className="flex items-center gap-2 mt-1">
              <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${dotColor}`} />
              <span className="text-xs text-gray-600 italic">processing...</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ResearchPage() {
  const searchParams = useSearchParams()
  const initialQ     = searchParams.get('q') || ''
  const { sessionId } = useChat()

  const [messages,  setMessages]  = useState<Message[]>([{
    role:    'alex',
    content: 'Hello! I\'m Alex, your AI financial research assistant.\n\n⚡ **Fast Mode** — Price, news, and analysis in 45 seconds.\n\n🔍 **Deep Mode** — SEC filings, insider trading, analyst ratings in 3-4 minutes.\n\n🔀 **Multi-Agent** — Auto-detected for complex queries like "Compare NVDA vs AMD".\n\nAsk me anything about stocks, markets, or investment topics.',
    time:    ''
  }])
  const [input,        setInput]        = useState(initialQ)
  const [loading,      setLoading]      = useState(false)
  const [deepMode,     setDeepMode]     = useState(false)
  const [status,       setStatus]       = useState('')
  const [mounted,      setMounted]      = useState(false)
  const [collapsedMap, setCollapsedMap] = useState<Record<number, boolean>>({})

  const bottomRef        = useRef<HTMLDivElement>(null)
  const submittedRef     = useRef(false)
  const hasAutoSubmitted = useRef(false)

  useEffect(() => { setMounted(true) }, [])
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])
  useEffect(() => {
    if (initialQ && !hasAutoSubmitted.current) {
      hasAutoSubmitted.current = true
      handleSubmit(null, initialQ)
    }
  }, [])

  function getTime() {
    return mounted ? new Date().toLocaleTimeString() : ''
  }

  function toggleCollapsed(idx: number) {
    setCollapsedMap(prev => ({ ...prev, [idx]: !prev[idx] }))
  }

  async function handleStreamResearch(question: string) {
    setStatus('Connecting to Alex...')
    const reasoningSteps: string[] = []

    setMessages(prev => [...prev, {
      role: 'alex', content: '', time: getTime(), mode: 'fast', streaming: true, reasoning: []
    }])

    const response = await fetch('/api/research/stream', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
      body:    JSON.stringify({ topic: question, session_id: sessionId }),
    })

    if (!response.ok || !response.body) throw new Error('Stream unavailable')

    const reader  = response.body.getReader()
    const decoder = new TextDecoder()
    let   buffer  = ''
    let   content = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const rawData = line.slice(6).trim()
          if (!rawData) continue

          try {
            const data = JSON.parse(rawData)

            if (data.type === 'reasoning') {
              reasoningSteps.push(data.content)
              setStatus(data.content)
              setMessages(prev => [
                ...prev.slice(0, -1),
                { role: 'alex', content: '', time: getTime(), mode: 'fast', streaming: true, reasoning: [...reasoningSteps] }
              ])
            } else if (data.type === 'status') {
              setStatus(data.content)
            } else if (data.type === 'reasoning_done') {
              setStatus('Streaming response...')
            } else if (data.type === 'token') {
              content += data.content
              setMessages(prev => [
                ...prev.slice(0, -1),
                { role: 'alex', content, time: getTime(), mode: 'fast', streaming: true, reasoning: reasoningSteps }
              ])
            } else if (data.type === 'done') {
              setStatus('')
              setMessages(prev => [
                ...prev.slice(0, -1),
                { role: 'alex', content, time: getTime(), mode: 'fast', streaming: false, reasoning: reasoningSteps }
              ])
              return content
            } else if (data.type === 'error') {
              throw new Error(data.content)
            }
          } catch (parseErr) {}
        }
      }
    } finally {
      reader.releaseLock()
    }
    return content
  }

  async function handleMultiAgentResearch(question: string) {
    setStatus('Decomposing query...')

    setMessages(prev => [...prev, {
      role: 'alex', content: '', time: getTime(), mode: 'multi', streaming: true,
      reasoning: ['🔀 Activating Planner Agent...']
    }])

    const response = await fetch('/api/research', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ topic: question, session_id: sessionId }),
    })

    const data = await response.json()

    if (data.mode === 'multi-agent' && data.tasks) {
      const taskSteps = data.tasks.map((t: string, i: number) =>
        `⏳ Task ${i+1}/${data.tasks.length}: ${t.substring(0, 60)}...`
      )

      setMessages(prev => [
        ...prev.slice(0, -1),
        {
          role: 'alex', content: '', time: getTime(), mode: 'multi', streaming: true,
          tasks: data.tasks,
          reasoning: ['🔀 Planner decomposed into parallel tasks', ...taskSteps]
        }
      ])

      const statusMessages = [
        '📊 Analyzing financial data...', '📈 Comparing metrics...',
        '📋 Fetching analyst ratings...', '🧮 Computing valuations...',
        '🧠 Synthesizing results...'
      ]
      let idx = 0
      const interval = setInterval(() => {
        setStatus(statusMessages[idx % statusMessages.length])
        idx++
      }, 4000)
      clearInterval(interval)
      setStatus('')

      const finalSteps = data.tasks.map((t: string, i: number) =>
        `✅ Task ${i+1}/${data.tasks.length}: ${t.substring(0, 60)}...`
      )

      setMessages(prev => [
        ...prev.slice(0, -1),
        {
          role: 'alex', content: data.result || 'Research complete', time: getTime(),
          mode: 'multi', streaming: false, tasks: data.tasks,
          reasoning: ['🔀 Planner decomposed query into parallel tasks', ...finalSteps, '🧠 All results synthesized successfully']
        }
      ])
    }

    return data.result
  }

  async function handleSubmit(e: React.FormEvent | null, overrideInput?: string) {
    if (e) e.preventDefault()
    const question = overrideInput || input
    if (!question.trim() || loading) return

    // Prevent double submission
    if (submittedRef.current) return
    submittedRef.current = true
    setTimeout(() => { submittedRef.current = false }, 1000)

    const complex = isComplexQuery(question)
    const mode    = deepMode ? 'deep' : complex ? 'multi' : 'fast'

    setMessages(prev => [...prev, {
      role: 'user', content: question, time: getTime(), mode
    }])
    setInput('')
    setLoading(true)

    try {
      if (complex && !deepMode) {
        await handleMultiAgentResearch(question)

      } else if (!deepMode) {
        try {
          await handleStreamResearch(question)
        } catch (streamErr) {
          console.log('Stream failed, falling back')
          setStatus('Researching...')
          const res = await fetch('/api/research', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ topic: question, session_id: sessionId }),
          })
          const data = await res.json()
          setMessages(prev => [...prev, {
            role: 'alex', content: data.result || 'Research complete.', time: getTime(), mode: 'fast'
          }])
        }

      } else {
        const deepReasoningSteps: string[] = ['🔌 Connecting to SEC EDGAR...']
        setStatus('Connecting to SEC EDGAR...')
        setMessages(prev => [...prev, {
          role: 'alex', content: '', time: getTime(), mode: 'deep', streaming: true,
          reasoning: [...deepReasoningSteps]
        }])

        try {
          const response = await fetch('/api/research/deep/stream', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ topic: question, session_id: sessionId }),
          })

          if (!response.ok || !response.body) throw new Error('Stream failed')

          const reader  = response.body.getReader()
          const decoder = new TextDecoder()
          let   buffer  = ''
          let   content = ''

          while (true) {
            const { done, value } = await reader.read()
            if (done) break

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''

            for (const line of lines) {
              if (!line.startsWith('data: ')) continue
              try {
                const data = JSON.parse(line.slice(6))
                if (data.type === 'reasoning') {
                  deepReasoningSteps.push(data.content)
                  setStatus(data.content)
                  setMessages(prev => [
                    ...prev.slice(0, -1),
                    { role: 'alex', content: '', time: getTime(), mode: 'deep', streaming: true, reasoning: [...deepReasoningSteps] }
                  ])
                } else if (data.type === 'status') {
                  setStatus(data.content)
                } else if (data.type === 'reasoning_done') {
                  setStatus('Streaming analysis...')
                } else if (data.type === 'token') {
                  content += data.content
                  setMessages(prev => [
                    ...prev.slice(0, -1),
                    { role: 'alex', content, time: getTime(), mode: 'deep', streaming: true, reasoning: deepReasoningSteps }
                  ])
                } else if (data.type === 'done') {
                  setStatus('')
                  setMessages(prev => [
                    ...prev.slice(0, -1),
                    { role: 'alex', content, time: getTime(), mode: 'deep', streaming: false, reasoning: deepReasoningSteps }
                  ])
                } else if (data.type === 'error') {
                  throw new Error(data.content)
                }
              } catch (e) {}
            }
          }

        } catch (err) {
          setStatus('Reading SEC EDGAR filings...')
          const res = await fetch('/api/research/deep', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ topic: question, session_id: sessionId }),
            signal:  AbortSignal.timeout(300000)
          })
          const data = await res.json()
          setMessages(prev => [
            ...prev.slice(0, -1),
            { role: 'alex', content: data.result || 'Research complete', time: getTime(), mode: 'deep', reasoning: deepReasoningSteps }
          ])
          setStatus('')
        }
      }

    } catch (error: any) {
      setStatus('')
      setMessages(prev => [
        ...prev.slice(0, -1),
        {
          role: 'alex', time: getTime(), mode,
          content: deepMode
            ? 'Deep research encountered an error. SEC filings may be temporarily unavailable.'
            : 'Research encountered an error. Please ensure the researcher service is running.'
        }
      ])
    } finally {
      setLoading(false)
      setStatus('')
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-6 flex flex-col">

        <div className="flex items-center gap-2 mb-4">
          <Brain className="text-blue-400" size={20} />
          <h1 className="font-semibold text-white">Research Chat</h1>
          <span className="ml-auto text-xs text-gray-500">Powered by AWS Bedrock Nova Pro</span>
        </div>

        <div className="flex items-center gap-3 mb-4 p-3 bg-gray-900 border border-gray-800 rounded-xl">
          <span className="text-xs text-gray-500 font-medium">Mode:</span>
          <button
            onClick={() => setDeepMode(false)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              !deepMode ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20' : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            <Zap size={12} /> Fast
          </button>
          <button
            onClick={() => setDeepMode(true)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              deepMode ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/20' : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            <Search size={12} /> Deep
          </button>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-600/10 border border-green-600/20 text-green-400 text-xs">
            <GitBranch size={12} /> Multi-Agent auto
          </div>
          <span className="text-xs text-gray-600 ml-1">
            {deepMode ? '🔍 SEC + analyst ratings + options flow (3-4 min)' : '⚡ Price + news + analysis (45 sec) · 🔀 Auto multi-agent for comparisons'}
          </span>
        </div>

        {status && (
          <div className="mb-3 px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-lg flex items-center gap-2">
            <Loader2 size={12} className="animate-spin text-blue-400" />
            <span className="text-xs text-blue-400">{status}</span>
          </div>
        )}

        {messages.length === 1 && (
          <div className="mb-4 grid grid-cols-2 gap-2">
            {(deepMode ? [
              'Analyze NVDA SEC 10-K for hidden risks',
              'Show AAPL insider trading activity',
              'MSFT analyst ratings and price targets',
              'TSLA options flow signals today',
            ] : [
              'Should I buy NVDA before earnings?',
              'Compare NVDA vs AMD for AI chips',
              'How is Fed rate affecting tech stocks?',
              'What is happening with AI stocks today?',
            ]).map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => handleSubmit(null, suggestion)}
                className="text-left p-3 bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-gray-600 rounded-xl text-gray-400 text-xs transition"
              >
                "{suggestion}"
              </button>
            ))}
          </div>
        )}

        <div className="flex-1 space-y-4 overflow-y-auto mb-4 min-h-0">
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
              {msg.role === 'alex' && (
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${
                  msg.mode === 'deep' ? 'bg-purple-600' : msg.mode === 'multi' ? 'bg-green-600' : 'bg-blue-600'
                }`}>
                  {msg.mode === 'multi' ? <GitBranch size={16} className="text-white" /> : <Brain size={16} className="text-white" />}
                </div>
              )}

              <div className={`max-w-[85%] p-4 ${
                msg.role === 'user'
                  ? 'bg-blue-600 rounded-2xl rounded-tr-sm'
                  : 'bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-sm'
              }`}>

                {msg.role === 'alex' && msg.mode && i > 0 && (
                  <div className="mb-3 flex items-center gap-2">
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                      msg.mode === 'deep'  ? 'bg-purple-500/20 text-purple-400' :
                      msg.mode === 'multi' ? 'bg-green-500/20 text-green-400'   :
                      'bg-blue-500/20 text-blue-400'
                    }`}>
                      {msg.mode === 'deep' ? '🔍 Deep Research' : msg.mode === 'multi' ? '🔀 Multi-Agent Research' : '⚡ Fast Research'}
                    </span>
                    {msg.streaming && (
                      <span className="text-xs text-gray-500 flex items-center gap-1">
                        <Loader2 size={10} className="animate-spin" /> streaming
                      </span>
                    )}
                  </div>
                )}

                {msg.role === 'alex' && msg.reasoning && msg.reasoning.length > 0 && i > 0 && (
                  <ReasoningSteps
                    steps={msg.reasoning}
                    streaming={msg.streaming ?? false}
                    mode={msg.mode}
                    collapsed={collapsedMap[i] ?? false}
                    onToggle={() => toggleCollapsed(i)}
                  />
                )}

                {msg.reasoning && msg.reasoning.length > 0 && msg.content && (
                  <div className="border-t border-gray-800 mb-3" />
                )}

                {msg.tasks && msg.tasks.length > 0 && !msg.reasoning && (
                  <div className="mb-3 p-2 bg-green-500/5 border border-green-500/10 rounded-lg">
                    <div className="text-xs text-green-400 font-medium mb-1">Parallel research tasks:</div>
                    {msg.tasks.map((task, ti) => (
                      <div key={ti} className="text-xs text-gray-400">{ti + 1}. {task}</div>
                    ))}
                  </div>
                )}

                <div className={`text-sm leading-relaxed ${msg.role === 'user' ? 'text-white' : 'text-gray-200'}`}>
                  {msg.role === 'user' ? (
                    <span>{msg.content}</span>
                  ) : (
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                      {msg.content}
                    </ReactMarkdown>
                  )}
                  {msg.streaming && msg.content && (
                    <span className="inline-block w-1 h-4 bg-blue-400 ml-0.5 animate-pulse" />
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

          {loading && !messages[messages.length - 1]?.streaming && (
            <div className="flex gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${deepMode ? 'bg-purple-600' : 'bg-blue-600'}`}>
                <Brain size={16} className="text-white" />
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-sm p-4">
                <div className="flex items-center gap-2 text-gray-400 text-sm">
                  <Loader2 size={14} className="animate-spin" />
                  {deepMode ? 'Reading SEC EDGAR filings... (3-4 minutes)' : 'Researching markets... (30-60 seconds)'}
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
            placeholder={deepMode ? 'Ask for SEC filing analysis, insider trades...' : 'Ask about any stock, market, or use "Compare X vs Y" for multi-agent...'}
            disabled={loading}
            className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500 transition disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className={`px-4 py-3 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl transition flex items-center gap-2 text-white text-sm font-medium ${
              deepMode ? 'bg-purple-600 hover:bg-purple-500' : 'bg-blue-600 hover:bg-blue-500'
            }`}
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </form>

        <p className="text-xs text-gray-600 text-center mt-3">
          {deepMode ? 'Deep mode reads SEC EDGAR + analyst ratings — allow 3-4 minutes' : 'Fast mode streams live market data · Multi-agent auto-activates for comparisons'}
        </p>

      </main>
    </div>
  )
}

export default function ResearchPageWrapper() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400 text-sm">Loading...</div>
      </div>
    }>
      <ResearchPage />
    </Suspense>
  )
}