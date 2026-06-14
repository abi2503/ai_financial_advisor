import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data'

const rds = new RDSDataClient({ region: process.env.AWS_REGION || 'us-east-1' })

const DB = {
  resourceArn: process.env.DB_CLUSTER_ARN!,
  secretArn:   process.env.DB_SECRET_ARN!,
  database:    process.env.DB_NAME || 'alex_db',
}

async function executeWithRetry(command: ExecuteStatementCommand, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      return await rds.send(command)
    } catch (err: any) {
      if ((err.name === 'DatabaseResumingException' || err.message?.includes('resuming')) && i < retries - 1) {
        await new Promise(r => setTimeout(r, 8000))
      } else {
        throw err
      }
    }
  }
  throw new Error('Aurora failed')
}

async function ensureUser(clerkId: string) {
  await executeWithRetry(new ExecuteStatementCommand({
    ...DB,
    sql: `
      INSERT INTO users (clerk_id, email, name)
      VALUES (:cid, '', 'User')
      ON CONFLICT (clerk_id) DO UPDATE SET updated_at = NOW()
    `,
    parameters: [{ name: 'cid', value: { stringValue: clerkId } }],
  }))
}

export async function GET(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const sessionId = req.nextUrl.searchParams.get('session_id') || ''
  if (!sessionId) return NextResponse.json({ messages: [] })

  try {
    const result = await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
      sql: `
        SELECT cs.messages::text FROM chat_sessions cs
        JOIN users u ON u.id = cs.user_id
        WHERE cs.session_id = :sid AND u.clerk_id = :uid
        LIMIT 1
      `,
      parameters: [
        { name: 'sid', value: { stringValue: sessionId } },
        { name: 'uid', value: { stringValue: userId } },
      ],
    }))

    const raw = result.records?.[0]?.[0]?.stringValue || '[]'
    const messages = JSON.parse(raw)
    return NextResponse.json({ messages, session_id: sessionId })
  } catch (e) {
    console.error('Session load error:', e)
    return NextResponse.json({ messages: [], session_id: sessionId })
  }
}

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const body = await req.json()
  const sessionId = body.session_id || ''
  const messages  = body.messages || []

  if (!sessionId || !Array.isArray(messages)) {
    return NextResponse.json({ error: 'session_id and messages required' }, { status: 400 })
  }

  try {
    await ensureUser(userId)
    const trimmed = messages.slice(-30).map((m: any) => ({
      role:    m.role,
      content: (m.content || '').slice(0, 2000),
      time:    m.time || '',
      mode:    m.mode || '',
    }))
    const payload = JSON.stringify(trimmed)

    const existing = await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
      sql: `
        SELECT cs.id::text FROM chat_sessions cs
        JOIN users u ON u.id = cs.user_id
        WHERE cs.session_id = :sid AND u.clerk_id = :uid LIMIT 1
      `,
      parameters: [
        { name: 'sid', value: { stringValue: sessionId } },
        { name: 'uid', value: { stringValue: userId } },
      ],
    }))

    if (existing.records?.length) {
      await executeWithRetry(new ExecuteStatementCommand({
        ...DB,
        sql: `
          UPDATE chat_sessions cs SET messages = :msgs::jsonb, updated_at = NOW()
          FROM users u
          WHERE cs.user_id = u.id AND cs.session_id = :sid AND u.clerk_id = :uid
        `,
        parameters: [
          { name: 'msgs', value: { stringValue: payload } },
          { name: 'sid',  value: { stringValue: sessionId } },
          { name: 'uid',  value: { stringValue: userId } },
        ],
      }))
    } else {
      await executeWithRetry(new ExecuteStatementCommand({
        ...DB,
        sql: `
          INSERT INTO chat_sessions (user_id, session_id, messages)
          SELECT id, :sid, :msgs::jsonb FROM users WHERE clerk_id = :uid
        `,
        parameters: [
          { name: 'sid',  value: { stringValue: sessionId } },
          { name: 'msgs', value: { stringValue: payload } },
          { name: 'uid',  value: { stringValue: userId } },
        ],
      }))
    }

    return NextResponse.json({ ok: true, count: trimmed.length })
  } catch (e) {
    console.error('Session save error:', e)
    return NextResponse.json({ error: 'Save failed' }, { status: 500 })
  }
}
