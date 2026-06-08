import { auth } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'
import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data'

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

export async function GET() {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const userResult = await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
      sql: `SELECT id FROM users WHERE clerk_id = :clerk_id LIMIT 1`,
      parameters: [{ name: 'clerk_id', value: { stringValue: userId } }]
    })) as any

    const dbUserId = userResult.records?.[0]?.[0]?.stringValue
    if (!dbUserId) {
      return NextResponse.json({ history: [] })
    }

    const result = await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
      sql: `
        SELECT id, topic, result, created_at
        FROM research_sessions
        WHERE user_id = :user_id::uuid
        ORDER BY created_at DESC
        LIMIT 20
      `,
      parameters: [{ name: 'user_id', value: { stringValue: dbUserId } }]
    })) as any

    const history = (result.records || []).map((r: any) => ({
      id:         r[0]?.stringValue,
      topic:      r[1]?.stringValue,
      result:     r[2]?.stringValue,
      created_at: r[3]?.stringValue,
    }))

    return NextResponse.json({ history })

  } catch (error: any) {
    console.error('History GET error:', error)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}