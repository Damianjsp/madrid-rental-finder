# Frontend QA Report — Madrid Rental Finder

Date: 2026-03-11
Repo: `madrid-rental-finder`
Scope: `frontend/`

## Overall verdict
Quality score: **6/10**

The frontend is in decent MVP shape visually and the production build passes, but it is **not Phase 2 complete** and has a few correctness / QA gaps:
- lint fails
- API contract is not aligned with the architecture docs
- key Phase 2 features are missing (`saved presets`, `favorites`)
- mobile responsiveness is weak for table-heavy views
- some accessibility and UX details need cleanup

---

## 1. Build verification

### `npm ci`
Status: ✅ Pass

### `npm run build`
Status: ✅ Pass

Output summary:
- `tsc -b && vite build` completed successfully
- production bundle built cleanly

### `npm run lint`
Status: ❌ Fail

#### Errors
1. **High** — `src/hooks/useLastVisit.ts:13`
   - ESLint: `react-hooks/set-state-in-effect`
   - `setLastVisit()` is called synchronously inside `useEffect`
   - Risk: extra render / cascading render pattern

2. **Medium** — `src/mocks/data.ts:223`
   - ESLint: `no-constant-binary-expression`
   - `Number(l.size_m2) ?? 0` is invalid logic because `Number(...)` is never nullish

3. **Medium** — `src/mocks/data.ts:224`
   - Same issue as above

#### Warnings
4. **Low** — `src/views/ListingsView.tsx:135`
   - React compiler warning around `useReactTable()` incompatible memoization assumptions
   - Not blocking, but worth noting

5. **Low** — `src/views/NeighborhoodsView.tsx:118`
   - Same TanStack warning

---

## 2. Code review findings

### Critical
None found.

### High

#### H1. API client does not match documented backend contract
Files:
- `frontend/src/api/index.ts`
- `docs/architecture/implementation-plan.md`

Problem:
- Docs for Phase 1/2 document these minimal read endpoints:
  - `GET /healthz`
  - `GET /listings`
  - `GET /neighborhoods`
  - `GET /stats`
- Frontend calls:
  - `GET /api/listings`
  - `GET /api/listings/:id`
  - `GET /api/neighborhoods`
  - `GET /api/stats`
  - `GET /api/portals`

Mismatch:
- `/api` prefix is undocumented
- `GET /listings/:id` is undocumented
- `GET /portals` is undocumented

Impact:
- frontend can ship against mock data but break immediately against the real backend unless backend grows undocumented endpoints or a reverse proxy rewrites paths

Recommendation:
- either update docs/spec to include the real frontend contract, or update the frontend client to match the documented API exactly
- don’t leave this implicit

#### H2. Phase 2 feature gap: saved presets missing
Spec source:
- `docs/architecture/implementation-plan.md`

Problem:
- Phase 2 explicitly includes **“Listings table (filters + saved presets)”**
- I found filter controls, but no preset save/load UI, no local persistence, no preset model

Impact:
- implementation is incomplete against the plan

Recommendation:
- add preset save/load/delete backed by localStorage first

#### H3. Phase 2 feature gap: favorites missing
Spec source:
- `docs/architecture/implementation-plan.md`

Problem:
- Phase 2 explicitly includes **“Favorites (stored in localStorage first; DB later)”**
- no favorites button, no favorite state, no persisted favorites list

Impact:
- another explicit spec miss

Recommendation:
- add favorite toggle in table and drawer, plus a favorites-only filter

### Medium

#### M1. Mock data district mapping is inconsistent / incorrect
Files:
- `frontend/src/mocks/data.ts`
- `docs/architecture/database-schema.md`

Problem examples:
- `Prosperidad` is assigned `district_name: 'Hortaleza'`, but Prosperidad belongs to **Chamartín**, not Hortaleza
- `district_id` values in mock neighborhoods/listings appear arbitrary and are not trustworthy vs real Madrid district mapping
- benchmark fields named `district_avg_rent_*` are sometimes populated from neighborhood-level mock data, which blurs scope semantics

Impact:
- UI demos can mislead users
- frontend logic may get validated against bad assumptions

Recommendation:
- clean mock fixtures to match real district/neighborhood taxonomy and benchmark scope exactly

#### M2. Empty/error states are generic and lose useful detail
Files:
- `frontend/src/components/ui/Spinner.tsx`
- views using `ErrorState`

