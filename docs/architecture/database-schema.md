# Database schema (PostgreSQL)

Assumptions:
- Use existing PostgreSQL on K3s (`postgresql` namespace).
- Create a **new database**: `madrid_rental_finder`.
- Use a dedicated schema inside it: `mrf`.

Notes:
- Normalize enough for filtering, but keep raw fields for traceability.
- De-dup on `(portal_id, source_listing_id)`.
- Keep `first_seen_at`, `last_seen_at`, `is_active` for “still listed?” tracking.

## SQL — initial DDL

```sql
-- Create schema
CREATE SCHEMA IF NOT EXISTS mrf;

-- Extensions (optional but useful)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- =========================
-- Reference tables
-- =========================

CREATE TABLE IF NOT EXISTS mrf.portals (
  id            SMALLSERIAL PRIMARY KEY,
  key           TEXT NOT NULL UNIQUE,        -- 'pisos', 'yaencontre', ...
  name          TEXT NOT NULL,
  tier          SMALLINT NOT NULL DEFAULT 1, -- 1 easy/ssr/api, 2 harder
  base_url      TEXT,
  notes         TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mrf.scraper_runs (
  id              BIGSERIAL PRIMARY KEY,
  portal_id       SMALLINT NOT NULL REFERENCES mrf.portals(id),
  started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at     TIMESTAMPTZ,
  status          TEXT NOT NULL DEFAULT 'running', -- running|success|error
  listings_seen   INTEGER NOT NULL DEFAULT 0,
  listings_new    INTEGER NOT NULL DEFAULT 0,
  listings_updated INTEGER NOT NULL DEFAULT 0,
  error_message   TEXT,
  meta            JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Madrid geography (keep simple and extensible)
CREATE TABLE IF NOT EXISTS mrf.districts (
  id            SMALLSERIAL PRIMARY KEY,
  name          TEXT NOT NULL UNIQUE,    -- 'Salamanca'
  city          TEXT NOT NULL DEFAULT 'Madrid',
  zone          TEXT,                   -- 'A', 'B1', etc.
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mrf.neighborhoods (
  id               BIGSERIAL PRIMARY KEY,
  name             TEXT NOT NULL,
  district_id      SMALLINT REFERENCES mrf.districts(id),
  municipality     TEXT NOT NULL DEFAULT 'Madrid', -- for suburbs
  zone             TEXT,                           -- A/B1/B2...
  safety_score     SMALLINT,                       -- 1..5
  transport_score  SMALLINT,                       -- 1..5
  commute_to_sol_min    SMALLINT,
  commute_to_sol_max    SMALLINT,
  commute_to_atocha_min SMALLINT,
  commute_to_atocha_max SMALLINT,
  notes            TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (municipality, name)
);

-- Optional: store stations/lines if you later want richer transport overlays
CREATE TABLE IF NOT EXISTS mrf.transport_nodes (
  id            BIGSERIAL PRIMARY KEY,
  kind          TEXT NOT NULL,           -- 'metro'|'cercanias'
  name          TEXT NOT NULL,
  lines         TEXT[],                  -- ['L1','L6'] or ['C4','C10']
  lat           DOUBLE PRECISION,
  lon           DOUBLE PRECISION,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (kind, name)
);

CREATE TABLE IF NOT EXISTS mrf.neighborhood_transport_nodes (
  neighborhood_id BIGINT NOT NULL REFERENCES mrf.neighborhoods(id) ON DELETE CASCADE,
  transport_node_id BIGINT NOT NULL REFERENCES mrf.transport_nodes(id) ON DELETE CASCADE,
  PRIMARY KEY (neighborhood_id, transport_node_id)
);

-- Rental cost benchmarks from research (district/municipio-level)
CREATE TABLE IF NOT EXISTS mrf.cost_benchmarks (
  id             BIGSERIAL PRIMARY KEY,
  scope_kind     TEXT NOT NULL,  -- 'district'|'municipality'
  scope_name     TEXT NOT NULL,
  avg_rent_1bed  INTEGER,
  avg_rent_2bed  INTEGER,
  avg_rent_3bed  INTEGER,
  avg_house      INTEGER,
  avg_chalet     INTEGER,
  observed_at    DATE NOT NULL,
  source         TEXT,
  meta           JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (scope_kind, scope_name, observed_at)
);

-- =========================
-- Listings
-- =========================

CREATE TABLE IF NOT EXISTS mrf.listings (
  id                 BIGSERIAL PRIMARY KEY,

  portal_id           SMALLINT NOT NULL REFERENCES mrf.portals(id),
  source_listing_id   TEXT NOT NULL,
  url                TEXT NOT NULL,

  title              TEXT,
  description        TEXT,

  price_eur          INTEGER,
  deposit_eur        INTEGER,
  expenses_included  BOOLEAN,

  bedrooms           SMALLINT,
  bathrooms          SMALLINT,
  size_m2            NUMERIC(6,2),

  property_type      TEXT,      -- 'piso','estudio','habitacion','chalet',...
  furnished          BOOLEAN,
  elevator           BOOLEAN,
  parking            BOOLEAN,

  address_raw        TEXT,
  neighborhood_raw   TEXT,
  district_raw       TEXT,
  municipality_raw   TEXT,

  neighborhood_id    BIGINT REFERENCES mrf.neighborhoods(id),
  district_id        SMALLINT REFERENCES mrf.districts(id),

  lat                DOUBLE PRECISION,
  lon                DOUBLE PRECISION,

  first_seen_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  scraped_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  is_active          BOOLEAN NOT NULL DEFAULT TRUE,

  -- scraper traceability
  scraper_run_id     BIGINT REFERENCES mrf.scraper_runs(id),
  raw               JSONB NOT NULL DEFAULT '{}'::jsonb,

  UNIQUE (portal_id, source_listing_id)
);

CREATE INDEX IF NOT EXISTS idx_listings_active ON mrf.listings(is_active);
CREATE INDEX IF NOT EXISTS idx_listings_price ON mrf.listings(price_eur);
CREATE INDEX IF NOT EXISTS idx_listings_bedrooms ON mrf.listings(bedrooms);
CREATE INDEX IF NOT EXISTS idx_listings_size ON mrf.listings(size_m2);
CREATE INDEX IF NOT EXISTS idx_listings_last_seen ON mrf.listings(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_listings_neighborhood ON mrf.listings(neighborhood_id);

-- Optional full-text search
ALTER TABLE mrf.listings
  ADD COLUMN IF NOT EXISTS tsv tsvector;

CREATE INDEX IF NOT EXISTS idx_listings_tsv ON mrf.listings USING GIN(tsv);

-- Keep tsvector updated (simple trigger)
CREATE OR REPLACE FUNCTION mrf.listings_tsv_update() RETURNS trigger AS $$
BEGIN
  NEW.tsv :=
    setweight(to_tsvector('spanish', unaccent(coalesce(NEW.title,''))), 'A') ||
    setweight(to_tsvector('spanish', unaccent(coalesce(NEW.description,''))), 'B') ||
    setweight(to_tsvector('spanish', unaccent(coalesce(NEW.neighborhood_raw,''))), 'C') ||
    setweight(to_tsvector('spanish', unaccent(coalesce(NEW.district_raw,''))), 'C');
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_listings_tsv_update ON mrf.listings;
CREATE TRIGGER trg_listings_tsv_update
BEFORE INSERT OR UPDATE OF title, description, neighborhood_raw, district_raw
ON mrf.listings
FOR EACH ROW EXECUTE FUNCTION mrf.listings_tsv_update();

-- Images (optional but useful for UI cards)
CREATE TABLE IF NOT EXISTS mrf.listing_images (
  id          BIGSERIAL PRIMARY KEY,
  listing_id  BIGINT NOT NULL REFERENCES mrf.listings(id) ON DELETE CASCADE,
  url         TEXT NOT NULL,
  position    SMALLINT,
  UNIQUE (listing_id, url)
);

-- Audit table for portal URL patterns / parsing versions
CREATE TABLE IF NOT EXISTS mrf.portal_parsing_versions (
  id          BIGSERIAL PRIMARY KEY,
  portal_id   SMALLINT NOT NULL REFERENCES mrf.portals(id),
  version     TEXT NOT NULL, -- git sha or semantic version
  deployed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes       TEXT
);
```

## Mapping the research datasets into tables

### Safety + transport (from `docs/research/safety-transport.md`)
- Populate `mrf.districts` with the districts listed.
- Populate `mrf.neighborhoods` with the “Area” rows (municipality = Madrid unless it’s a suburb).
- Save:
  - `safety_score`
  - `zone`
  - `commute_to_sol_min/max`, `commute_to_atocha_min/max`
  - optionally create `transport_nodes` for the main stations/lines.

### Rental costs (from `docs/research/rental-costs.md`)
- Populate `mrf.cost_benchmarks` with:
  - `scope_kind='district'` for the 21 Madrid districts
  - `scope_kind='municipality'` for satellite cities
  - `observed_at='2026-03-10'` (or actual snapshot date)

## Suggested minimal constraints for the scraper
- Always store:
  - `portal_id`, `source_listing_id`, `url`, `scraped_at`, `last_seen_at`, `is_active`
- Prefer normalized fields where possible:
  - `price_eur`, `bedrooms`, `size_m2`, `district_id/neighborhood_id`
- Keep `raw` JSON for whatever each portal exposes (future-proofing).
