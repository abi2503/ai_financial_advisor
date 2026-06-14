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
        parameters
      }))
    } catch (e: any) {
      if (e.name === 'DatabaseResumingException' || e.message?.includes('resuming')) {
        console.log(`Aurora resuming, retry ${i+1}/5...`)
        await new Promise(r => setTimeout(r, 8000))
      } else {
        throw e
      }
    }
  }
  throw new Error('Aurora failed after 5 retries')
}

function parseVal(field: any): any {
  if (!field) return null
  return Object.values(field)[0] ?? null
}

function enrichPosition(row: {
  ticker: string
  shares: number
  avg_cost: number
  current_price: number
  current_value: number
  pnl: number
  pnl_pct: number
  last_action: string | null
}) {
  const shares       = row.shares || 0
  const avgCost      = row.avg_cost || 0
  const currentPrice = row.current_price || 0
  const costBasis    = shares * avgCost
  const marketValue  = shares * currentPrice
  const pnl          = marketValue - costBasis
  const pnlPct       = costBasis > 0 ? (pnl / costBasis) * 100 : 0
  return {
    ...row,
    cost_basis:    costBasis,
    current_value: marketValue,
    pnl,
    pnl_pct: pnlPct,
  }
}

export async function GET(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  try {
    const tradesResult = await executeWithRetry(
      `SELECT st.ticker, st.action, st.confidence, st.price,
              st.shares, st.total_value, st.rationale,
              st.agent_debate, st.mode, st.executed_at
       FROM simulated_trades st
       JOIN users u ON u.id = st.user_id
       WHERE u.clerk_id = :uid
       ORDER BY st.executed_at DESC LIMIT 20`,
      [{ name: 'uid', value: { stringValue: userId } }]
    )

    const trades = (tradesResult?.records || []).map(row => ({
      ticker:       parseVal(row[0]),
      action:       parseVal(row[1]),
      confidence:   parseFloat(String(parseVal(row[2]) || 0)),
      price:        parseFloat(String(parseVal(row[3]) || 0)),
      shares:       parseInt(String(parseVal(row[4]) || 0)),
      total_value:  parseFloat(String(parseVal(row[5]) || 0)),
      rationale:    parseVal(row[6]),
      agent_debate: JSON.parse(parseVal(row[7]) || '[]'),
      mode:         parseVal(row[8]),
      executed_at:  parseVal(row[9]),
    }))

    const posResult = await executeWithRetry(
      `SELECT ap.ticker, ap.shares, ap.avg_cost, ap.current_price,
              ap.current_value, ap.pnl, ap.pnl_pct, ap.last_action
       FROM agent_positions ap
       JOIN trading_simulations ts ON ts.id = ap.simulation_id
       JOIN users u ON u.id = ts.user_id
       WHERE u.clerk_id = :uid AND ts.status = 'active'
       ORDER BY ap.current_value DESC`,
      [{ name: 'uid', value: { stringValue: userId } }]
    )

    const positions = (posResult?.records || []).map(row => enrichPosition({
      ticker:        parseVal(row[0]),
      shares:        parseInt(String(parseVal(row[1]) || 0)),
      avg_cost:      parseFloat(String(parseVal(row[2]) || 0)),
      current_price: parseFloat(String(parseVal(row[3]) || 0)),
      current_value: parseFloat(String(parseVal(row[4]) || 0)),
      pnl:           parseFloat(String(parseVal(row[5]) || 0)),
      pnl_pct:       parseFloat(String(parseVal(row[6]) || 0)),
      last_action:   parseVal(row[7]),
    }))

    const simResult = await executeWithRetry(
      `SELECT ts.total_pnl, ts.total_trades, ts.win_count,
              ts.current_value, ts.mode
       FROM trading_simulations ts
       JOIN users u ON u.id = ts.user_id
       WHERE u.clerk_id = :uid AND ts.status = 'active'
       ORDER BY ts.started_at DESC LIMIT 1`,
      [{ name: 'uid', value: { stringValue: userId } }]
    )

    const portfolioSummary = {
      total_market_value: positions.reduce((s, p) => s + p.current_value, 0),
      total_cost_basis:   positions.reduce((s, p) => s + p.cost_basis, 0),
      total_pnl:          0,
      total_pnl_pct:      0,
      position_count:     positions.length,
    }
    portfolioSummary.total_pnl = portfolioSummary.total_market_value - portfolioSummary.total_cost_basis
    portfolioSummary.total_pnl_pct = portfolioSummary.total_cost_basis > 0
      ? (portfolioSummary.total_pnl / portfolioSummary.total_cost_basis) * 100
      : 0

    const sim = simResult?.records?.[0] ? {
      total_pnl:     parseFloat(String(parseVal(simResult.records[0][0]) || 0)),
      total_trades:  parseInt(String(parseVal(simResult.records[0][1]) || 0)),
      win_count:     parseInt(String(parseVal(simResult.records[0][2]) || 0)),
      current_value: positions.reduce((sum, p) => sum + p.current_value, 0) ||
                     parseFloat(String(parseVal(simResult.records[0][3]) || 0)),
      mode:          parseVal(simResult.records[0][4]),
    } : null

    return NextResponse.json({ trades, positions, simulation: sim, portfolio_summary: portfolioSummary })
  } catch (error) {
    console.error('Trading API error:', error)
    return NextResponse.json({ trades: [], positions: [], simulation: null, portfolio_summary: null, error: 'DB unavailable' })
  }
}
