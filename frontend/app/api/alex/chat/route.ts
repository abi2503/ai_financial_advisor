import { auth } from '@clerk/nextjs/server'
import { NextRequest } from 'next/server'
import { getEcsUrl } from '@/lib/config'
import {
  invokePlanner, pollForResults, synthesizeResults, newCorrelationId,
} from '@/lib/deepResearch'

export const maxDuration = 300
export const dynamic     = 'force-dynamic'

type Routing = {
  route:      'fast' | 'deep' | 'chat' | 'debater'
  deep_kind?: 'mcp' | 'parallel' | null
  intent?:    string
  entities?:  string[]
  debater?:   string
  reasoning?: string
  confidence?: number
  uses_mcp?:  boolean
}

function sse(data: object) {
  return `data: ${JSON.stringify(data)}\n\n`
}

async function pipeEcsStream(
  ecsUrl: string,
  path: string,
  body: object,
  controller: ReadableStreamDefaultController<Uint8Array>,
  encoder: TextEncoder,
) {
  const res = await fetch(`${ecsUrl}${path}`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  })
  if (!res.ok || !res.body) throw new Error(`ECS ${path} failed: ${res.status}`)

  const reader = res.body.getReader()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    controller.enqueue(value)
    controller.enqueue(encoder.encode(': \n\n'))
  }
}

function streamText(content: string, controller: ReadableStreamDefaultController<Uint8Array>, encoder: TextEncoder) {
  const words = content.split(' ')
  for (let i = 0; i < words.length; i += 4) {
    const chunk = words.slice(i, i + 4).join(' ') + (i + 4 < words.length ? ' ' : '')
    controller.enqueue(encoder.encode(sse({ type: 'token', content: chunk })))
  }
}

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return new Response('Unauthorized', { status: 401 })

  const body      = await req.json()
  const query     = body.query || body.topic || ''
  const sessionId = body.session_id || req.headers.get('x-session-id') || ''

  if (!query.trim()) return new Response('Missing query', { status: 400 })

  const ECS_URL = await getEcsUrl()
  if (!ECS_URL) return new Response('Service unavailable', { status: 503 })

  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    async start(controller) {
      const t0 = Date.now()
      try {
        // 1. Route query
        const routeRes = await fetch(`${ECS_URL}/research/route`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ topic: query, user_id: userId, session_id: sessionId }),
        })
        const routeData = await routeRes.json()
        const routing: Routing = routeData.routing || { route: 'chat' }
        const steps: string[]  = routeData.steps || []

        controller.enqueue(encoder.encode(sse({
          type: 'routing',
          routing,
          steps,
          display_route: routing.route === 'deep' ? 'deep' : routing.route,
        })))

        for (const step of steps) {
          controller.enqueue(encoder.encode(sse({ type: 'reasoning', content: step })))
        }

        // 2. Dispatch
        if (routing.route === 'debater') {
          await pipeEcsStream(
            ECS_URL, '/research/debater/stream',
            {
              topic: query, user_id: userId, session_id: sessionId,
              debater: routing.debater,
              ticker:  routing.entities?.[0],
            },
            controller, encoder,
          )

        } else if (routing.route === 'chat') {
          await pipeEcsStream(
            ECS_URL, '/research/conversation/stream',
            { topic: query, user_id: userId, session_id: sessionId, intent: routing.intent },
            controller, encoder,
          )

        } else if (routing.route === 'deep' && routing.deep_kind === 'parallel') {
          controller.enqueue(encoder.encode(sse({ type: 'reasoning', content: '🔍 Deep Research — decomposing into parallel tasks...' })))

          const correlationId = newCorrelationId()
          const { tasks, taskCount } = await invokePlanner(query, userId, sessionId, correlationId)

          for (let i = 0; i < tasks.length; i++) {
            controller.enqueue(encoder.encode(sse({
              type: 'reasoning',
              content: `⏳ Task ${i + 1}/${tasks.length}: ${tasks[i].substring(0, 70)}...`,
            })))
          }

          const { results, timedOut } = await pollForResults(taskCount, correlationId)
          const synthesized = synthesizeResults(query, tasks, results, timedOut)

          controller.enqueue(encoder.encode(sse({ type: 'reasoning_done' })))
          streamText(synthesized, controller, encoder)
          controller.enqueue(encoder.encode(sse({
            type: 'done',
            route:      'deep',
            deep_kind:  'parallel',
            latency:    (Date.now() - t0) / 1000,
            timedOut,
          })))

        } else if (routing.route === 'deep') {
          controller.enqueue(encoder.encode(sse({
            type: 'reasoning',
            content: '🔍 Deep Research — connecting SEC EDGAR via MCP...',
          })))
          await pipeEcsStream(
            ECS_URL, '/research/deep/stream',
            { topic: query, user_id: userId, session_id: sessionId },
            controller, encoder,
          )

        } else {
          controller.enqueue(encoder.encode(sse({
            type: 'reasoning',
            content: '⚡ Fast Research — fetching live market data...',
          })))
          await pipeEcsStream(
            ECS_URL, '/research/stream',
            { topic: query, user_id: userId, session_id: sessionId },
            controller, encoder,
          )
        }

        controller.close()
      } catch (err: any) {
        console.error('Alex chat error:', err)
        controller.enqueue(encoder.encode(sse({ type: 'error', content: err.message || 'Chat failed' })))
        controller.close()
      }
    },
  })

  return new Response(stream, {
    status: 200,
    headers: {
      'Content-Type':                'text/event-stream; charset=utf-8',
      'Cache-Control':               'no-cache, no-store, no-transform',
      'Connection':                  'keep-alive',
      'X-Accel-Buffering':           'no',
      'Access-Control-Allow-Origin': '*',
    },
  })
}
