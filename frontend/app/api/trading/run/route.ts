import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import { LambdaClient, InvokeCommand } from '@aws-sdk/client-lambda'

const lambda = new LambdaClient({ region: 'us-east-1' })

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  try {
    const result = await lambda.send(new InvokeCommand({
      FunctionName: 'alex-trading-orchestrator',
      Payload: JSON.stringify({
        trigger: 'manual',
        user_id: userId,
        force:   true
      })
    }))

    const raw = JSON.parse(new TextDecoder().decode(result.Payload || new Uint8Array()))
    if (raw.errorMessage || raw.errorType) {
      console.error('Orchestrator Lambda error:', raw.errorMessage)
      return NextResponse.json(
        { error: raw.errorMessage || 'Trading orchestrator failed' },
        { status: 500 },
      )
    }

    const body = typeof raw.body === 'string' ? JSON.parse(raw.body) : raw.body || raw

    return NextResponse.json({
      success: true,
      queued:  body.results?.[0]?.queued || [],
      message: `Analyzing ${body.results?.[0]?.queued?.length || 0} positions...`
    })
  } catch (error) {
    console.error('Run trading error:', error)
    return NextResponse.json({ error: 'Failed to start analysis' }, { status: 500 })
  }
}
