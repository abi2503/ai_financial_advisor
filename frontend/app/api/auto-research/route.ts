import { auth } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'

const INGEST_API = process.env.NEXT_PUBLIC_ALEX_API || ''
const API_KEY    = process.env.ALEX_API_KEY || ''

export async function GET() {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Search S3 Vectors for latest auto-research
    const response = await fetch(`${INGEST_API}/search`, {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key':    API_KEY
      },
      body: JSON.stringify({
        query:      'financial market research analysis',
        top_k:      5,
        filter_key: 'source',
        filter_val: 'alex-researcher'
      }),
      signal: AbortSignal.timeout(15000)
    })

    if (!response.ok) {
      return NextResponse.json({ results: [] })
    }

    const data = await response.json()
    return NextResponse.json({
      results: data.results || []
    })

  } catch (error: any) {
    console.error('Auto research fetch error:', error)
    return NextResponse.json({ results: [] })
  }
}