import { auth } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'
import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data'

const rds = new RDSDataClient({ region: process.env.AWS_REGION || 'us-east-1' })

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
  throw new Error('Aurora query failed')
}

export async function GET() {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  try {
    const [costResult, opsResult, alertsResult] = await Promise.all([
      executeWithRetry(new ExecuteStatementCommand({
        ...DB,
        sql: `
          SELECT snapshot_date::text, total_cost, service_costs, digest
          FROM cost_snapshots ORDER BY snapshot_date DESC LIMIT 7
        `,
      })),
      executeWithRetry(new ExecuteStatementCommand({
        ...DB,
        sql: `
          SELECT snapshot_time::text, health_status::text, daily_cost, digest
          FROM ops_snapshots ORDER BY snapshot_time DESC LIMIT 1
        `,
      })),
      executeWithRetry(new ExecuteStatementCommand({
        ...DB,
        sql: `
          SELECT alert_date::text, daily_spend, threshold, message
          FROM cost_alerts ORDER BY sent_at DESC LIMIT 5
        `,
      })),
    ])

    const snapshots = (costResult.records || []).map(row => ({
      date:     row[0]?.stringValue || '',
      total:    parseNumber(row[1]),
      services: JSON.parse(row[2]?.stringValue || '{}'),
      digest:   row[3]?.stringValue || '',
    }))

    let ops: Record<string, unknown> | null = null
    const opsRow = opsResult.records?.[0]
    if (opsRow) {
      let health: Record<string, unknown> = {}
      try {
        health = JSON.parse(opsRow[1]?.stringValue || '{}')
      } catch { /* */ }
      ops = {
        last_run:    opsRow[0]?.stringValue || '',
        daily_cost:  parseNumber(opsRow[2]),
        digest:      opsRow[3]?.stringValue || '',
        health,
      }
    }

    const alerts = (alertsResult.records || []).map(row => ({
      date:      row[0]?.stringValue || '',
      spend:     parseNumber(row[1]),
      threshold: parseNumber(row[2]),
      message:   row[3]?.stringValue || '',
    }))

    const todayStr  = new Date().toISOString().split('T')[0]
    const todaySnap = snapshots.find(s => s.date === todayStr) || snapshots[0]
    const weekTotal = snapshots.reduce((sum, s) => sum + s.total, 0)
    const mtdTotal  = (ops?.health as any)?.mtd?.total ?? 0
    const healthDetail = ((ops?.health as any)?.health_detail || []) as {
      service: string; status: string; detail?: string
    }[]

    return NextResponse.json({
      snapshots,
      alerts,
      latest:       todaySnap || null,
      weeklyTotal:  weekTotal,
      mtdTotal,
      ops,
      health:       healthDetail,
      healthScore:  healthDetail.length
        ? Math.round((healthDetail.filter(h => h.status === 'healthy').length / healthDetail.length) * 100)
        : null,
      pollIntervalMs: 30 * 60 * 1000,
      updatedAt:      ops?.last_run || todaySnap?.date || null,
    })
  } catch (err) {
    console.error('Ops API error:', err)
    return NextResponse.json({
      snapshots: [], alerts: [], latest: null, weeklyTotal: 0, mtdTotal: 0,
      ops: null, health: [], healthScore: null, pollIntervalMs: 1800000, updatedAt: null,
    })
  }
}
