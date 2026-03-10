"""
Spotahome scraper — uses internal JSON API + JSON-LD from search pages.

Run: python -m mrf.scrapers.spotahome

Strategy:
1. GET /api/fe/marketplace/markers/madrid → all listing IDs with coords & price range
2. GET /es/s/madrid?page=N → JSON-LD ItemList with title, address, URL, images per page
3. Merge markers data into listings (price from marker, details from JSON-LD)
4. Optionally fetch detail page for richer data (bedrooms, bathrooms, etc.)
"""

import json
import logging
import re
import time
from typing import Iterator

import httpx
from selectolax.parser import HTMLParser

from mrf.scrapers.base import BaseScraper, ListingData, ParseError, RateLimitError

log = logging.getLogger("mrf.scrapers.spotahome")

BASE_URL = "https://www.spotahome.com"
MARKERS_URL = f"{BASE_URL}/api/fe/marketplace/markers/madrid"
SEARCH_URL = f"{BASE_URL}/es/s/madrid"
PAGE_SIZE = 15  # JSON-LD returns 15 per page


def _safe_int(val) -> int | None:
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _safe_float(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _parse_json_ld_item(item: dict, marker: dict | None) -> ListingData:
    """Parse a JSON-LD LodgingBusiness item from the search page."""
    inner = item.get("item", item)
    lid = str(inner.get("identifier", ""))

    # URL
    url_path = inner.get("url", "")
    if url_path.startswith("/"):
        url = BASE_URL + url_path
    else:
        url = url_path or f"{BASE_URL}/es/madrid/for-rent:rooms/{lid}"

    # Title
    title = inner.get("name", "")

    # Address
    address = inner.get("address", {}) or {}
    address_raw = address.get("streetAddress")
    neighborhood_raw = address.get("addressLocality")
    district_raw = None

    # Price from marker (markers have price range)
    price_eur = None
    lat = None
    lon = None
    if marker:
        min_price = _safe_int(marker.get("minimumPrice"))
        max_price = _safe_int(marker.get("maximumPrice"))
        if min_price is not None:
            price_eur = min_price
        coord = marker.get("coord", [None, None])
        if coord and len(coord) == 2:
            lon = _safe_float(coord[0])
            lat = _safe_float(coord[1])

    # Rooms
    bedrooms = _safe_int(inner.get("numberOfRooms"))
    bathrooms = _safe_int(inner.get("numberOfBathroomsTotal"))

    # Images
    images = []
    img = inner.get("image")
    if isinstance(img, str) and img.startswith("http"):
        images = [img]
    elif isinstance(img, list):
        images = [i for i in img if isinstance(i, str) and i.startswith("http")][:10]

    # Property type from title
    title_lower = title.lower() if title else ""
    if "estudio" in title_lower:
        property_type = "estudio"
    elif "habitaci" in title_lower:
        property_type = "habitacion"
    elif "piso" in title_lower or "apartamento" in title_lower:
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
        raw={
            "identifier": lid,
            "marker": marker,
            "address": address,
        },
    )


def _parse_detail_page(html: str, partial: ListingData) -> ListingData:
    """Extract richer data from a Spotahome detail page."""
    # Try JSON-LD on detail page
    for m in re.finditer(
        r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL
    ):
        try:
            d = json.loads(m.group(1))
            if isinstance(d, dict) and d.get("@type") in (
                "LodgingBusiness",
                "Apartment",
                "Product",
            ):
                if not partial.bedrooms:
                    partial.bedrooms = _safe_int(d.get("numberOfRooms"))
                if not partial.bathrooms:
                    partial.bathrooms = _safe_int(d.get("numberOfBathroomsTotal"))
                # Price from offers
                offers = d.get("offers", {}) or {}
                if isinstance(offers, dict) and not partial.price_eur:
                    partial.price_eur = _safe_int(
                        offers.get("price") or offers.get("lowPrice")
                    )
        except Exception:
            pass

    # Extract size from page text
    tree = HTMLParser(html)
    text = tree.body.text(strip=True) if tree.body else ""
    if not partial.size_m2:
        m = re.search(r"([\d.]+)\s*m[²2]", text, re.I)
        if m:
            try:
                partial.size_m2 = float(m.group(1))
            except ValueError:
                pass

    # More images
    images = list(partial.images)
    for img in tree.css("img[src]"):
        src = img.attributes.get("src", "")
        if (
            src.startswith("http")
            and "spotahome" in src
            and src not in images
        ):
            images.append(src)
        if len(images) >= 10:
            break
    partial.images = images

    return partial


