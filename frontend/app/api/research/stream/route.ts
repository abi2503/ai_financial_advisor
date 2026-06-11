import { auth } from '@clerk/nextjs/server'
import { NextRequest } from 'next/server'
import { getEcsUrl } from '@/lib/config'

export const maxDuration = 300
export const dynamic     = 'force-dynamic'

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return new Response('Unauthorized', { status: 401 })

  const body      = await req.json()
  const topic     = body.topic
  const sessionId = body.session_id || req.headers.get('x-session-id') || ''

  if (!topic)    return new Response('Missing topic', { status: 400 })

  const ECS_URL = await getEcsUrl()
  if (!ECS_URL) return new Response('Service unavailable', { status: 503 })

  try {
    const ecsResponse = await fetch(`${ECS_URL}/research/stream`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        topic,
        user_id:    userId,
        session_id: sessionId
      }),
    })

    if (!ecsResponse.ok || !ecsResponse.body) {
      return new Response('Stream error', { status: 500 })
    }

    const reader = ecsResponse.body.getReader()
    const stream = new ReadableStream({
      async start(controller) {
        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) { controller.close(); break }
            controller.enqueue(value)
          }
        } catch (err) {
          controller.error(err)
        }
      },
      cancel() { reader.cancel() }
    })

    return new Response(stream, {
      status:  200,
      headers: {
        'Content-Type':                'text/event-stream',
        'Cache-Control':               'no-cache, no-transform',
        'Connection':                  'keep-alive',
        'X-Accel-Buffering':           'no',
        'Access-Control-Allow-Origin': '*',
      }
    })

  } catch (err: any) {
    console.error('Stream route error:', err)
    return new Response('Stream failed', { status: 500 })
  }
}