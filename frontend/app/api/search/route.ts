import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'

const INGEST_API = process.env.NEXT_PUBLIC_ALEX_API || ''
const API_KEY    = process.env.ALEX_API_KEY || ''

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

    const response = await fetch(
      `${INGEST_API.replace('/ingest', '')}/search`,
      {
        method:  'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key':    API_KEY
        },
        body:   JSON.stringify({ query, top_k: 5 }),
        signal: AbortSignal.timeout(15000)
      }
    )

    if (!response.ok) {
      console.error(`Search API error: ${response.status}`)
      return NextResponse.json({ results: [] })
    }

    const data = await response.json()
    return NextResponse.json({ results: data.results || [] })

  } catch (error: any) {
    console.error('Search route error:', error)
    return NextResponse.json({ results: [] })
  }
}