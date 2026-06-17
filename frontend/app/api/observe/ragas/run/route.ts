import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { getEcsUrl } from '@/lib/config'

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  let smoke = false
  try {
    const body = await req.json()
    smoke = Boolean(body?.smoke)
  } catch {
    /* default smoke=false */
  }

  const ECS_URL = await getEcsUrl()
  if (!ECS_URL) {
    return NextResponse.json({ error: 'Research service not available' }, { status: 503 })
  }

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 600000)

  try {
    const ecsResponse = await fetch(`${ECS_URL}/eval/ragas/run`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ gate: 'observe', smoke }),
      signal:  controller.signal,
    })

    clearTimeout(timeout)
    const data = await ecsResponse.json().catch(() => ({}))

    // 422 = eval completed but quality gate failed — still return scores
    if (ecsResponse.status === 422) {
      return NextResponse.json({ status: 'failed', ...data })
    }

    if (!ecsResponse.ok) {
      return NextResponse.json(
        { error: data.detail || data.error || `RAGAS eval failed (${ecsResponse.status})`, ...data },
        { status: ecsResponse.status },
      )
    }

    return NextResponse.json({ status: 'ok', ...data })
  } catch (err: any) {
    clearTimeout(timeout)
    if (err.name === 'AbortError') {
      return NextResponse.json({ error: 'RAGAS eval timed out (10 min limit)' }, { status: 408 })
    }
    console.error('RAGAS run proxy error:', err)
    return NextResponse.json({ error: err.message || 'RAGAS eval failed' }, { status: 500 })
  }
}
