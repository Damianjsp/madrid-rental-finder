import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import type { SortingState } from '@tanstack/react-table'
import { fetchNeighborhoods } from '../api'
import type { Neighborhood } from '../types'
import { LoadingState, ErrorState } from '../components/ui/Spinner'
import { ScoreBar } from '../components/ui/ScoreBar'
import { ChevronUp, ChevronDown } from 'lucide-react'

const col = createColumnHelper<Neighborhood>()

function fmt(val?: number, prefix = '€') {
  if (val == null) return '—'
  return `${prefix}${val.toLocaleString()}`
}

function CommuteCell({ min, max }: { min?: number; max?: number }) {
  if (min == null && max == null) return <span className="text-slate-600">—</span>
  return (
    <span className="text-slate-300">
      {min}–{max} min
    </span>
  )
}

function ZoneBadge({ zone }: { zone?: string }) {
  if (!zone) return <span className="text-slate-600">—</span>
  const colors: Record<string, string> = {
    A: 'bg-emerald-900/50 text-emerald-400 border-emerald-800',
    B1: 'bg-blue-900/50 text-blue-400 border-blue-800',
    B2: 'bg-slate-700 text-slate-300 border-slate-600',
    C1: 'bg-amber-900/50 text-amber-400 border-amber-800',
    C2: 'bg-orange-900/50 text-orange-400 border-orange-800',
  }
  const cls = colors[zone] ?? 'bg-slate-700 text-slate-300 border-slate-600'
  return (
    <span className={`inline-block text-xs px-1.5 py-0.5 rounded border ${cls}`}>
      {zone}
    </span>
  )
}

export function NeighborhoodsView() {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'safety_score', desc: true }])
  const [search, setSearch] = useState('')

  const { data: raw = [], isLoading, error } = useQuery({
    queryKey: ['neighborhoods'],
    queryFn: fetchNeighborhoods,
  })

  const data = raw.filter(n =>
    !search || n.name.toLowerCase().includes(search.toLowerCase()) ||
    n.district_name?.toLowerCase().includes(search.toLowerCase()) ||
    n.municipality.toLowerCase().includes(search.toLowerCase())
  )

  const columns = [
    col.accessor('name', {
      header: 'Neighborhood',
      cell: info => <span className="text-slate-200 font-medium">{info.getValue()}</span>,
    }),
    col.accessor('district_name', {
      header: 'District',
      cell: info => {
        const n = info.row.original
        const label = info.getValue() ?? (n.municipality !== 'Madrid' ? n.municipality : undefined)
        return <span className="text-slate-400 text-sm">{label ?? '—'}</span>
      },
    }),
    col.accessor('zone', {
      header: 'Zone',
      cell: info => <ZoneBadge zone={info.getValue()} />,
    }),
    col.accessor('safety_score', {
      header: 'Safety',
      cell: info => <ScoreBar score={info.getValue()} />,
    }),
    col.accessor('transport_score', {
      header: 'Transport',
      cell: info => <ScoreBar score={info.getValue()} />,
    }),
    col.display({
      id: 'commute_sol',
      header: 'Commute Sol',
      cell: ({ row }) => (
        <CommuteCell min={row.original.commute_to_sol_min} max={row.original.commute_to_sol_max} />
      ),
    }),
    col.display({
      id: 'commute_atocha',
      header: 'Commute Atocha',
      cell: ({ row }) => (
        <CommuteCell min={row.original.commute_to_atocha_min} max={row.original.commute_to_atocha_max} />
      ),
    }),
    col.accessor('avg_rent_1bed', {
      header: '1 bed avg',
      cell: info => <span className="text-slate-400 text-sm">{fmt(info.getValue())}</span>,
    }),
    col.accessor('avg_rent_2bed', {
      header: '2 bed avg',
      cell: info => <span className="text-slate-400 text-sm">{fmt(info.getValue())}</span>,
    }),
    col.accessor('avg_rent_3bed', {
      header: '3 bed avg',
      cell: info => <span className="text-slate-400 text-sm">{fmt(info.getValue())}</span>,
    }),
  ]

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Neighborhoods</h1>
          <p className="text-sm text-slate-500 mt-0.5">Safety, transport scores & rent benchmarks</p>
        </div>
        <input
          type="text"
          placeholder="Search..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-[var(--bg-elevated)] border border-[var(--border)] rounded px-3 py-1.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 w-48"
        />
      </div>

      {isLoading && <LoadingState message="Loading neighborhoods..." />}
      {error && <ErrorState message="Failed to load neighborhoods" />}

      {!isLoading && !error && (
        <div className="rounded-lg border border-[var(--border)] overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              {table.getHeaderGroups().map(hg => (
                <tr key={hg.id} className="border-b border-[var(--border)]">
                  {hg.headers.map(header => (
                    <th
                      key={header.id}
                      className={`px-3 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider bg-[var(--bg-elevated)] whitespace-nowrap ${header.column.getCanSort() ? 'cursor-pointer select-none hover:text-slate-300 transition-colors' : ''}`}
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
                    No results
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map(row => (
                  <tr
                    key={row.id}
                    className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--bg-elevated)] transition-colors"
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
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-slate-500">
        <span className="font-medium text-slate-400">Zone:</span>
        {['A', 'B1', 'B2', 'C1', 'C2'].map(z => (
          <span key={z} className="flex items-center gap-1">
            <ZoneBadge zone={z} /> {
              { A: 'Inner', B1: 'Mid-inner', B2: 'Mid', C1: 'Outer', C2: 'Far outer' }[z]
            }
          </span>
        ))}
      </div>
    </div>
  )
}
