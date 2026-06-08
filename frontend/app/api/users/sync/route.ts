import { auth, currentUser } from '@clerk/nextjs/server'
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

export async function POST() {
  try {
    const { userId } = await auth()

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const user  = await currentUser()
    const email = user?.emailAddresses?.[0]?.emailAddress || ''
    const name  = `${user?.firstName || ''} ${user?.lastName || ''}`.trim()

    const result = await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
      sql: `
        INSERT INTO users (clerk_id, email, name)
        VALUES (:clerk_id, :email, :name)
        ON CONFLICT (clerk_id) DO UPDATE
          SET email      = EXCLUDED.email,
              name       = EXCLUDED.name,
              updated_at = NOW()
        RETURNING id, clerk_id, email, name
      `,
      parameters: [
        { name: 'clerk_id', value: { stringValue: userId } },
        { name: 'email',    value: { stringValue: email } },
        { name: 'name',     value: { stringValue: name } },
      ]
    })) as any

    const record = result.records?.[0]
    const dbUser = {
      id:       record?.[0]?.stringValue,
      clerk_id: record?.[1]?.stringValue,
      email:    record?.[2]?.stringValue,
      name:     record?.[3]?.stringValue,
    }

    console.log(`User synced: ${userId} → ${dbUser.id}`)
    return NextResponse.json({ success: true, user: dbUser })

  } catch (error: any) {
    console.error('User sync error:', error)
    return NextResponse.json({ error: error.message || 'Sync failed' }, { status: 500 })
  }
}