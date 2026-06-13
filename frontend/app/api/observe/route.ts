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

export async function GET(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  try {
    // Per-agent stats (last 24h)
    const agentResult = await executeWithRetry(`
      SELECT
        agent_name,
        COUNT(*) as calls,
        SUM(input_tokens) as input_tokens,
        SUM(output_tokens) as output_tokens,
        SUM(total_tokens) as total_tokens,
        SUM(cost_usd) as total_cost,
        AVG(latency_ms) as avg_latency,
        SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
        SUM(CASE WHEN guardrail_triggered THEN 1 ELSE 0 END) as guardrail_hits,
        COUNT(DISTINCT ticker) as unique_tickers,
        SUM(CASE WHEN action='BUY' THEN 1 ELSE 0 END) as buy_count,
        SUM(CASE WHEN action='SELL' THEN 1 ELSE 0 END) as sell_count,
        SUM(CASE WHEN action='HOLD' THEN 1 ELSE 0 END) as hold_count,
        SUM(CASE WHEN action='TRIM' THEN 1 ELSE 0 END) as trim_count
      FROM agent_observations
      WHERE created_at > NOW() - INTERVAL '7 days'
      GROUP BY agent_name
      ORDER BY total_cost DESC
    `)

    const agents = (agentResult?.records || []).map(row => ({
      agent:          row[0]?.stringValue,
      calls:          parseInt(String(val(row[1]) || 0)),
      input_tokens:   parseInt(String(val(row[2]) || 0)),
      output_tokens:  parseInt(String(val(row[3]) || 0)),
      total_tokens:   parseInt(String(val(row[4]) || 0)),
      total_cost:     parseFloat(String(val(row[5]) || 0)),
      avg_latency:    parseFloat(String(val(row[6]) || 0)),
      successes:      parseInt(String(val(row[7]) || 0)),
      guardrail_hits: parseInt(String(val(row[8]) || 0)),
      unique_tickers: parseInt(String(val(row[9]) || 0)),
      buy_count:      parseInt(String(val(row[10]) || 0)),
      sell_count:     parseInt(String(val(row[11]) || 0)),
      hold_count:     parseInt(String(val(row[12]) || 0)),
      trim_count:     parseInt(String(val(row[13]) || 0)),
    }))

    // Platform totals
    const platformResult = await executeWithRetry(`
      SELECT
        SUM(cost_usd) as total_cost,
        SUM(total_tokens) as total_tokens,
        COUNT(*) as total_calls,
        COUNT(DISTINCT ticker) as unique_tickers,
        SUM(CASE WHEN guardrail_triggered THEN 1 ELSE 0 END) as total_guardrails
      FROM agent_observations
      WHERE created_at > NOW() - INTERVAL '7 days'
    `)

    const p = platformResult?.records?.[0]
    const platform = p ? {
      total_cost:       parseFloat(String(val(p[0]) || 0)),
      total_tokens:     parseInt(String(val(p[1]) || 0)),
      total_calls:      parseInt(String(val(p[2]) || 0)),
      unique_tickers:   parseInt(String(val(p[3]) || 0)),
      total_guardrails: parseInt(String(val(p[4]) || 0)),
    } : null

    // Recent guardrail logs
    const guardrailResult = await executeWithRetry(`
      SELECT agent_name, ticker, action, confidence, guardrail_action, created_at
      FROM agent_observations
      WHERE guardrail_triggered = true
      ORDER BY created_at DESC LIMIT 10
    `)

    const guardrails = (guardrailResult?.records || []).map(row => ({
      agent:      row[0]?.stringValue,
      ticker:     row[1]?.stringValue,
      action:     row[2]?.stringValue,
      confidence: parseFloat(String(val(row[3]) || 0)),
      reason:     row[4]?.stringValue,
      created_at: row[5]?.stringValue,
    }))

    // Daily cost trend (last 7 days)
    const trendResult = await executeWithRetry(`
      SELECT DATE(created_at) as day, SUM(cost_usd) as cost, COUNT(*) as calls
      FROM agent_observations
      WHERE created_at > NOW() - INTERVAL '7 days'
      GROUP BY DATE(created_at)
      ORDER BY day ASC
    `)

    const trend = (trendResult?.records || []).map(row => ({
      day:   row[0]?.stringValue,
      cost:  parseFloat(String(val(row[1]) || 0)),
      calls: parseInt(String(val(row[2]) || 0)),
    }))

    return NextResponse.json({ agents, platform, guardrails, trend })
  } catch (error) {
    console.error('Observe API error:', error)
    return NextResponse.json({ agents: [], platform: null, guardrails: [], trend: [], error: 'DB unavailable' })
  }
}
