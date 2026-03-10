import { useQuery } from '@tanstack/react-query'
import { fetchPortals, fetchNeighborhoods } from '../api'
import type { ListingsFilters } from '../types'
import { X } from 'lucide-react'

interface FilterPanelProps {
  filters: ListingsFilters
  onUpdate: (partial: Partial<ListingsFilters>) => void
  onReset: () => void
}

const DISTRICTS = [
  'Centro', 'Salamanca', 'Retiro', 'Chamberí', 'Chamartín', 'Tetuán',
  'Fuencarral-El Pardo', 'Moncloa-Aravaca', 'Latina', 'Carabanchel',
  'Usera', 'Puente de Vallecas', 'Moratalaz', 'Ciudad Lineal',
  'Hortaleza', 'Barajas', 'San Blas-Canillejas', 'Vicálvaro',
  'Villa de Vallecas', 'Arganzuela', 'Getafe', 'Leganés',
]

export function FilterPanel({ filters, onUpdate, onReset }: FilterPanelProps) {
  const { data: portals = [] } = useQuery({ queryKey: ['portals'], queryFn: fetchPortals })
  const { data: neighborhoods = [] } = useQuery({ queryKey: ['neighborhoods'], queryFn: fetchNeighborhoods })

  const activeFilters = [
    filters.price_min || filters.price_max,
    filters.bedrooms,
    filters.size_min || filters.size_max,
    filters.district,
    filters.neighborhood,
    filters.portal,
    !filters.active_only,
  ].filter(Boolean).length

  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Filters</h2>
        {activeFilters > 0 && (
          <button
            onClick={onReset}
            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            <X size={12} />
            Clear ({activeFilters})
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
        {/* Price range */}
        <div className="space-y-1">
          <label className="text-xs text-slate-500 uppercase tracking-wider">Price (€/mo)</label>
          <div className="flex gap-1 items-center">
            <input
              type="number"
              placeholder="Min"
              value={filters.price_min ?? ''}
              onChange={e => onUpdate({ price_min: e.target.value ? Number(e.target.value) : undefined })}
              className="w-full bg-[var(--bg-elevated)] border border-[var(--border)] rounded px-2 py-1.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
            />
            <span className="text-slate-600 text-xs">–</span>
            <input
              type="number"
              placeholder="Max"
              value={filters.price_max ?? ''}
              onChange={e => onUpdate({ price_max: e.target.value ? Number(e.target.value) : undefined })}
              className="w-full bg-[var(--bg-elevated)] border border-[var(--border)] rounded px-2 py-1.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Bedrooms */}
        <div className="space-y-1">
          <label className="text-xs text-slate-500 uppercase tracking-wider">Bedrooms</label>
          <div className="flex gap-1">
            {[undefined, 1, 2, 3, 4].map((val, i) => (
              <button
                key={i}
                onClick={() => onUpdate({ bedrooms: val })}
                className={`flex-1 py-1.5 text-xs rounded border transition-colors ${
                  filters.bedrooms === val
                    ? 'bg-indigo-600 border-indigo-500 text-white'
                    : 'bg-[var(--bg-elevated)] border-[var(--border)] text-slate-400 hover:border-slate-500'
                }`}
              >
                {val == null ? 'Any' : val === 4 ? '4+' : val}
              </button>
            ))}
          </div>
        </div>

        {/* Size range */}
        <div className="space-y-1">
          <label className="text-xs text-slate-500 uppercase tracking-wider">Size (m²)</label>
          <div className="flex gap-1 items-center">
            <input
              type="number"
              placeholder="Min"
              value={filters.size_min ?? ''}
              onChange={e => onUpdate({ size_min: e.target.value ? Number(e.target.value) : undefined })}
              className="w-full bg-[var(--bg-elevated)] border border-[var(--border)] rounded px-2 py-1.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
            />
            <span className="text-slate-600 text-xs">–</span>
            <input
              type="number"
              placeholder="Max"
              value={filters.size_max ?? ''}
              onChange={e => onUpdate({ size_max: e.target.value ? Number(e.target.value) : undefined })}
              className="w-full bg-[var(--bg-elevated)] border border-[var(--border)] rounded px-2 py-1.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* District */}
        <div className="space-y-1">
          <label className="text-xs text-slate-500 uppercase tracking-wider">District</label>
          <select
            value={filters.district ?? ''}
            onChange={e => onUpdate({ district: e.target.value || undefined, neighborhood: undefined })}
            className="w-full bg-[var(--bg-elevated)] border border-[var(--border)] rounded px-2 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All districts</option>
            {DISTRICTS.map(d => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>

        {/* Neighborhood */}
        <div className="space-y-1">
          <label className="text-xs text-slate-500 uppercase tracking-wider">Neighborhood</label>
          <select
            value={filters.neighborhood ?? ''}
            onChange={e => onUpdate({ neighborhood: e.target.value || undefined })}
            className="w-full bg-[var(--bg-elevated)] border border-[var(--border)] rounded px-2 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All</option>
            {neighborhoods
              .filter(n => !filters.district || n.district_name === filters.district || n.municipality === filters.district)
              .map(n => (
                <option key={n.id} value={n.name}>{n.name}</option>
              ))}
          </select>
        </div>

        {/* Portal */}
        <div className="space-y-1">
          <label className="text-xs text-slate-500 uppercase tracking-wider">Portal</label>
          <select
            value={filters.portal ?? ''}
            onChange={e => onUpdate({ portal: e.target.value || undefined })}
            className="w-full bg-[var(--bg-elevated)] border border-[var(--border)] rounded px-2 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All portals</option>
            {portals.map(p => (
              <option key={p.key} value={p.key}>{p.name}</option>
            ))}
          </select>
        </div>

        {/* Active only + sort */}
        <div className="space-y-1">
          <label className="text-xs text-slate-500 uppercase tracking-wider">Sort / Status</label>
          <div className="flex flex-col gap-1.5">
            <select
              value={filters.sort}
              onChange={e => onUpdate({ sort: e.target.value as ListingsFilters['sort'] })}
              className="w-full bg-[var(--bg-elevated)] border border-[var(--border)] rounded px-2 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="newest">Newest first</option>
              <option value="price_asc">Price ↑</option>
              <option value="price_desc">Price ↓</option>
              <option value="size_asc">Size ↑</option>
              <option value="size_desc">Size ↓</option>
            </select>
            <label className="flex items-center gap-2 cursor-pointer">
              <div
                className={`relative w-9 h-5 rounded-full transition-colors ${filters.active_only ? 'bg-indigo-600' : 'bg-slate-700'}`}
                onClick={() => onUpdate({ active_only: !filters.active_only })}
              >
                <div className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${filters.active_only ? 'translate-x-4' : ''}`} />
              </div>
              <span className="text-xs text-slate-400">Active only</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  )
}
