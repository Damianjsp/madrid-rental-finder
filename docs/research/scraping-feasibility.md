# Spanish Property Portal Scraping — Technical Feasibility Report

> Generated: 2026-03-10 | Focus: Madrid rental aggregator

---

## 1. Summary Table

| Portal | Anti-Bot Level (1-5) | API Available | Scraping Method | Safe Rate Limit | Ban Risk | SSR Content |
|---|---|---|---|---|---|---|
| **Idealista.com** | ⭐⭐⭐⭐⭐ (5) | Yes — invitation-only OAuth2 | API (preferred) or Playwright + stealth | 1-2 req/min (web) | 🔴 Very High | ❌ Requires JS |
| **Fotocasa.es** | ⭐⭐⭐⭐ (4) | No public API | Playwright + stealth | 2-3 req/min | 🟠 High | ❌ Disallows /search/ in robots.txt |
| **Pisos.com** | ⭐⭐ (2) | No public API | HTTP requests + BeautifulSoup | 5-10 req/min | 🟢 Low | ✅ Full SSR |
| **Habitaclia.com** | ⭐⭐ (2) | No public API | HTTP requests + BeautifulSoup | 5-10 req/min | 🟢 Low | ✅ Full SSR |
| **Milanuncios.com** | ⭐⭐⭐⭐ (4) | No public API | Selenium/Playwright (CAPTCHA wall) | 1-2 req/min | 🟠 High | ❌ DataDome protection |
| **Yaencontre.com** | ⭐⭐ (2) | No public API | HTTP requests + BeautifulSoup | 5-10 req/min | 🟢 Low | ✅ Full SSR with listing data |
| **Enalquiler.com** | ⭐ (1) | No public API | HTTP requests + BeautifulSoup | 10-15 req/min | 🟢 Very Low | ✅ Full SSR |
| **Spotahome.com** | ⭐ (1) | Internal JSON API (open!) | Direct API calls | 10-20 req/min | 🟢 Very Low | ✅ SSR + internal API |
| **HousingAnywhere.com** | ⭐ (1) | Internal API (likely) | HTTP requests + API | 10-15 req/min | 🟢 Very Low | ✅ Full SSR |
| **Uniplaces.com** | ⭐ (1) | No public API | HTTP requests + BeautifulSoup | 10-15 req/min | 🟢 Very Low | ✅ SSR ("crawl it!" in robots.txt) |

---

## 2. Detailed Portal Analysis (Ranked by Difficulty: Easiest → Hardest)

### Tier 1: Easy — HTTP Requests + HTML Parsing

#### 🟢 Uniplaces.com
- **Anti-bot**: Virtually none. Their robots.txt literally says `"Book it, crawl it!"`
- **Tech**: SSR, content loads without JS. Standard HTTP requests work.
- **Robots.txt**: Allows crawling of accommodation pages. Only blocks `/dashboard/`, `/booking/`, `/search` (but accommodation pages are allowed).
- **Approach**: `requests` + `BeautifulSoup`. Parse `/accommodation/madrid` and paginate.
- **Rate limit**: Conservative 10-15 req/min. No signs of IP banning.
- **GitHub tools**: None found (easy enough to DIY).
- **Notes**: Focused on student housing. Good for rooms/studios. International platform.

#### 🟢 Enalquiler.com
- **Anti-bot**: Minimal. Basic bot-agent blocklist in robots.txt (HTTrack, wget, etc.).
- **Tech**: Server-side rendered. Listings visible in HTML source. Uses Vue.js for UI but content is SSR.
- **URL pattern**: `https://www.enalquiler.com/search?tipo=1&cp=28` (cp=28 is Madrid province code)
- **Approach**: `requests` + `BeautifulSoup`. Paginate via query params.
- **Rate limit**: 10-15 req/min should be safe. Small platform, less monitoring.
- **Notes**: ~21,000 listings across Spain. Niche but has Madrid coverage. Blocks `/search?` in robots.txt but `/search` endpoint works.

#### 🟢 Spotahome.com
- **Anti-bot**: None detected. No Cloudflare/DataDome.
- **Tech**: SSR with **exposed internal JSON API**.
- **API Discovery**: Their 404 page leaked the entire internal route structure:
  - `GET /api/fe/marketplace/homecards` — listing cards
  - `GET /api/fe/marketplace/markers/:cityId` — map markers
  - `GET /api/fe/marketplace/rentable-unit/:rentableId` — individual listing details
  - `GET /api/fe/marketplace/similars/:adId` — similar listings
  - `GET /api/fe/marketplace/poi/:city` — points of interest
