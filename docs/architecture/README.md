# Madrid Rental Finder — Architecture

Personal rental listing aggregator for Madrid and nearby municipios.

## Goals
- Pull listings from a small set of Spanish portals (focus on **Tier 1 SSR/API**).
- Normalize and store in **existing homelab PostgreSQL**.
- Provide a private dashboard to filter/compare listings.
- Overlay **research datasets** (safety + transport + rental cost benchmarks) on listings.

## Non-goals
- Not a public marketplace.
- Not a full “contact/lead CRM” (no mass outreach, no personal-data harvesting).
- Not a perfect real-time feed. “Fresh enough” for apartment hunting.

## Proposed stack (opinionated)

### Backend (API + ingestion)
- **Python 3.12**
- **FastAPI** for read-only API + admin endpoints (health, scrape status)
- **SQLAlchemy 2.0** (+ Alembic for migrations)
- **httpx + selectolax** for SSR scraping (fast parsing)
- **Playwright** only for JS-heavy portals (defer)

Why: scraping is Python’s home turf; FastAPI is minimal and reliable.

### Frontend (dashboard)
- **React + Vite + TypeScript**
- **TanStack Query + TanStack Table**
- **Leaflet** (OpenStreetMap) for map view

Why: fastest path to a solid, filter-heavy personal dashboard.

### Deployment
- **K3s (ARM64)** on Raspberry Pi 5
- **ArgoCD** GitOps
- Images in **dahomelab.azurecr.io** (multi-arch)

## High-level architecture

```
                 (public internet)
     +---------------------------------------+
     |  Portals                              |
     |  - Spotahome (API-ish)                |
     |  - Pisos.com (SSR)                    |
     |  - Yaencontre (SSR)                   |
     |  - Habitaclia (SSR)                   |
     |  - Enalquiler (SSR)                   |
     +-------------------+-------------------+
                         |
                         | HTTP(S)
                         v
+--------------------------------------------------------------+
| K3s cluster (pi5-01 / pi5-02)                                |
|                                                              |
|  Namespace: madrid-rental-finder                              |
|                                                              |
|  +---------------------+         +-------------------------+ |
|  | CronJobs: scrapers  |  write  | PostgreSQL (existing)   | |
|  |  - scrape-spotahome |-------> | db: madrid_rental_finder| |
|  |  - scrape-pisos     |         | schema: mrf             | |
|  |  - scrape-yaencontre|         +-------------------------+ |
|  |  ...                |                                   | |
|  +----------+----------+                                   | |
|             |                                           read| |
|             v                                               | |
|  +---------------------+         +-------------------------+ |
|  | Backend API         |<------->| Redis (optional cache)  | |
|  |  FastAPI            |         | already exists on k3s   | |
|  +----------+----------+         +-------------------------+ |
|             |  HTTP                                            
|             v                                                  
|  +---------------------+                                      |
|  | Dashboard (React)   |                                      |
|  | served by Nginx     |                                      |
|  +----------+----------+                                      |
|             | ingress (Traefik)                               |
+-------------+-------------------------------------------------+
              |
              v
     https://rentals.<your-domain>   (private)
```

## Data flow (ingest → normalize → serve)
1. CronJob runs a portal scraper.
2. Scraper fetches search/list pages, extracts listing “cards”, and then detail pages **only for new/changed** listings.
3. Scraper upserts into Postgres:
   - de-dup by `(source_portal, source_listing_id)`
   - maintain `first_seen_at`, `last_seen_at`, `is_active`
   - store normalized fields (price, bedrooms, m², neighborhood)
4. API serves filtered queries for the dashboard + aggregates (counts by barrio, heatmaps).
5. Dashboard overlays:
   - Safety score
   - Transport score
   - Cost benchmarks by district/municipio

## Key design decisions
- **Single source of truth: PostgreSQL** (no separate DB deployments).
- **Separate ingestion from serving**:
  - CronJobs do scraping.
  - API is read-mostly and stable.
- **Treat “neighborhood” as a first-class dimension**:
  - listings may have messy location strings → keep raw text + normalized barrio/distrito when possible.
- **Idempotent ingestion**: every run safe to re-run.

## Operational considerations
- Rate limiting per portal (see `scraping-strategy.md`).
- Store raw extracts (HTML/JSON) **only for debugging**, with retention (e.g., 7 days) to avoid disk bloat.
- Observability: basic Prometheus metrics endpoint from API; logs to stdout; optional Grafana dashboard later.

## Where the research fits
- `neighborhoods` / `districts` tables store:
  - safety score (1–5)
  - transport score (1–5)
  - commute minutes ranges (optional)
  - zone (A/B1/…)
- `cost_benchmarks` stores typical rent bands by district/municipio.

Next docs:
- `database-schema.md`
- `scraping-strategy.md`
- `gitops-deployment.md`
- `implementation-plan.md`