Problem:
- errors render only generic messages like `Failed to load listings`
- no retry CTA
- no surfaced status code / message from `apiFetch`

Impact:
- poor debugging and weak UX when real API fails

Recommendation:
- show actionable message + retry button
- optionally expose `Error.message` for non-prod / debug mode

#### M3. Table sorting UX is misleading vs server-side query model
Files:
- `src/views/ListingsView.tsx`
- `src/api/index.ts`

Problem:
- API/filter model already has a backend `sort` field (`newest`, `price_*`, `size_*`)
- table headers also expose client-side TanStack sorting on all columns
- sorting UI state is not synchronized with API `filters.sort`

Impact:
- two competing sort systems
- with paginated real API data, client-side sorting on one page is not the same as dataset sorting

Recommendation:
- choose one model:
  - either server-driven sorting only, wired to header clicks
  - or clearly separate local sort from backend sort

#### M4. Pagination control is not scalable
File:
- `src/views/ListingsView.tsx`

Problem:
- pagination buttons render `1..min(pages,7)` only
- no sliding window around the active page

Impact:
- bad UX once pages > 7; user cannot directly jump to middle ranges

Recommendation:
- render a window around current page with ellipses

#### M5. Accessibility: several interactive controls lack strong labels
Files:
- `src/App.tsx`
- `src/components/ListingDrawer.tsx`
- `src/components/FilterPanel.tsx`

Examples:
- top nav icon buttons collapse to icon-only on small screens and rely on hidden text; accessible name may survive, but this needs explicit validation and is brittle
- drawer close button has no explicit `aria-label`
- image carousel prev/next buttons have no explicit `aria-label`
- toggle UI for `Active only` is a clickable `div` inside a label, not a real checkbox/switch control

Impact:
- weaker screen reader semantics and keyboard accessibility

Recommendation:
- use semantic button/checkbox/switch controls with explicit labels

#### M6. Listing drawer lacks focus management / dialog semantics
File:
- `src/components/ListingDrawer.tsx`

Problem:
- drawer is visually modal but not implemented as an accessible dialog
- no `role="dialog"`, `aria-modal`, focus trap, or Escape handling found

Impact:
- keyboard / assistive-tech usability issue

Recommendation:
- treat drawer as proper dialog

#### M7. `useLastVisit` behavior can make “NEW” flaky during same-session QA
File:
- `src/hooks/useLastVisit.ts`

Problem:
- it reads previous timestamp then immediately overwrites localStorage on mount
- logic is okay-ish for simple use, but coupled with generic mock timestamps it can behave inconsistently during repeated refresh testing

Recommendation:
- initialize state lazily from localStorage and separate “read previous visit” from “write current visit” more cleanly

### Low

#### L1. No dark mode toggle despite strong dark theme styling
Problem:
- app is consistently dark, which is fine visually, but there is no theme choice
- not a spec miss, just a UX note

#### L2. No explicit loading skeletons
Problem:
- loading states exist, but they are plain spinners
- for dense tables/cards, skeletons would feel better

#### L3. `StatsView` sorts `stats.by_district` in place
File:
- `src/views/StatsView.tsx`

Problem:
- `stats.by_district.sort(...)` mutates query data

Impact:
- low in this app, but mutating cached query data is not great practice

Recommendation:
- sort a cloned array: `[...stats.by_district].sort(...)`

---

## 3. Visual QA

Dev server status: ✅ `npm run dev` launched successfully

### Screenshots captured
- Listings: `/home/damian/.openclaw/media/browser/9b7be944-1c40-4b95-83fe-5872f2638966.png`
- Listing drawer: `/home/damian/.openclaw/media/browser/78ab9d42-0030-45df-96d5-a819c6930068.png`
- Stats: `/home/damian/.openclaw/media/browser/b3d0fbfc-5e11-4205-8394-3533cd2f1fe4.png`
- Neighborhoods: `/home/damian/.openclaw/media/browser/2194800d-bb8b-4178-9275-61a1dd544c62.png`
- Mobile/responsive sample: `/home/damian/.openclaw/media/browser/02839f6f-1b78-4349-a8cb-0867685cd4f5.png`

### Visual findings

#### Good
- Dark theme is visually consistent across Listings / Drawer / Neighborhoods / Stats
- Visual hierarchy is clean and readable on desktop
- Drawer design is solid for an MVP
- Badge and score components are consistent

