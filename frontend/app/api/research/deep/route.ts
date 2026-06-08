import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'

const ECS_URL = process.env.ECS_URL || process.env.NEXT_PUBLIC_ECS_URL || ''

export async function POST(req: NextRequest) {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { topic } = await req.json()
    if (!topic) {
      return NextResponse.json({ error: 'Missing topic' }, { status: 400 })
    }

    console.log(`Deep research from ${userId}: ${topic}`)

    // Deep research can take 3-5 minutes
    const controller = new AbortController()
    const timeout    = setTimeout(() => controller.abort(), 280000) // 4.5 min

    try {
      const ecsResponse = await fetch(`${ECS_URL}/research/deep`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ topic }),
        signal:  controller.signal
      })

      clearTimeout(timeout)

      if (!ecsResponse.ok) {
        const text = await ecsResponse.text()
        console.error(`ECS deep error: ${ecsResponse.status} ${text}`)
        return NextResponse.json(
          { error: `Deep research service error: ${ecsResponse.status}` },
          { status: 500 }
        )
      }

      const data = await ecsResponse.json()
      return NextResponse.json({
        status: 'success',
        result: data.result || data.detail || 'Deep research complete'
      })

    } catch (fetchErr: any) {
      clearTimeout(timeout)
      if (fetchErr.name === 'AbortError') {
        return NextResponse.json(
          { error: 'Deep research timed out — SEC filings can take 5+ minutes. Try a more specific query.' },
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