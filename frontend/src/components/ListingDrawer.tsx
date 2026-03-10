import { useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchListing } from '../api'
import { ScoreBar } from './ui/ScoreBar'
import { Badge } from './ui/Badge'
import { Spinner } from './ui/Spinner'
import { formatRelativeDate } from '../lib/date'
import {
  X,
  ExternalLink,
  BedDouble,
  Maximize2,
  Bath,
  Car,
  ArrowUpDown,
  Sofa,
  MapPin,
  Building2,
  Shield,
  Train,
} from 'lucide-react'

interface ListingDrawerProps {
  listingId: number | null
  onClose: () => void
}

function formatPrice(price?: number) {
  if (!price) return '—'
  return `€${price.toLocaleString()}/mo`
}

function formatValue(value?: number, suffix = '') {
  if (value == null) return '—'
  return `${value.toLocaleString()}${suffix}`
}

export function ListingDrawer({ listingId, onClose }: ListingDrawerProps) {
  const { data: listing, isLoading, error } = useQuery({
    queryKey: ['listing', listingId],
    queryFn: () => fetchListing(listingId!),
    enabled: listingId != null,
  })

  useEffect(() => {
    if (listingId == null) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [listingId, onClose])

  const metrics = useMemo(() => {
    if (!listing) return { pricePerM2: null as number | null, benchmark: null as null | { beds: number; pct: number } }

    const pricePerM2 = listing.price_eur && listing.size_m2
      ? Math.round(listing.price_eur / Number(listing.size_m2))
      : null

    const beds = Math.min(listing.bedrooms ?? 0, 3)
    const benchmarkMap: Record<number, number | undefined> = {
      1: listing.district_avg_rent_1bed,
      2: listing.district_avg_rent_2bed,
      3: listing.district_avg_rent_3bed,
    }
    const benchmarkValue = beds > 0 ? benchmarkMap[beds] : undefined
    const benchmark = benchmarkValue && listing.price_eur
      ? { beds, pct: Math.round(((listing.price_eur - benchmarkValue) / benchmarkValue) * 100) }
      : null

    return { pricePerM2, benchmark }
  }, [listing])

  if (listingId == null) return null

  const images = listing?.images ?? []
  const hasImages = images.length > 0
  const imgIdx = 0

  return (
    <>
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity" onClick={onClose} aria-hidden="true" />

      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="listing-drawer-title"
        className="fixed right-0 top-0 bottom-0 w-full max-w-xl bg-[var(--bg)] border-l border-[var(--border)] z-50 overflow-y-auto flex flex-col shadow-2xl text-slate-100"
      >
        <div className="flex items-center justify-between p-4 border-b border-[var(--border)] sticky top-0 bg-[var(--bg)]/95 backdrop-blur z-10">
          <h2 id="listing-drawer-title" className="text-sm font-semibold text-slate-200 truncate pr-4">
            {isLoading ? 'Loading...' : listing?.title ?? 'Listing detail'}
          </h2>
          <button
            onClick={onClose}
            aria-label="Close listing details"
            className="p-1.5 rounded hover:bg-slate-800 transition-colors text-slate-400"
          >
            <X size={18} />
          </button>
        </div>

        {isLoading && (
          <div className="flex-1 flex items-center justify-center">
            <Spinner size="lg" />
          </div>
        )}

        {error && (
          <div className="flex-1 flex items-center justify-center text-red-400 text-sm px-6 text-center">
            Failed to load listing
          </div>
        )}

        {listing && (
          <div className="flex-1 flex flex-col bg-[var(--bg)]">
            {hasImages && (
              <div className="relative h-56 bg-slate-950 flex-shrink-0">
                <img
                  src={images[imgIdx]?.url}
                  alt={`Listing photo ${imgIdx + 1}`}
                  className="w-full h-full object-cover"
                  onError={e => { (e.target as HTMLImageElement).src = 'https://via.placeholder.com/800x400/111827/64748b?text=No+image' }}
                />
                {images.length > 1 && (
                  <div className="absolute bottom-2 right-2 bg-black/60 text-white text-xs px-2 py-0.5 rounded">
                    1 / {images.length}
                  </div>
                )}
                {!listing.is_active && (
                  <div className="absolute top-2 left-2">
                    <Badge variant="warning">Inactive</Badge>
                  </div>
                )}
              </div>
            )}

            <div className="p-5 space-y-6 flex-1">
              <section className="space-y-4">
                <div>
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <span className="text-4xl font-bold text-indigo-300 leading-none">{formatPrice(listing.price_eur)}</span>
                    {listing.expenses_included && <Badge variant="info" size="sm">Gastos incl.</Badge>}
                    {!listing.is_active && <Badge variant="warning" size="sm">Inactive</Badge>}
                  </div>
                  <div className="text-sm text-slate-400 flex items-center gap-2 flex-wrap">
                    <span className="inline-flex items-center gap-1"><Building2 size={14} /> {listing.property_type ?? 'Property'}</span>
                    <span>•</span>
                    <span>{formatRelativeDate(listing.last_seen_at)}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-[var(--bg-elevated)] rounded-lg p-3 text-center">
                    <BedDouble size={14} className="mx-auto text-slate-500 mb-1" />
                    <div className="text-base font-semibold text-slate-100">{formatValue(listing.bedrooms)}</div>
                    <div className="text-xs text-slate-500">Bedrooms</div>
                  </div>
                  <div className="bg-[var(--bg-elevated)] rounded-lg p-3 text-center">
                    <Bath size={14} className="mx-auto text-slate-500 mb-1" />
                    <div className="text-base font-semibold text-slate-100">{formatValue(listing.bathrooms)}</div>
                    <div className="text-xs text-slate-500">Bathrooms</div>
                  </div>
                  <div className="bg-[var(--bg-elevated)] rounded-lg p-3 text-center">
                    <Maximize2 size={14} className="mx-auto text-slate-500 mb-1" />
                    <div className="text-base font-semibold text-slate-100">{formatValue(listing.size_m2, ' m²')}</div>
                    <div className="text-xs text-slate-500">Size</div>
                  </div>
                  <div className="bg-[var(--bg-elevated)] rounded-lg p-3 text-center">
                    <div className="text-xs text-slate-500 mb-1">€/m²</div>
                    <div className="text-base font-semibold text-slate-100">{metrics.pricePerM2 ? `€${metrics.pricePerM2}` : '—'}</div>
                    <div className="text-xs text-slate-500">Ratio</div>
                  </div>
                </div>
              </section>

              <section className="space-y-3">
                <h3 className="text-xs text-slate-500 uppercase tracking-wider">Property details</h3>
                <div className="flex flex-wrap gap-2">
                  {listing.property_type && <span className="text-xs text-slate-300 bg-slate-800 px-2 py-1 rounded capitalize">{listing.property_type}</span>}
                  <span className={`flex items-center gap-1 text-xs px-2 py-1 rounded ${listing.furnished ? 'text-slate-200 bg-slate-800' : 'text-slate-500 bg-slate-900'}`}><Sofa size={12} /> {listing.furnished ? 'Furnished' : 'Not furnished'}</span>
                  <span className={`flex items-center gap-1 text-xs px-2 py-1 rounded ${listing.elevator ? 'text-slate-200 bg-slate-800' : 'text-slate-500 bg-slate-900'}`}><ArrowUpDown size={12} /> {listing.elevator ? 'Elevator' : 'No elevator'}</span>
                  <span className={`flex items-center gap-1 text-xs px-2 py-1 rounded ${listing.parking ? 'text-slate-200 bg-slate-800' : 'text-slate-500 bg-slate-900'}`}><Car size={12} /> {listing.parking ? 'Parking' : 'No parking'}</span>
                  {listing.deposit_eur != null && <span className="text-xs text-slate-300 bg-slate-800 px-2 py-1 rounded">Deposit: €{listing.deposit_eur.toLocaleString()}</span>}
                </div>
              </section>

              <section className="space-y-3">
                <h3 className="text-xs text-slate-500 uppercase tracking-wider">Location</h3>
                <div className="bg-[var(--bg-elevated)] rounded-lg p-4 space-y-3">
                  {listing.address_raw && (
                    <div className="flex items-start gap-2 text-sm text-slate-300">
                      <MapPin size={15} className="mt-0.5 text-slate-500 shrink-0" />
                      <span>{listing.address_raw}</span>
                    </div>
                  )}
                  <div className="flex gap-2 flex-wrap">
                    {listing.neighborhood_name && <span className="bg-slate-800 px-2 py-1 rounded text-xs text-slate-200">{listing.neighborhood_name}</span>}
                    {listing.district_name && <span className="bg-slate-800 px-2 py-1 rounded text-xs text-slate-200">{listing.district_name}</span>}
                    {listing.municipality_raw && listing.municipality_raw !== 'Madrid' && <span className="bg-slate-800 px-2 py-1 rounded text-xs text-slate-200">{listing.municipality_raw}</span>}
                  </div>
                </div>
              </section>

              {(listing.neighborhood_safety_score != null || listing.neighborhood_transport_score != null) && (
                <section className="space-y-3">
                  <h3 className="text-xs text-slate-500 uppercase tracking-wider">Neighborhood scores</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="bg-[var(--bg-elevated)] rounded-lg p-4 space-y-2">
                      <div className="flex items-center gap-2 text-sm text-slate-300">
                        <Shield size={16} className="text-emerald-400" />
                        <span>Safety score</span>
                      </div>
                      <ScoreBar score={listing.neighborhood_safety_score} label={listing.neighborhood_safety_score != null ? `${listing.neighborhood_safety_score}/5` : undefined} />
                    </div>
                    <div className="bg-[var(--bg-elevated)] rounded-lg p-4 space-y-2">
                      <div className="flex items-center gap-2 text-sm text-slate-300">
                        <Train size={16} className="text-sky-400" />
                        <span>Transport score</span>
                      </div>
                      <ScoreBar score={listing.neighborhood_transport_score} label={listing.neighborhood_transport_score != null ? `${listing.neighborhood_transport_score}/5` : undefined} />
                    </div>
                  </div>
                </section>
              )}

              {(listing.district_avg_rent_1bed || listing.district_avg_rent_2bed || listing.district_avg_rent_3bed) && (
                <section className="space-y-3">
                  <h3 className="text-xs text-slate-500 uppercase tracking-wider">District benchmark</h3>
                  <div className="bg-[var(--bg-elevated)] rounded-lg p-4 space-y-3">
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div>
                        <div className="text-xs text-slate-500 mb-1">1 bed</div>
                        <div className="text-sm font-semibold text-slate-200">{listing.district_avg_rent_1bed ? `€${listing.district_avg_rent_1bed}` : '—'}</div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-500 mb-1">2 bed</div>
                        <div className="text-sm font-semibold text-slate-200">{listing.district_avg_rent_2bed ? `€${listing.district_avg_rent_2bed}` : '—'}</div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-500 mb-1">3 bed</div>
                        <div className="text-sm font-semibold text-slate-200">{listing.district_avg_rent_3bed ? `€${listing.district_avg_rent_3bed}` : '—'}</div>
                      </div>
                    </div>
                    {metrics.benchmark && (
                      <p className={`text-sm font-medium ${metrics.benchmark.pct > 0 ? 'text-orange-400' : metrics.benchmark.pct < 0 ? 'text-emerald-400' : 'text-slate-300'}`}>
                        {metrics.benchmark.pct > 0 && `${metrics.benchmark.pct}% above district avg for ${metrics.benchmark.beds}bed`}
                        {metrics.benchmark.pct < 0 && `${Math.abs(metrics.benchmark.pct)}% below district avg for ${metrics.benchmark.beds}bed`}
                        {metrics.benchmark.pct === 0 && `At district avg for ${metrics.benchmark.beds}bed`}
                      </p>
                    )}
                  </div>
                </section>
              )}

              {listing.description && (
                <section className="space-y-3">
                  <h3 className="text-xs text-slate-500 uppercase tracking-wider">Description</h3>
                  <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{listing.description}</p>
                </section>
              )}

              <section className="space-y-3">
                <h3 className="text-xs text-slate-500 uppercase tracking-wider">Tracking</h3>
                <div className="bg-[var(--bg-elevated)] rounded-lg p-4 grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <div className="text-slate-500 mb-0.5">First seen</div>
                    <div className="text-slate-300">{formatRelativeDate(listing.first_seen_at)}</div>
                  </div>
                  <div>
                    <div className="text-slate-500 mb-0.5">Last seen</div>
                    <div className="text-slate-300">{formatRelativeDate(listing.last_seen_at)}</div>
                  </div>
                  <div>
                    <div className="text-slate-500 mb-0.5">Portal</div>
                    <div className="text-slate-300">{listing.portal_name}</div>
                  </div>
                  <div>
                    <div className="text-slate-500 mb-0.5">Status</div>
                    <div className={listing.is_active ? 'text-emerald-400' : 'text-amber-400'}>
                      {listing.is_active ? 'Active' : 'Inactive'}
                    </div>
                  </div>
                </div>
              </section>
            </div>

            <div className="sticky bottom-0 p-4 border-t border-[var(--border)] bg-[var(--bg)]/95 backdrop-blur">
              <a
                href={listing.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg transition-colors text-sm"
              >
                <ExternalLink size={16} />
                View on {listing.portal_name} →
              </a>
            </div>
          </div>
        )}
      </aside>
    </>
  )
}
