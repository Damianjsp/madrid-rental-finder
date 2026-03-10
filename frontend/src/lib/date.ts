export function formatRelativeDate(dateStr?: string) {
  if (!dateStr) return '—'

  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return '—'

  const diffMs = Date.now() - date.getTime()
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (diffMs < hour) {
    const minutes = Math.max(1, Math.round(diffMs / minute))
    return `${minutes}m ago`
  }

  if (diffMs < day) {
    return `${Math.max(1, Math.round(diffMs / hour))}h ago`
  }

  const days = Math.floor(diffMs / day)
  if (days < 7) return `${days}d ago`

  return date.toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
}
