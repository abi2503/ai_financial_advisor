import { auth } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'
import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data'

function parseJson(field: any, fallback: any = {}) {
  if (!field?.stringValue) return fallback
  try {
    return JSON.parse(field.stringValue)
  } catch {
    return fallback
  }
}

export async function GET() {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const rds = new RDSDataClient({ region: process.env.AWS_REGION || 'us-east-1' })
    const result = await rds.send(new ExecuteStatementCommand({
      resourceArn: process.env.DB_CLUSTER_ARN!,
      secretArn:   process.env.DB_SECRET_ARN!,
      database:    process.env.DB_NAME || 'alex_db',
      sql: `
        SELECT pd.ticker, pd.company, pd.headline, pd.sentiment,
               pd.digest, pd.key_news, pd.dimensions, pd.updated_at::text
        FROM portfolio_digests pd
        JOIN users u ON u.id = pd.user_id
        WHERE u.clerk_id = :clerk_id
        ORDER BY pd.updated_at DESC
      `,
      parameters: [
        { name: 'clerk_id', value: { stringValue: userId } },
      ],
    }))

    const cards = (result.records || []).map(row => ({
      ticker:     row[0]?.stringValue || '',
      company:    row[1]?.stringValue || '',
      headline:   row[2]?.stringValue || '',
      sentiment:  row[3]?.stringValue || 'neutral',
      digest:     row[4]?.stringValue || '',
      key_news:   parseJson(row[5], []),
      dimensions: parseJson(row[6], {}),
      updated_at: row[7]?.stringValue || '',
    }))

    return NextResponse.json({ cards })
  } catch (error: any) {
    console.error('Portfolio research fetch error:', error)
    return NextResponse.json({ cards: [] })
  }
}
