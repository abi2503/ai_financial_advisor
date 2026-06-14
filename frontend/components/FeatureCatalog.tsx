import Link from 'next/link'
import { NEW_FEATURES, CORE_FEATURES } from '@/lib/featureData'
import { FeatureTags } from '@/components/TagPills'

export default function FeatureCatalog() {
  return (
    <>
      <section className="mb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {NEW_FEATURES.map((f) => (
            <Link
              key={f.title}
              href={f.href}
              className={`group p-5 border rounded-xl transition hover:scale-[1.01] ${f.accent} hover:border-opacity-60`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="p-2 bg-gray-900/80 rounded-lg">{f.icon}</div>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
                  {f.badge}
                </span>
              </div>
              <h3 className="text-white font-semibold mb-2 group-hover:text-blue-300 transition">
                {f.title}
              </h3>
              <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
              <FeatureTags ai={f.ai} stack={f.stack} theme={f.theme} />
              <p className="text-xs text-gray-600 mt-3 group-hover:text-blue-400 transition">
                Open →
              </p>
            </Link>
          ))}
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-white mb-1">Core platform</h2>
        <p className="text-gray-500 text-sm mb-6">
          The infrastructure behind every Alex response.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {CORE_FEATURES.map((f) => (
            <div
              key={f.title}
              className="p-5 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-600 transition"
            >
              <div className="mb-3">{f.icon}</div>
              <h3 className="text-white font-semibold mb-2 text-sm">{f.title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
              <FeatureTags ai={f.ai} stack={f.stack} theme={f.theme} />
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
