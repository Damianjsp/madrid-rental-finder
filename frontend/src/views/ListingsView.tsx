import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
  getSortedRowModel,
} from '@tanstack/react-table'
import type { SortingState } from '@tanstack/react-table'
import { fetchListings } from '../api'
import type { Listing, ListingsFilters } from '../types'
import { FilterPanel } from '../components/FilterPanel'
import { ListingDrawer } from '../components/ListingDrawer'
import { Badge } from '../components/ui/Badge'
import { ScoreDot } from '../components/ui/ScoreBar'
import { LoadingState, ErrorState } from '../components/ui/Spinner'
import { useLastVisit } from '../hooks/useLastVisit'
import { ExternalLink, ChevronLeft, ChevronRight, ChevronUp, ChevronDown } from 'lucide-react'

const col = createColumnHelper<Listing>()

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  const now = new Date()
  const diffH = (now.getTime() - d.getTime()) / 3600000
  if (diffH < 24) return `${Math.round(diffH)}h ago`
  const diffD = Math.floor(diffH / 24)
  if (diffD < 7) return `${diffD}d ago`
  return d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })
}

interface ListingsViewProps {
  filters: ListingsFilters
  onUpdate: (partial: Partial<ListingsFilters>) => void
  onSetPage: (page: number) => void
  onReset: () => void
}

