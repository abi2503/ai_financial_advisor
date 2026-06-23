import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import { SSMClient, PutParameterCommand, GetParameterCommand } from '@aws-sdk/client-ssm'
import { resetTradingDebateContext } from '@/lib/tradingDb'

const ssm = new SSMClient({ region: 'us-east-1' })

export async function GET() {
  try {
    const result = await ssm.send(new GetParameterCommand({ Name: '/alex/trading/enabled' }))
    return NextResponse.json({ enabled: result.Parameter?.Value === 'true' })
  } catch {
    return NextResponse.json({ enabled: false })
  }
}

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const body = await req.json().catch(() => ({}))
  const enabled = Boolean(body.enabled)
  const resetContext = Boolean(body.reset_context)

  try {
    let resetResult = null
    if (enabled && resetContext) {
      resetResult = await resetTradingDebateContext(userId)
    }

    await ssm.send(new PutParameterCommand({
      Name:      '/alex/trading/enabled',
      Value:     enabled ? 'true' : 'false',
      Type:      'String',
      Overwrite: true,
    }))

    return NextResponse.json({
      enabled,
      reset_context: resetContext && enabled,
      reset: resetResult,
    })
  } catch (error) {
    console.error('Trading toggle error:', error)
    return NextResponse.json({ error: 'Failed to update trading toggle' }, { status: 500 })
  }
}
