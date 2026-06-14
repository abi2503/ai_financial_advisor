import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data'
import { auth, currentUser } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import Navbar from '@/components/Navbar'
import AlexMarkdown from '@/components/AlexMarkdown'
import OpsCostWidget from '@/components/OpsCostWidget'
import Link from 'next/link'
import { Brain, MessageSquare, PieChart, History, Clock, TrendingUp, TrendingDown, Minus, Zap, BarChart2 } from 'lucide-react'

const rds = new RDSDataClient({ region: process.env.AWS_REGION || 'us-east-1' })

const DB = {
  resourceArn: process.env.DB_CLUSTER_ARN!,
  secretArn:   process.env.DB_SECRET_ARN!,
  database:    process.env.DB_NAME || 'alex_db',
}

function isAuroraResuming(err: unknown): boolean {
  const e = err as { name?: string; message?: string }
  return e.name === 'DatabaseResumingException' || !!e.message?.toLowerCase().includes('resuming')
}

async function executeWithRetry(command: ExecuteStatementCommand, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      return await rds.send(command)
    } catch (err) {
      if (isAuroraResuming(err) && i < retries - 1) {
        console.log(`Aurora resuming — waiting 30s (attempt ${i + 1}/${retries})`)
        await new Promise(r => setTimeout(r, 30000))
      } else {
        throw err
      }
    }
  }
  throw new Error('Aurora query failed after retries')
}

async function getPortfolioDigests(clerkId: string) {
  try {
    const result = await executeWithRetry(new ExecuteStatementCommand({
      ...DB,
      sql: `
        SELECT pd.ticker, pd.company, pd.headline, pd.sentiment,
               pd.digest, pd.key_news, pd.updated_at::text
        FROM portfolio_digests pd
        JOIN users u ON u.id = pd.user_id
        WHERE u.clerk_id = :clerk_id
        ORDER BY pd.updated_at DESC
      `,
      parameters: [{ name: 'clerk_id', value: { stringValue: clerkId } }],
    }))
    return (result.records || []).map(row => ({
      ticker:     row[0]?.stringValue || '',
      company:    row[1]?.stringValue || '',
      headline:   row[2]?.stringValue || '',
      sentiment:  row[3]?.stringValue || 'neutral',
      digest:     row[4]?.stringValue || '',
      key_news:   JSON.parse(row[5]?.stringValue || '[]'),
      updated_at: row[6]?.stringValue || '',
    }))
  } catch (err) {
    console.error('Portfolio digests fetch error:', err)
    return []
  }
}

function sentimentIcon(sentiment: string) {
  if (sentiment === 'bullish') return <TrendingUp size={14} className="text-green-400" />
  if (sentiment === 'bearish') return <TrendingDown size={14} className="text-red-400" />
  return <Minus size={14} className="text-gray-400" />
}

function sentimentBadge(sentiment: string) {
  const styles: Record<string, string> = {
    bullish: 'bg-green-500/20 text-green-400',
    bearish: 'bg-red-500/20 text-red-400',
    neutral: 'bg-gray-500/20 text-gray-400',
  }
  return styles[sentiment] || styles.neutral
}