export function ListingsView({ filters, onUpdate, onSetPage, onReset }: ListingsViewProps) {
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [sorting, setSorting] = useState<SortingState>([])
  const { isNew } = useLastVisit()

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ['listings', filters],
    queryFn: () => fetchListings(filters),
    placeholderData: (prev) => prev,
  })

  const columns = [
    col.accessor('price_eur', {
      header: 'Price',
      cell: info => {
        const val = info.getValue()
        const listing = info.row.original
        return (
          <div className="flex flex-col">
            <span className="font-semibold text-indigo-300">
              {val ? `€${val.toLocaleString()}` : '—'}
            </span>
            {listing.expenses_included && (
              <span className="text-xs text-slate-500">gastos incl.</span>
            )}
          </div>
        )
      },
    }),
    col.accessor('bedrooms', {
      header: 'Beds',
      cell: info => <span className="text-slate-300">{info.getValue() ?? '—'}</span>,
    }),
    col.accessor('size_m2', {
      header: 'm²',
      cell: info => {
        const val = info.getValue()
        return <span className="text-slate-300">{val ? Number(val).toFixed(0) : '—'}</span>
      },
    }),
    col.accessor('neighborhood_name', {
      header: 'Neighborhood',
      cell: info => <span className="text-slate-300">{info.getValue() ?? info.row.original.neighborhood_raw ?? '—'}</span>,
    }),
    col.accessor('district_name', {
      header: 'District',
      cell: info => <span className="text-slate-400 text-sm">{info.getValue() ?? info.row.original.district_raw ?? '—'}</span>,
    }),
    col.accessor('portal_name', {
      header: 'Portal',
      cell: info => {
        const listing = info.row.original
        return (
          <a
            href={listing.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium transition-colors group"
            title={listing.url}
          >
            <span>{info.getValue()}</span>
            <ExternalLink size={11} className="opacity-0 group-hover:opacity-100 transition-opacity" />
          </a>
        )
      },
    }),
    col.accessor('neighborhood_safety_score', {
      header: 'Safety',
      cell: info => <ScoreDot score={info.getValue()} />,
    }),
    col.accessor('neighborhood_transport_score', {
      header: 'Transit',
      cell: info => <ScoreDot score={info.getValue()} />,
    }),
    col.accessor('first_seen_at', {
      header: 'First seen',
      cell: info => {
        const val = info.getValue()
        const listing = info.row.original
        return (
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-sm">{formatDate(val)}</span>
            {isNew(val) && <Badge variant="new" size="sm">NEW</Badge>}
            {!listing.is_active && <Badge variant="warning" size="sm">off</Badge>}
          </div>
        )
      },
    }),
    col.accessor('last_seen_at', {
      header: 'Last seen',
      cell: info => <span className="text-slate-500 text-sm">{formatDate(info.getValue())}</span>,
    }),
  ]

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualPagination: true,
    pageCount: data?.pages ?? 0,
  })

  const total = data?.total ?? 0
  const pages = data?.pages ?? 0
  const page = filters.page
  const perPage = filters.per_page

  return (
    <div className="flex flex-col gap-4">
      <FilterPanel filters={filters} onUpdate={onUpdate} onReset={onReset} />

      {/* Results header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-400">
            {isLoading ? 'Loading...' : `${total} listing${total !== 1 ? 's' : ''}`}
          </span>
          {isFetching && !isLoading && (
            <div className="w-4 h-4 border-2 border-slate-600 border-t-indigo-400 rounded-full animate-spin" />
          )}
        </div>
        <select
          value={perPage}
          onChange={e => onUpdate({ per_page: Number(e.target.value) })}
          className="bg-[var(--bg-elevated)] border border-[var(--border)] rounded px-2 py-1 text-xs text-slate-400"
        >
          <option value={10}>10 / page</option>
          <option value={25}>25 / page</option>
          <option value={50}>50 / page</option>
        </select>
      </div>

      {isLoading && <LoadingState message="Loading listings..." />}
      {error && <ErrorState message="Failed to load listings" />}

      {!isLoading && !error && (
        <>
          {/* Table */}
          <div className="rounded-lg border border-[var(--border)] overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                {table.getHeaderGroups().map(hg => (
                  <tr key={hg.id} className="border-b border-[var(--border)]">
                    {hg.headers.map(header => (
                      <th
                        key={header.id}
                        className={`px-3 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider bg-[var(--bg-elevated)] first:rounded-tl-lg last:rounded-tr-lg ${header.column.getCanSort() ? 'cursor-pointer select-none hover:text-slate-300 transition-colors' : ''}`}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        <div className="flex items-center gap-1">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {header.column.getIsSorted() === 'asc' && <ChevronUp size={12} />}
                          {header.column.getIsSorted() === 'desc' && <ChevronDown size={12} />}
                        </div>
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length} className="px-3 py-12 text-center text-slate-500">
                      No listings match your filters
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map(row => (
                    <tr
                      key={row.id}
                      className="border-b border-[var(--border)] hover:bg-[var(--bg-elevated)] cursor-pointer transition-colors group"
                      onClick={() => setSelectedId(row.original.id)}
                    >
                      {row.getVisibleCells().map(cell => (
                        <td key={cell.id} className="px-3 py-3 whitespace-nowrap">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {pages > 1 && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500">
                Page {page} of {pages} · {total} results
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => onSetPage(1)}
                  disabled={page <= 1}
                  className="px-2 py-1 text-xs rounded bg-[var(--bg-elevated)] border border-[var(--border)] text-slate-400 disabled:opacity-30 hover:border-slate-500 transition-colors"
                >
                  «
                </button>
                <button
                  onClick={() => onSetPage(page - 1)}
                  disabled={page <= 1}
                  className="px-2 py-1 text-xs rounded bg-[var(--bg-elevated)] border border-[var(--border)] text-slate-400 disabled:opacity-30 hover:border-slate-500 transition-colors flex items-center gap-1"
                >
                  <ChevronLeft size={12} /> Prev
                </button>
                {Array.from({ length: Math.min(pages, 7) }).map((_, i) => {
                  const p = i + 1
                  return (
                    <button
                      key={p}
                      onClick={() => onSetPage(p)}
                      className={`px-2.5 py-1 text-xs rounded border transition-colors ${
                        p === page
                          ? 'bg-indigo-600 border-indigo-500 text-white'
                          : 'bg-[var(--bg-elevated)] border-[var(--border)] text-slate-400 hover:border-slate-500'
                      }`}
                    >
                      {p}
                    </button>
                  )
                })}
                <button
                  onClick={() => onSetPage(page + 1)}
                  disabled={page >= pages}
                  className="px-2 py-1 text-xs rounded bg-[var(--bg-elevated)] border border-[var(--border)] text-slate-400 disabled:opacity-30 hover:border-slate-500 transition-colors flex items-center gap-1"
                >
                  Next <ChevronRight size={12} />
                </button>
                <button
                  onClick={() => onSetPage(pages)}
                  disabled={page >= pages}
                  className="px-2 py-1 text-xs rounded bg-[var(--bg-elevated)] border border-[var(--border)] text-slate-400 disabled:opacity-30 hover:border-slate-500 transition-colors"
                >
                  »
                </button>
              </div>
            </div>
          )}
        </>
      )}

      <ListingDrawer
        listingId={selectedId}
        onClose={() => setSelectedId(null)}
      />
    </div>
  )
}
