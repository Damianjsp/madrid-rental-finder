"""
Spotahome scraper — markers discovery + robust detail page extraction.

Run: python -m mrf.scrapers.spotahome
"""

import json
import logging
import re
from typing import Iterator

import httpx
from selectolax.parser import HTMLParser

from mrf.neighborhoods import apply_title_neighborhood_fallback, extract_neighborhood_from_title
from mrf.scrapers.base import BaseScraper, ListingData, ParseError

log = logging.getLogger("mrf.scrapers.spotahome")

BASE_URL = "https://www.spotahome.com"
MARKERS_URL = f"{BASE_URL}/api/fe/marketplace/markers/madrid"
SEARCH_URL = f"{BASE_URL}/es/s/madrid"
MAX_PAGES = 100


def _safe_int(val) -> int | None:
    try:
        return int(float(val)) if val is not None else None
    except (TypeError, ValueError):
        return None


def _safe_float(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _extract_json_objects(html: str) -> list[dict]:
    objs: list[dict] = []
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL):
        try:
            payload = json.loads(m.group(1))
        except Exception:
            continue
        if isinstance(payload, dict):
            objs.append(payload)
        elif isinstance(payload, list):
            objs.extend([x for x in payload if isinstance(x, dict)])
    return objs


def _extract_breadcrumbs(tree: HTMLParser) -> list[str]:
    crumbs = []
    for node in tree.css('[itemprop="name"]'):
        txt = _clean(node.text(strip=True))
        if txt and txt not in crumbs:
            crumbs.append(txt)
    return crumbs


