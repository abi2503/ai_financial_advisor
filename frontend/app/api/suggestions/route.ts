import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { getEcsUrl } from '@/lib/config'

export async function GET(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ suggestions: [] })

  const ECS_URL = await getEcsUrl()
  if (!ECS_URL) return NextResponse.json({ suggestions: [] })

  try {
    const res  = await fetch(`${ECS_URL}/suggestions?user_id=${userId}`, {
      signal: AbortSignal.timeout(5000)
    })
    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ suggestions: [] })
  }
}