'use client'

import Link from 'next/link'
import Navbar from '@/components/Navbar'
import { FeatureTags } from '@/components/TagPills'
import {
  TODAY_FEATURES,
  NEW_FEATURES,
  CORE_FEATURES,
  SHIP_DATE_LABEL,
} from '@/lib/featureData'
import { Sparkles, Package } from 'lucide-react'

function FeatureCard({
  f,
  linkable = true,
}: {
  f: (typeof TODAY_FEATURES)[0]
  linkable?: boolean
}) {
  const inner = (
    <>
      <div className="flex items-start justify-between mb-4">
        <div className="p-2.5 bg-gray-900/80 rounded-lg">{f.icon}</div>
        <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
          {f.badge}
        </span>
      </div>
      <h3 className="text-white font-semibold text-lg mb-2 group-hover:text-blue-300 transition">
        {f.title}
      </h3>
      <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
      <FeatureTags ai={f.ai} stack={f.stack} />
      {linkable && (
        <p className="text-xs text-gray-600 mt-4 group-hover:text-blue-400 transition">
          Open →
        </p>
      )}
    </>
  )

  if (linkable && f.href) {
    return (
      <Link
        href={f.href}
        className={`group block p-6 border rounded-xl transition hover:scale-[1.01] ${f.accent} hover:border-opacity-60`}
      >
        {inner}
      </Link>
    )
  }

  return (
    <div className={`p-6 border rounded-xl ${f.accent}`}>
      {inner}
    </div>
  )
}

export default function FeaturesPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <Navbar />

      <div className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-6xl mx-auto px-4 py-8">
          <div className="flex items-center gap-2 text-purple-400 text-sm mb-2">
            <Sparkles size={16} />
            Feature catalog
          </div>
          <h1 className="text-2xl font-bold text-white">What Alex ships</h1>
          <p className="text-sm text-gray-500 mt-1 max-w-2xl">
            Living inventory of platform capabilities — AI behaviors, stack components, and where to try them.
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8 space-y-12">

        {/* Today's batch */}
        <section>
          <div className="flex items-center gap-3 mb-2">
            <Package className="text-emerald-400" size={20} />
            <h2 className="text-xl font-bold text-white">Shipped today — {SHIP_DATE_LABEL}</h2>
          </div>
          <p className="text-sm text-gray-500 mb-6">
            RAGAS eval framework, trading outcome scoring, market overview fix, charts breakdown, and expanded /observe panels.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {TODAY_FEATURES.map((f) => (
              <FeatureCard key={f.title} f={f} />
            ))}
          </div>
        </section>

        {/* Platform features */}
        <section>
          <h2 className="text-xl font-bold text-white mb-1">Platform features</h2>
          <p className="text-sm text-gray-500 mb-6">Major user-facing capabilities</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {NEW_FEATURES.map((f) => (
              <FeatureCard key={f.title} f={f} />
            ))}
          </div>
        </section>

        {/* Core infra */}
        <section>
          <h2 className="text-xl font-bold text-white mb-1">Core platform</h2>
          <p className="text-sm text-gray-500 mb-6">Infrastructure behind every response</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {CORE_FEATURES.map((f) => (
              <div
                key={f.title}
                className="p-5 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-600 transition"
              >
                <div className="mb-3">{f.icon}</div>
                <h3 className="text-white font-semibold mb-2 text-sm">{f.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
                <FeatureTags ai={f.ai} stack={f.stack} />
              </div>
            ))}
          </div>
        </section>

        <p className="text-center text-xs text-gray-600 pb-8">
          Full engineering write-up in{' '}
          <code className="text-gray-500">Alex_report.md</code> §36 ·{' '}
          <Link href="/observe" className="text-blue-400 hover:underline">/observe</Link> for live eval metrics
        </p>
      </div>
    </div>
  )
}
