import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { LambdaClient, InvokeCommand } from '@aws-sdk/client-lambda'

const lambda = new LambdaClient({ region: 'us-east-1' })

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  let horizon = 5
  try {
    const body = await req.json()
    horizon = Number(body?.horizon_days) || 5
  } catch {
    /* default */
  }

  try {
    const result = await lambda.send(new InvokeCommand({
      FunctionName: process.env.TRADING_EVAL_LAMBDA || 'alex-trade-evaluator',
      Payload: JSON.stringify({ gate: 'observe', horizon_days: horizon }),
    }))

    const response = JSON.parse(new TextDecoder().decode(result.Payload))
    const body = typeof response.body === 'string' ? JSON.parse(response.body) : response

    if (response.statusCode && response.statusCode >= 400) {
      return NextResponse.json(
        { error: 'Outcome eval failed', ...body },
        { status: response.statusCode },
      )
    }

    return NextResponse.json({ status: 'ok', ...body })
  } catch (error: any) {
    console.error('Trading eval invoke error:', error)
    if (error.name === 'ResourceNotFoundException') {
      return NextResponse.json({
        error: 'alex-trade-evaluator Lambda not deployed yet. Run terraform apply in terraform/9_trading_floor.',
      }, { status: 503 })
    }
    return NextResponse.json({ error: error.message || 'Outcome eval failed' }, { status: 500 })
  }
}
