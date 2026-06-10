import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { tickers } = await req.json()
    if (!tickers?.length) {
      return NextResponse.json({ prices: {} })
    }

    // Fetch prices for all tickers in parallel
    const prices: Record<string, any> = {}

    await Promise.all(
      tickers.map(async (ticker: string) => {
        try {
          const res = await fetch(
            `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?interval=1d&range=1d`,
            {
              headers: {
                'User-Agent': 'Mozilla/5.0'
              }
            }
          )
          const data = await res.json()
          const meta = data?.chart?.result?.[0]?.meta

          if (meta) {
            const price      = meta.regularMarketPrice
            const prevClose  = meta.previousClose || meta.chartPreviousClose
            const change     = price - prevClose
            const changePct  = ((change / prevClose) * 100)

            prices[ticker] = {
              price:     price?.toFixed(2),
              change:    change?.toFixed(2),
              changePct: changePct?.toFixed(2),
              high:      meta.regularMarketDayHigh?.toFixed(2),
              low:       meta.regularMarketDayLow?.toFixed(2),
              volume:    meta.regularMarketVolume,
            }
          }
        } catch (err) {
          console.error(`Price fetch failed for ${ticker}:`, err)
          prices[ticker] = null
        }
      })
    )

    return NextResponse.json({ prices })

  } catch (error: any) {
    console.error('Prices error:', error)
    return NextResponse.json({ prices: {} })
  }
}