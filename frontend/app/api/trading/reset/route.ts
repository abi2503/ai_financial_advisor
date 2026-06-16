import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import { resetTradingDebateContext } from '@/lib/tradingDb'

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const body = await req.json().catch(() => ({}))
  if (!body.confirm) {
    return NextResponse.json(
      { error: 'Confirmation required. Send { confirm: true } to reset debate context.' },
      { status: 400 },
    )
  }

  try {
    const result = await resetTradingDebateContext(userId, body.mode || 'neutral')
    return NextResponse.json({
      success: true,
      message: result.simulation_id
        ? `Debate context reset. Fresh simulation seeded with ${result.positions_seeded} position(s) from your portfolio.`
        : 'Debate context cleared. Add portfolio holdings to seed a new simulation.',
      ...result,
    })
  } catch (error) {
    console.error('Trading reset error:', error)
    return NextResponse.json({ error: 'Failed to reset debate context' }, { status: 500 })
  }
}
