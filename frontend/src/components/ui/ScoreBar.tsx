interface ScoreBarProps {
  score?: number
  max?: number
  label?: string
}

const colors = ['', 'bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-emerald-400', 'bg-emerald-500']

export function ScoreBar({ score, max = 5, label }: ScoreBarProps) {
  if (score == null) return <span className="text-slate-600 text-xs">—</span>

  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-0.5">
        {Array.from({ length: max }).map((_, i) => (
          <div
            key={i}
            className={`w-3 h-3 rounded-sm ${i < score ? colors[score] : 'bg-slate-700'}`}
          />
        ))}
      </div>
      {label && <span className="text-xs text-slate-400">{label}</span>}
    </div>
  )
}

export function ScoreDot({ score }: { score?: number }) {
  if (score == null) return <span className="text-slate-600">—</span>
  const color = ['', 'text-red-400', 'text-orange-400', 'text-yellow-400', 'text-emerald-400', 'text-emerald-300'][score]
  return (
    <span className={`font-bold ${color}`}>{score}/5</span>
  )
}
