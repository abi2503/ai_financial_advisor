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
    // Latest run summary
    const latestResult = await executeWithRetry(`
      SELECT
        id::text, gate, judge_model, backend, query_count,
        faithfulness, answer_relevancy, context_precision, context_recall,
        hallucination_rate, overall_score, passed, evaluated_at::text
      FROM ragas_eval_runs
      ORDER BY evaluated_at DESC
      LIMIT 1
    `)

    const latestRow = latestResult?.records?.[0]
    const latest = latestRow ? {
      run_id:             latestRow[0]?.stringValue,
      gate:               latestRow[1]?.stringValue,
      judge_model:        latestRow[2]?.stringValue,
      backend:            latestRow[3]?.stringValue,
      query_count:        parseInt(String(val(latestRow[4]) || 0)),
      faithfulness:       num(val(latestRow[5])),
      answer_relevancy:   num(val(latestRow[6])),
      context_precision:  num(val(latestRow[7])),
      context_recall:     num(val(latestRow[8])),
      hallucination_rate: num(val(latestRow[9])),
      overall_score:      num(val(latestRow[10])),
      passed:             bool(latestRow[11]?.booleanValue),
      evaluated_at:       latestRow[12]?.stringValue,
    } : null

    // Trend (last 10 runs)
    const trendResult = await executeWithRetry(`
      SELECT
        id::text, evaluated_at::text, faithfulness, answer_relevancy,
        hallucination_rate, overall_score, passed, gate
      FROM ragas_eval_runs
      ORDER BY evaluated_at DESC
      LIMIT 10
    `)

    const trend = (trendResult?.records || []).map(row => ({
      run_id:             row[0]?.stringValue,
      evaluated_at:       row[1]?.stringValue,
      faithfulness:       num(val(row[2])),
      answer_relevancy:   num(val(row[3])),
      hallucination_rate: num(val(row[4])),
      overall_score:      num(val(row[5])),
      passed:             bool(row[6]?.booleanValue),
      gate:               row[7]?.stringValue,
    })).reverse()

    // Per-query audits for selected or latest run
    const targetRunId = runId || latest?.run_id
    let audits: any[] = []

    if (targetRunId) {
      const auditResult = await executeWithRetry(`
        SELECT
          id::text, query, response, ground_truth,
          faithfulness, answer_relevancy, context_precision, context_recall,
          hallucination_rate, overall_score, passed, gate,
          contexts::text, audit_json::text, evaluated_at::text
        FROM ragas_evaluations
        WHERE run_id = :run_id::uuid
        ORDER BY evaluated_at ASC
      `, [{ name: 'run_id', value: { stringValue: targetRunId } }])

      audits = (auditResult?.records || []).map(row => {
        let contexts: string[] = []
        let audit: Record<string, unknown> = {}
        try { contexts = JSON.parse(row[12]?.stringValue || '[]') } catch { /* */ }
        try { audit = JSON.parse(row[13]?.stringValue || '{}') } catch { /* */ }
        return {
          id:                 row[0]?.stringValue,
          query:              row[1]?.stringValue,
          response:           row[2]?.stringValue,
          ground_truth:       row[3]?.stringValue,
          faithfulness:       num(val(row[4])),
          answer_relevancy:   num(val(row[5])),
          context_precision:  num(val(row[6])),
          context_recall:     num(val(row[7])),
          hallucination_rate: num(val(row[8])),
          overall_score:      num(val(row[9])),
          passed:             bool(row[10]?.booleanValue),
          gate:               row[11]?.stringValue,
          contexts,
          audit,
          evaluated_at:       row[14]?.stringValue,
        }
      })
    }

    return NextResponse.json({
      latest,
      trend,
      audits,
      selected_run_id: targetRunId,
      thresholds: {
        faithfulness:       0.88,
        answer_relevancy:   0.85,
        hallucination_rate: 0.08,
        context_recall:     0.70,
      },
    })
  } catch (error) {
    console.error('RAGAS observe API error:', error)
    return NextResponse.json({
      latest: null,
      trend: [],
      audits: [],
      thresholds: {
        faithfulness: 0.88,
        answer_relevancy: 0.85,
        hallucination_rate: 0.08,
        context_recall: 0.70,
      },
      error: 'DB unavailable',
    })
  }
}
