# Scraping strategy

This project is a personal tool. The right strategy is: **boring, polite, resilient**.

## Portal priority

### Tier 1 (start here - SSR / easy / API-like)
1. **Spotahome** - internal JSON endpoints; low ban risk.
2. **Yaencontre** - SSR, clean listing data in HTML.
3. **Pisos.com** - SSR, large inventory.
4. **Habitaclia** - SSR, good listing detail.
5. **Enalquiler** - SSR, smaller but unique.

Notes:
- **Idealista** is dropped - API access is nearly impossible to get, web scraping is high-risk. Not worth the effort.
- There is overlap across Adevinta properties (Pisos/Habitaclia/Fotocasa). You likely don't need Fotocasa at all.

### Tier 2 (defer - only if Tier 1 inventory isn't enough)
- **Fotocasa** - SPA + stricter controls. Playwright needed.
- **Milanuncios** - DataDome. Only if you really need private-landlord listings.

## Core principles

### 1) Two-stage scrape (list → detail)
- **List/search pages**: cheap. Iterate pages, extract (id, url, price, beds, m²).
- **Detail pages**: expensive. Fetch only for:
  - new listing ids
  - listing with changed key fields (price/availability)

This keeps request volume low and reduces ban risk.

### 2) Idempotent upserts
Every run can be re-run.
- Upsert by `(portal_id, source_listing_id)`.
- Update `last_seen_at` when present in current search results.
- Set `is_active=false` when not seen for N runs or beyond TTL.

### 3) Rate limiting + jitter
Per-portal token bucket + random delay.

Conservative starting limits (you can dial up later):
- Spotahome: **1 req / 3-8s**
- Enalquiler: **1 req / 4-10s**
- Yaencontre: **1 req / 6-15s**
- Pisos.com: **1 req / 6-15s**
- Habitaclia: **1 req / 6-15s**
- Fotocasa (later): **1 req / 20-45s** (Playwright)


### 4) Session persistence
- Keep cookies per portal (reduces "new bot" fingerprint).
- Rotate user-agents from a small realistic pool.

### 5) Don't scrape personal contact details
You don't need phones/emails for this use case. Avoid storing personal data.

## Extraction approach by portal

### Spotahome
- Preferred: reverse-engineer internal marketplace JSON endpoints.
- Output is structured → easiest normalization.

### Yaencontre
- SSR HTML parsing.
- Prices, rooms, m² often present on list pages.

### Pisos.com
- SSR HTML parsing.
- Usually needs a stable selector strategy (avoid brittle CSS chains; target semantic attributes/labels).

### Habitaclia
- SSR HTML parsing.
- Often includes useful derived fields (€/m²).

### Enalquiler
- SSR HTML parsing.
- Smaller stock; treat as "nice-to-have".

## Scheduling on K3s
Use **Kubernetes CronJobs**, one per portal.

### Suggested schedules (Phase 1)
- Spotahome: every **30 min**
- Pisos.com: every **30 min**
- Yaencontre: every **30 min**
- Habitaclia: every **60 min**
- Enalquiler: every **60-120 min**

Stagger starts to avoid traffic spikes:
- `*/30 * * * *` (spotahome)
- `5,35 * * * *` (pisos)
- `10,40 * * * *` (yaencontre)
- `15 * * * *` (habitaclia)
- `25 */2 * * *` (enalquiler)

### Reconciliation job
Add a separate CronJob daily:
- Mark listings inactive if `last_seen_at < now() - interval '7 days'`.

## Proxy strategy

Phase 1: **no proxies**.
- Run slow, rotate UAs, keep sessions.

Phase 3 (only if needed for Fotocasa/Milanuncios):
- Residential proxies (Spain). Evaluate cost vs. value before committing.

## Failure modes and how we handle them
- 403/429: immediately backoff, mark scraper run as `error`, reduce rate.
- HTML layout change: parser fails → store one raw sample payload for debugging (short retention).
- Captcha wall: skip portal, alert in logs, do not hammer.

## Data quality strategy
- Always store `address_raw`, `neighborhood_raw`, `district_raw`.
- Run a post-processing "normalizer" step:
  - map common strings → canonical neighborhood/district
  - optionally call a geocoder later (but keep it offline / minimal).

## Minimum compliance
- Respect low volume.
- Avoid scraping endpoints explicitly blocked if there's an alternative.
- Don't redistribute data.
