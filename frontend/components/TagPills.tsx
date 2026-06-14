import { Cpu, Sparkles } from 'lucide-react'

export type TagTheme =
  | 'blue' | 'amber' | 'indigo' | 'emerald'
  | 'purple' | 'green' | 'yellow' | 'red' | 'orange'

const AI_PILL: Record<TagTheme, string> = {
  blue:    'bg-blue-500/20 border-blue-400/40 text-blue-100 ring-blue-400/15',
  amber:   'bg-amber-500/20 border-amber-400/40 text-amber-100 ring-amber-400/15',
  indigo:  'bg-indigo-500/20 border-indigo-400/40 text-indigo-100 ring-indigo-400/15',
  emerald: 'bg-emerald-500/20 border-emerald-400/40 text-emerald-100 ring-emerald-400/15',
  purple:  'bg-purple-500/20 border-purple-400/40 text-purple-100 ring-purple-400/15',
  green:   'bg-green-500/20 border-green-400/40 text-green-100 ring-green-400/15',
  yellow:  'bg-yellow-500/20 border-yellow-400/40 text-yellow-100 ring-yellow-400/15',
  red:     'bg-red-500/20 border-red-400/40 text-red-100 ring-red-400/15',
  orange:  'bg-orange-500/20 border-orange-400/40 text-orange-100 ring-orange-400/15',
}

const LABEL_AI: Record<TagTheme, string> = {
  blue: 'text-blue-400', amber: 'text-amber-400', indigo: 'text-indigo-400',
  emerald: 'text-emerald-400', purple: 'text-purple-400', green: 'text-green-400',
  yellow: 'text-yellow-400', red: 'text-red-400', orange: 'text-orange-400',
}

const LABEL_AI_BG: Record<TagTheme, string> = {
  blue: 'bg-blue-500/15 border-blue-500/25', amber: 'bg-amber-500/15 border-amber-500/25',
  indigo: 'bg-indigo-500/15 border-indigo-500/25', emerald: 'bg-emerald-500/15 border-emerald-500/25',
  purple: 'bg-purple-500/15 border-purple-500/25', green: 'bg-green-500/15 border-green-500/25',
  yellow: 'bg-yellow-500/15 border-yellow-500/25', red: 'bg-red-500/15 border-red-500/25',
  orange: 'bg-orange-500/15 border-orange-500/25',
}

function TagPills({
  kind,
  tags,
  theme,
}: {
  kind: 'ai' | 'stack'
  tags: string[]
  theme: TagTheme
}) {
  const isAi = kind === 'ai'
  const pillClass = isAi
    ? AI_PILL[theme]
    : 'bg-gray-950/70 border-gray-500/35 text-gray-200 ring-white/5'

  return (
    <div>
      <div className="flex items-center gap-1.5 mb-2">
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-semibold uppercase tracking-widest ${
            isAi ? `${LABEL_AI[theme]} ${LABEL_AI_BG[theme]}` : 'text-gray-400 bg-gray-800/60 border-gray-700/50'
          }`}
        >
          {isAi ? <Sparkles size={9} /> : <Cpu size={9} />}
          {kind}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {tags.map((t) => (
          <span
            key={t}
            className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-medium tracking-wide backdrop-blur-sm shadow-sm ring-1 ring-inset ${pillClass}`}
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
    <div className="mt-4 space-y-3">
      <TagPills kind="ai" tags={ai} theme={theme} />
      <TagPills kind="stack" tags={stack} theme={theme} />
    </div>
  )
}