#### Issues

##### Medium — Mobile responsiveness is weak for data tables
- On narrow viewport (`390x844`), nav collapses to icon-only and main tables still require heavy horizontal scanning/overflow
- Neighborhoods table especially remains desktop-first
- technically usable, but not pleasant on mobile

##### Medium — Listings drawer opens correctly, but modal UX is incomplete
- visually okay
- no obvious keyboard affordances or modal semantics

##### Low — Stats page is the strongest responsive view
- cards adapt better than table views

##### Low — Filter UX works, but dense controls can feel cramped on smaller widths
- especially the 7-column desktop filter strip

### Functional spot checks

#### Listings
- filter panel renders correctly
- sorting controls visible
- listing row click opens drawer
- source portal link present in table and drawer ✅
- `NEW` indicator appears after revisit ✅

#### Neighborhoods
- search field present
- table sorts appear available
- safety/transport + benchmark rent visible ✅

#### Stats
- overview cards and portal status render ✅

#### Pagination
- dataset too small to fully stress edge cases
- current implementation is functional for low page counts, but limited for larger result sets

---

## 4. API contract validation

### What matches the docs
- frontend models include the major listing fields expected from normalized listing data
- filters cover documented MVP dimensions:
  - price range
  - bedrooms
  - size
  - district / neighborhood
  - portal
  - active only
  - sort
- neighborhoods UI includes safety/transport + benchmark rent overlay
- stats UI includes counts by district/portal

### What does not match

#### Endpoint mismatch
Documented:
- `GET /listings`
- `GET /neighborhoods`
- `GET /stats`

Frontend expects:
- `GET /api/listings`
- `GET /api/listings/:id`
- `GET /api/neighborhoods`
- `GET /api/stats`
- `GET /api/portals`

#### Undocumented response assumptions
- `Portal[]` endpoint is used by filters but not in architecture docs
- `Listing detail` endpoint is used by drawer but not in architecture docs
- `ListingsResponse` pagination shape is assumed in frontend but not described in the implementation plan

#### Error handling gap
- client throws on non-OK response, but UI doesn’t provide retries or richer diagnostics

### Verdict
Contract alignment: **partial**

The frontend reflects the intended domain, but the **actual HTTP contract is drifting from the documented one**. Eso hay que cuadrarlo antes de integrar backend real.

---

## 5. Cross-reference with implementation plan Phase 2

### Implemented
- ✅ Listings table
- ✅ Listing detail drawer
- ✅ direct source portal URL CTA
- ✅ Neighborhood view with safety/transport + rent benchmark data
- ✅ “New since last visit” indicator

### Missing / incomplete
- ❌ Saved presets
- ❌ Favorites (localStorage)
- ⚠️ No explicit “where should I look this week?” helper workflow; user can infer from data, but no dedicated shortlist/recommendation UX exists

### Extra, undocumented frontend expectations
- `Portals` endpoint
- Listing detail endpoint

---

## 6. Recommendations

### Must fix before real backend integration
1. Fix lint errors
2. Align API contract with docs/backend
3. Correct mock geography / benchmark data
4. Decide one sorting model (server vs client) and wire it properly

### Should fix next
5. Add Favorites with localStorage
6. Add Saved Presets with localStorage
7. Improve drawer accessibility (dialog semantics, Escape, focus trap)
8. Replace fake switch with semantic input/button pattern
9. Add richer error states + retry actions

### Nice to have
10. Improve mobile layout for tables
11. Better pagination windowing
12. Skeleton loaders instead of spinner-only states

---

## Summary by severity

### High
- API contract mismatch with architecture docs
- Saved presets missing (Phase 2 gap)
- Favorites missing (Phase 2 gap)

### Medium
- Mock data correctness issues (district mapping / benchmark scope)
- Generic error handling UX
- Conflicting sort model (client + server style)
- Pagination edge-case UX
- Accessibility labels / semantics gaps
- Drawer missing dialog/focus handling

### Low
- TanStack compiler warnings
- Dark-mode-only UX
- Spinner-only loading states
- In-place sort mutation in stats view

---

## Final call
If this were a private MVP demo, fine.
If this is supposed to integrate to the real backend now, **not yet**.

Main blockers are contract drift + missing explicit Phase 2 features. The UI base is good, but the spec compliance is only partial.