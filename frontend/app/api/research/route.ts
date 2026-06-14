import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data'
import { LambdaClient, InvokeCommand } from '@aws-sdk/client-lambda'
import { SQSClient, ReceiveMessageCommand, DeleteMessageCommand } from '@aws-sdk/client-sqs'
import { getEcsUrl } from '@/lib/config'
import { randomUUID } from 'crypto'

const rds    = new RDSDataClient({ region: process.env.AWS_REGION || 'us-east-1' })
const lambda = new LambdaClient({ region: process.env.AWS_REGION || 'us-east-1' })
const sqs    = new SQSClient({ region: process.env.AWS_REGION || 'us-east-1' })

const DB = {
  resourceArn: process.env.DB_CLUSTER_ARN!,
  secretArn:   process.env.DB_SECRET_ARN!,
  database:    process.env.DB_NAME || 'alex_db',
}

const RESULTS_QUEUE_URL = 
  process.env.SQS_FRONTEND_RESULTS_QUEUE_URL || 
  process.env.SQS_RESULTS_QUEUE_URL!
const PLANNER_FUNCTION  = process.env.PLANNER_FUNCTION || 'alex-planner'

// ============================================
// Complexity Detection — FIX 1
// Require BOTH 2+ tickers AND a meaningful
// comparison keyword (not filler words like
// "and" / "or" that match everything)
// ============================================
const COMPLEX_PATTERNS = [
  'compare', 'vs', 'versus', 'should i',
  'or ', 'both', 'multiple', 'analyze both',
  'which is better', 'difference between',
  'contrast', 'and ', 'portfolio of', 'portfolio analysis',
  'side by side', 'pick between', 'choose between'
]

// "Weak" patterns — only count as complex when 2+ tickers also present
const WEAK_PATTERNS = ['and ', 'or ', 'multiple', 'should i']

function isComplexQuery(topic: string): boolean {
  const lower = topic.toLowerCase()

  const tickerPattern = /\b[A-Z]{2,5}\b/g
  const tickers       = topic.match(tickerPattern) || []
  const hasMultiple   = tickers.length >= 2

  const matchedPattern = COMPLEX_PATTERNS.find(p => lower.includes(p))
  if (!matchedPattern) return false

  const isWeak = WEAK_PATTERNS.includes(matchedPattern)

  // Weak patterns (and, or) only trigger complex mode if 2+ tickers present
  // Strong patterns (compare, vs, both) trigger regardless
  return isWeak ? hasMultiple : true
}

// ============================================
// Database helpers
// ============================================
async function executeWithRetry(command: any, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      return await rds.send(command)
    } catch (err: any) {
      if (err.name === 'DatabaseResumingException' && i < retries - 1) {
        console.log(`Aurora resuming — waiting 30s (attempt ${i+1}/${retries})`)
        await new Promise(r => setTimeout(r, 30000))
      } else {
        throw err
      }
    }
  }
}

async function saveResearchSession(
  userId: string,
  topic:  string,
  result: string
) {
  try {
    const userResult = await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
      sql: `
        INSERT INTO users (clerk_id, email, name)
        VALUES (:clerk_id, :email, :name)
        ON CONFLICT (clerk_id) DO UPDATE SET updated_at = NOW()
        RETURNING id
      `,
      parameters: [
        { name: 'clerk_id', value: { stringValue: userId } },
        { name: 'email',    value: { stringValue: '' } },
        { name: 'name',     value: { stringValue: '' } },
      ]
    })) as any

    const dbUserId = userResult.records?.[0]?.[0]?.stringValue
    if (!dbUserId) return

    await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
      sql: `
        INSERT INTO research_sessions (user_id, topic, result)
        VALUES (:user_id::uuid, :topic, :result)
      `,
      parameters: [
        { name: 'user_id', value: { stringValue: dbUserId } },
        { name: 'topic',   value: { stringValue: topic } },
        // FIX 4 — guard against undefined/null result before substring
        { name: 'result',  value: { stringValue: (result ?? '').substring(0, 10000) } },
      ]
    }))

    console.log(`Saved session for ${dbUserId}`)
  } catch (err) {
    console.error('DB save error:', err)
  }
}

