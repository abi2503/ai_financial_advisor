import Navbar from '@/components/Navbar'
import { CatalogSection } from '@/components/CatalogGrid'
import {
  CORE_FEATURES,
  SHIP_DATE_LABEL,
  SHIPPED_TODAY_CATALOG,
  PLATFORM_CATALOG,
} from '@/lib/featureData'

export default function FeaturesPage() {
  return (
    <main className="min-h-screen bg-gray-950">
      <Navbar />

      <CatalogSection
        id="catalog"
        title={`Shipped — ${SHIP_DATE_LABEL}`}
        subtitle="Eval frameworks, observability, market data, and charts added today"
        items={SHIPPED_TODAY_CATALOG}
      />

      <CatalogSection
        title="Platform features"
        subtitle="Major user-facing capabilities in Alex"
        items={PLATFORM_CATALOG}
        bordered
      />

      <CatalogSection
        id="features"
        title="Core platform"
        subtitle="The infrastructure behind every Alex response"
        items={CORE_FEATURES}
        bordered
      />

      <footer className="border-t border-gray-800 px-6 py-8 text-center text-gray-600 text-sm">
        <p>Alex AI © 2026 · For research purposes only, not financial advice</p>
      </footer>
    </main>
  )
}