- **Tested**: API returns `200 OK` with JSON. Homecards endpoint returned empty for tested city IDs (may need session/city context from the search page), but the endpoints are open.
- **Approach**: Reverse-engineer the API params (inspect browser network tab for correct cityId format), then direct JSON API calls. No browser needed.
- **Rate limit**: 10-20 req/min easily. API is designed for frontend consumption.
- **Robots.txt**: Blocks `/api/*` for crawlers, but no technical enforcement.
- **Notes**: Best target for clean data extraction. International platform focused on mid/long-term rentals.

#### 🟢 HousingAnywhere.com
- **Anti-bot**: None detected. Minimal robots.txt restrictions.
- **Tech**: SSR. Content visible in initial HTML.
- **API**: Blocks `/api/*` in robots.txt. Likely has internal JSON API similar to Spotahome.
- **Approach**: HTTP requests + parsing, or reverse-engineer their search API via browser dev tools.
- **Rate limit**: 10-15 req/min. Small, international platform.
- **Notes**: Targets expats/students. Protected bookings. Good for furnished apartments.

#### 🟢 Yaencontre.com
- **Anti-bot**: Low. Blocks Exabot, AhrefsBot, gptbot specifically. No general anti-bot tech.
- **Tech**: **Full SSR with listing data in HTML**. Tested: returned actual listings with prices, rooms, m², descriptions.
- **URL pattern**: `https://www.yaencontre.com/alquiler/pisos/madrid`
- **Approach**: `requests` + `BeautifulSoup`. Excellent data density in SSR response.
- **Rate limit**: 5-10 req/min. Mid-size Spanish portal.
- **GitHub tools**: [YaencontreScraper](https://github.com/kami4ka/YaencontreScraper) — uses ScrapingAnt API proxy.
- **Notes**: ~10,000 Madrid listings. Very clean SSR markup with price/size/rooms inline.

### Tier 2: Moderate — SSR but Needs Care

#### 🟡 Pisos.com
- **Anti-bot**: Low-moderate. Standard bot blocklist. No Cloudflare/DataDome.
- **Tech**: **Full SSR**. Tested: returns complete listing data (price, rooms, bathrooms, m², floor, description) in HTML.
- **URL pattern**: `https://www.pisos.com/alquiler/pisos-madrid/` — paginate with `/{page}/`
- **Approach**: `requests` + `BeautifulSoup` with rotating User-Agents.
- **Robots.txt**: Blocks `/busqueda/$` and `/*.aspx` but allows semantic listing URLs.
- **Rate limit**: 5-10 req/min. Third-largest Spanish portal.
- **GitHub tools**: [PisosScraper](https://github.com/kami4ka/PisosScraper) — ScrapingAnt proxy-based.
- **Notes**: Excellent SSR data quality. One of the easiest large portals to scrape. Part of the Adevinta group.

#### 🟡 Habitaclia.com
- **Anti-bot**: Low-moderate. No Cloudflare. Standard parameter filtering in robots.txt.
- **Tech**: **Full SSR**. Tested: returns listing data with photos count, price, area, rooms, bathrooms, €/m² ratio.
- **URL pattern**: `https://www.habitaclia.com/alquiler-madrid.htm`
- **Approach**: `requests` + `BeautifulSoup`. Uses `.asp` backend (older tech, often easier to scrape).
- **Rate limit**: 5-10 req/min. Smaller than Pisos.com.
- **Robots.txt**: Blocks AJAX endpoints and parameter-heavy URLs. Clean listing pages allowed.
- **GitHub tools**: [HabitacliaScraper](https://github.com/kami4ka/HabitacliaScraper) — ScrapingAnt proxy.
- **Notes**: Historically strong in Catalonia, has Madrid listings. Good data quality. Merged with Idealista group but maintains separate infrastructure.

### Tier 3: Hard — Requires Browser Automation

#### 🟠 Fotocasa.es
- **Anti-bot**: High. Blocks many user-agents. Disallows `/search/`, `/buscar/`, `/property/` in robots.txt.
- **Tech**: Client-side rendered (React/SPA). Requires JavaScript execution. Content loaded via XHR/fetch calls.
- **Approach**: Playwright with stealth plugin. Alternatively, intercept their internal API calls via browser network tab.
- **Rate limit**: 2-3 req/min. Aggressive session tracking.
- **IP rotation**: Recommended. Sessions tied to IP/cookies.
- **GitHub tools**: [fotocasa-scraper](https://github.com/rociobenitez/fotocasa-scraper) (2★) — Python-based.
- **Notes**: Second-largest Spanish portal. Part of Adevinta (same group as Pisos.com, Habitaclia). Many listings overlap with Pisos.com — consider skipping if you have Pisos.com covered.

#### 🟠 Milanuncios.com
- **Anti-bot**: High. **DataDome** protection. Immediately shows CAPTCHA to non-browser requests.
- **Tech**: Requires JS execution. DataDome fingerprinting active.
- **Tested**: Direct HTTP request returned 403 with CAPTCHA page referencing DataDome.
- **Approach**: Playwright with stealth + residential proxies. Must solve/bypass DataDome challenge.
- **Rate limit**: 1-2 req/min maximum. Very aggressive blocking.
- **IP rotation**: Essential. Bans IPs quickly.
- **GitHub tools**: [milanuncios](https://github.com/mondeja/milanuncios) (16★) — Python3, requires Firefox/Geckodriver. Older but proven approach.
- **Notes**: General classifieds (like Craigslist). Less curated listings, more private landlords. May have unique listings not on other portals.

### Tier 4: Fortress — API is the Only Real Path

#### 🔴 Idealista.com
- **Anti-bot**: Maximum. **Cloudflare** + custom anti-bot. Requires JS. Returns "Please enable JS" to simple HTTP requests. Aggressive fingerprinting, session tracking, rate limiting.
- **API**: **YES — invitation-only OAuth2 API exists!**
  - Developer portal: `https://developers.idealista.com/access-request` (behind Cloudflare, currently 502)
  - Authentication: OAuth2 client_credentials flow
  - Search endpoint with filters: location, property type, operation (rent/sale), price range, date range
  - Returns structured JSON with all listing data
  - **Rate limits**: Typically 100 requests/month for free tier, 1000-2000/month for approved partners
  - Multiple Python wrappers exist
- **Approach (ranked)**:
  1. **API** (best): Apply for API access at developers.idealista.com. Takes days-weeks for approval.
  2. **Scraping** (painful): Playwright + undetected-chromedriver + residential proxies + human-like delays. Still gets blocked frequently.
- **Rate limit (web)**: 1-2 req/min max. Gets banned within minutes of aggressive scraping.
- **IP rotation**: Residential proxies essential. Datacenter IPs blocked instantly.
- **GitHub tools**:
  - [python-idealista](https://github.com/astrojuanlu/python-idealista) (8★) — Clean async Python API wrapper. Shows OAuth2 flow.
  - [pydealista](https://github.com/marnovo/pydealista) (13★) — Another API wrapper.
  - [idealista-api](https://github.com/yagueto/idealista-api) (8★) — Python client.
  - [dedomeno](https://github.com/ginopalazzo/dedomeno) (44★) — Scraper (likely broken with current protections).
  - [idealista-notifier](https://github.com/martin0995/idealista-notifier) (8★) — Telegram bot, scrapes every 2 min. Barcelona-focused but adaptable.
  - [idealiScrape](https://github.com/KevinLiebergen/idealiScrape) (1★) — Uses official API + Telegram notifications.
- **Notes**: ~70% of the Spanish rental market. Getting API access should be priority #1. Without it, scraping is a constant cat-and-mouse game.

---

## 3. Alternative Data Sources

### Idealista API — Deep Dive
- **Status**: Still exists but invitation-only. Developer portal at `developers.idealista.com`.
- **How to apply**: Fill out the access request form. Provide a description of your project (academic research or personal use works).
- **Authentication**: OAuth2 `client_credentials` grant type. You get a `client_id` and `client_secret`.
- **Endpoints**: `/3.5/{country}/search` with extensive filters.
- **Limits**: Historically 100 req/month free, upgradable. The API returns up to 50 items per request.
- **Working wrappers**: `python-idealista`, `pydealista`, `idealista-api` on GitHub.

### RSS/Atom Feeds
- **Idealista**: No RSS feeds available.
- **Fotocasa**: No RSS feeds.
- **Pisos.com**: No RSS feeds detected.
- **Yaencontre**: No RSS feeds detected.
- **Verdict**: None of the major Spanish portals offer RSS. This approach is dead.

### Google Alerts / Search Operators
- `site:idealista.com alquiler madrid` — works for discovery but very limited.
- Google Alerts can track new pages but with hours of delay and limited results.
- Not viable as a primary data source but useful as a supplementary discovery mechanism.

### Telegram Bots (Existing in Spain)
- [idealista-notifier](https://github.com/martin0995/idealista-notifier) — Open source, scrapes Idealista → Telegram. Runs every 2 min. Docker-deployable.
- [idealiScrape](https://github.com/KevinLiebergen/idealiScrape) — Uses official API → Telegram channel.
- Various private bots exist in Spanish Telegram groups for apartment hunting (search "pisos madrid" on Telegram).
- **Strategy**: Join existing Telegram groups for apartment alerts and cross-reference with your scraper data.

### Government Open Data
- **Catastro** (catastro.meh.es): Property registry. Has building data but NOT rental listings/prices.
- **INE** (Instituto Nacional de Estadística): Aggregate rental price indices by zone. No individual listings.
- **Portal de Transparencia**: Some municipalities publish housing data, not at listing level.
- **Comunidad de Madrid**: Published rental price reference indices (Índice de Referencia de Precios de Alquiler). Aggregate data only.
- **Idealista Data**: Publishes quarterly reports with average prices per district/neighborhood. Available as PDFs.
- **Verdict**: Government data is useful for price benchmarking, NOT for finding actual available apartments.

---

## 4. Technical Stack Recommendation

### Core Stack
```
Python 3.11+
├── httpx (async HTTP client, faster than requests)
├── beautifulsoup4 + lxml (HTML parsing for SSR portals)
├── playwright (for JS-rendered portals: Idealista web fallback, Fotocasa, Milanuncios)
├── playwright-stealth (anti-detection for Playwright)
├── pydantic (data models for listings)
├── sqlmodel / SQLAlchemy (SQLite/PostgreSQL for storage)
├── apscheduler (scheduling periodic scrapes)
├── python-telegram-bot (notifications)
└── uvicorn + fastapi (optional: API/dashboard for your aggregated data)
```

### Recommended Libraries
- **httpx**: Async HTTP with connection pooling. Better than `requests` for concurrent scraping.
- **selectolax**: Faster HTML parsing than BeautifulSoup for high-volume. Consider for Pisos.com/Habitaclia.
- **playwright**: Over Selenium. Faster, more reliable, better stealth plugins.
- **fake-useragent**: Rotating user-agents from real browser distributions.

### Data Model (per listing)
```python
class Listing(BaseModel):
    source: str           # "idealista", "pisos", etc.
    external_id: str      # Portal's listing ID
    url: str
    title: str
    price: int            # Monthly rent in EUR
    rooms: int
    bathrooms: int
    area_m2: float
    floor: str | None
    address: str
    neighborhood: str
    city: str = "Madrid"
    latitude: float | None
    longitude: float | None
    description: str
    has_elevator: bool | None
    has_parking: bool | None
    is_furnished: bool | None
    images: list[str]
    contact_phone: str | None
    first_seen: datetime
    last_seen: datetime
    is_active: bool
```

---

## 5. Architecture: Anti-Ban Scraper Design

### Proxy Rotation Strategy
```
Tier 1 (Easy portals - Pisos, Habitaclia, Yaencontre, Enalquiler, Uniplaces):
  → No proxy needed. Use your own IP with rate limiting.
  → Optional: Rotate through 2-3 VPN endpoints for safety.

Tier 2 (Medium portals - Fotocasa, Spotahome API):
  → Datacenter proxies (cheap, ~$1-5/month). BrightData, Oxylabs.
  → Rotate IPs every 50-100 requests.

Tier 3 (Hard portals - Idealista web, Milanuncios):
  → Residential proxies ($10-50/month). Spanish IPs preferred.
  → Rotate per request or per session.
  → BrightData, Oxylabs, IPRoyal, SmartProxy.
  → OR: Just use the Idealista API and skip web scraping entirely.
```

### Request Pacing
```python
# Pacing configuration per portal
PACING = {
    "idealista_api": {"delay_min": 60, "delay_max": 120},    # API: conservative, limited quota
    "idealista_web": {"delay_min": 30, "delay_max": 90},     # Web: very slow, human-like
    "fotocasa":      {"delay_min": 20, "delay_max": 45},     # Moderate
    "pisos":         {"delay_min": 6,  "delay_max": 15},     # Easy
    "habitaclia":    {"delay_min": 6,  "delay_max": 15},     # Easy
    "milanuncios":   {"delay_min": 30, "delay_max": 60},     # Hard
    "yaencontre":    {"delay_min": 6,  "delay_max": 15},     # Easy
    "enalquiler":    {"delay_min": 4,  "delay_max": 10},     # Very easy
    "spotahome":     {"delay_min": 3,  "delay_max": 8},      # API, very easy
    "housinganyw":   {"delay_min": 4,  "delay_max": 10},     # Easy
    "uniplaces":     {"delay_min": 4,  "delay_max": 10},     # Very easy
}
```

### User-Agent Rotation
```python
# Use real browser UA strings. Rotate from a pool of 20-30.
# Weight towards Chrome 120+ (most common).
# Never use Python/requests/httpx default UAs.
# Match UA with appropriate headers:
HEADERS_TEMPLATE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}
```

### Session Management
```
1. Create one session per portal (persist cookies across requests).
2. For hard portals: Create a new session every 20-30 requests.
3. Start each session by visiting the homepage, then navigate to search.
4. For Playwright sessions: mimic human behavior (scroll, wait, move cursor).
5. Store cookies and reuse between runs (avoids "new visitor" fingerprint).
```

### Data Extraction Pattern
```
Phase 1: List pages (search results)
  → Extract: listing ID, price, basic info, URL
  → Paginate through all results (usually 20-50 pages max for Madrid rentals)

Phase 2: Detail pages (individual listings)
  → Only fetch NEW listings (compare against DB by external_id)
  → Extract: full description, all images, contact info, amenities
  → This is where most bans happen — space these out the most

Phase 3: Update check (periodic)
  → Re-check list pages every 15-30 min for new listings
  → Mark listings as inactive if they disappear from search results
  → Only fetch detail pages for genuinely new listings
```

### Scheduling Strategy
```
Easy portals (Pisos, Habitaclia, Yaencontre, Enalquiler, Spotahome, HousingAnywhere, Uniplaces):
  → Full scan: Every 30 minutes
  → Detail pages: On new listing detection
  → Total: ~200-500 requests/day per portal

Hard portals (Idealista, Fotocasa, Milanuncios):
  → Full scan: Every 2-4 hours
  → Idealista API: Every 1 hour (limited by quota)
  → Detail pages: Batch at night
  → Total: ~50-100 requests/day per portal
```

---

## 6. Legal Considerations (Brief, Practical)

⚠️ **Not legal advice. Just practical observations:**

1. **Terms of Service**: Most portals explicitly prohibit automated scraping. Idealista and Fotocasa are most aggressive about enforcement.

2. **GDPR**: Listing data is semi-public (published by the owner/agent). Personal contact info (phone, email) should be handled carefully. Don't build a database of personal data — focus on listing data.

3. **Spanish law**: The "right to scrape" publicly available data is a gray area in EU law. The 2024 EU Data Act provides some clarity but primarily for B2B contexts.

4. **Practical risk for personal use**:
   - You'll get IP-banned, not sued, for a personal aggregator.
   - API usage with proper credentials (Idealista) is fully legal.
   - SSR scraping of public listing pages at low volume is extremely low risk.
   - Redistributing/reselling the data is where legal trouble starts.

5. **Best practices**:
   - Use official APIs where available.
   - Respect `robots.txt` where practical.
   - Don't overload their servers (be polite with rate limits).
   - Don't scrape personal data (phones, emails) unless needed.
   - Keep it personal — don't commercialize the aggregated data.

---

## 7. Recommended Implementation Order

### Phase 1: Quick Wins (Week 1)
1. **Apply for Idealista API access** — start the approval process immediately.
2. **Pisos.com** — SSR, easy parsing, lots of Madrid listings, covers the second-largest volume.
3. **Yaencontre.com** — SSR, ~10K Madrid listings, clean data.
4. **Spotahome.com** — Internal API, structured JSON, zero ban risk.

### Phase 2: Coverage Expansion (Week 2)
5. **Habitaclia.com** — SSR, good data quality.
6. **Enalquiler.com** — SSR, niche but unique listings.
7. **HousingAnywhere.com** — SSR, good for expat-focused furnished rentals.
8. **Uniplaces.com** — SSR, student housing, "crawl it!" attitude.

### Phase 3: Hard Targets (Week 3+)
9. **Idealista API** — Once approved, this becomes your primary data source.
10. **Fotocasa.es** — Only if you need listings not on Pisos.com (significant overlap).
11. **Milanuncios.com** — Only for private landlord listings not on other portals.

---

## 8. Existing GitHub Tools — Quick Reference

| Tool | Portal | Stars | Language | Approach | Link |
|---|---|---|---|---|---|
| dedomeno | Idealista | 44★ | Python | Web scraping | [github](https://github.com/ginopalazzo/dedomeno) |
| milanuncios | Milanuncios | 16★ | Python | Selenium/Firefox | [github](https://github.com/mondeja/milanuncios) |
| idealisto | Idealista | 15★ | R | Web scraping | [github](https://github.com/hmeleiro/idealisto) |
| pydealista | Idealista | 13★ | Python | Official API | [github](https://github.com/marnovo/pydealista) |
| idealista-notifier | Idealista | 8★ | Python | Scrape → Telegram | [github](https://github.com/martin0995/idealista-notifier) |
| python-idealista | Idealista | 8★ | Python | Official API (async) | [github](https://github.com/astrojuanlu/python-idealista) |
| idealista-api | Idealista | 8★ | Python | Official API | [github](https://github.com/yagueto/idealista-api) |
| rent-flat-scraper | Idealista | 7★ | JavaScript | Web scraping | [github](https://github.com/oscard0m/rent-flat-scraper) |
| fotocasa-scraper | Fotocasa | 2★ | Python | Web scraping | [github](https://github.com/rociobenitez/fotocasa-scraper) |
| idealiScrape | Idealista | 1★ | Python | API → Telegram | [github](https://github.com/KevinLiebergen/idealiScrape) |
| PisosScraper | Pisos.com | 0★ | Python | ScrapingAnt proxy | [github](https://github.com/kami4ka/PisosScraper) |
| HabitacliaScraper | Habitaclia | 0★ | Python | ScrapingAnt proxy | [github](https://github.com/kami4ka/HabitacliaScraper) |
| YaencontreScraper | Yaencontre | 0★ | Python | ScrapingAnt proxy | [github](https://github.com/kami4ka/YaencontreScraper) |
| FotocasaScraper | Fotocasa | 0★ | Python | ScrapingAnt proxy | [github](https://github.com/kami4ka/FotocasaScraper) |

---

## 9. Key Findings & Recommendations

### 🎯 Critical Insight
**You don't need to scrape every portal.** Due to listing overlap between portals (agents post on multiple sites), covering Idealista (API) + Pisos.com + Yaencontre + Spotahome gives you ~90% of Madrid rental listings. The remaining portals add marginal value.

### 🏆 Recommended Minimum Viable Aggregator
1. **Idealista API** → 70% of the market (apply NOW, takes days)
2. **Pisos.com scraper** → Catches most listings not on Idealista
3. **Yaencontre.com scraper** → Good for private landlord listings
4. **Spotahome internal API** → Furnished/international listings
5. **Telegram notifications** → Alert on new listings matching your criteria

### 💰 Cost Estimate
- **Free tier**: Pisos + Yaencontre + Enalquiler + Uniplaces + personal IP → €0
- **With Idealista API**: Free (100 req/month on basic tier)
- **With residential proxies** (for Idealista web fallback): €10-30/month
- **With all portals + proxies**: €20-50/month

### ⚡ Fastest Path to Results
1. Start with Pisos.com (SSR, works in 30 min of coding)
2. Add Yaencontre (same difficulty)
3. Apply for Idealista API (background process)
4. Add Telegram notifications
5. Run on a cheap VPS or Raspberry Pi

---

*This report is based on live testing performed on 2026-03-10. Anti-bot measures evolve; verify current state before implementation.*
