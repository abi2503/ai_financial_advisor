import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data'
import { auth, currentUser } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import Navbar from '@/components/Navbar'
import Link from 'next/link'
import { Brain, MessageSquare, PieChart, History, Clock, TrendingUp, Zap, BarChart2 } from 'lucide-react'

async function getAutoResearch() {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_ALEX_API!.replace('/ingest', '')}/search`,
      {
        method:  'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key':    process.env.ALEX_API_KEY!
        },
        body: JSON.stringify({
          query: 'financial market research stock analysis',
          top_k: 5
        }),
        next: { revalidate: 300 }
      }
    )
    if (!response.ok) return []
    const data = await response.json()
    return data.results || []
  } catch (err) {
    console.error('Auto research fetch error:', err)
    return []
  }
}

function cleanContent(content: string): string {
  return content
    .replace(/\*\*/g, '')
    .replace(/\*/g, '')
    .replace(/\|.*?\|/g, '')
    .replace(/#+\s/g, '')
    .replace(/\n+/g, ' ')
    .replace(/---+/g, '')
    .replace(/\[|\]/g, '')
    .replace(/\(https?:\/\/[^)]+\)/g, '')
    .replace(/Source:.*$/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .substring(0, 100) + '...'
}

async function getCosts() {
  try {
    const rds = new RDSDataClient({ region: process.env.AWS_REGION || 'us-east-1' })
    const result = await rds.send(new ExecuteStatementCommand({
      resourceArn: process.env.DB_CLUSTER_ARN!,
      secretArn:   process.env.DB_SECRET_ARN!,
      database:    process.env.DB_NAME || 'alex_db',
      sql: `SELECT snapshot_date, total_cost, service_costs, digest FROM cost_snapshots ORDER BY snapshot_date DESC LIMIT 7`
    }))
    return (result.records || []).map(row => ({
      date:     row[0]?.stringValue || '',
      total:    parseFloat(row[1]?.stringValue || '0'),
      services: JSON.parse(row[2]?.stringValue || '{}'),
      digest:   row[3]?.stringValue || ''
    }))
  } catch (e) {
    return []
  }
}

export default async function Dashboard() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')

  const user         = await currentUser()
  const autoResearch = await getAutoResearch()
  const costs     = await getCosts()
  const todayCost = costs[0]?.total || 0
  const weekCost  = costs.reduce((sum: number, c: any) => sum + c.total, 0)
  const hour         = new Date().getHours()
  const greeting     = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar />
      <main className="max-w-6xl mx-auto px-6 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white">
            {greeting}, {user?.firstName || 'there'} 👋
          </h1>
          <p className="text-gray-400 mt-1">
            Alex has been researching while you slept.
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
              desc:  '6-agent AI debate',
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

        {/* Auto Research Results */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <h2 className="font-semibold text-white">
                Latest from Alex's Autonomous Research
              </h2>
            </div>
            <div className="flex items-center gap-1 text-gray-500 text-sm">
              <Clock size={14} />
              Updates every 2 hours
            </div>
          </div>

          {autoResearch.length > 0 ? (
            <div className="grid grid-cols-1 gap-2">
              {autoResearch.map((item: any) => (
                <Link
                  key={item.id}
                  href={`/research?q=${encodeURIComponent(item.topic)}`}
                  className="flex items-center gap-4 p-3 bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-gray-600 rounded-xl transition"
                >
                  <Brain size={14} className="text-blue-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-blue-400 text-xs font-medium truncate">
                        {item.topic}
                      </span>
                    </div>
                    <p className="text-gray-400 text-xs truncate">
                      {cleanContent(item.content)}
                    </p>
                  </div>
                  <div className="text-gray-600 text-xs flex-shrink-0">
                    {new Date(item.timestamp).toLocaleDateString()}
                  </div>
                  <TrendingUp size={14} className="text-gray-600 flex-shrink-0" />
                </Link>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-5 gap-3">
              {[
                'Stock Market Movers',
                'AI Technology News',
                'Federal Reserve',
                'Cryptocurrency',
                'Energy Sector'
              ].map((topic) => (
                <Link
                  key={topic}
                  href={`/research?q=${encodeURIComponent(topic)}`}
                  className="bg-gray-800 hover:bg-gray-700 rounded-lg p-3 text-center text-xs text-gray-400 transition"
                >
                  {topic}
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Ask Alex */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
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

        {/* Cost Monitor Widget */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mt-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${todayCost > 10 ? 'bg-red-400 animate-pulse' : 'bg-green-400'}`} />
              <h2 className="font-semibold text-white">AWS Cost Monitor</h2>
            </div>
            <span className={`text-xs px-2 py-1 rounded-full ${todayCost > 10 ? 'bg-red-500/20 text-red-400' : todayCost > 5 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}`}>
              {todayCost > 10 ? '⚠️ Alert' : todayCost > 5 ? '👀 Monitor' : '✅ On Track'}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="bg-gray-800 rounded-lg p-3 text-center">
      <div className="text-xs text-gray-500 mb-1">Today</div>
              <div className={`text-lg font-bold ${todayCost > 10 ? 'text-red-400' : 'text-white'}`}>${todayCost.toFixed(2)}</div>
              <div className="text-xs text-gray-600">threshold: $10</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <div className="text-xs text-gray-500 mb-1">This Week</div>
              <div className="text-lg font-bold text-white">${weekCost.toFixed(2)}</div>
              <div className="text-xs text-gray-600">last 7 days</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <div className="text-xs text-gray-500 mb-1">Daily Avg</div>
              <div className="text-lg font-bold text-white">${costs.length > 0 ? (weekCost / costs.length).toFixed(2) : '0.00'}</div>
              <div className="text-xs text-gray-600">7-day average</div>
            </div>
          </div>
          {costs[0]?.digest && (
            <div className="p-3 bg-gray-800 rounded-lg">
              <div className="text-xs text-gray-500 mb-1">AI Cost Analysis</div>
              <p className="text-xs text-gray-300 leading-relaxed line-clamp-3">{costs[0].digest}</p>
            </div>
          )}
          <div className="mt-3 text-xs text-gray-600 text-center">Updates daily at 8AM UTC · Alert threshold: $10/day</div>
        </div>
        </div>

      </main>
    </div>
  )
}