class SpotahomeScraper(BaseScraper):
    portal_key = "spotahome"
    rate_min = 1.0
    rate_max = 5.0

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
        """Fetch all listing markers (ID → {price, coords}) in one request."""
        log.info("[spotahome] Fetching all markers...")
        resp = self._client.get(  # type: ignore
            MARKERS_URL,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        markers = resp.json().get("data", [])
        log.info(f"[spotahome] Got {len(markers)} markers")
        # Map rentableId → marker data; also track unique adIds
        by_id: dict[str, dict] = {}
        for m in markers:
            lid = str(m.get("id", ""))
            if lid:
                by_id[lid] = m
        return by_id

    def list_pages(self) -> Iterator[list[ListingData]]:
        # Step 1: bulk-fetch all markers (one request, fast)
        import time

        time.sleep(2)
        markers_by_id = self._fetch_markers()

        # Step 2: paginate search pages for JSON-LD details
        page = 1
        seen_ids: set[str] = set()

        while True:
            url = f"{SEARCH_URL}?page={page}" if page > 1 else SEARCH_URL
            log.info(f"[spotahome] Fetching search page {page}")

            try:
                resp = self._get(url)
            except Exception as e:
                log.error(f"[spotahome] Search page {page} failed: {e}")
                break

            # Extract JSON-LD ItemList
            page_listings: list[ListingData] = []
            found = False
            for m in re.finditer(
                r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
                resp.text,
                re.DOTALL,
            ):
                try:
                    d = json.loads(m.group(1))
                    if isinstance(d, dict) and d.get("@type") == "ItemList":
                        items = d.get("itemListElement", [])
                        found = True
                        for item in items:
                            lid = str(item.get("item", {}).get("identifier", ""))
                            if lid and lid not in seen_ids:
                                seen_ids.add(lid)
                                marker = markers_by_id.get(lid)
                                listing = _parse_json_ld_item(item, marker)
                                if listing.source_listing_id:
                                    page_listings.append(listing)
                except Exception:
                    pass

            if not found or not page_listings:
                log.info(f"[spotahome] No more listings at page {page}")
                break

            log.info(f"[spotahome] Page {page}: {len(page_listings)} listings")
            yield page_listings
            page += 1

        # Step 3: emit any remaining markers not seen in search pages
        # (markers with IDs not in any JSON-LD page — use sparse data)
        remaining = [
            m for lid, m in markers_by_id.items() if lid not in seen_ids
        ]
        if remaining:
            log.info(
                f"[spotahome] Emitting {len(remaining)} listings from markers only"
            )
            batch: list[ListingData] = []
            for m in remaining:
                lid = str(m.get("id", ""))
                min_price = _safe_int(m.get("minimumPrice"))
                coord = m.get("coord", [None, None])
                listing = ListingData(
                    source_listing_id=lid,
                    url=f"{BASE_URL}/es/madrid/for-rent:rooms/{lid}",
                    price_eur=min_price,
                    lat=_safe_float(coord[1]) if coord else None,
                    lon=_safe_float(coord[0]) if coord else None,
                    municipality_raw="Madrid",
                    raw=m,
                )
                batch.append(listing)
                if len(batch) >= 50:
                    yield batch
                    batch = []
            if batch:
                yield batch

    def fetch_detail(self, partial: ListingData) -> ListingData:
        """Fetch detail page only if we're missing key fields."""
        if partial.title and partial.price_eur and partial.bedrooms:
            return partial
        try:
            resp = self._get(partial.url)
            return _parse_detail_page(resp.text, partial)
        except Exception as e:
            log.debug(f"[spotahome] Detail skip {partial.url}: {e}")
            return partial


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    scraper = SpotahomeScraper()
    stats = scraper.run()
    log.info(f"Done: {stats}")


if __name__ == "__main__":
    main()
