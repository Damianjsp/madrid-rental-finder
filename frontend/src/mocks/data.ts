import type { Listing, Neighborhood, Stats, Portal, ListingsResponse } from '../types'

export const MOCK_PORTALS: Portal[] = [
  { id: 1, key: 'spotahome', name: 'Spotahome', base_url: 'https://www.spotahome.com', last_scrape: '2026-03-10T22:00:00Z', scrape_status: 'success', listings_count: 142 },
  { id: 2, key: 'pisos', name: 'Pisos.com', base_url: 'https://www.pisos.com', last_scrape: '2026-03-10T21:30:00Z', scrape_status: 'success', listings_count: 89 },
  { id: 3, key: 'yaencontre', name: 'Yaencontre', base_url: 'https://www.yaencontre.com', last_scrape: '2026-03-10T20:00:00Z', scrape_status: 'error', listings_count: 0 },
  { id: 4, key: 'habitaclia', name: 'Habitaclia', base_url: 'https://www.habitaclia.com', last_scrape: undefined, scrape_status: 'never', listings_count: 0 },
  { id: 5, key: 'enalquiler', name: 'Enalquiler', base_url: 'https://www.enalquiler.com', last_scrape: '2026-03-10T19:00:00Z', scrape_status: 'success', listings_count: 67 },
]

export const MOCK_NEIGHBORHOODS: Neighborhood[] = [
  { id: 1, name: 'Malasaña', district_id: 1, district_name: 'Centro', municipality: 'Madrid', zone: 'A', safety_score: 3, transport_score: 5, commute_to_sol_min: 10, commute_to_sol_max: 15, commute_to_atocha_min: 15, commute_to_atocha_max: 20, avg_rent_1bed: 1100, avg_rent_2bed: 1500, avg_rent_3bed: 2100 },
  { id: 2, name: 'Lavapiés', district_id: 1, district_name: 'Centro', municipality: 'Madrid', zone: 'A', safety_score: 2, transport_score: 5, commute_to_sol_min: 8, commute_to_sol_max: 12, commute_to_atocha_min: 10, commute_to_atocha_max: 15, avg_rent_1bed: 950, avg_rent_2bed: 1300, avg_rent_3bed: 1800 },
  { id: 3, name: 'Chueca', district_id: 1, district_name: 'Centro', municipality: 'Madrid', zone: 'A', safety_score: 4, transport_score: 5, commute_to_sol_min: 5, commute_to_sol_max: 10, commute_to_atocha_min: 12, commute_to_atocha_max: 18, avg_rent_1bed: 1200, avg_rent_2bed: 1700, avg_rent_3bed: 2400 },
  { id: 4, name: 'Goya', district_id: 2, district_name: 'Salamanca', municipality: 'Madrid', zone: 'A', safety_score: 5, transport_score: 5, commute_to_sol_min: 12, commute_to_sol_max: 18, commute_to_atocha_min: 15, commute_to_atocha_max: 22, avg_rent_1bed: 1400, avg_rent_2bed: 2000, avg_rent_3bed: 2900 },
  { id: 5, name: 'Lista', district_id: 2, district_name: 'Salamanca', municipality: 'Madrid', zone: 'A', safety_score: 5, transport_score: 4, commute_to_sol_min: 15, commute_to_sol_max: 22, commute_to_atocha_min: 18, commute_to_atocha_max: 25, avg_rent_1bed: 1500, avg_rent_2bed: 2100, avg_rent_3bed: 3000 },
  { id: 6, name: 'Prosperidad', district_id: 3, district_name: 'Chamartín', municipality: 'Madrid', zone: 'B1', safety_score: 4, transport_score: 3, commute_to_sol_min: 25, commute_to_sol_max: 35, commute_to_atocha_min: 30, commute_to_atocha_max: 40, avg_rent_1bed: 900, avg_rent_2bed: 1200, avg_rent_3bed: 1700 },
  { id: 7, name: 'Acacias', district_id: 4, district_name: 'Arganzuela', municipality: 'Madrid', zone: 'A', safety_score: 3, transport_score: 4, commute_to_sol_min: 12, commute_to_sol_max: 18, commute_to_atocha_min: 8, commute_to_atocha_max: 12, avg_rent_1bed: 1000, avg_rent_2bed: 1400, avg_rent_3bed: 1900 },
  { id: 8, name: 'Usera', district_id: 5, district_name: 'Usera', municipality: 'Madrid', zone: 'B1', safety_score: 2, transport_score: 3, commute_to_sol_min: 20, commute_to_sol_max: 30, commute_to_atocha_min: 15, commute_to_atocha_max: 22, avg_rent_1bed: 750, avg_rent_2bed: 1050, avg_rent_3bed: 1400 },
  { id: 9, name: 'Carabanchel', district_id: 6, district_name: 'Carabanchel', municipality: 'Madrid', zone: 'B2', safety_score: 2, transport_score: 3, commute_to_sol_min: 25, commute_to_sol_max: 35, commute_to_atocha_min: 20, commute_to_atocha_max: 30, avg_rent_1bed: 700, avg_rent_2bed: 950, avg_rent_3bed: 1300 },
  { id: 10, name: 'Vallecas', district_id: 7, district_name: 'Puente de Vallecas', municipality: 'Madrid', zone: 'B2', safety_score: 2, transport_score: 3, commute_to_sol_min: 22, commute_to_sol_max: 32, commute_to_atocha_min: 18, commute_to_atocha_max: 25, avg_rent_1bed: 750, avg_rent_2bed: 1000, avg_rent_3bed: 1350 },
  { id: 11, name: 'Getafe Centro', district_id: undefined, district_name: undefined, municipality: 'Getafe', zone: 'B2', safety_score: 3, transport_score: 3, commute_to_sol_min: 30, commute_to_sol_max: 45, commute_to_atocha_min: 22, commute_to_atocha_max: 35, avg_rent_1bed: 650, avg_rent_2bed: 900, avg_rent_3bed: 1200 },
  { id: 12, name: 'Leganés Norte', district_id: undefined, district_name: undefined, municipality: 'Leganés', zone: 'B2', safety_score: 3, transport_score: 2, commute_to_sol_min: 35, commute_to_sol_max: 50, commute_to_atocha_min: 28, commute_to_atocha_max: 40, avg_rent_1bed: 620, avg_rent_2bed: 850, avg_rent_3bed: 1150 },
]

