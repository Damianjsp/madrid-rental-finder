import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { fetchListings } from '../api'
import type { Listing, ListingsFilters } from '../types'
import { FilterPanel } from '../components/FilterPanel'
import { ListingDrawer } from '../components/ListingDrawer'
import { Badge } from '../components/ui/Badge'
import { ScoreDot } from '../components/ui/ScoreBar'
import { LoadingState, ErrorState } from '../components/ui/Spinner'
import { useLastVisit } from '../hooks/useLastVisit'
import { formatRelativeDate } from '../lib/date'
import { ExternalLink, ChevronLeft, ChevronRight } from 'lucide-react'

const col = createColumnHelper<Listing>()

interface ListingsViewProps {
  filters: ListingsFilters
  onUpdate: (partial: Partial<ListingsFilters>) => void
  onSetPage: (page: number) => void
  onReset: () => void
}

function getPageWindow(page: number, pages: number): Array<number | 'ellipsis'> {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1)
  if (page <= 4) return [1, 2, 3, 4, 5, 'ellipsis', pages]
  if (page >= pages - 3) return [1, 'ellipsis', pages - 4, pages - 3, pages - 2, pages - 1, pages]
  return [1, 'ellipsis', page - 1, page, page + 1, 'ellipsis', pages]
}

export function ListingsView({ filters, onUpdate, onSetPage, onReset }: ListingsViewProps) {
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const { isNew } = useLastVisit()

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ['listings', filters],
    queryFn: () => fetchListings(filters),
    placeholderData: prev => prev,
  })

  const columns = useMemo(() => [
    col.accessor('price_eur', {
      header: 'Price',
      enableSorting: false,
      cell: info => {
        const val = info.getValue()
        const listing = info.row.original
        return (
          <div className="flex flex-col min-w-[96px]">
            <span className="font-semibold text-indigo-300">
              {val ? `€${val.toLocaleString()}` : '—'}
            </span>
            {listing.expenses_included && <span className="text-xs text-slate-500">gastos incl.</span>}
          </div>
        )
      },
    }),
    col.accessor('bedrooms', {
      header: 'Beds',
      enableSorting: false,
      cell: info => <span className="text-slate-300">{info.getValue() ?? '—'}</span>,
    }),
    col.accessor('size_m2', {
      header: 'm²',
      enableSorting: false,
      cell: info => {
        const val = info.getValue()
        return <span className="text-slate-300">{val ? Number(val).toFixed(0) : '—'}</span>
      },
    }),
    col.accessor('neighborhood_name', {
      header: 'Neighborhood',
      enableSorting: false,
      cell: info => <span className="text-slate-300 inline-block min-w-[140px]">{info.getValue() ?? info.row.original.neighborhood_raw ?? '—'}</span>,
    }),
    col.accessor('district_name', {
      header: 'District',
      enableSorting: false,
      cell: info => <span className="text-slate-400 text-sm inline-block min-w-[120px]">{info.getValue() ?? info.row.original.district_raw ?? '—'}</span>,
    }),
    col.accessor('portal_name', {
      header: 'Portal',
      enableSorting: false,
      cell: info => {
        const listing = info.row.original
        return (
          <a
            href={listing.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium transition-colors group min-w-[100px]"
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
      enableSorting: false,
      cell: info => <ScoreDot score={info.getValue()} />,
    }),
    col.accessor('neighborhood_transport_score', {
      header: 'Transit',
      enableSorting: false,
      cell: info => <ScoreDot score={info.getValue()} />,
    }),
    col.accessor('first_seen_at', {
      header: 'First seen',
      enableSorting: false,
      cell: info => {
        const val = info.getValue()
        const listing = info.row.original
        return (
          <div className="flex items-center gap-2 min-w-[132px]">
            <span className="text-slate-400 text-sm">{formatRelativeDate(val)}</span>
            {isNew(val) && <Badge variant="new" size="sm">NEW</Badge>}
            {!listing.is_active && <Badge variant="warning" size="sm">off</Badge>}
          </div>
        )
      },
    }),
    col.accessor('last_seen_at', {
      header: 'Last seen',
      enableSorting: false,
      cell: info => <span className="text-slate-500 text-sm inline-block min-w-[96px]">{formatRelativeDate(info.getValue())}</span>,
    }),
  ], [isNew])

  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Table intentionally returns non-memoizable helpers; this component does not pass them into memoized hooks/components.
  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    manualSorting: true,
    pageCount: data?.pages ?? 0,
  })

  const total = data?.total ?? 0
  const pages = data?.pages ?? 0
  const page = filters.page
  const perPage = filters.per_page
  const pageWindow = getPageWindow(page, pages)

  return (
    <div className="flex flex-col gap-4 min-w-0">
      <FilterPanel filters={filters} onUpdate={onUpdate} onReset={onReset} />

      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
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
          className="bg-[var(--bg-elevated)] border border-[var(--border)] rounded px-2 py-1 text-xs text-slate-400 shrink-0"
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
          <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[980px] text-sm">
                <thead>
                  {table.getHeaderGroups().map(hg => (
                    <tr key={hg.id} className="border-b border-[var(--border)]">
                      {hg.headers.map(header => (
                        <th
                          key={header.id}
                          className="px-3 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider bg-[var(--bg-elevated)] first:rounded-tl-lg last:rounded-tr-lg whitespace-nowrap"
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
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
            <div className="px-3 py-2 border-t border-[var(--border)] text-xs text-slate-500 bg-[var(--bg-elevated)]">
              Scroll horizontally to see all columns →
            </div>
          </div>

          {pages > 1 && (
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <span className="text-xs text-slate-500">
                Page {page} of {pages} · {total} results
              </span>
              <div className="flex items-center gap-1 flex-wrap">
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
                {pageWindow.map((item, index) => (
                  item === 'ellipsis' ? (
                    <span key={`ellipsis-${index}`} className="px-1 text-slate-500">…</span>
                  ) : (
                    <button
                      key={item}
                      onClick={() => onSetPage(item)}
                      className={`px-2.5 py-1 text-xs rounded border transition-colors ${
                        item === page
                          ? 'bg-indigo-600 border-indigo-500 text-white'
                          : 'bg-[var(--bg-elevated)] border-[var(--border)] text-slate-400 hover:border-slate-500'
                      }`}
                    >
                      {item}
                    </button>
                  )
                ))}
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

      <ListingDrawer listingId={selectedId} onClose={() => setSelectedId(null)} />
    </div>
  )
}
