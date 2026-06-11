'use client'
import { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react'

interface Message {
  role:      'user' | 'alex'
  content:   string
  time:      string
  mode?:     string
  reasoning?: string[]
  streaming?: boolean
}

interface ChatContextType {
  messages:    Message[]
  sessionId:   string
  addMessage:  (msg: Message) => void
  updateLast:  (content: string, streaming?: boolean) => void
  clearChat:   () => void
}

const ChatContext = createContext<ChatContextType | null>(null)

export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages,  setMessages]  = useState<Message[]>([])
  const [sessionId, setSessionId] = useState('')
  const initialized = useRef(false)

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true

    // Load persisted chat
    try {
      const saved = sessionStorage.getItem('alex_chat')
      const sid   = sessionStorage.getItem('alex_session_id')
      if (saved) setMessages(JSON.parse(saved))
      if (sid) {
        setSessionId(sid)
      } else {
        const newSid = crypto.randomUUID()
        setSessionId(newSid)
        sessionStorage.setItem('alex_session_id', newSid)
      }
    } catch (e) {
      const newSid = crypto.randomUUID()
      setSessionId(newSid)
    }
  }, [])

  // Persist messages to sessionStorage
  useEffect(() => {
    if (messages.length > 0) {
      try {
        sessionStorage.setItem('alex_chat', JSON.stringify(messages.slice(-50)))
      } catch (e) {}
    }
  }, [messages])

  function addMessage(msg: Message) {
    setMessages(prev => [...prev, msg])
  }

  function updateLast(content: string, streaming?: boolean) {
    setMessages(prev => [
      ...prev.slice(0, -1),
      { ...prev[prev.length - 1], content, streaming }
    ])
  }

  function clearChat() {
    setMessages([])
    try {
      sessionStorage.removeItem('alex_chat')
      const newSid = crypto.randomUUID()
      setSessionId(newSid)
      sessionStorage.setItem('alex_session_id', newSid)
    } catch (e) {}
  }

  return (
    <ChatContext.Provider value={{ messages, sessionId, addMessage, updateLast, clearChat }}>
      {children}
    </ChatContext.Provider>
  )
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used within ChatProvider')
  return ctx
}
