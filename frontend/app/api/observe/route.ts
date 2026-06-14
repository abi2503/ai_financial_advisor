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

function parseTools(raw: unknown): { name: string; success: boolean; error?: string; latency_ms?: number }[] {
  if (!Array.isArray(raw)) return []
  return raw.map(t => {
    if (typeof t === 'string') return { name: t, success: true }
    const o = t as Record<string, unknown>
    return {
      name:       String(o.name || ''),
      success:    o.success !== false,
      error:      o.error ? String(o.error) : undefined,
      latency_ms: typeof o.latency_ms === 'number' ? o.latency_ms : undefined,
    }
  })
}

function parseMcps(raw: unknown): { name: string; success: boolean; error?: string }[] {
  if (!Array.isArray(raw)) return []
  return raw.map(m => {
    if (typeof m === 'string') return { name: m, success: true }
    const o = m as Record<string, unknown>
    return { name: String(o.name || ''), success: o.success !== false, error: o.error ? String(o.error) : undefined }
  })
}

function parseApis(raw: unknown): { name: string; url: string; latency_ms: number; success: boolean; error?: string }[] {
  if (!Array.isArray(raw)) return []
  return raw.map(a => {
    const o = a as Record<string, unknown>
    return {
      name:       String(o.name || ''),
      url:        String(o.url || ''),
      latency_ms: typeof o.latency_ms === 'number' ? o.latency_ms : 0,
      success:    o.success !== false,
      error:      o.error ? String(o.error) : undefined,
    }
  })
}

function passFailSummary(tools: ReturnType<typeof parseTools>, mcps: ReturnType<typeof parseMcps>, apis: ReturnType<typeof parseApis>) {
  const tp = tools.filter(t => t.success).length
  const tf = tools.length - tp
  const ap = apis.filter(a => a.success).length
  const af = apis.length - ap
  const mp = mcps.filter(m => m.success).length
  const mf = mcps.length - mp
  return { tools_passed: tp, tools_failed: tf, apis_passed: ap, apis_failed: af, mcps_passed: mp, mcps_failed: mf }
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

    // Research query latency (last 7 days, current user)
    let querySummary: any[] = []
    let recentQueries: any[] = []
    try {
      const summaryResult = await executeWithRetry(`
        SELECT
          q.route,
          COUNT(*)::int as cnt,
          ROUND(AVG(q.total_ms))::int as avg_ms,
          ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY q.total_ms))::int as p50_ms,
          ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY q.total_ms))::int as p95_ms,
          ROUND(AVG(q.first_token_ms))::int as avg_first_token_ms
        FROM query_latency_metrics q
        JOIN users u ON u.id = q.user_id
        WHERE u.clerk_id = :clerk_id
          AND q.created_at > NOW() - INTERVAL '7 days'
        GROUP BY q.route
        ORDER BY cnt DESC
      `, [{ name: 'clerk_id', value: { stringValue: userId } }])

      querySummary = (summaryResult?.records || []).map(row => ({
        route:             row[0]?.stringValue,
        count:             parseInt(String(val(row[1]) || 0)),
        avg_ms:            parseInt(String(val(row[2]) || 0)),
        p50_ms:            parseInt(String(val(row[3]) || 0)),
        p95_ms:            parseInt(String(val(row[4]) || 0)),
        avg_first_token_ms: parseInt(String(val(row[5]) || 0)),
      }))

      const recentResult = await executeWithRetry(`
        SELECT
          q.query_id, q.query, q.route, q.model,
          q.total_ms, q.first_token_ms, q.context_ms, q.agent_ms, q.guardrail_ms,
          q.tools_called::text, q.mcp_servers::text, q.data_sources::text,
          q.response_chars, q.success, q.created_at::text
        FROM query_latency_metrics q
        JOIN users u ON u.id = q.user_id
        WHERE u.clerk_id = :clerk_id
        ORDER BY q.created_at DESC
        LIMIT 30
      `, [{ name: 'clerk_id', value: { stringValue: userId } }])

      recentQueries = (recentResult?.records || []).map(row => {
        let tools = parseTools([])
        let mcps  = parseMcps([])
        let apis  = parseApis([])
        try { tools = parseTools(JSON.parse(row[9]?.stringValue || '[]')) } catch { /* */ }
        try { mcps  = parseMcps(JSON.parse(row[10]?.stringValue || '[]')) } catch { /* */ }
        try { apis  = parseApis(JSON.parse(row[11]?.stringValue || '[]')) } catch { /* */ }
        return {
          query_id:       row[0]?.stringValue,
          query:          row[1]?.stringValue,
          route:          row[2]?.stringValue,
          model:          row[3]?.stringValue,
          total_ms:       parseInt(String(val(row[4]) || 0)),
          first_token_ms: parseInt(String(val(row[5]) || 0)) || null,
          context_ms:     parseInt(String(val(row[6]) || 0)),
          agent_ms:       parseInt(String(val(row[7]) || 0)),
          guardrail_ms:   parseInt(String(val(row[8]) || 0)),
          tools,
          mcp_servers:    mcps,
          data_sources:   apis,
          pass_fail:      passFailSummary(tools, mcps, apis),
          response_chars: parseInt(String(val(row[12]) || 0)),
          success:        row[13]?.booleanValue ?? true,
          created_at:     row[14]?.stringValue,
        }
      })
    } catch (e) {
      console.error('Query metrics unavailable:', e)
    }

    return NextResponse.json({ agents, platform, guardrails, trend, querySummary, recentQueries })
  } catch (error) {
    console.error('Observe API error:', error)
    return NextResponse.json({ agents: [], platform: null, guardrails: [], trend: [], querySummary: [], recentQueries: [], error: 'DB unavailable' })
  }
}
