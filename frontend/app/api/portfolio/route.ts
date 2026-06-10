import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data'

const rds = new RDSDataClient({ region: process.env.AWS_REGION || 'us-east-1' })

const DB = {
  resourceArn: process.env.DB_CLUSTER_ARN!,
  secretArn:   process.env.DB_SECRET_ARN!,
  database:    process.env.DB_NAME || 'alex_db',
}

async function executeWithRetry(command: any, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      return await rds.send(command)
    } catch (err: any) {
      if (err.name === 'DatabaseResumingException' && i < retries - 1) {
        console.log(`Aurora resuming — waiting 30s (attempt ${i + 1}/${retries})`)
        await new Promise(r => setTimeout(r, 30000))
      } else {
        throw err
      }
    }
  }
}

async function getDbUserId(clerkId: string): Promise<string | null> {
  const result = await executeWithRetry(new ExecuteStatementCommand({
    ...DB,
    sql:        `SELECT id FROM users WHERE clerk_id = :clerk_id LIMIT 1`,
    parameters: [{ name: 'clerk_id', value: { stringValue: clerkId } }]
  })) as any
  return result.records?.[0]?.[0]?.stringValue || null
}

export async function GET() {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const dbUserId = await getDbUserId(userId)
    if (!dbUserId) return NextResponse.json({ portfolio: [] })

    const result = await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
      sql: `
        SELECT id, ticker, company, shares, purchase_price,
               asset_class, sector, notes, added_at
        FROM portfolios
        WHERE user_id = :user_id::uuid
        ORDER BY added_at DESC
      `,
      parameters: [{ name: 'user_id', value: { stringValue: dbUserId } }]
    })) as any

    const portfolio = (result.records || []).map((r: any) => ({
      id:             r[0]?.stringValue,
      ticker:         r[1]?.stringValue,
      company:        r[2]?.stringValue,
      shares:         r[3]?.doubleValue || 0,
      purchase_price: r[4]?.doubleValue || 0,
      asset_class:    r[5]?.stringValue || 'stocks',
      sector:         r[6]?.stringValue || '',
      notes:          r[7]?.stringValue || '',
      added_at:       r[8]?.stringValue,
    }))

    return NextResponse.json({ portfolio })

  } catch (error: any) {
    console.error('Portfolio GET error:', error)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const {
      ticker,
      company,
      shares         = 0,
      purchase_price = 0,
      asset_class    = 'stocks',
      sector         = '',
      notes          = ''
    } = await req.json()

    if (!ticker || !company) {
      return NextResponse.json(
        { error: 'Missing ticker or company' },
        { status: 400 }
      )
    }

    const dbUserId = await getDbUserId(userId)
    if (!dbUserId) {
      return NextResponse.json(
        { error: 'User not found — sync first' },
        { status: 404 }
      )
    }

    const result = await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
      sql: `
        INSERT INTO portfolios 
          (user_id, ticker, company, shares, purchase_price,
           asset_class, sector, notes)
        VALUES 
          (:user_id::uuid, :ticker, :company, :shares,
           :purchase_price, :asset_class, :sector, :notes)
        ON CONFLICT DO NOTHING
        RETURNING id, ticker, company, shares, purchase_price,
                  asset_class, sector, added_at
      `,
      parameters: [
        { name: 'user_id',         value: { stringValue: dbUserId } },
        { name: 'ticker',          value: { stringValue: ticker.toUpperCase() } },
        { name: 'company',         value: { stringValue: company } },
        { name: 'shares',          value: { doubleValue: parseFloat(shares) || 0 } },
        { name: 'purchase_price',  value: { doubleValue: parseFloat(purchase_price) || 0 } },
        { name: 'asset_class',     value: { stringValue: asset_class } },
        { name: 'sector',          value: { stringValue: sector } },
        { name: 'notes',           value: { stringValue: notes } },
      ]
    })) as any

    const record = result.records?.[0]
    return NextResponse.json({
      success: true,
      stock: {
        id:             record?.[0]?.stringValue,
        ticker:         record?.[1]?.stringValue,
        company:        record?.[2]?.stringValue,
        shares:         record?.[3]?.doubleValue || 0,
        purchase_price: record?.[4]?.doubleValue || 0,
        asset_class:    record?.[5]?.stringValue,
        sector:         record?.[6]?.stringValue,
        added_at:       record?.[7]?.stringValue,
      }
    })

  } catch (error: any) {
    console.error('Portfolio POST error:', error)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { ticker } = await req.json()
    const dbUserId   = await getDbUserId(userId)
    if (!dbUserId) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 })
    }

    await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
      sql: `
        DELETE FROM portfolios
        WHERE user_id = :user_id::uuid
        AND ticker = :ticker
      `,
      parameters: [
        { name: 'user_id', value: { stringValue: dbUserId } },
        { name: 'ticker',  value: { stringValue: ticker.toUpperCase() } },
      ]
    }))

    return NextResponse.json({ success: true })

  } catch (error: any) {
    console.error('Portfolio DELETE error:', error)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}

export async function PATCH(req: NextRequest) {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { ticker, shares, purchase_price } = await req.json()
    const dbUserId = await getDbUserId(userId)
    if (!dbUserId) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 })
    }

    await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
      sql: `
        UPDATE portfolios
        SET shares = :shares,
            purchase_price = :purchase_price
        WHERE user_id = :user_id::uuid
        AND ticker = :ticker
      `,
      parameters: [
        { name: 'user_id',        value: { stringValue: dbUserId } },
        { name: 'ticker',         value: { stringValue: ticker.toUpperCase() } },
        { name: 'shares',         value: { doubleValue: parseFloat(shares) || 0 } },
        { name: 'purchase_price', value: { doubleValue: parseFloat(purchase_price) || 0 } },
      ]
    }))

    return NextResponse.json({ success: true })

  } catch (error: any) {
    console.error('Portfolio PATCH error:', error)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}