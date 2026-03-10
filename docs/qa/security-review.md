# Security Review — Madrid Rental Finder

**Date:** 2026-03-11  
**Reviewer:** codesentinel (automated security review)  
**Scope:** backend/, k8s/, .github/workflows/  
**Overall Security Posture:** 🟡 **Good for homelab** — no critical issues, a handful of medium findings to harden before any public exposure.

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 1 |
| Medium   | 5 |
| Low      | 5 |
| Info     | 4 |

---

## Findings

### HIGH

#### H-1: SQL-like injection via `ilike` with unsanitized user input

**File:** `backend/src/mrf/api/main.py:131-133, 193`  
**Description:** The `district` and `neighborhood` query params (and `municipality` on the neighborhoods endpoint) are interpolated directly into SQLAlchemy `ilike` filters using f-strings:

```python
q = q.filter(Listing.district_raw.ilike(f"%{district}%"))
q = q.filter(Listing.neighborhood_raw.ilike(f"%{neighborhood}%"))
q = q.filter(Neighborhood.municipality.ilike(f"%{municipality}%"))
```

While SQLAlchemy parameterizes the `ilike` argument (so this is **not** classic SQL injection), the `%` and `_` wildcard characters in user input are **not escaped**. An attacker can craft queries like `district=_%_%_%` to perform wildcard-based data enumeration or cause slow `LIKE` scans.

**Risk:** Data enumeration, potential performance degradation via crafted wildcards.  
**Recommendation:** Escape `%` and `_` in user input before passing to `ilike`:

```python
import re
def escape_like(s: str) -> str:
    return re.sub(r"([%_])", r"\\\1", s)

q = q.filter(Listing.district_raw.ilike(f"%{escape_like(district)}%"))
```

---

### MEDIUM

#### M-1: Default database credentials in config and alembic.ini

**Files:** `backend/src/mrf/core/config.py:14`, `backend/alembic.ini:6`  
**Description:** Both files contain hardcoded default connection strings with credentials `mrf:mrf`:

```python
# config.py
database_url: str = "postgresql+psycopg://mrf:mrf@localhost:5432/madrid_rental_finder"
```
```ini
# alembic.ini
sqlalchemy.url = postgresql+psycopg://mrf:mrf@localhost:5432/madrid_rental_finder
```

In production (K8s), `DATABASE_URL` is injected from a Secret — so these defaults only apply in local dev. However, if someone runs the API without setting the env var, it falls back to these creds.

**Risk:** Credential exposure in source code; functional if DB is reachable from attacker's network.  
**Recommendation:**
- Remove the default from `config.py` (make `database_url` required, no default).
- In `alembic.ini`, replace with a placeholder like `driver://user:pass@localhost/dbname` and document that `DATABASE_URL` env var is required.

#### M-2: CORS allows all origins (`allow_origins=["*"]`)

**File:** `backend/src/mrf/api/main.py:49-53`  
**Description:** CORS is configured with `allow_origins=["*"]`. The comment says "LAN-only; tighten in production" — but since this is deployed via K8s with a LoadBalancer IP, it's effectively network-accessible on the LAN.

**Risk:** Any webpage loaded in a browser on the LAN can make cross-origin requests to the API.  
**Recommendation:** Restrict to the dashboard's origin (e.g., `http://192.168.79.42`) or use a config env var for allowed origins.

#### M-3: No API rate limiting

**File:** `backend/src/mrf/api/main.py` (entire API)  
**Description:** The FastAPI API has no rate limiting middleware. While this is read-only and LAN-only, a misbehaving client could hammer the DB with expensive stats/listing queries.

**Risk:** Denial of service via query abuse (especially `/api/stats` which runs multiple aggregate queries).  
**Recommendation:** For LAN use, this is low priority, but consider adding `slowapi` or a simple middleware with per-IP limits (e.g., 60 req/min).

#### M-4: No `securityContext` on any K8s pod

