import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data'

const rds = new RDSDataClient({ region: process.env.DEFAULT_AWS_REGION || 'us-east-1' })
const CLUSTER_ARN = process.env.DB_CLUSTER_ARN!
const SECRET_ARN = process.env.DB_SECRET_ARN!
const DB_NAME = 'alex_db'

export async function executeWithRetry(sql: string, parameters: any[] = []) {
  for (let i = 0; i < 5; i++) {
    try {
      return await rds.send(new ExecuteStatementCommand({
        resourceArn: CLUSTER_ARN,
        secretArn: SECRET_ARN,
        database: DB_NAME,
        sql,
        parameters,
      }))
    } catch (e: unknown) {
      const err = e as { name?: string; message?: string }
      if (err.name === 'DatabaseResumingException' || err.message?.includes('resuming')) {
        await new Promise(r => setTimeout(r, 8000))
      } else {
        throw e
      }
    }
  }
  throw new Error('Aurora failed after 5 retries')
}

export function parseVal(field: any): unknown {
  if (!field) return null
  return Object.values(field)[0] ?? null
}

/** Tables that feed debate context per Alex_Trading_Floor_2.0 — cleared per user, then re-seeded from portfolio. */
const CONTEXT_TABLES = [
  'trading_floor_intelligence',
  'simulated_trades',
  'agent_positions',
  'trading_daily_pnl',
  'trading_events',
  'scout_candidates',
  'rl_weights',
  'trading_simulations',
] as const

export interface ResetContextResult {
  cleared_tables: string[]
  simulation_id: string | null
  positions_seeded: number
  initial_value: number
  mode: string
}

export async function resetTradingDebateContext(clerkId: string, mode = 'neutral'): Promise<ResetContextResult> {
  const uidParam = { name: 'uid', value: { stringValue: clerkId } }
  const modeParam = { name: 'mode', value: { stringValue: mode } }

  for (const table of CONTEXT_TABLES) {
    await executeWithRetry(
      `DELETE FROM ${table} WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid)`,
      [uidParam],
    )
  }

  const valueResult = await executeWithRetry(
    `SELECT COALESCE(SUM(p.shares * p.purchase_price), 0)
     FROM portfolios p
     JOIN users u ON u.id = p.user_id
     WHERE u.clerk_id = :uid AND p.shares > 0 AND p.ticker IS NOT NULL`,
    [uidParam],
  )
  let initialValue = parseFloat(String(parseVal(valueResult.records?.[0]?.[0]) || 0))
  if (initialValue <= 0) initialValue = 10000

  const cashBalance = initialValue * 0.05

  const simResult = await executeWithRetry(
    `INSERT INTO trading_simulations
       (user_id, mode, status, initial_value, current_value, cash_balance,
        total_pnl, total_trades, win_count, loss_count)
     SELECT id, :mode, 'active', :init, :init, :cash, 0, 0, 0, 0
     FROM users WHERE clerk_id = :uid
     RETURNING id`,
    [
      uidParam,
      modeParam,
      { name: 'init', value: { doubleValue: initialValue } },
      { name: 'cash', value: { doubleValue: cashBalance } },
    ],
  )

  const simulationId = parseVal(simResult.records?.[0]?.[0]) as string | null
  if (!simulationId) {
    return {
      cleared_tables: [...CONTEXT_TABLES],
      simulation_id: null,
      positions_seeded: 0,
      initial_value: initialValue,
      mode,
    }
  }

  await executeWithRetry(
    `INSERT INTO agent_positions
       (simulation_id, user_id, ticker, shares, avg_cost,
        current_price, current_value, pnl, pnl_pct, last_updated)
     SELECT :sim::uuid, u.id, p.ticker,
            GREATEST(FLOOR(p.shares)::int, 0),
            p.purchase_price, p.purchase_price,
            p.shares * p.purchase_price, 0, 0, NOW()
     FROM users u
     JOIN portfolios p ON p.user_id = u.id
     WHERE u.clerk_id = :uid
       AND p.shares > 0
       AND p.ticker IS NOT NULL
     ON CONFLICT (simulation_id, ticker) DO NOTHING`,
    [
      uidParam,
      { name: 'sim', value: { stringValue: simulationId } },
    ],
  )

  const countResult = await executeWithRetry(
    `SELECT COUNT(*) FROM agent_positions ap
     JOIN users u ON u.id = ap.user_id
     WHERE u.clerk_id = :uid AND ap.simulation_id = :sim::uuid`,
    [uidParam, { name: 'sim', value: { stringValue: simulationId } }],
  )
  const positionsSeeded = parseInt(String(parseVal(countResult.records?.[0]?.[0]) || 0), 10)

  return {
    cleared_tables: [...CONTEXT_TABLES],
    simulation_id: simulationId,
    positions_seeded: positionsSeeded,
    initial_value: initialValue,
    mode,
  }
}
