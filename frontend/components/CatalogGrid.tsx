import Link from 'next/link'
import { FeatureTags } from '@/components/TagPills'

export type CatalogItem = {
  icon: React.ReactNode
  title: string
  desc: string
  ai: string[]
  stack: string[]
  href?: string
}

export function CatalogCard({ item }: { item: CatalogItem }) {
  const card = (
    <div className="p-6 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-600 transition h-full">
      <div className="mb-3">{item.icon}</div>
      <h3 className="text-white font-semibold mb-2">{item.title}</h3>
      <p className="text-gray-400 text-sm leading-relaxed">{item.desc}</p>
      <FeatureTags ai={item.ai} stack={item.stack} section="core" />
    </div>
  )

  if (item.href) {
    return (
      <Link href={item.href} className="block h-full hover:scale-[1.01] transition">
        {card}
      </Link>
    )
  }

  return card
}

export function CatalogSection({
  id,
  title,
  subtitle,
  items,
  bordered = false,
}: {
  id?: string
  title: string
  subtitle: string
  items: CatalogItem[]
  bordered?: boolean
}) {
  return (
    <section
      id={id}
      className={`max-w-5xl mx-auto px-6 py-20 ${bordered ? 'border-t border-gray-800/60' : ''}`}
    >
      <h2 className="text-2xl font-bold text-white text-center mb-3">{title}</h2>
      <p className="text-gray-500 text-center mb-12 text-sm">{subtitle}</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {items.map((item) => (
          <CatalogCard key={item.title} item={item} />
        ))}
      </div>
    </section>
  )
}
