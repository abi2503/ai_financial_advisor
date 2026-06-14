const PILL =
  'text-[11px] px-2.5 py-1 rounded-md border border-gray-600/50 bg-gray-900/70 text-gray-300'

const LABEL = 'text-[10px] uppercase tracking-wider text-purple-400/80 mb-1.5'

function TagRow({ label, tags }: { label: string; tags: string[] }) {
  return (
    <div>
      <p className={LABEL}>{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {tags.map((t) => (
          <span key={t} className={PILL}>
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}

export function FeatureTags({
  ai,
  stack,
}: {
  ai: string[]
  stack: string[]
  section?: 'new' | 'core'
}) {
  return (
    <div className="mt-4 space-y-3">
      <TagRow label="ai" tags={ai} />
      <TagRow label="stack" tags={stack} />
    </div>
  )
}