// ============================================
// Planner Lambda invocation
// FIX 2 — pass correlationId so SQS messages
// can be filtered per-request
// ============================================
async function invokePlanner(
  question:      string,
  correlationId: string,
  userId:        string,
  sessionId:     string,
): Promise<{
  tasks:     string[]
  taskCount: number
  timestamp: string
}> {
  const response = await lambda.send(new InvokeCommand({
    FunctionName:   PLANNER_FUNCTION,
    InvocationType: 'RequestResponse',
    Payload:        Buffer.from(JSON.stringify({
      body: JSON.stringify({
        question,
        correlationId,
        user_id:    userId,
        clerk_id:   userId,
        session_id: sessionId,
      })
    }))
  }))

  const result = JSON.parse(Buffer.from(response.Payload!).toString())
  const body   = JSON.parse(result.body || '{}')

  return {
    tasks:     body.tasks_queued || [],
    taskCount: body.task_count   || 0,
    timestamp: body.timestamp    || new Date().toISOString()
  }
}

// ============================================
// Poll SQS for results — FIX 2
// Filter by correlationId so concurrent users
// never receive each other's messages.
// Messages belonging to other requests are
// left in the queue (visibility timeout expires
// and they become available again for their
// rightful owner).
// ============================================
async function pollForResults(
  taskCount:     number,
  correlationId: string,
  timeoutMs:     number = 180000
): Promise<{ results: string[]; timedOut: boolean }> {
  const results:   string[] = []
  const startTime: number   = Date.now()

  console.log(`=== POLL START ===`)
  console.log(`Queue: ${RESULTS_QUEUE_URL}`)
  console.log(`Looking for: ${correlationId}`)
  console.log(`Timeout: ${timeoutMs}ms`)

  while (
    results.length < taskCount &&
    Date.now() - startTime < timeoutMs
  ) {
    try {
      const response = await sqs.send(new ReceiveMessageCommand({
        QueueUrl:              RESULTS_QUEUE_URL,
        MaxNumberOfMessages:   10,
        WaitTimeSeconds:       5,
        VisibilityTimeout:     30,
        MessageAttributeNames: ['correlationId'],
      }))

      const messages = response.Messages || []
      console.log(`Poll: got ${messages.length} messages from SQS`)

      for (const msg of messages) {
        const body          = JSON.parse(msg.Body || '{}')
        const msgCorrelationId = body.correlationId || 
          msg.MessageAttributes?.correlationId?.StringValue
        
        console.log(`  Message correlationId: ${msgCorrelationId}`)
        console.log(`  Expected correlationId: ${correlationId}`)
        console.log(`  Match: ${msgCorrelationId === correlationId}`)

        if (msgCorrelationId === correlationId) {
          const result = body.result || body.content || ''
          if (result) {
            results.push(result)
            console.log(`  ✅ Got result ${results.length}/${taskCount}`)
            await sqs.send(new DeleteMessageCommand({
              QueueUrl:      RESULTS_QUEUE_URL,
              ReceiptHandle: msg.ReceiptHandle!
            }))
          }
        }
      }

      if (results.length < taskCount) {
        const elapsed = Math.round((Date.now() - startTime) / 1000)
        console.log(`Waiting... ${results.length}/${taskCount} (${elapsed}s)`)
        await new Promise(r => setTimeout(r, 2000))
      }

    } catch (err) {
      console.error('SQS poll error:', err)
      break
    }
  }

  const timedOut = results.length < taskCount
  console.log(`=== POLL END: ${results.length}/${taskCount} timedOut=${timedOut} ===`)
  return { results, timedOut }
}

