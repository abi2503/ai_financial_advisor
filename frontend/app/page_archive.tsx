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
          Alex autonomously researches financial markets, builds a searchable knowledge base,
          and delivers personalized intelligence — without any human intervention.
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/sign-up" className="px-8 py-4 bg-blue-600 hover:bg-blue-500 rounded-xl text-white font-semibold text-lg transition">
            Start Free →
          </Link>
          <Link href="#features" className="px-8 py-4 border border-gray-700 hover:border-gray-500 rounded-xl text-gray-300 font-semibold text-lg transition">
            See How It Works
          </Link>
        </div>
      </section>

      {/* Stats */}
      {/*<section className="border-y border-gray-800 py-12">
        <div className="max-w-4xl mx-auto grid grid-cols-3 gap-8 text-center px-6">
          {[
            { value: '$24,000', label: 'Bloomberg Terminal/year' },
            { value: '$50',     label: 'Alex AI/month' },
            { value: '480x',    label: 'Cost reduction' },
          ].map((stat) => (
            <div key={stat.label}>
              <div className="text-3xl font-bold text-blue-400 mb-1">{stat.value}</div>
              <div className="text-gray-500 text-sm">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>*/}

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
              desc:  'Alex researches trending financial topics every 2 hours without any human input. Wake up to fresh intelligence every morning.',
            },
            {
              icon:  <Brain className="text-purple-400" size={24} />,
              title: 'Semantic Knowledge Base',
              desc:  'Every research report stored as a searchable vector. Ask anything and find research by meaning not just keywords.',
            },
            {
              icon:  <Shield className="text-green-400" size={24} />,
              title: 'Portfolio Intelligence',
              desc:  'Add your stocks and Alex monitors them continuously. Get alerts when risk signals are detected before they become problems.',
            },
            {
              icon:  <TrendingUp className="text-yellow-400" size={24} />,
              title: 'Real Market Data',
              desc:  'Live prices from Yahoo Finance API combined with news context from real web browsing. No hallucinated numbers.',
            },
            {
              icon:  <BarChart2 className="text-red-400" size={24} />,
              title: 'Multi-Agent Pipeline',
              desc:  'Planner, Tagger, and Reporter agents work together to produce comprehensive research faster than any single AI.',
            },
            {
              icon:  <Zap className="text-orange-400" size={24} />,
              title: 'Ask Anything',
              desc:  'Type any financial question. Alex decomposes it into research tasks, runs them in parallel, and synthesizes the answer.',
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

      {/* CTA */}
      <section className="max-w-2xl mx-auto px-6 py-24 text-center">
        <h2 className="text-3xl font-bold text-white mb-4">
          Start your free trial today
        </h2>
        <p className="text-gray-400 mb-8">
          No credit card required. Get access to autonomous financial research immediately.
        </p>
        <Link href="/sign-up" className="px-10 py-4 bg-blue-600 hover:bg-blue-500 rounded-xl text-white font-semibold text-lg transition inline-block">
          Get Started Free →
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 px-6 py-8 text-center text-gray-600 text-sm">
        <p>Alex AI © 2026 — Financial Research Platform</p>
        <p className="mt-1">This platform provides research not financial advice.</p>
      </footer>

    </main>
  )
}