import { SSMClient, GetParameterCommand } from '@aws-sdk/client-ssm'

const ssm = new SSMClient({ region: process.env.AWS_REGION || 'us-east-1' })

// Cache URL in memory — refresh every 5 minutes
// Why: SSM costs $0.05 per 10,000 requests
//      Caching prevents unnecessary API calls
//      5 min TTL means URL updates within 5 mins
let cachedEcsUrl:   string | null = null
let cacheTimestamp: number        = 0
const CACHE_TTL = 5 * 60 * 1000

export async function getEcsUrl(): Promise<string> {
  const now = Date.now()

  // Return cached value if still fresh
  if (cachedEcsUrl && (now - cacheTimestamp) < CACHE_TTL) {
    return cachedEcsUrl
  }

  try {
    const response = await ssm.send(new GetParameterCommand({
      Name: '/alex/ecs_url'
    }))

    cachedEcsUrl   = response.Parameter?.Value || ''
    cacheTimestamp = now

    console.log(`ECS URL from SSM: ${cachedEcsUrl}`)
    return cachedEcsUrl

  } catch (error) {
    console.error('SSM read failed, using env var fallback')
    return process.env.ECS_URL ||
           process.env.NEXT_PUBLIC_ECS_URL ||
           ''
  }
}