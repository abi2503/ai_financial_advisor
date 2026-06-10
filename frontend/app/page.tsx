import Link from 'next/link'
import { auth } from '@clerk/nextjs/server'
import { TrendingUp, Brain, Shield, Zap, BarChart2, Clock } from 'lucide-react'

export default async function LandingPage() {
  const { userId } = await auth()

  return (
    <main className="min-h-screen bg-gray-950">

      {/* Navbar */}
      <nav className="border-b border-gray-800 px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Brain className="text-blue-400" size={28} />
          <span className="text-xl font-bold text-white">Alex AI</span>
        </div>
        <div className="flex gap-3">
          {userId ? (
            <Link href="/dashboard" className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white transition">
              Dashboard →
            </Link>
          ) : (
            <>
              <Link href="/sign-in" className="px-4 py-2 text-gray-300 hover:text-white transition">
                Sign In
              </Link>
              <Link href="/sign-up" className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white transition">
                Get Started Free
              </Link>
            </>
          )}
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-6 py-24 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-blue-400 text-sm mb-6">
          <Zap size={14} />
          Autonomous AI Research — Running 24/7
        </div>
        <h1 className="text-5xl font-bold text-white mb-6 leading-tight">
          Bloomberg-level research
          <span className="text-blue-400"> at $50/month</span>
        </h1>
        <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
        Alex researches financial markets, builds a searchable knowledge base, and delivers personalized intelligence automatically.
        </p>
        <div className="flex gap-4 justify-center">
          {userId ? (
            <Link
              href="/dashboard"
              className="px-8 py-4 bg-blue-600 hover:bg-blue-500 rounded-xl text-white font-semibold text-lg transition"
            >
              Go to Dashboard →
            </Link>
          ) : (
            <Link
              href="/sign-up"
              className="px-8 py-4 bg-blue-600 hover:bg-blue-500 rounded-xl text-white font-semibold text-lg transition"
            >
              Start Free →
            </Link>
          )}
          <Link
            href="#features"
            className="px-8 py-4 border border-gray-700 hover:border-gray-500 rounded-xl text-gray-300 font-semibold text-lg transition"
          >
            See How It Works
          </Link>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-5xl mx-auto px-6 py-24">
        <h2 className="text-3xl font-bold text-white text-center mb-16">
          What Alex does for you
        </h2>
        <div className="grid grid-cols-3 gap-8">
          {[
            {
              icon:  <Clock className="text-blue-400" size={24} />,
              title: '24/7 Autonomous Research',
              desc:  'Scheduled AI workflows generate market research every 2 hours.',
            },
            {
              icon:  <Brain className="text-purple-400" size={24} />,
              title: 'Semantic Knowledge Base',
              desc:  'Semantic retrieval system built on vector embeddings and similarity search.',
            },
            {
              icon:  <Shield className="text-green-400" size={24} />,
              title: 'Portfolio Intelligence',
              desc:  'Real-time stock tracking with automated risk and sentiment analysis.',
            },
            {
              icon:  <TrendingUp className="text-yellow-400" size={24} />,
              title: 'Real Market Data',
              desc:  'Combines market APIs, news sources, and web research into a unified pipeline.',
            },
            {
              icon:  <BarChart2 className="text-red-400" size={24} />,
              title: 'Multi-Agent Pipeline',
              desc:  'Planner, Tagger, and Reporter agents coordinate through an orchestration layer.',
            },
            {
              icon:  <Zap className="text-orange-400" size={24} />,
              title: 'Ask Anything',
              desc:  'Converts user queries into structured research workflows and actionable insights.',
            },
          ].map((f) => (
            <div key={f.title} className="p-6 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-600 transition">
              <div className="mb-3">{f.icon}</div>
              <h3 className="text-white font-semibold mb-2">{f.title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA — only show to logged out users */}
      {!userId && (
        <section className="max-w-2xl mx-auto px-6 py-24 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Start your free trial today
          </h2>
          <p className="text-gray-400 mb-8">
            No credit card required. Get access to autonomous financial
            research immediately.
          </p>
          <Link
            href="/sign-up"
            className="px-10 py-4 bg-blue-600 hover:bg-blue-500 rounded-xl text-white font-semibold text-lg transition inline-block"
          >
            Get Started Free →
          </Link>
        </section>
      )}

      {/* Footer */}
      <footer className="border-t border-gray-800 px-6 py-8 text-center text-gray-600 text-sm">
        <p>Alex AI © 2026 — Financial Research Platform</p>
        <p className="mt-1">This platform provides research not financial advice.</p>
      </footer>

    </main>
  )
}