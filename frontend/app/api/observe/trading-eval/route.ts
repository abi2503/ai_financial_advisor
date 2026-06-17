import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data'

const rds = new RDSDataClient({ region: 'us-east-1' })
const CLUSTER_ARN = process.env.DB_CLUSTER_ARN!
const SECRET_ARN  = process.env.DB_SECRET_ARN!
const DB_NAME     = 'alex_db'

async function executeWithRetry(sql: string, parameters: any[] = []) {
  for (let i = 0; i < 5; i++) {
    try {
      return await rds.send(new ExecuteStatementCommand({
        resourceArn: CLUSTER_ARN,
        secretArn:   SECRET_ARN,
        database:    DB_NAME,
        sql,
        parameters,
      }))
    } catch (e: any) {
      if (e.name === 'DatabaseResumingException' || e.message?.includes('resuming')) {
        await new Promise(r => setTimeout(r, 8000))
      } else {
        throw e
      }
    }
  }
  throw new Error('Aurora failed after retries')
}

function val(field: any): any {
  if (!field) return null
  return Object.values(field)[0] ?? null
}

function num(v: unknown): number {
  if (v == null) return 0
  return parseFloat(String(v)) || 0
}

function bool(v: unknown): boolean {
  if (typeof v === 'boolean') return v
  return v === true || v === 'true'
}

export async function GET(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const runId = req.nextUrl.searchParams.get('run_id')

  try {
    const latestResult = await executeWithRetry(`
      SELECT
        id::text, gate, horizon_days, trades_evaluated, trades_pending, trades_skipped,
        overall_accuracy, buy_accuracy, sell_accuracy, hold_neutral_rate,
        avg_pnl_pct, passed, evaluated_at::text
      FROM trading_eval_runs
      ORDER BY evaluated_at DESC
      LIMIT 1
    `)

    const latestRow = latestResult?.records?.[0]
    const latest = latestRow ? {
      run_id:             latestRow[0]?.stringValue,
      gate:               latestRow[1]?.stringValue,
      horizon_days:       parseInt(String(val(latestRow[2]) || 5)),
      trades_evaluated:   parseInt(String(val(latestRow[3]) || 0)),
      trades_pending:     parseInt(String(val(latestRow[4]) || 0)),
      trades_skipped:     parseInt(String(val(latestRow[5]) || 0)),
      overall_accuracy:   num(val(latestRow[6])),
      buy_accuracy:       num(val(latestRow[7])),
      sell_accuracy:      num(val(latestRow[8])),
      hold_neutral_rate:  num(val(latestRow[9])),
      avg_pnl_pct:        num(val(latestRow[10])),
      passed:             bool(latestRow[11]?.booleanValue),
      evaluated_at:       latestRow[12]?.stringValue,
    } : null

    const trendResult = await executeWithRetry(`
      SELECT
        id::text, evaluated_at::text, overall_accuracy, trades_evaluated, passed, gate
      FROM trading_eval_runs
      ORDER BY evaluated_at DESC
      LIMIT 10
    `)

    const trend = (trendResult?.records || []).map(row => ({
      run_id:           row[0]?.stringValue,
      evaluated_at:     row[1]?.stringValue,
      overall_accuracy: num(val(row[2])),
      trades_evaluated: parseInt(String(val(row[3]) || 0)),
      passed:           bool(row[4]?.booleanValue),
      gate:             row[5]?.stringValue,
    })).reverse()

    const targetRunId = runId || latest?.run_id
    let leaderboard: any[] = []
    let audits: any[] = []

    if (targetRunId) {
      const lbResult = await executeWithRetry(`
        SELECT
          agent_name,
          COUNT(*)::int as votes,
          SUM(CASE WHEN correct = true THEN 1 ELSE 0 END)::int as correct_count,
          SUM(CASE WHEN correct IS NOT NULL THEN 1 ELSE 0 END)::int as scored,
          ROUND(AVG(CASE WHEN correct = true THEN 1.0 WHEN correct = false THEN 0.0 ELSE NULL END), 3) as accuracy
        FROM agent_performance
        WHERE eval_run_id = :run_id::uuid
        GROUP BY agent_name
        ORDER BY accuracy DESC NULLS LAST
      `, [{ name: 'run_id', value: { stringValue: targetRunId } }])

      leaderboard = (lbResult?.records || []).map(row => ({
        agent_name:    row[0]?.stringValue,
        votes:         parseInt(String(val(row[1]) || 0)),
        correct_count: parseInt(String(val(row[2]) || 0)),
        scored:        parseInt(String(val(row[3]) || 0)),
        accuracy:      num(val(row[4])),
      }))

      const auditResult = await executeWithRetry(`
        SELECT
          st.id::text, st.ticker, st.action, st.outcome, st.realized_pnl,
          ap.return_pct, st.executed_at::text,
          ap.agent_name, ap.action as vote_action, ap.confidence, ap.correct, ap.outcome as vote_outcome
        FROM agent_performance ap
        JOIN simulated_trades st ON st.id = ap.trade_id
        WHERE ap.eval_run_id = :run_id::uuid
        ORDER BY st.executed_at DESC, ap.agent_name
      `, [{ name: 'run_id', value: { stringValue: targetRunId } }])

      const tradeMap = new Map<string, any>()
      for (const row of auditResult?.records || []) {
        const tradeId = row[0]?.stringValue
        if (!tradeId) continue
        if (!tradeMap.has(tradeId)) {
          tradeMap.set(tradeId, {
            trade_id:     tradeId,
            ticker:       row[1]?.stringValue,
            final_action: row[2]?.stringValue,
            outcome:      row[3]?.stringValue,
            realized_pnl: num(val(row[4])),
            return_pct:   num(val(row[5])),
            evaluated_at: row[6]?.stringValue,
            agent_votes:  [],
          })
        }
        tradeMap.get(tradeId).agent_votes.push({
          agent_name: row[7]?.stringValue,
          action:     row[8]?.stringValue,
          confidence: num(val(row[9])),
          correct:    row[10]?.booleanValue ?? null,
          outcome:    row[11]?.stringValue,
        })
      }
      audits = Array.from(tradeMap.values())
    }

    const pendingResult = await executeWithRetry(`
      SELECT COUNT(*)::int
      FROM simulated_trades
      WHERE outcome IS NULL
        AND executed_at <= NOW() - INTERVAL '5 days'
    `)
    const pending_mature = parseInt(String(val(pendingResult?.records?.[0]?.[0]) || 0))

    return NextResponse.json({
      latest,
      trend,
      leaderboard,
      audits,
      selected_run_id: targetRunId,
      pending_mature_trades: pending_mature,
      thresholds: { pass_accuracy: 0.50, horizon_days: 5 },
    })
  } catch (error) {
    console.error('Trading eval API error:', error)
    return NextResponse.json({
      latest: null,
      trend: [],
      leaderboard: [],
      audits: [],
      pending_mature_trades: 0,
      thresholds: { pass_accuracy: 0.50, horizon_days: 5 },
      error: 'DB unavailable',
    })
  }
}