const now = new Date()
const daysAgo = (d: number) => new Date(now.getTime() - d * 86400000).toISOString()

export const MOCK_LISTINGS: Listing[] = [
  {
    id: 1, portal_id: 1, portal_key: 'spotahome', portal_name: 'Spotahome',
    source_listing_id: 'SPH-001', url: 'https://www.spotahome.com/listings/001',
    title: 'Luminoso piso en Malasaña con terraza', description: 'Piso reformado de 2 habitaciones en el corazón de Malasaña. Cocina equipada, baño moderno, terraza privada de 8m². Amueblado con gusto. Metro Tribunal a 3 minutos.',
    price_eur: 1350, deposit_eur: 2700, expenses_included: false,
    bedrooms: 2, bathrooms: 1, size_m2: 68, property_type: 'piso',
    furnished: true, elevator: false, parking: false,
    address_raw: 'Calle Fuencarral 45, Malasaña', neighborhood_raw: 'Malasaña', district_raw: 'Centro',
    neighborhood_id: 1, neighborhood_name: 'Malasaña', district_id: 1, district_name: 'Centro',
    first_seen_at: daysAgo(0), last_seen_at: daysAgo(0), is_active: true,
    neighborhood_safety_score: 3, neighborhood_transport_score: 5,
    district_avg_rent_1bed: 1100, district_avg_rent_2bed: 1500, district_avg_rent_3bed: 2100,
    images: [
      { id: 1, url: 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800', position: 0 },
      { id: 2, url: 'https://images.unsplash.com/photo-1484154218962-a197022b5858?w=800', position: 1 },
      { id: 3, url: 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800', position: 2 },
    ]
  },
  {
    id: 2, portal_id: 2, portal_key: 'pisos', portal_name: 'Pisos.com',
    source_listing_id: 'PIS-002', url: 'https://www.pisos.com/listings/002',
    title: 'Estudio moderno en Lavapiés', description: 'Estudio completamente reformado de 35m². Perfecto para estudiante o profesional. Zona muy bien comunicada con metro y bus.',
    price_eur: 850, deposit_eur: 850, expenses_included: true,
    bedrooms: 1, bathrooms: 1, size_m2: 35, property_type: 'estudio',
    furnished: true, elevator: true, parking: false,
    address_raw: 'Calle Amparo 12, Lavapiés', neighborhood_raw: 'Lavapiés', district_raw: 'Centro',
    neighborhood_id: 2, neighborhood_name: 'Lavapiés', district_id: 1, district_name: 'Centro',
    first_seen_at: daysAgo(1), last_seen_at: daysAgo(0), is_active: true,
    neighborhood_safety_score: 2, neighborhood_transport_score: 5,
    district_avg_rent_1bed: 950, district_avg_rent_2bed: 1300, district_avg_rent_3bed: 1800,
    images: [
      { id: 4, url: 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800', position: 0 },
    ]
  },
  {
    id: 3, portal_id: 5, portal_key: 'enalquiler', portal_name: 'Enalquiler',
    source_listing_id: 'ENQ-003', url: 'https://www.enalquiler.com/listings/003',
    title: 'Piso 3 habitaciones en Goya', description: 'Amplio piso de 3 habitaciones en el exclusivo barrio de Goya. Totalmente reformado, doble acristalamiento, suelo de parquet. Garaje incluido.',
    price_eur: 2200, deposit_eur: 4400, expenses_included: false,
    bedrooms: 3, bathrooms: 2, size_m2: 110, property_type: 'piso',
    furnished: false, elevator: true, parking: true,
    address_raw: 'Calle Narváez 28, Goya', neighborhood_raw: 'Goya', district_raw: 'Salamanca',
    neighborhood_id: 4, neighborhood_name: 'Goya', district_id: 2, district_name: 'Salamanca',
    first_seen_at: daysAgo(3), last_seen_at: daysAgo(1), is_active: true,
    neighborhood_safety_score: 5, neighborhood_transport_score: 5,
    district_avg_rent_1bed: 1400, district_avg_rent_2bed: 2000, district_avg_rent_3bed: 2900,
    images: [
      { id: 5, url: 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800', position: 0 },
      { id: 6, url: 'https://images.unsplash.com/photo-1493809842364-78817add7ffb?w=800', position: 1 },
    ]
  },
  {
    id: 4, portal_id: 1, portal_key: 'spotahome', portal_name: 'Spotahome',
    source_listing_id: 'SPH-004', url: 'https://www.spotahome.com/listings/004',
    title: 'Habitación en piso compartido — Chueca', description: 'Habitación amplia en piso de 4 personas. Zona céntrica e ideal para recién llegados. Gastos incluidos.',
    price_eur: 650, deposit_eur: 650, expenses_included: true,
    bedrooms: 1, bathrooms: 1, size_m2: 18, property_type: 'habitacion',
    furnished: true, elevator: false, parking: false,
    address_raw: 'Calle Hortaleza 55, Chueca', neighborhood_raw: 'Chueca', district_raw: 'Centro',
    neighborhood_id: 3, neighborhood_name: 'Chueca', district_id: 1, district_name: 'Centro',
    first_seen_at: daysAgo(0), last_seen_at: daysAgo(0), is_active: true,
    neighborhood_safety_score: 4, neighborhood_transport_score: 5,
    district_avg_rent_1bed: 1200, district_avg_rent_2bed: 1700, district_avg_rent_3bed: 2400,
    images: []
  },
  {
    id: 5, portal_id: 2, portal_key: 'pisos', portal_name: 'Pisos.com',
    source_listing_id: 'PIS-005', url: 'https://www.pisos.com/listings/005',
    title: 'Piso 2 hab. en Arganzuela — próximo Atocha', description: 'Piso bien distribuido a 5 minutos de Atocha. Ideal para profesionales. Recién pintado y con cocina renovada.',
    price_eur: 1100, deposit_eur: 2200, expenses_included: false,
    bedrooms: 2, bathrooms: 1, size_m2: 62, property_type: 'piso',
    furnished: false, elevator: true, parking: false,
    address_raw: 'Paseo de las Acacias 8, Arganzuela', neighborhood_raw: 'Acacias', district_raw: 'Arganzuela',
    neighborhood_id: 7, neighborhood_name: 'Acacias', district_id: 4, district_name: 'Arganzuela',
    first_seen_at: daysAgo(2), last_seen_at: daysAgo(0), is_active: true,
    neighborhood_safety_score: 3, neighborhood_transport_score: 4,
    district_avg_rent_1bed: 1000, district_avg_rent_2bed: 1400, district_avg_rent_3bed: 1900,
    images: [
      { id: 7, url: 'https://images.unsplash.com/photo-1574362848149-11496d93a7c7?w=800', position: 0 },
    ]
  },
  {
    id: 6, portal_id: 5, portal_key: 'enalquiler', portal_name: 'Enalquiler',
    source_listing_id: 'ENQ-006', url: 'https://www.enalquiler.com/listings/006',
    title: 'Piso reformado en Usera — precio asequible', description: 'Gran oportunidad en Usera. Piso de 3 habitaciones con mucha luz. Bien comunicado con metro L3 y L5.',
    price_eur: 980, deposit_eur: 1960, expenses_included: false,
    bedrooms: 3, bathrooms: 1, size_m2: 78, property_type: 'piso',
    furnished: false, elevator: false, parking: false,
    address_raw: 'Calle General Ricardos 100, Usera', neighborhood_raw: 'Usera', district_raw: 'Usera',
    neighborhood_id: 8, neighborhood_name: 'Usera', district_id: 5, district_name: 'Usera',
    first_seen_at: daysAgo(5), last_seen_at: daysAgo(2), is_active: true,
    neighborhood_safety_score: 2, neighborhood_transport_score: 3,
    district_avg_rent_1bed: 750, district_avg_rent_2bed: 1050, district_avg_rent_3bed: 1400,
    images: []
  },
  {
    id: 7, portal_id: 2, portal_key: 'pisos', portal_name: 'Pisos.com',
    source_listing_id: 'PIS-007', url: 'https://www.pisos.com/listings/007',
    title: 'Chalet adosado en Getafe — amplio jardín', description: 'Chalet de 4 habitaciones con jardín de 80m² y garaje doble. Perfecto para familia. Cercanías C4 a 10 min.',
    price_eur: 1450, deposit_eur: 2900, expenses_included: false,
    bedrooms: 4, bathrooms: 2, size_m2: 140, property_type: 'chalet',
    furnished: false, elevator: false, parking: true,
    address_raw: 'Calle Jarama 15, Getafe', neighborhood_raw: 'Getafe Centro', district_raw: undefined,
    neighborhood_id: 11, neighborhood_name: 'Getafe Centro', district_id: undefined, district_name: undefined,
    first_seen_at: daysAgo(7), last_seen_at: daysAgo(3), is_active: true,
    neighborhood_safety_score: 3, neighborhood_transport_score: 3,
    district_avg_rent_1bed: 650, district_avg_rent_2bed: 900, district_avg_rent_3bed: 1200,
    images: [
      { id: 8, url: 'https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=800', position: 0 },
    ]
  },
  {
    id: 8, portal_id: 1, portal_key: 'spotahome', portal_name: 'Spotahome',
    source_listing_id: 'SPH-008', url: 'https://www.spotahome.com/listings/008',
    title: 'Estudio moderno en Lista (Salamanca)', description: 'Estudio de diseño en barrio Salamanca. Reformado en 2024, domótica, cocina americana. Muy silencioso.',
    price_eur: 1100, deposit_eur: 1100, expenses_included: true,
    bedrooms: 1, bathrooms: 1, size_m2: 42, property_type: 'estudio',
    furnished: true, elevator: true, parking: false,
    address_raw: 'Calle Ayala 88, Lista', neighborhood_raw: 'Lista', district_raw: 'Salamanca',
    neighborhood_id: 5, neighborhood_name: 'Lista', district_id: 2, district_name: 'Salamanca',
    first_seen_at: daysAgo(1), last_seen_at: daysAgo(0), is_active: true,
    neighborhood_safety_score: 5, neighborhood_transport_score: 4,
    district_avg_rent_1bed: 1500, district_avg_rent_2bed: 2100, district_avg_rent_3bed: 3000,
    images: [
      { id: 9, url: 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800', position: 0 },
      { id: 10, url: 'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800', position: 1 },
    ]
  },
  {
    id: 9, portal_id: 5, portal_key: 'enalquiler', portal_name: 'Enalquiler',
    source_listing_id: 'ENQ-009', url: 'https://www.enalquiler.com/listings/009',
    title: 'Piso 1 hab. en Carabanchel — recién reformado', description: 'Piso de 1 habitación completamente reformado. Calefacción central, carpintería nueva. Muy tranquilo.',
    price_eur: 720, deposit_eur: 1440, expenses_included: false,
    bedrooms: 1, bathrooms: 1, size_m2: 45, property_type: 'piso',
    furnished: false, elevator: false, parking: false,
    address_raw: 'Calle Laguna 22, Carabanchel', neighborhood_raw: 'Carabanchel', district_raw: 'Carabanchel',
    neighborhood_id: 9, neighborhood_name: 'Carabanchel', district_id: 6, district_name: 'Carabanchel',
    first_seen_at: daysAgo(10), last_seen_at: daysAgo(5), is_active: false,
    neighborhood_safety_score: 2, neighborhood_transport_score: 3,
    district_avg_rent_1bed: 700, district_avg_rent_2bed: 950, district_avg_rent_3bed: 1300,
    images: []
  },
  {
    id: 10, portal_id: 2, portal_key: 'pisos', portal_name: 'Pisos.com',
    source_listing_id: 'PIS-010', url: 'https://www.pisos.com/listings/010',
    title: 'Piso luminoso en Prosperidad (Chamartín)', description: '2 habitaciones con muchísima luz en Prosperidad. Comunidad tranquila, piscina comunitaria. Metro L4.',
    price_eur: 1050, deposit_eur: 2100, expenses_included: false,
    bedrooms: 2, bathrooms: 1, size_m2: 70, property_type: 'piso',
    furnished: true, elevator: true, parking: false,
    address_raw: 'Calle Arturo Soria 150, Prosperidad', neighborhood_raw: 'Prosperidad', district_raw: 'Chamartín',
    neighborhood_id: 6, neighborhood_name: 'Prosperidad', district_id: 3, district_name: 'Chamartín',
    first_seen_at: daysAgo(4), last_seen_at: daysAgo(1), is_active: true,
    neighborhood_safety_score: 4, neighborhood_transport_score: 3,
    district_avg_rent_1bed: 900, district_avg_rent_2bed: 1200, district_avg_rent_3bed: 1700,
    images: [
      { id: 11, url: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800', position: 0 },
    ]
  },
]

export const MOCK_STATS: Stats = {
  total_active_listings: 9,
  total_listings: 10,
  new_today: 3,
  last_updated: new Date().toISOString(),
  by_portal: [
    { portal_key: 'spotahome', portal_name: 'Spotahome', listings_count: 142, last_scrape_at: '2026-03-10T22:00:00Z', scrape_status: 'success' },
    { portal_key: 'pisos', portal_name: 'Pisos.com', listings_count: 89, last_scrape_at: '2026-03-10T21:30:00Z', scrape_status: 'success' },
    { portal_key: 'yaencontre', portal_name: 'Yaencontre', listings_count: 0, last_scrape_at: '2026-03-10T20:00:00Z', scrape_status: 'error' },
    { portal_key: 'habitaclia', portal_name: 'Habitaclia', listings_count: 0, last_scrape_at: undefined, scrape_status: 'never' },
    { portal_key: 'enalquiler', portal_name: 'Enalquiler', listings_count: 67, last_scrape_at: '2026-03-10T19:00:00Z', scrape_status: 'success' },
  ],
  by_district: [
    { district_name: 'Centro', listings_count: 4, avg_price: 987, min_price: 650, max_price: 1350 },
    { district_name: 'Salamanca', listings_count: 2, avg_price: 1650, min_price: 1100, max_price: 2200 },
    { district_name: 'Arganzuela', listings_count: 1, avg_price: 1100, min_price: 1100, max_price: 1100 },
    { district_name: 'Chamartín', listings_count: 1, avg_price: 1050, min_price: 1050, max_price: 1050 },
    { district_name: 'Usera', listings_count: 1, avg_price: 980, min_price: 980, max_price: 980 },
  ],
}

export function getMockListings(params: {
  price_min?: number; price_max?: number; bedrooms?: number;
  size_min?: number; size_max?: number; district?: string;
  neighborhood?: string; portal?: string; property_type?: 'all' | 'piso' | 'estudio' | 'habitacion'; active_only?: boolean;
  sort?: string; page?: number; per_page?: number;
}): ListingsResponse {
  let results = [...MOCK_LISTINGS]

  if (params.active_only) results = results.filter(l => l.is_active)
  if (params.price_min) results = results.filter(l => (l.price_eur ?? 0) >= params.price_min!)
  if (params.price_max) results = results.filter(l => (l.price_eur ?? 0) <= params.price_max!)
  if (params.bedrooms) results = results.filter(l => (l.bedrooms ?? 0) >= params.bedrooms!)
  if (params.size_min) results = results.filter(l => (Number(l.size_m2) || 0) >= params.size_min!)
  if (params.size_max) results = results.filter(l => (Number(l.size_m2) || 0) <= params.size_max!)
  if (params.district) results = results.filter(l => l.district_name?.toLowerCase() === params.district?.toLowerCase())
  if (params.neighborhood) results = results.filter(l => l.neighborhood_name?.toLowerCase() === params.neighborhood?.toLowerCase())
  if (params.portal) results = results.filter(l => l.portal_key === params.portal)
  if (params.property_type && params.property_type !== 'all') {
    results = results.filter(l => l.property_type === params.property_type)
  } else if (!params.property_type) {
    results = results.filter(l => l.property_type === 'piso' || l.property_type === 'estudio')
  }

  switch (params.sort) {
    case 'price_asc': results.sort((a, b) => (a.price_eur ?? 0) - (b.price_eur ?? 0)); break
    case 'price_desc': results.sort((a, b) => (b.price_eur ?? 0) - (a.price_eur ?? 0)); break
    case 'size_asc': results.sort((a, b) => Number(a.size_m2 ?? 0) - Number(b.size_m2 ?? 0)); break
    case 'size_desc': results.sort((a, b) => Number(b.size_m2 ?? 0) - Number(a.size_m2 ?? 0)); break
    default: results.sort((a, b) => new Date(b.first_seen_at).getTime() - new Date(a.first_seen_at).getTime())
  }

  const page = params.page ?? 1
  const per_page = params.per_page ?? 25
  const total = results.length
  const pages = Math.ceil(total / per_page)
  const start = (page - 1) * per_page
  const items = results.slice(start, start + per_page)

  return { items, total, page, per_page, pages }
}