def _infer_district_from_text(text: str | None) -> str | None:
    if not text:
        return None
    patterns = [
        r"madrid\s+(centro|salamanca|chamber[ií]|chamart[ií]n|tetu[aá]n|retiro|arganzuela|moncloa-aravaca|latina|carabanchel|usera|puente de vallecas|moratalaz|ciudad lineal|hortaleza|villaverde|villa de vallecas|vic[aá]lvaro|san blas-canillejas|barajas)",
        r"(?:district|distrito)[:\s]+([a-zA-ZÁÉÍÓÚáéíóúñÑ\- ]+)",
        r"rooms?\s+for\s+rent\s+in\s+madrid\s+([a-zA-ZÁÉÍÓÚáéíóúñÑ\- ]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return _clean(m.group(1).title())
    return None


def _parse_json_ld_item(item: dict, marker: dict | None) -> ListingData:
    inner = item.get("item", item)
    lid = str(inner.get("identifier", ""))
    url_path = inner.get("url", "")
    url = BASE_URL + url_path if url_path.startswith("/") else (url_path or f"{BASE_URL}/es/madrid/for-rent:rooms/{lid}")
    title = inner.get("name", "")
    address = inner.get("address", {}) or {}
    address_raw = address.get("streetAddress")
    neighborhood_raw = address.get("addressLocality")
    extracted_neighborhood = extract_neighborhood_from_title(title)
    if extracted_neighborhood and (not neighborhood_raw or neighborhood_raw.strip().lower() == "madrid"):
        neighborhood_raw = extracted_neighborhood
    district_raw = None
    price_eur = None
    lat = None
    lon = None
    if marker:
        # Spotahome pricing comes from the markers JSON API as numeric values (or null),
        # not free-form DOM text, so the HTML scraper keyword guard is not needed here.
        price_eur = _safe_int(marker.get("minimumPrice")) or _safe_int(marker.get("price"))
        coord = marker.get("coord", [None, None])
        if coord and len(coord) == 2:
            lon = _safe_float(coord[0])
            lat = _safe_float(coord[1])
    bedrooms = _safe_int(inner.get("numberOfRooms"))
    bathrooms = _safe_int(inner.get("numberOfBathroomsTotal"))
    images = []
    img = inner.get("image")
    if isinstance(img, str) and img.startswith("http"):
        images = [img]
    elif isinstance(img, list):
        images = [i for i in img if isinstance(i, str) and i.startswith("http")][:10]
    title_lower = title.lower() if title else ""
    if "estudio" in title_lower:
        property_type = "estudio"
    elif "habitaci" in title_lower:
        property_type = "habitacion"
    elif "apart" in title_lower or "piso" in title_lower:
        property_type = "piso"
    else:
        property_type = "piso"
    return ListingData(
        source_listing_id=lid,
        url=url,
        title=title,
        price_eur=price_eur,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        property_type=property_type,
        address_raw=address_raw,
        neighborhood_raw=neighborhood_raw,
        district_raw=district_raw,
        municipality_raw="Madrid",
        lat=lat,
        lon=lon,
        images=images,
        raw={"identifier": lid, "marker": marker, "address": address},
    )


def _parse_detail_page(html: str, partial: ListingData) -> ListingData:
    tree = HTMLParser(html)
    lowered = html.lower()
    json_docs = _extract_json_objects(html)

    for d in json_docs:
        kind = d.get("@type")
        if kind == "Product":
            partial.title = partial.title or d.get("name")
            partial.description = partial.description or _clean(d.get("description"))
            offers = d.get("offers", {}) or {}
            partial.price_eur = partial.price_eur or _safe_int(offers.get("price") or offers.get("lowPrice"))
        if kind in {"Apartment", "Residence", "LodgingBusiness", "ApartmentComplex"}:
            partial.bedrooms = partial.bedrooms or _safe_int(d.get("numberOfRooms"))
            partial.bathrooms = partial.bathrooms or _safe_int(d.get("numberOfBathroomsTotal"))
            adr = d.get("address", {}) or {}
            partial.address_raw = partial.address_raw or adr.get("streetAddress")
            partial.neighborhood_raw = partial.neighborhood_raw or adr.get("addressLocality")

    if not partial.description:
        meta_match = re.search(r'<meta[^>]+(?:name|property)="(?:description|og:description)"[^>]+content="([^"]+)"', html, re.I)
        if meta_match:
            partial.description = _clean(meta_match.group(1))

    embedded_desc = re.search(r'"description":"(<p>.*?</p>)"', html, re.S)
    if embedded_desc and (not partial.description or len(partial.description) < 80):
        partial.description = _clean(embedded_desc.group(1))

    for pattern in [r'([\d]+(?:[.,]\d+)?)m²', r'([\d]+(?:[.,]\d+)?)\s*m\^?2', r'"area":([\d]+(?:\.\d+)?)']:
        if partial.size_m2 is None:
            m = re.search(pattern, html, re.I)
            if m:
                partial.size_m2 = _safe_float(m.group(1).replace(',', '.'))

    if partial.lat is None or partial.lon is None:
        m = re.search(r'"coords":\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]', html)
        if m:
            partial.lon = partial.lon if partial.lon is not None else _safe_float(m.group(1))
            partial.lat = partial.lat if partial.lat is not None else _safe_float(m.group(2))

    if partial.address_raw is None:
        m = re.search(r'"address":"([^"]+)"', html)
        if m:
            partial.address_raw = _clean(m.group(1))

    if partial.property_type is None:
        m = re.search(r'"property type:\s*([^<]+)<', lowered)
        if m:
            partial.property_type = _clean(m.group(1))
    if partial.property_type == "piso" and re.search(r'"type":"room_', html):
        partial.property_type = "habitacion"

    # Extract neighborhood from propertySeoMetaTitle (e.g. "Rooms for rent in Madrid Centro")
    seo_match = re.search(r'"propertySeoMetaTitle":"([^"]+)"', html)
    if seo_match:
        seo_title = seo_match.group(1)
        m = re.search(r"(?:in|en)\s+(?:Madrid\s+)?(.+)", seo_title, re.I)
        if m:
            candidate = _clean(m.group(1))
            if candidate and candidate.lower() not in {"madrid", "spain", "españa"}:
                partial.neighborhood_raw = partial.neighborhood_raw or candidate

    # Breadcrumbs as fallback for neighborhood
    breadcrumbs = _extract_breadcrumbs(tree)
    _skip = {"inicio", "madrid", "españa", "spain"}
    if not partial.neighborhood_raw:
        for crumb in breadcrumbs[::-1]:
            cl = crumb.lower()
            if cl in _skip or "alquiler" in cl or "piso en" in cl or "habitaci" in cl or "room" in cl:
                continue
            partial.neighborhood_raw = crumb
            break

    district_hint = None
    for candidate in [partial.title, partial.description, _clean(" ".join(breadcrumbs)), html]:
        district_hint = _infer_district_from_text(candidate)
        if district_hint:
            break
    if district_hint:
        partial.district_raw = partial.district_raw or district_hint

    detail_text = _clean(html)
    if partial.furnished is None:
        if re.search(r'\bamueblad[oa]s?\b|\bfurnished\b', lowered):
            partial.furnished = True
        elif re.search(r'sin muebles|unfurnished', lowered):
            partial.furnished = False

    if partial.elevator is None:
        if re.search(r'ascensor|elevator:\s*yes', lowered):
            partial.elevator = True
        elif re.search(r'elevator:\s*no', lowered):
            partial.elevator = False

    if detail_text:
        partial.raw = {**(partial.raw or {}), "detail_excerpt": detail_text[:1200]}

    images = list(partial.images)
    for img in tree.css('img[src], source[srcset]'):
        src = img.attributes.get('src') or img.attributes.get('srcset', '')
        if src and ',' in src:
            src = src.split(',')[0].strip().split(' ')[0]
        if src.startswith('http') and 'spotahome' in src and src not in images:
            images.append(src)
        if len(images) >= 12:
            break
    partial.images = images

    return partial


class SpotahomeScraper(BaseScraper):
    portal_key = "spotahome"
    rate_min = 1.0
    rate_max = 4.0

    def _build_client(self) -> httpx.Client:
        return httpx.Client(
            headers={
                "User-Agent": self._ua,
                "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Referer": "https://www.spotahome.com/",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        )

    def _fetch_markers(self) -> dict[str, dict]:
        log.info("[spotahome] Fetching all markers...")
        resp = self._get(MARKERS_URL, headers={"Accept": "application/json"}, retries=3)
        markers = resp.json().get("data", [])
        log.info("[spotahome] Got %s markers", len(markers))
        by_id: dict[str, dict] = {}
        for marker in markers:
            lid = str(marker.get("id", ""))
            if lid:
                by_id[lid] = marker
        return by_id

    def list_pages(self) -> Iterator[list[ListingData]]:
        markers_by_id = self._fetch_markers()
        page = 1
        seen_ids: set[str] = set()
        while page <= MAX_PAGES:
            url = f"{SEARCH_URL}?page={page}" if page > 1 else SEARCH_URL
            log.info("[spotahome] Fetching search page %s", page)
            try:
                resp = self._get(url)
            except Exception as e:
                log.error("[spotahome] Search page %s failed: %s", page, e)
                break
            page_listings: list[ListingData] = []
            for payload in _extract_json_objects(resp.text):
                if payload.get("@type") != "ItemList":
                    continue
                for item in payload.get("itemListElement", []):
                    lid = str(item.get("item", {}).get("identifier", ""))
                    if not lid or lid in seen_ids:
                        continue
                    seen_ids.add(lid)
                    listing = _parse_json_ld_item(item, markers_by_id.get(lid))
                    if listing.source_listing_id:
                        page_listings.append(listing)
            if not page_listings:
                log.info("[spotahome] No more listings at page %s", page)
                break
            yield page_listings
            page += 1

        remaining = [m for lid, m in markers_by_id.items() if lid not in seen_ids]
        if remaining:
            batch: list[ListingData] = []
            for marker in remaining:
                lid = str(marker.get("id", ""))
                coord = marker.get("coord", [None, None])
                kind = str(marker.get("type") or "rooms")
                batch.append(ListingData(
                    source_listing_id=lid,
                    url=f"{BASE_URL}/es/madrid/for-rent:{kind}/{lid}",
                    # Marker fallback uses the same JSON payload: numeric price or null.
                    price_eur=_safe_int(marker.get("minimumPrice")),
                    lat=_safe_float(coord[1]) if coord else None,
                    lon=_safe_float(coord[0]) if coord else None,
                    municipality_raw="Madrid",
                    raw=marker,
                ))
                if len(batch) >= 50:
                    yield batch
                    batch = []
            if batch:
                yield batch

    def fetch_detail(self, partial: ListingData) -> ListingData:
        try:
            resp = self._get(partial.url, retries=4, retry_backoff=3.0)
            full = _parse_detail_page(resp.text, partial)
            from mrf.db.session import SessionLocal
            db = SessionLocal()
            try:
                full.neighborhood_raw, neighborhood_id, district_id = apply_title_neighborhood_fallback(
                    db,
                    title=full.title,
                    neighborhood_raw=full.neighborhood_raw,
                    district_id=None,
                )
                if neighborhood_id:
                    full.raw = {**(full.raw or {}), "matched_neighborhood_id": neighborhood_id, "matched_district_id": district_id}
            finally:
                db.close()
            if not full.description and not full.size_m2 and not full.neighborhood_raw:
                raise ParseError(f"Spotahome detail parse weak for {partial.url}")
            return full
        except Exception as e:
            log.warning("[spotahome] Detail fetch failed for %s: %s", partial.url, e)
            raise


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s — %(message)s")
    scraper = SpotahomeScraper()
    stats = scraper.run()
    log.info("Done: %s", stats)


if __name__ == "__main__":
    main()
