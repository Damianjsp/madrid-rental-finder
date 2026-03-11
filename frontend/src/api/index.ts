import type { Listing, ListingsResponse, Neighborhood, Stats, Portal, ListingsFilters } from '../types'
import {
  getMockListings,
  MOCK_NEIGHBORHOODS,
  MOCK_STATS,
  MOCK_PORTALS,
  MOCK_LISTINGS,
} from '../mocks/data'

// Toggle: set to false when real API is available
const USE_MOCK = false

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

export async function fetchListings(filters: ListingsFilters): Promise<ListingsResponse> {
  if (USE_MOCK) {
    await delay(200)
    return getMockListings({
      ...filters,
      active_only: filters.active_only,
    })
  }
  const params = new URLSearchParams()
  if (filters.price_min) params.set('price_min', String(filters.price_min))
  if (filters.price_max) params.set('price_max', String(filters.price_max))
  if (filters.bedrooms) params.set('bedrooms', String(filters.bedrooms))
  if (filters.size_min) params.set('size_min', String(filters.size_min))
  if (filters.size_max) params.set('size_max', String(filters.size_max))
  if (filters.district) params.set('district', filters.district)
  if (filters.neighborhood) params.set('neighborhood', filters.neighborhood)
  if (filters.portal) params.set('portal', filters.portal)
  params.set('active_only', String(filters.active_only))
  params.set('sort', filters.sort)
  params.set('page', String(filters.page))
  params.set('per_page', String(filters.per_page))
  return apiFetch<ListingsResponse>(`/api/listings?${params}`)
}

export async function fetchListing(id: number): Promise<Listing> {
  if (USE_MOCK) {
    await delay(100)
    const listing = MOCK_LISTINGS.find(l => l.id === id)
    if (!listing) throw new Error(`Listing ${id} not found`)
    return listing
  }
  return apiFetch<Listing>(`/api/listings/${id}`)
}

export async function fetchNeighborhoods(): Promise<Neighborhood[]> {
  if (USE_MOCK) {
    await delay(150)
    return MOCK_NEIGHBORHOODS
  }
  return apiFetch<Neighborhood[]>('/api/neighborhoods')
}

export async function fetchStats(): Promise<Stats> {
  if (USE_MOCK) {
    await delay(100)
    return MOCK_STATS
  }
  return apiFetch<Stats>('/api/stats')
}

export async function fetchPortals(): Promise<Portal[]> {
  if (USE_MOCK) {
    await delay(100)
    return MOCK_PORTALS
  }
  return apiFetch<Portal[]>('/api/portals')
}

function delay(ms: number) {
  return new Promise(r => setTimeout(r, ms))
}
