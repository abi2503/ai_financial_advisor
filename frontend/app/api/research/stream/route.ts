import { auth } from '@clerk/nextjs/server'
import { NextRequest } from 'next/server'
import { getEcsUrl } from '@/lib/config'

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) {
    return new Response('Unauthorized', { status: 401 })
  }

  const { topic } = await req.json()
  if (!topic) {
    return new Response('Missing topic', { status: 400 })
  }

  const ECS_URL = await getEcsUrl()
  if (!ECS_URL) {
    return new Response('Research service unavailable', { status: 503 })
  }

  // Forward SSE stream from ECS to browser
  const ecsResponse = await fetch(`${ECS_URL}/research/stream`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ topic }),
    signal:  AbortSignal.timeout(180000)
  })

  if (!ecsResponse.ok || !ecsResponse.body) {
    return new Response('Stream error', { status: 500 })
  }

  // Pass stream directly to browser
  return new Response(ecsResponse.body, {
    headers: {
      'Content-Type':                'text/event-stream',
      'Cache-Control':               'no-cache',
      'Connection':                  'keep-alive',
      'Access-Control-Allow-Origin': '*',
    }
  })
}