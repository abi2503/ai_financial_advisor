import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { LambdaClient, InvokeCommand } from '@aws-sdk/client-lambda'

const lambda   = new LambdaClient({ region: process.env.AWS_REGION || 'us-east-1' })
const INGEST_API = process.env.NEXT_PUBLIC_ALEX_API || ''
const API_KEY    = process.env.ALEX_API_KEY || ''

async function searchViaLambda(query: string, topK: number) {
  const response = await lambda.send(new InvokeCommand({
    FunctionName:   'alex-ingest',
    InvocationType: 'RequestResponse',
    Payload:        Buffer.from(JSON.stringify({
      path:       '/search',
      httpMethod: 'POST',
      body:       JSON.stringify({ query, top_k: topK }),
    })),
  }))

  const raw  = JSON.parse(Buffer.from(response.Payload ?? new Uint8Array()).toString())
  const body = typeof raw.body === 'string' ? JSON.parse(raw.body) : raw.body ?? raw

  if (raw.statusCode && raw.statusCode >= 400) {
    throw new Error(body.error || `Lambda search failed (${raw.statusCode})`)
  }
  return body.results || []
}

async function searchViaApiGateway(query: string, topK: number) {
  const response = await fetch(
    `${INGEST_API.replace('/ingest', '')}/search`,
    {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key':    API_KEY,
      },
      body:   JSON.stringify({ query, top_k: topK }),
      signal: AbortSignal.timeout(45000),
    },
  )

  if (!response.ok) {
    throw new Error(`API Gateway search failed (${response.status})`)
  }

  const data = await response.json()
  return data.results || []
}

export async function POST(req: NextRequest) {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { query } = await req.json()
    if (!query) {
      return NextResponse.json({ error: 'Missing query' }, { status: 400 })
    }

    console.log(`Semantic search: "${query}"`)

    let results: unknown[] = []
    let source = 'lambda'

    try {
      results = await searchViaLambda(query, 5)
    } catch (lambdaErr) {
      console.warn('Lambda search failed, trying API Gateway:', lambdaErr)
      if (INGEST_API && API_KEY) {
        results = await searchViaApiGateway(query, 5)
        source  = 'api_gateway'
      } else {
        throw lambdaErr
      }
    }

    return NextResponse.json({ results, source })

  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : 'Search failed'
    console.error('Search route error:', msg)
    return NextResponse.json({ results: [], error: msg }, { status: 503 })
  }
}