export default async function Dashboard() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')

  const user            = await currentUser()
  const portfolioCards  = await getPortfolioDigests(userId)
  const hour         = new Date().getHours()
  const greeting     = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar />
      <main className="max-w-6xl mx-auto px-6 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white">
            {greeting}, {user?.firstName || 'there'}
          </h1>
          <p className="text-gray-400 mt-1">
            Portfolio research and platform overview
          </p>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            {
              href:  '/research',
              icon:  <MessageSquare className="text-blue-400" size={20} />,
              title: 'Ask Alex',
              desc:  'Research any stock or topic',
              color: 'border-blue-500/20 hover:border-blue-500/40'
            },
            {
              href:  '/portfolio',
              icon:  <PieChart className="text-green-400" size={20} />,
              title: 'Portfolio',
              desc:  'View your tracked stocks',
              color: 'border-green-500/20 hover:border-green-500/40'
            },
            {
              href:  '/charts',
              icon:  <BarChart2 className="text-yellow-400" size={20} />,
              title: 'Charts',
              desc:  'Portfolio visualization',
              color: 'border-yellow-500/20 hover:border-yellow-500/40'
            },
            {
              href:  '/history',
              icon:  <History className="text-purple-400" size={20} />,
              title: 'History',
              desc:  'Browse past analysis',
              color: 'border-purple-500/20 hover:border-purple-500/40'
            },
            {
              href:  '/trading',
              icon:  <TrendingUp className="text-indigo-400" size={20} />,
              title: 'Trading Floor',
              desc:  'Multi-agent debate and voting',
              color: 'border-indigo-500/20 hover:border-indigo-500/40'
            },
          ].map((action) => (
            <Link
              key={action.href}
              href={action.href}
              className={`p-5 bg-gray-900 border rounded-xl transition ${action.color}`}
            >
              <div className="mb-2">{action.icon}</div>
              <div className="font-semibold text-white text-sm">{action.title}</div>
              <div className="text-gray-500 text-xs mt-0.5">{action.desc}</div>
            </Link>
          ))}
        </div>

        {/* Ask Alex */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="text-blue-400" size={20} />
            <h2 className="font-semibold text-white">Ask Alex</h2>
          </div>
          <div className="space-y-2">
            {[
              'Should I buy NVDA before earnings?',
              'What\'s happening with AI infrastructure stocks?',
              'How is the Fed affecting tech valuations?',
              'Compare NVDA vs AMD for next quarter',
            ].map((suggestion) => (
              <Link
                key={suggestion}
                href={`/research?q=${encodeURIComponent(suggestion)}`}
                className="block w-full text-left p-3 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300 text-sm transition"
              >
                "{suggestion}"
              </Link>
            ))}
          </div>
          <Link
            href="/research"
            className="mt-4 w-full flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg text-white text-sm font-medium transition"
          >
            <MessageSquare size={16} />
            Open Research Chat
          </Link>
        </div>

        {/* Portfolio Research Digests */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <h2 className="font-semibold text-white">
                Your Portfolio Research
              </h2>
            </div>
            <div className="flex items-center gap-1 text-gray-500 text-sm">
              <Clock size={14} />
              Updates every 2 hours
            </div>
          </div>

          {portfolioCards.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {portfolioCards.map((card: any) => (
                <Link
                  key={card.ticker}
                  href={`/research?q=${encodeURIComponent(card.ticker + ' latest news and analysis')}`}
                  className="block p-4 bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-gray-600 rounded-xl transition"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Brain size={16} className="text-blue-400 flex-shrink-0" />
                      <span className="text-white font-semibold">{card.ticker}</span>
                      <span className="text-gray-500 text-xs">{card.company}</span>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${sentimentBadge(card.sentiment)}`}>
                      {sentimentIcon(card.sentiment)}
                      {' '}{card.sentiment}
                    </span>
                  </div>
                  <p className="text-blue-300 text-sm font-medium mb-2">{card.headline}</p>
                  <div className="text-gray-400 text-xs mb-2 max-h-24 overflow-hidden">
                    <AlexMarkdown content={card.digest} />
                  </div>
                  {card.key_news?.length > 0 && (
                    <ul className="text-gray-500 text-xs space-y-0.5 mb-2">
                      {card.key_news.slice(0, 3).map((item: string, i: number) => (
                        <li key={i} className="truncate">• {item}</li>
                      ))}
                    </ul>
                  )}
                  <div className="text-gray-600 text-xs">
                    {card.updated_at ? new Date(card.updated_at).toLocaleString() : 'Pending first scan'}
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Brain size={32} className="text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm mb-2">No portfolio research yet</p>
              <p className="text-gray-600 text-xs mb-4">
                Add holdings on your portfolio page — Alex will research each stock every 2 hours
              </p>
              <Link
                href="/portfolio"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white text-sm transition"
              >
                <PieChart size={14} />
                Go to Portfolio
              </Link>
            </div>
          )}
        </div>

        <div id="ops-cost" className="mb-8">
          <OpsCostWidget />
        </div>

      </main>
    </div>
  )
}