**Files:** All manifests in `k8s/apps/madrid-rental-finder/base/`  
**Description:** No deployments or CronJobs set `securityContext`. Missing:
- `runAsNonRoot: true`
- `readOnlyRootFilesystem: true`
- `allowPrivilegeEscalation: false`
- `capabilities.drop: ["ALL"]`

The Docker image does use `USER mrf` (non-root), but K8s doesn't enforce this at the pod spec level.

**Risk:** Container breakout attack surface is wider than necessary.  
**Recommendation:** Add to all pod specs:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
```

#### M-5: No `activeDeadlineSeconds` or `ttlSecondsAfterFinished` on CronJobs

**Files:** All `cronjob-*.yaml` files  
**Description:** Scraper CronJobs have `backoffLimit: 1` and `concurrencyPolicy: Forbid` (good), but no `activeDeadlineSeconds`. A hung scraper pod could run indefinitely, consuming resources.

**Risk:** Resource exhaustion from stuck scraper pods.  
**Recommendation:** Add to each CronJob's `jobTemplate.spec`:

```yaml
activeDeadlineSeconds: 1800   # 30 min hard timeout
ttlSecondsAfterFinished: 3600 # clean up completed pods after 1h
```

---

### LOW

#### L-1: `healthz` endpoint leaks exception details

**File:** `backend/src/mrf/api/main.py:62`  
**Description:** The health check returns `str(e)` in the HTTP 503 detail, which could leak DB connection strings or internal error messages.

```python
raise HTTPException(status_code=503, detail=str(e))
```

**Recommendation:** Return a generic message: `detail="database unavailable"`.

#### L-2: No `page_size` upper bound enforcement beyond 100

**File:** `backend/src/mrf/api/main.py:110`  
**Description:** `page_size` is capped at `le=100` via FastAPI `Query`, which is fine. However, combined with complex filters, 100 results + eager-loaded images could be memory-heavy. Not a real issue at current scale.

**Recommendation:** Acceptable as-is. Monitor if dataset grows significantly.

#### L-3: Scraper `while True` loop in Spotahome without hard page cap

**File:** `backend/src/mrf/scrapers/spotahome.py:227`  
**Description:** `list_pages()` uses `while True` with a break condition (no listings found). If the site returns non-empty pages indefinitely (e.g., circular pagination), the scraper would loop forever.

**Recommendation:** Add a `MAX_PAGES` constant (like other scrapers) as a hard upper bound:

```python
MAX_PAGES = 200
page = 1
while page <= MAX_PAGES:
    ...
    page += 1
