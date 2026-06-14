import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { getEcsUrl } from '@/lib/config'

export async function POST(req: NextRequest) {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body      = await req.json()
    const topic     = body.topic
    const sessionId = body.session_id || req.headers.get('x-session-id') || ''

    if (!topic) {
      return NextResponse.json({ error: 'Missing topic' }, { status: 400 })
    }

    // Get ECS URL from SSM
    const ECS_URL = await getEcsUrl()
    if (!ECS_URL) {
      return NextResponse.json(
        { error: 'Research service not available' },
        { status: 503 }
      )
    }

    console.log(`Deep research from ${userId}: ${topic}`)

    const controller = new AbortController()
    const timeout    = setTimeout(() => controller.abort(), 280000)

    try {
      const ecsResponse = await fetch(`${ECS_URL}/research/deep`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          topic,
          user_id:    userId,
          session_id: sessionId,
        }),
        signal:  controller.signal
      })

      clearTimeout(timeout)

      if (!ecsResponse.ok) {
        return NextResponse.json(
          { error: `Deep research error: ${ecsResponse.status}` },
          { status: 500 }
        )
      }

      const data = await ecsResponse.json()
      return NextResponse.json({
        status: 'success',
        result: data.result || 'Deep research complete'
      })

    } catch (fetchErr: any) {
      clearTimeout(timeout)
      if (fetchErr.name === 'AbortError') {
        return NextResponse.json(
          { error: 'Deep research timed out — try a more specific query' },
          { status: 408 }
        )
      }
      throw fetchErr
    }

  } catch (error: any) {
    console.error('Deep research error:', error)
    return NextResponse.json(
      { error: error.message || 'Deep research failed' },
      { status: 500 }
    )
  }
}