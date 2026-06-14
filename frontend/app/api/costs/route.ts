import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data'
import { LambdaClient, InvokeCommand } from '@aws-sdk/client-lambda'

const rds    = new RDSDataClient({ region: process.env.AWS_REGION || 'us-east-1' })
const lambda = new LambdaClient({ region: process.env.AWS_REGION || 'us-east-1' })

const DB = {
  resourceArn: process.env.DB_CLUSTER_ARN!,
  secretArn:   process.env.DB_SECRET_ARN!,
  database:    process.env.DB_NAME || 'alex_db',
}

function parseNumber(field: any): number {
  if (!field) return 0
  if (field.doubleValue !== undefined) return Number(field.doubleValue)
  if (field.longValue !== undefined) return Number(field.longValue)
  return parseFloat(field.stringValue || '0') || 0
}

export async function GET(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  try {
    const result = await rds.send(new ExecuteStatementCommand({
      ...DB,
      sql: `
        SELECT snapshot_date::text, total_cost, service_costs, digest
        FROM cost_snapshots
        ORDER BY snapshot_date DESC
        LIMIT 7
      `
    }))

    const snapshots = (result.records || []).map(row => ({
      date:     row[0]?.stringValue || '',
      total:    parseNumber(row[1]),
      services: JSON.parse(row[2]?.stringValue || '{}'),
      digest:   row[3]?.stringValue || ''
    }))

    const alerts = await rds.send(new ExecuteStatementCommand({
      ...DB,
      sql: `
        SELECT alert_date::text, daily_spend, threshold, message
        FROM cost_alerts
        ORDER BY sent_at DESC
        LIMIT 5
      `
    }))

    const alertsList = (alerts.records || []).map(row => ({
      date:      row[0]?.stringValue || '',
      spend:     parseNumber(row[1]),
      threshold: parseNumber(row[2]),
      message:   row[3]?.stringValue || ''
    }))

    const todayStr = new Date().toISOString().split('T')[0]
    const todaySnap = snapshots.find(s => s.date === todayStr) || snapshots[0]

    return NextResponse.json({
      snapshots,
      alerts:      alertsList,
      latest:      todaySnap || null,
      weeklyTotal: snapshots.reduce((sum, s) => sum + s.total, 0)
    })

  } catch (err) {
    console.error('Costs API error:', err)
    return NextResponse.json({ snapshots: [], alerts: [], latest: null, weeklyTotal: 0 })
  }
}

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  try {
    const response = await lambda.send(new InvokeCommand({
      FunctionName:   'alex-cost-monitor',
      InvocationType: 'RequestResponse',
      Payload:        Buffer.from(JSON.stringify({ source: 'manual' }))
    }))

    const result = JSON.parse(Buffer.from(response.Payload!).toString())
    const body   = JSON.parse(result.body || '{}')

    return NextResponse.json({ success: true, ...body })
  } catch (err) {
    return NextResponse.json({ error: 'Failed to run cost monitor' }, { status: 500 })
  }
}