// ============================================
// Synthesize results — FIX 3
// Clearly surface partial results to the caller
// instead of silently returning an incomplete report
// ============================================
function synthesizeResults(
  question:  string,
  tasks:     string[],
  results:   string[],
  timedOut:  boolean
): string {
  if (results.length === 0) {
    return [
      `## Research Incomplete: ${question}`,
      '',
      '> ⚠️ All research tasks timed out before returning results.',
      '> Please try again or break your query into individual stock lookups.',
    ].join('\n')
  }

  const isPartial = timedOut && results.length < tasks.length

  const header = `## Multi-Stock Research: ${question}\n\n`

  // FIX 3 — warn the user when results are partial
  const meta = isPartial
    ? `> ⚠️ **Partial results** — ${results.length} of ${tasks.length} research tasks completed before timeout. ` +
      `Missing: ${tasks.slice(results.length).join(', ')}\n\n---\n\n`
    : `*Researched ${results.length} of ${tasks.length} topics in parallel*\n\n---\n\n`

  const sections = results.map((result, i) => {
    const taskLabel = tasks[i] ? `### ${tasks[i]}\n\n` : `### Research ${i + 1}\n\n`
    return taskLabel + result
  }).join('\n\n---\n\n')

  const footer = `\n\n---\n\n> ⚠️ Multi-agent research combining ${results.length} parallel analyses. Not financial advice.`

  return header + meta + sections + footer
}

// ============================================
// Main POST handler
// ============================================
export async function POST(req: NextRequest) {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await req.json()
    const topic = body.topic
    const sessionId = body.session_id || req.headers.get('x-session-id') || ''
    if (!topic) {
      return NextResponse.json({ error: 'Missing topic' }, { status: 400 })
    }

    const complex = isComplexQuery(topic)
    console.log(`Research: "${topic}" — ${complex ? 'COMPLEX → Planner' : 'SIMPLE → ECS'}`)

    // ============================================
    // COMPLEX QUERY → Planner Lambda + SQS
    // ============================================
    if (complex) {
      console.log('Complex query detected — invoking Planner Lambda')

      // FIX 2 — generate a unique ID for this request
      const correlationId = randomUUID()

      const { tasks, taskCount, timestamp } = await invokePlanner(topic, correlationId, userId, sessionId)
      console.log(`Planner queued ${taskCount} tasks:`, tasks)

      const { results, timedOut } = await pollForResults(taskCount, correlationId, 180000)
      console.log(`Got ${results.length}/${taskCount} results from SQS`)

      const synthesized = synthesizeResults(topic, tasks, results, timedOut)
      await saveResearchSession(userId, topic, synthesized)

      return NextResponse.json({
        status:      timedOut && results.length < taskCount ? 'partial' : 'success',
        result:      synthesized,
        mode:        'multi-agent',
        tasks,
        taskCount,
        gotResults:  results.length,
        // FIX 3 — surface timeout clearly to frontend
        timedOut,
        missingTasks: timedOut ? tasks.slice(results.length) : [],
      })
    }

    // ============================================
    // SIMPLE QUERY → ECS directly
    // ============================================
    const ECS_URL = await getEcsUrl()
    if (!ECS_URL) {
      return NextResponse.json(
        { error: 'Research service not available' },
        { status: 503 }
      )
    }

    const ecsResponse = await fetch(`${ECS_URL}/research`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ topic, user_id: userId, session_id: sessionId }),
      signal:  AbortSignal.timeout(120000)
    })

    if (!ecsResponse.ok) {
      return NextResponse.json(
        { error: 'Research service error' },
        { status: 500 }
      )
    }

    const data = await ecsResponse.json()
    await saveResearchSession(userId, topic, data.result || '')

    return NextResponse.json({
      status: 'success',
      result: data.result || 'Research complete',
      mode:   'single-agent',
    })

  } catch (error: any) {
    console.error('Research route error:', error)
    if (error.name === 'TimeoutError') {
      return NextResponse.json(
        { error: 'Research timed out — try a simpler query' },
        { status: 408 }
      )
    }
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}