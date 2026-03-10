import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchListing } from '../api'
import { ScoreBar } from './ui/ScoreBar'
import { Badge } from './ui/Badge'
import { Spinner } from './ui/Spinner'
import { X, ExternalLink, ChevronLeft, ChevronRight, BedDouble, Maximize2, Bath, Car, ArrowUpDown, Sofa } from 'lucide-react'

interface ListingDrawerProps {
  listingId: number | null
  onClose: () => void
}

function formatDate(dateStr?: string) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
}

function formatPrice(price?: number) {
  if (!price) return '—'
  return `€${price.toLocaleString()}/mo`
}

export function ListingDrawer({ listingId, onClose }: ListingDrawerProps) {
  const [imgIdx, setImgIdx] = useState(0)

  const { data: listing, isLoading, error } = useQuery({
    queryKey: ['listing', listingId],
    queryFn: () => fetchListing(listingId!),
    enabled: listingId != null,
  })

  if (listingId == null) return null

  const images = listing?.images ?? []
  const hasImages = images.length > 0

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-xl bg-[var(--bg-surface)] border-l border-[var(--border)] z-50 overflow-y-auto flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[var(--border)] sticky top-0 bg-[var(--bg-surface)] z-10">
          <h2 className="text-sm font-semibold text-slate-300 truncate pr-4">
            {isLoading ? 'Loading...' : listing?.title ?? 'Listing detail'}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded hover:bg-slate-700 transition-colors text-slate-400"
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
          <div className="flex-1 flex items-center justify-center text-red-400 text-sm">
            Failed to load listing
          </div>
        )}

        {listing && (
          <div className="flex-1 flex flex-col">
            {/* Image carousel */}
            {hasImages && (
              <div className="relative h-56 bg-slate-900 flex-shrink-0">
                <img
                  src={images[imgIdx]?.url}
                  alt={`Photo ${imgIdx + 1}`}
                  className="w-full h-full object-cover"
                  onError={e => { (e.target as HTMLImageElement).src = 'https://via.placeholder.com/800x400/1a1d27/64748b?text=No+image' }}
                />
                {images.length > 1 && (
                  <>
                    <button
                      onClick={() => setImgIdx(i => Math.max(0, i - 1))}
                      disabled={imgIdx === 0}
                      className="absolute left-2 top-1/2 -translate-y-1/2 bg-black/60 rounded-full p-1 text-white disabled:opacity-30 hover:bg-black/80 transition"
                    >
                      <ChevronLeft size={20} />
                    </button>
                    <button
                      onClick={() => setImgIdx(i => Math.min(images.length - 1, i + 1))}
                      disabled={imgIdx === images.length - 1}
                      className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/60 rounded-full p-1 text-white disabled:opacity-30 hover:bg-black/80 transition"
                    >
                      <ChevronRight size={20} />
                    </button>
                    <div className="absolute bottom-2 right-2 bg-black/60 text-white text-xs px-2 py-0.5 rounded">
                      {imgIdx + 1} / {images.length}
                    </div>
                  </>
                )}
                {!listing.is_active && (
                  <div className="absolute top-2 left-2">
                    <Badge variant="warning">Inactive</Badge>
                  </div>
                )}
              </div>
            )}

            {/* Main CTA */}
            <div className="p-4 border-b border-[var(--border)]">
              <a
                href={listing.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg transition-colors text-sm"
              >
                <ExternalLink size={16} />
                View on {listing.portal_name}
              </a>
            </div>

            <div className="p-4 space-y-5 flex-1">
              {/* Price + key stats */}
              <div>
                <div className="flex items-baseline gap-3 mb-3">
                  <span className="text-3xl font-bold text-indigo-400">
                    {formatPrice(listing.price_eur)}
                  </span>
                  {listing.expenses_included && (
                    <Badge variant="info" size="sm">Gastos incl.</Badge>
                  )}
                  {!listing.is_active && (
                    <Badge variant="warning" size="sm">Inactive</Badge>
                  )}
                </div>

                <div className="grid grid-cols-4 gap-2">
                  <div className="bg-[var(--bg-elevated)] rounded p-2 text-center">
                    <BedDouble size={14} className="mx-auto text-slate-500 mb-1" />
                    <div className="text-sm font-semibold text-slate-200">{listing.bedrooms ?? '—'}</div>
                    <div className="text-xs text-slate-500">beds</div>
                  </div>
                  <div className="bg-[var(--bg-elevated)] rounded p-2 text-center">
                    <Bath size={14} className="mx-auto text-slate-500 mb-1" />
                    <div className="text-sm font-semibold text-slate-200">{listing.bathrooms ?? '—'}</div>
                    <div className="text-xs text-slate-500">baths</div>
                  </div>
                  <div className="bg-[var(--bg-elevated)] rounded p-2 text-center">
                    <Maximize2 size={14} className="mx-auto text-slate-500 mb-1" />
                    <div className="text-sm font-semibold text-slate-200">{listing.size_m2 ? `${listing.size_m2}` : '—'}</div>
                    <div className="text-xs text-slate-500">m²</div>
                  </div>
                  <div className="bg-[var(--bg-elevated)] rounded p-2 text-center">
                    <div className="text-xs text-slate-500 mb-1">€/m²</div>
                    <div className="text-sm font-semibold text-slate-200">
                      {listing.price_eur && listing.size_m2 ? Math.round(listing.price_eur / Number(listing.size_m2)) : '—'}
                    </div>
                    <div className="text-xs text-slate-500">ratio</div>
                  </div>
                </div>
              </div>

              {/* Amenities */}
              <div className="flex flex-wrap gap-2">
                {listing.furnished && <span className="flex items-center gap-1 text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded"><Sofa size={12} /> Furnished</span>}
                {listing.elevator && <span className="flex items-center gap-1 text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded"><ArrowUpDown size={12} /> Elevator</span>}
                {listing.parking && <span className="flex items-center gap-1 text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded"><Car size={12} /> Parking</span>}
                {listing.deposit_eur && <span className="text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded">Deposit: €{listing.deposit_eur.toLocaleString()}</span>}
                {listing.property_type && <span className="text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded capitalize">{listing.property_type}</span>}
              </div>

              {/* Location */}
              <div>
                <h3 className="text-xs text-slate-500 uppercase tracking-wider mb-2">Location</h3>
                <div className="space-y-1 text-sm text-slate-300">
                  {listing.address_raw && <div className="text-slate-400">{listing.address_raw}</div>}
                  <div className="flex gap-2 flex-wrap">
                    {listing.neighborhood_name && (
                      <span className="bg-slate-800 px-2 py-0.5 rounded text-xs">{listing.neighborhood_name}</span>
                    )}
                    {listing.district_name && (
                      <span className="bg-slate-800 px-2 py-0.5 rounded text-xs">{listing.district_name}</span>
                    )}
                    {listing.municipality_raw && listing.municipality_raw !== 'Madrid' && (
                      <span className="bg-slate-800 px-2 py-0.5 rounded text-xs">{listing.municipality_raw}</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Neighborhood scores */}
              {(listing.neighborhood_safety_score != null || listing.neighborhood_transport_score != null) && (
                <div>
                  <h3 className="text-xs text-slate-500 uppercase tracking-wider mb-2">Neighborhood</h3>
                  <div className="bg-[var(--bg-elevated)] rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-400">Safety</span>
                      <ScoreBar score={listing.neighborhood_safety_score} />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-400">Transport</span>
                      <ScoreBar score={listing.neighborhood_transport_score} />
                    </div>
                  </div>
                </div>
              )}

              {/* Rent benchmarks */}
              {(listing.district_avg_rent_1bed || listing.district_avg_rent_2bed || listing.district_avg_rent_3bed) && (
                <div>
                  <h3 className="text-xs text-slate-500 uppercase tracking-wider mb-2">
                    Benchmark rent — {listing.district_name}
                  </h3>
                  <div className="bg-[var(--bg-elevated)] rounded-lg p-3 grid grid-cols-3 gap-2 text-center">
                    <div>
                      <div className="text-xs text-slate-500 mb-1">1 bed</div>
                      <div className="text-sm font-semibold text-slate-200">
                        {listing.district_avg_rent_1bed ? `€${listing.district_avg_rent_1bed}` : '—'}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 mb-1">2 bed</div>
                      <div className="text-sm font-semibold text-slate-200">
                        {listing.district_avg_rent_2bed ? `€${listing.district_avg_rent_2bed}` : '—'}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 mb-1">3 bed</div>
                      <div className="text-sm font-semibold text-slate-200">
                        {listing.district_avg_rent_3bed ? `€${listing.district_avg_rent_3bed}` : '—'}
                      </div>
                    </div>
                  </div>
                  {listing.price_eur && listing.bedrooms && (() => {
                    const benchmarks: Record<number, number | undefined> = {
                      1: listing.district_avg_rent_1bed,
                      2: listing.district_avg_rent_2bed,
                      3: listing.district_avg_rent_3bed,
                    }
                    const bench = benchmarks[Math.min(listing.bedrooms, 3)]
                    if (!bench) return null
                    const pct = Math.round(((listing.price_eur - bench) / bench) * 100)
                    return (
                      <p className={`text-xs mt-2 ${pct > 0 ? 'text-orange-400' : 'text-emerald-400'}`}>
                        {pct > 0 ? `▲ ${pct}% above` : `▼ ${Math.abs(pct)}% below`} district benchmark
                      </p>
                    )
                  })()}
                </div>
              )}

              {/* Description */}
              {listing.description && (
                <div>
                  <h3 className="text-xs text-slate-500 uppercase tracking-wider mb-2">Description</h3>
                  <p className="text-sm text-slate-400 leading-relaxed whitespace-pre-wrap">{listing.description}</p>
                </div>
              )}

              {/* Metadata */}
              <div>
                <h3 className="text-xs text-slate-500 uppercase tracking-wider mb-2">Tracking</h3>
                <div className="bg-[var(--bg-elevated)] rounded-lg p-3 grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <div className="text-slate-500 mb-0.5">First seen</div>
                    <div className="text-slate-300">{formatDate(listing.first_seen_at)}</div>
                  </div>
                  <div>
                    <div className="text-slate-500 mb-0.5">Last seen</div>
                    <div className="text-slate-300">{formatDate(listing.last_seen_at)}</div>
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
              </div>
            </div>

            {/* Sticky bottom CTA */}
            <div className="sticky bottom-0 p-4 border-t border-[var(--border)] bg-[var(--bg-surface)]">
              <a
                href={listing.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg transition-colors text-sm"
              >
                <ExternalLink size={16} />
                Open on {listing.portal_name} →
              </a>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