```

#### L-4: `.venv` directory exists in repo tree (but not tracked)

**File:** `backend/.venv/`  
**Description:** The `.venv` directory exists locally and is correctly excluded by `.gitignore`. However, there's no root-level `.gitignore` — only `backend/.gitignore`. If someone creates a venv at the repo root, it would be tracked.

**Recommendation:** Add a root `.gitignore` that also covers common patterns (`.venv/`, `__pycache__/`, `*.pyc`, `.env`).

#### L-5: Duplicate CI workflow for dashboard

**Files:** `.github/workflows/build-and-push.yaml`, `.github/workflows/dashboard.yml`  
**Description:** Both workflows build and push the dashboard image on push to `main` with changes in `frontend/`. This means every frontend push triggers **two** builds of the dashboard image. No security risk, but wasteful and could cause race conditions on image tags.

**Recommendation:** Remove `dashboard.yml` or add a path exclusion in `build-and-push.yaml`.

---

### INFO

#### I-1: Secret management is template-based (no sealed secrets or external secrets)

**File:** `k8s/apps/madrid-rental-finder/overlays/homelab/secret.yaml`  
**Description:** The secret file is correctly a commented-out template with instructions to create manually via `kubectl`. No real credentials are committed. For a homelab this is adequate.

**Recommendation:** For multi-operator environments, consider ExternalSecrets or SealedSecrets.

#### I-2: Docker image uses `python:3.12-slim` — acceptable base

**File:** `backend/Dockerfile`  
**Description:** Uses `python:3.12-slim` (not `alpine` but still minimal). Runs as non-root user `mrf` (uid 1000). Has a health check. No secrets are `COPY`'d into the image. Layer caching is correctly structured (deps before source).

**Status:** ✅ Good practice.

#### I-3: CI secrets are properly handled

**Files:** `.github/workflows/build-and-push.yaml`, `.github/workflows/dashboard.yml`  
**Description:** All sensitive values (`ACR_LOGIN_SERVER`, `ACR_USERNAME`, `ACR_PASSWORD`) are read from GitHub Actions secrets. No `echo` of secrets in log steps. Image tagging uses SHA (immutable) + `latest` (mutable convenience tag). The kustomize overlay commit approach is sound for GitOps.

**Status:** ✅ Good practice.

#### I-4: All DB access uses SQLAlchemy ORM — no raw SQL injection risk

**Files:** `backend/src/mrf/api/main.py`, `backend/src/mrf/scrapers/base.py`  
**Description:** All queries go through SQLAlchemy ORM (`.query()`, `.filter()`, `.filter_by()`). The only `text()` usage is `SELECT 1` in the health check and schema defaults — both are static strings. The alembic migrations use `op.execute()` with static DDL strings. No user input ever reaches raw SQL.

**Status:** ✅ No SQL injection risk.

---

## Dependency Review

**File:** `backend/pyproject.toml`

| Package | Version | Notes |
|---------|---------|-------|
| fastapi | >=0.111.0 | ✅ No known CVEs at this floor |
| uvicorn | >=0.30.0 | ✅ OK |
| sqlalchemy | >=2.0.30 | ✅ OK |
| alembic | >=1.13.0 | ✅ OK |
| httpx | >=0.27.0 | ✅ OK |
| selectolax | >=0.3.21 | ✅ OK (HTML parser, low attack surface) |
| psycopg[binary] | >=3.1.19 | ✅ OK |
| pydantic | >=2.7.0 | ✅ OK |
| pydantic-settings | >=2.3.0 | ✅ OK |
| python-dotenv | >=1.0.1 | ✅ OK |
| tenacity | >=8.3.0 | ✅ OK |

**Note:** All deps use `>=` (floor only, no ceiling). This means `pip install` will grab latest compatible versions. For reproducibility and supply-chain safety, consider pinning with a lockfile (`pip-compile`, `uv.lock`, or similar).

---

## Architecture Security Summary

| Area | Rating | Notes |
|------|--------|-------|
| SQL injection | ✅ Safe | ORM throughout, no raw user SQL |
| Secret handling | 🟡 Medium | Defaults in code, but overridden in prod |
| Input validation | 🟡 Medium | Good FastAPI Query constraints, but ilike wildcards unescaped |
| Dependency security | ✅ Good | No known vulnerabilities, but no lockfile |
| Docker security | ✅ Good | Non-root, slim base, no secrets in layers |
| K8s security | 🟡 Medium | No securityContext, no NetworkPolicy, no pod timeout |
| Scraper safety | ✅ Good | Rate limiting, retries, error handling, timeouts |
| CI/CD security | ✅ Good | Secrets in GH Actions, SHA-based tags, no log leakage |
| API rate limiting | 🟡 Missing | No rate limiting middleware |
| CORS | 🟡 Permissive | `*` origins |

---

## Top Recommendations (Priority Order)

1. **Escape `ilike` wildcards** in district/neighborhood/municipality filters (H-1)
2. **Add `securityContext`** to all K8s pod specs (M-4)
3. **Add `activeDeadlineSeconds`** to CronJobs (M-5)
4. **Remove default DB creds** from config.py and alembic.ini (M-1)
5. **Restrict CORS origins** to dashboard IP/hostname (M-2)
6. **Add `MAX_PAGES` cap** to Spotahome scraper's `while True` loop (L-3)
7. **Add root `.gitignore`** (L-4)
8. **Remove duplicate dashboard workflow** (L-5)

---

*Generated by codesentinel security review agent. For questions, ping @Damian.*
