import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data'

const rds = new RDSDataClient({ region: 'us-east-1' })
const CLUSTER_ARN = process.env.DB_CLUSTER_ARN!
const SECRET_ARN  = process.env.DB_SECRET_ARN!
const DB_NAME     = 'alex_db'

export async function GET(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  try {
    // Get recent trades with full debate
    const tradesResult = await rds.send(new ExecuteStatementCommand({
      resourceArn: CLUSTER_ARN,
      secretArn:   SECRET_ARN,
      database:    DB_NAME,
      sql: `SELECT st.ticker, st.action, st.confidence, st.price,
                   st.shares, st.total_value, st.rationale,
                   st.agent_debate, st.mode, st.executed_at
            FROM simulated_trades st
            JOIN users u ON u.id = st.user_id
            WHERE u.clerk_id = :uid
            ORDER BY st.executed_at DESC LIMIT 20`,
      parameters: [{ name: 'uid', value: { stringValue: userId } }]
    }))

    const trades = (tradesResult.records || []).map(row => ({
      ticker:      row[0]?.stringValue,
      action:      row[1]?.stringValue,
      confidence:  parseFloat(String(Object.values(row[2] || {})[0] || 0)),
      price:       parseFloat(String(Object.values(row[3] || {})[0] || 0)),
      shares:      parseInt(String(Object.values(row[4] || {})[0] || 0)),
      total_value: parseFloat(String(Object.values(row[5] || {})[0] || 0)),
      rationale:   row[6]?.stringValue,
      agent_debate: JSON.parse(row[7]?.stringValue || '[]'),
      mode:        row[8]?.stringValue,
      executed_at: row[9]?.stringValue,
    }))

    // Get positions
    const posResult = await rds.send(new ExecuteStatementCommand({
      resourceArn: CLUSTER_ARN,
      secretArn:   SECRET_ARN,
      database:    DB_NAME,
      sql: `SELECT ap.ticker, ap.shares, ap.avg_cost, ap.current_price,
                   ap.current_value, ap.pnl, ap.pnl_pct, ap.last_action
            FROM agent_positions ap
            JOIN trading_simulations ts ON ts.id = ap.simulation_id
            JOIN users u ON u.id = ts.user_id
            WHERE u.clerk_id = :uid AND ts.status = 'active'
            ORDER BY ap.current_value DESC`,
      parameters: [{ name: 'uid', value: { stringValue: userId } }]
    }))

    const positions = (posResult.records || []).map(row => ({
      ticker:        row[0]?.stringValue,
      shares:        parseInt(String(Object.values(row[1] || {})[0] || 0)),
      avg_cost:      parseFloat(String(Object.values(row[2] || {})[0] || 0)),
      current_price: parseFloat(String(Object.values(row[3] || {})[0] || 0)),
      current_value: parseFloat(String(Object.values(row[4] || {})[0] || 0)),
      pnl:           parseFloat(String(Object.values(row[5] || {})[0] || 0)),
      pnl_pct:       parseFloat(String(Object.values(row[6] || {})[0] || 0)),
      last_action:   row[7]?.stringValue,
    }))

    // Get simulation summary
    const simResult = await rds.send(new ExecuteStatementCommand({
      resourceArn: CLUSTER_ARN,
      secretArn:   SECRET_ARN,
      database:    DB_NAME,
      sql: `SELECT ts.total_pnl, ts.total_trades, ts.win_count,
                   ts.current_value, ts.mode
            FROM trading_simulations ts
            JOIN users u ON u.id = ts.user_id
            WHERE u.clerk_id = :uid AND ts.status = 'active'
            ORDER BY ts.started_at DESC LIMIT 1`,
      parameters: [{ name: 'uid', value: { stringValue: userId } }]
    }))

    const sim = simResult.records?.[0] ? {
      total_pnl:    parseFloat(String(Object.values(simResult.records[0][0] || {})[0] || 0)),
      total_trades: parseInt(String(Object.values(simResult.records[0][1] || {})[0] || 0)),
      win_count:    parseInt(String(Object.values(simResult.records[0][2] || {})[0] || 0)),
      current_value: parseFloat(String(Object.values(simResult.records[0][3] || {})[0] || 0)),
      mode:         simResult.records[0][4]?.stringValue,
    } : null

    return NextResponse.json({ trades, positions, simulation: sim })
  } catch (error) {
    console.error('Trading API error:', error)
    return NextResponse.json({ trades: [], positions: [], simulation: null })
  }
}
