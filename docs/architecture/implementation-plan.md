# Implementation plan (phased)

Constraint reality:
- Runs on **2× Raspberry Pi 5** with other workloads. Keep it lean.
- Highest value is: **fresh listings + good filters**. Everything else is optional.

## Phase 0 — Repo + deployment skeleton (0.5–1 day)
Deliverables:
- Repo layout (`backend/`, `frontend/`, `k8s/`), doc set (this folder).
- ArgoCD Application manifest wired (even if workloads are placeholders).
- LAN-only access via MetalLB LoadBalancer (no ingress/Traefik needed).

Success criteria:
- ArgoCD shows `madrid-rental-finder` app and can sync a namespace + a hello-world service.

## Phase 1 — Scrapers + DB + basic API (MVP) (3–7 days)

### 1.1 Database setup
- Create DB `madrid_rental_finder` in existing Postgres.
- Apply initial schema from `database-schema.md`.
- Seed reference data:
  - portals
  - districts/neighborhoods from research
  - cost benchmarks from research

### 1.2 Ingestion (Tier 1 portals only)
- Implement scrapers as CLI commands (one per portal).
- Portals (order):
  1) Spotahome
  2) Yaencontre
  3) Pisos.com
  4) Habitaclia
  5) Enalquiler

Rules:
- list → detail strategy
- strict rate limit
- upsert and status tracking (`scraper_runs`)

### 1.3 Scheduler
- Create K8s CronJobs for each scraper.
- Add daily reconciliation job to mark inactive.

### 1.4 API (read-only)
Endpoints (minimal):
- `GET /healthz`
- `GET /listings` with filters:
  - price range, bedrooms, size
  - district/neighborhood
  - portal
  - active only
  - sort (newest/price)
- `GET /neighborhoods` (with safety/transport + benchmark cost)
- `GET /stats` (counts by district/neighborhood)

Success criteria:
- Postgres contains listings from at least 2 portals.
- API returns filtered results fast (<500ms for typical queries).
- CronJobs run reliably (no overlaps, no bans).

## Phase 2 — Dashboard frontend (2–5 days)

### 2.1 Core views
- Listings table (filters + saved presets)
- Listing detail drawer with **direct link to source portal URL** (click → opens Pisos/Yaencontre/etc.)
- Neighborhood overlay:
  - show safety/transport score
  - show benchmark rent band

### 2.2 Quality-of-life
- “New since last visit” indicator.
- Favorites (stored in localStorage first; DB later).

Success criteria:
- You can answer: “where should I look this week?” in <2 minutes.

## Phase 3 — Advanced features (as needed)

Pick only what pays rent (figuratively).

### 3.1 Dedup + entity resolution
- Detect same property across portals:
  - fuzzy match on address + m² + rooms + geo
  - cluster into `property_entities` table

### 3.2 Telegram alerts
- Scraper CronJobs fire a Telegram Bot API notification when new listings match saved filters (price/bedrooms/neighborhood).
- Rate-limit to avoid spam (e.g., max 10 notifications per scrape run, or digest mode).
- No extra service — notification logic lives in the scraper itself.

### 3.3 Map view (Leaflet)
- Optional: Leaflet map with clustering, color by safety score or price.
- Only if the table view isn't enough.

### 3.4 Fotocasa / additional portals
- Only if Tier 1 portals don't cover enough inventory.
- Playwright-based, very low frequency.

### 3.5 Observability + reliability
- Prometheus metrics + Grafana dashboard.
- Alert when a portal scraper starts failing repeatedly.

## Resource budget (initial)

### Backend API
- requests: 50m CPU / 128Mi
- limits: 300m CPU / 512Mi

### Dashboard
- requests: 20m CPU / 64Mi
- limits: 150m CPU / 256Mi

### Scraper CronJobs (SSR)
- requests: 100m CPU / 256Mi
- limits: 500m CPU / 768Mi



## Risks + mitigations
- Portal HTML changes → keep parsers simple, store one sample payload for debugging.
- IP bans → low rate + stagger schedules; don’t run all portals at once.
- Bad location parsing → keep raw strings; map progressively.
- Scope creep → resist. MVP is listings + filters + overlays.
