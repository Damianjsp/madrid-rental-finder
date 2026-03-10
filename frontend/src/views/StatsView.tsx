import { useQuery } from '@tanstack/react-query'
import { fetchStats } from '../api'
import { StatCard } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { LoadingState, ErrorState } from '../components/ui/Spinner'
import { BarChart3, Building2, List, Zap, CheckCircle, XCircle, Clock, MinusCircle } from 'lucide-react'

function timeAgo(dateStr?: string) {
  if (!dateStr) return null
  const d = new Date(dateStr)
  const now = new Date()
  const diffMin = Math.round((now.getTime() - d.getTime()) / 60000)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffH = Math.round(diffMin / 60)
  if (diffH < 24) return `${diffH}h ago`
  return `${Math.floor(diffH / 24)}d ago`
}

function ScrapeStatusIcon({ status }: { status?: string }) {
  switch (status) {
    case 'success': return <CheckCircle size={14} className="text-emerald-400" />
    case 'error': return <XCircle size={14} className="text-red-400" />
    case 'running': return <Clock size={14} className="text-amber-400 animate-pulse" />
    default: return <MinusCircle size={14} className="text-slate-600" />
  }
}

function ScrapeStatusBadge({ status }: { status?: string }) {
  const variants: Record<string, 'success' | 'danger' | 'warning' | 'default'> = {
    success: 'success',
    error: 'danger',
    running: 'warning',
    never: 'default',
  }
  return (
    <Badge variant={variants[status ?? 'never'] ?? 'default'} size="sm">
      {status ?? 'never'}
    </Badge>
  )
}

export function StatsView() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['stats'],
    queryFn: fetchStats,
    refetchInterval: 60000, // refresh every minute
  })

  if (isLoading) return <LoadingState message="Loading stats..." />
  if (error || !stats) return <ErrorState message="Failed to load stats" />

  const maxCount = Math.max(...stats.by_district.map(d => d.listings_count), 1)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-bold text-slate-100">Overview</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Last updated: {timeAgo(stats.last_updated) ?? '—'}
        </p>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label="Active listings"
          value={stats.total_active_listings.toLocaleString()}
          sub={`${stats.total_listings.toLocaleString()} total`}
          icon={<List size={20} />}
          color="success"
        />
        <StatCard
          label="New today"
          value={stats.new_today}
          sub="since midnight"
          icon={<Zap size={20} />}
          color={stats.new_today > 0 ? 'success' : 'default'}
        />
        <StatCard
          label="Portals active"
          value={stats.by_portal.filter(p => p.scrape_status === 'success').length}
          sub={`of ${stats.by_portal.length} configured`}
          icon={<Building2 size={20} />}
        />
        <StatCard
          label="Districts covered"
          value={stats.by_district.length}
          sub="with listings"
          icon={<BarChart3 size={20} />}
        />
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {/* Portal status */}
        <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">
            Portal status
          </h2>
          <div className="space-y-3">
            {stats.by_portal.map(p => (
              <div key={p.portal_key} className="flex items-center gap-3">
                <ScrapeStatusIcon status={p.scrape_status} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-medium text-slate-200">{p.portal_name}</span>
                    <ScrapeStatusBadge status={p.scrape_status} />
                  </div>
                  <div className="text-xs text-slate-500">
                    {p.last_scrape_at ? `Last scraped: ${timeAgo(p.last_scrape_at)}` : 'Never scraped'}
                    {p.listings_count > 0 && ` · ${p.listings_count.toLocaleString()} listings`}
                  </div>
                </div>
                <div className="text-sm font-semibold text-slate-300 shrink-0">
                  {p.listings_count > 0 ? p.listings_count.toLocaleString() : '—'}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Listings by district */}
        <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">
            Listings by district
          </h2>
          <div className="space-y-2.5">
            {stats.by_district
              .sort((a, b) => b.listings_count - a.listings_count)
              .map(d => (
                <div key={d.district_name}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-slate-300">{d.district_name}</span>
                    <div className="flex items-center gap-3 text-xs">
                      {d.avg_price && (
                        <span className="text-slate-500">avg €{d.avg_price.toLocaleString()}</span>
                      )}
                      <span className="font-semibold text-slate-200">{d.listings_count}</span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-[var(--bg-elevated)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                      style={{ width: `${(d.listings_count / maxCount) * 100}%` }}
                    />
                  </div>
                  {d.min_price != null && d.max_price != null && (
                    <div className="text-xs text-slate-600 mt-0.5">
                      €{d.min_price.toLocaleString()} – €{d.max_price.toLocaleString()}
                    </div>
                  )}
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  )
}
