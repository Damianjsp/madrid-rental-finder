export interface Portal {
  id: number
  key: string
  name: string
  base_url: string
  last_scrape?: string
  scrape_status?: 'success' | 'error' | 'running' | 'never'
  listings_count?: number
}

export interface District {
  id: number
  name: string
  zone?: string
}

export interface Neighborhood {
  id: number
  name: string
  district_id?: number
  district_name?: string
  municipality: string
  zone?: string
  safety_score?: number
  transport_score?: number
  commute_to_sol_min?: number
  commute_to_sol_max?: number
  commute_to_atocha_min?: number
  commute_to_atocha_max?: number
  avg_rent_1bed?: number
  avg_rent_2bed?: number
  avg_rent_3bed?: number
}

export interface ListingImage {
  id: number
  url: string
  position: number
}

export interface Listing {
  id: number
  portal_id: number
  portal_key: string
  portal_name: string
  source_listing_id: string
  url: string
  title?: string
  description?: string
  price_eur?: number
  deposit_eur?: number
  expenses_included?: boolean
  bedrooms?: number
  bathrooms?: number
  size_m2?: number
  property_type?: string
  furnished?: boolean
  elevator?: boolean
  parking?: boolean
  address_raw?: string
  neighborhood_raw?: string
  district_raw?: string
  municipality_raw?: string
  neighborhood_id?: number
  neighborhood_name?: string
  district_id?: number
  district_name?: string
  lat?: number
  lon?: number
  first_seen_at: string
  last_seen_at: string
  is_active: boolean
  images?: ListingImage[]
  neighborhood_safety_score?: number
  neighborhood_transport_score?: number
  district_avg_rent_1bed?: number
  district_avg_rent_2bed?: number
  district_avg_rent_3bed?: number
}

export interface ListingsResponse {
  items: Listing[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface StatsPortal {
  portal_key: string
  portal_name: string
  listings_count: number
  last_scrape_at?: string
  scrape_status?: 'success' | 'error' | 'running' | 'never'
}

export interface StatsDistrict {
  district_name: string
  listings_count: number
  avg_price?: number
  min_price?: number
  max_price?: number
}

export interface Stats {
  total_active_listings: number
  total_listings: number
  new_today: number
  by_portal: StatsPortal[]
  by_district: StatsDistrict[]
  last_updated: string
}

export interface ListingsFilters {
  price_min?: number
  price_max?: number
  bedrooms?: number
  size_min?: number
  size_max?: number
  district?: string
  neighborhood?: string
  portal?: string
  property_type?: 'all' | 'piso' | 'estudio' | 'habitacion'
  active_only: boolean
  sort: 'newest' | 'price_asc' | 'price_desc' | 'size_asc' | 'size_desc'
  page: number
  per_page: number
}
