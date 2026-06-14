/**
 * Deep Research parallel path (formerly multi-agent) — planner + SQS.
 */
import { LambdaClient, InvokeCommand } from '@aws-sdk/client-lambda'
import { SQSClient, ReceiveMessageCommand, DeleteMessageCommand } from '@aws-sdk/client-sqs'
import { randomUUID } from 'crypto'

const lambda = new LambdaClient({ region: process.env.AWS_REGION || 'us-east-1' })
const sqs    = new SQSClient({ region: process.env.AWS_REGION || 'us-east-1' })

const RESULTS_QUEUE_URL = process.env.SQS_FRONTEND_RESULTS_QUEUE_URL || process.env.SQS_RESULTS_QUEUE_URL!
const PLANNER_FUNCTION  = process.env.PLANNER_FUNCTION || 'alex-planner'

export async function invokePlanner(question: string, userId: string, sessionId: string, correlationId: string) {
  const response = await lambda.send(new InvokeCommand({
    FunctionName:   PLANNER_FUNCTION,
    InvocationType: 'RequestResponse',
    Payload:        Buffer.from(JSON.stringify({
      body: JSON.stringify({
        question, correlationId,
        user_id: userId, clerk_id: userId, session_id: sessionId,
      }),
    })),
  }))
  const result = JSON.parse(Buffer.from(response.Payload!).toString())
  const body   = JSON.parse(result.body || '{}')
  return {
    tasks:     body.tasks_queued || [],
    taskCount: body.task_count   || 0,
  }
}

export async function pollForResults(taskCount: number, correlationId: string, timeoutMs = 180000) {
  const results: string[] = []
  const start = Date.now()

  while (results.length < taskCount && Date.now() - start < timeoutMs) {
    const response = await sqs.send(new ReceiveMessageCommand({
      QueueUrl:              RESULTS_QUEUE_URL,
      MaxNumberOfMessages:   10,
      WaitTimeSeconds:       5,
      VisibilityTimeout:     30,
      MessageAttributeNames: ['correlationId'],
    }))

    for (const msg of response.Messages || []) {
      const body = JSON.parse(msg.Body || '{}')
      const msgCorrelationId = body.correlationId || msg.MessageAttributes?.correlationId?.StringValue
      if (msgCorrelationId === correlationId) {
        const result = body.result || body.content || ''
        if (result) {
          results.push(result)
          await sqs.send(new DeleteMessageCommand({
            QueueUrl: RESULTS_QUEUE_URL, ReceiptHandle: msg.ReceiptHandle!,
          }))
        }
      }
    }
    if (results.length < taskCount) {
      await new Promise(r => setTimeout(r, 2000))
    }
  }

  return { results, timedOut: results.length < taskCount }
}

export function synthesizeResults(question: string, tasks: string[], results: string[], timedOut: boolean) {
  if (results.length === 0) {
    return `## Research Incomplete: ${question}\n\n> All tasks timed out. Try individual stock lookups.`
  }
  const partial = timedOut && results.length < tasks.length
  const meta = partial
    ? `> Partial — ${results.length}/${tasks.length} tasks completed.\n\n---\n\n`
    : `*Deep Research: ${results.length} parallel analyses*\n\n---\n\n`
  const sections = results.map((r, i) => `### ${tasks[i] || `Task ${i + 1}`}\n\n${r}`).join('\n\n---\n\n')
  return `## Deep Research: ${question}\n\n${meta}${sections}\n\n---\n\n> Not financial advice.`
}

export function newCorrelationId() {
  return randomUUID()
}
