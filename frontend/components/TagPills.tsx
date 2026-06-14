export type TagTheme =
  | 'blue' | 'amber' | 'indigo' | 'emerald'
  | 'purple' | 'green' | 'yellow' | 'red' | 'orange'

const AI_PILL: Record<TagTheme, string> = {
  blue:    'bg-blue-500/12 text-blue-300',
  amber:   'bg-amber-500/12 text-amber-300',
  indigo:  'bg-indigo-500/12 text-indigo-300',
  emerald: 'bg-emerald-500/12 text-emerald-300',
  purple:  'bg-purple-500/12 text-purple-300',
  green:   'bg-green-500/12 text-green-300',
  yellow:  'bg-yellow-500/12 text-yellow-300',
  red:     'bg-red-500/12 text-red-300',
  orange:  'bg-orange-500/12 text-orange-300',
}

const LABEL_COLOR: Record<TagTheme, string> = {
  blue: 'text-blue-400/80', amber: 'text-amber-400/80', indigo: 'text-indigo-400/80',
  emerald: 'text-emerald-400/80', purple: 'text-purple-400/80', green: 'text-green-400/80',
  yellow: 'text-yellow-400/80', red: 'text-red-400/80', orange: 'text-orange-400/80',
}

function TagRow({
  kind,
  tags,
  theme,
}: {
  kind: 'ai' | 'stack'
  tags: string[]
  theme: TagTheme
}) {
  const isAi = kind === 'ai'

  return (
    <div>
      <p className={`text-[10px] font-semibold uppercase tracking-widest mb-1.5 ${
        isAi ? LABEL_COLOR[theme] : 'text-gray-500'
      }`}>
        {kind}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {tags.map((t) => (
          <span
            key={t}
            className={`rounded-md px-2 py-0.5 text-[11px] font-medium ${
              isAi ? AI_PILL[theme] : 'bg-gray-800/70 text-gray-400'
            }`}
          >
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
  theme,
}: {
  ai: string[]
  stack: string[]
  theme: TagTheme
}) {
  return (
    <div className="mt-4 space-y-2.5">
      <TagRow kind="ai" tags={ai} theme={theme} />
      <TagRow kind="stack" tags={stack} theme={theme} />
    </div>
  )
}
