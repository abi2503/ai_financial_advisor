import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data'
import { getEcsUrl } from '@/lib/config'

const rds = new RDSDataClient({ region: process.env.AWS_REGION || 'us-east-1' })

const DB = {
  resourceArn: process.env.DB_CLUSTER_ARN!,
  secretArn:   process.env.DB_SECRET_ARN!,
  database:    process.env.DB_NAME || 'alex_db',
}

async function executeWithRetry(command: any, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      return await rds.send(command)
    } catch (err: any) {
      if (err.name === 'DatabaseResumingException' && i < retries - 1) {
        console.log(`Aurora resuming — waiting 30s (attempt ${i + 1}/${retries})`)
        await new Promise(r => setTimeout(r, 30000))
      } else {
        throw err
      }
    }
  }
}

async function saveResearchSession(
  userId: string,
  topic:  string,
  result: string
) {
  try {
    const userResult = await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
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
    })) as any

    const dbUserId = userResult.records?.[0]?.[0]?.stringValue
    if (!dbUserId) return

    await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
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

    console.log(`Saved session for ${dbUserId}`)
  } catch (err) {
    console.error('DB save error:', err)
  }
}

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

    // Get ECS URL from SSM — auto-updates after every deploy
    const ECS_URL = await getEcsUrl()
    if (!ECS_URL) {
      return NextResponse.json(
        { error: 'Research service not available' },
        { status: 503 }
      )
    }

    console.log(`Research from ${userId}: ${topic}`)
    console.log(`ECS URL: ${ECS_URL}`)

    const ecsResponse = await fetch(`${ECS_URL}/research`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ topic }),
      signal:  AbortSignal.timeout(120000)
    })

    if (!ecsResponse.ok) {
      return NextResponse.json(
        { error: 'Research service error' },
        { status: 500 }
      )
    }

    const data = await ecsResponse.json()

    await saveResearchSession(userId, topic, data.result || '')

    return NextResponse.json({
      status: 'success',
      result: data.result || 'Research complete'
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