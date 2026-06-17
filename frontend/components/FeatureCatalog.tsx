import { CatalogSection } from '@/components/CatalogGrid'
import {
  CORE_FEATURES,
  SHIP_DATE_LABEL,
  SHIPPED_TODAY_CATALOG,
  PLATFORM_CATALOG,
} from '@/lib/featureData'

export default function FeatureCatalog() {
  return (
    <>
      <CatalogSection
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
        title="Core platform"
        subtitle="The infrastructure behind every Alex response"
        items={CORE_FEATURES}
        bordered
      />
    </>
  )
}
