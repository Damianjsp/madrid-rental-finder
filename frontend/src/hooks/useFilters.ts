import { useState } from 'react'
import type { ListingsFilters } from '../types'

const DEFAULT_FILTERS: ListingsFilters = {
  active_only: true,
  sort: 'newest',
  page: 1,
  per_page: 25,
}

export function useFilters() {
  const [filters, setFilters] = useState<ListingsFilters>(DEFAULT_FILTERS)

  const update = (partial: Partial<ListingsFilters>) => {
    setFilters(prev => ({ ...prev, ...partial, page: 1 }))
  }

  const setPage = (page: number) => {
    setFilters(prev => ({ ...prev, page }))
  }

  const reset = () => setFilters(DEFAULT_FILTERS)

  return { filters, update, setPage, reset }
}
