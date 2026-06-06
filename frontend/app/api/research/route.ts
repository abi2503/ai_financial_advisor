import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'

const ECS_URL = process.env.ECS_URL || process.env.NEXT_PUBLIC_ECS_URL || ''

export async function POST(req: NextRequest) {
  try {
    // Verify user is logged in
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    // Get research topic from request
    const body = await req.json()
    const { topic } = body

    if (!topic) {
      return NextResponse.json(
        { error: 'Missing topic' },
        { status: 400 }
      )
    }

    console.log(`Research request from ${userId}: ${topic}`)

    // Call ECS researcher agent
    // This runs server-side so no CORS issues
    const ecsResponse = await fetch(`${ECS_URL}/research`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ topic }),
      signal:  AbortSignal.timeout(120000) // 2 min timeout
    })

    if (!ecsResponse.ok) {
      console.error(`ECS error: ${ecsResponse.status}`)
      return NextResponse.json(
        { error: 'Research service error' },
        { status: 500 }
      )
    }

    const data = await ecsResponse.json()
    console.log(`Research complete for ${userId}`)

    // Save to Aurora
    try {
      await saveResearchSession(userId, topic, data.result || '')
    } catch (dbError) {
      // Don't fail the request if DB save fails
      console.error('DB save error:', dbError)
    }

    return NextResponse.json({
      status: 'success',
      result: data.result || data.body || 'Research complete'
    })

  } catch (error: any) {
    console.error('Research route error:', error)

    if (error.name === 'TimeoutError') {
      return NextResponse.json(
        { error: 'Research timed out — try a simpler query' },
        { status: 408 }
      )
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

async function saveResearchSession(
  userId: string,
  topic:  string,
  result: string
) {
  const { RDSDataClient, ExecuteStatementCommand } = await import('@aws-sdk/client-rds-data')

  const client = new RDSDataClient({ region: process.env.AWS_REGION || 'ueast-1' })

  // First get or create user
  const userResult = await client.send(new ExecuteStatementCommand({
    resourceArn: process.env.DB_CLUSTER_ARN,
    secretArn:   process.env.DB_SECRET_ARN,
    database:    process.env.DB_NAME || 'alex_db',
    sql: `
      INSERT INTO users (clerk_id, email, name)
      VALUES (:clerk_id, :email, :name)
      ON CONFLICT (clerk_id) DO UPDATE SET updated_at = NOW()
      RETURNING id
    `,
    parameters: [
      { name: 'clerk_id', value: { stringValue: userId } },
      { name: 'email',    value: { stringValue: '' } },
      { name: 'name',     value: { stringValue: '' } },
    ]
  }))

  const dbUserId = userResult.records?.[0]?.[0]?.stringValue
  if (!dbUserId) return

  // Save research session
  await client.send(new ExecuteStatementCommand({
    resourceArn: process.env.DB_CLUSTER_ARN,
    secretArn:   process.env.DB_SECRET_ARN,
    database:    process.env.DB_NAME || 'alex_db',
    sql: `
      INSERT INTO research_sessions (user_id, topic, result)
      VALUES (:user_id::uuid, :topic, :result)
    `,
    parameters: [
      { name: 'user_id', value: { stringValue: dbUserId } },
      { name: 'topic',   value: { stringValue: topic } },
      { name: 'result',  value: { stringValue: result.substring(0, 10000) } },
    ]
  }))

  console.log(`Saved research session for user ${dbUserId}`)
}
