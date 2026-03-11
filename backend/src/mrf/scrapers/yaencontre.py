"""
Yaencontre scraper — Cloudflare Browser Rendering + selectolax parsing.

Run: python -m mrf.scrapers.yaencontre

Yaencontre uses DataDome bot protection. This scraper uses Cloudflare Browser
Rendering (``/content`` endpoint) to fetch pages through headless Chrome.
If CF credentials are not set, it falls back to direct httpx with session cookies.

URL pattern: https://www.yaencontre.com/alquiler/pisos/madrid?page=N
"""

import logging
import os
import re
from typing import Iterator

from selectolax.parser import HTMLParser

from mrf.scrapers.base import BaseScraper, ListingData, ScraperError
from mrf.scrapers.cf_browser import cf_fetch_html, _is_configured as _cf_available

log = logging.getLogger("mrf.scrapers.yaencontre")

BASE_URL = "https://www.yaencontre.com"
SEARCH_URL = f"{BASE_URL}/alquiler/pisos/madrid"
MAX_PAGES = 50


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip() or None


def _parse_price(text: str | None) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text.replace(".", ""))
    return int(digits) if digits else None


def _parse_card(node) -> ListingData | None:
    lid = (
        node.attributes.get("data-id")
        or node.attributes.get("data-listing-id")
        or node.attributes.get("id")
    )

    link_node = node.css_first("a[href]")
    if not link_node:
        return None
    href = link_node.attributes.get("href", "")
    if not href:
        return None
    if href.startswith("/"):
        href = BASE_URL + href

    if not lid:
        m = re.search(r"/(\d+)(?:[/-]|$)", href)
        lid = m.group(1) if m else href.rstrip("/").split("/")[-1]

    price_node = (
        node.css_first("[class*='price']")
        or node.css_first("[class*='Price']")
        or node.css_first("[class*='precio']")
    )
    price = _parse_price(price_node.text(strip=True) if price_node else None)

    title_node = (
        node.css_first("h2")
        or node.css_first("h3")
        or node.css_first("[class*='title']")
    )
    title = _clean(title_node.text(strip=True) if title_node else None)

    location_node = (
        node.css_first("[class*='location']")
        or node.css_first("[class*='address']")
        or node.css_first("[class*='zona']")
    )
    location_text = _clean(location_node.text(strip=True) if location_node else None)
    neighborhood_raw = None
    district_raw = None
    if location_text:
        parts = [p.strip() for p in location_text.split(",")]
        if len(parts) >= 2:
            neighborhood_raw = parts[-2]
            district_raw = parts[-1]
        else:
            district_raw = parts[0] if parts else None

    features_text = node.text(strip=True)
    bedrooms = None
    bathrooms = None
    size_m2 = None

    m_bed = re.search(r"(\d+)\s*(?:hab|dorm|bed)", features_text, re.I)
    if m_bed:
        bedrooms = int(m_bed.group(1))
    m_bath = re.search(r"(\d+)\s*(?:ba[ñn]|bath|wc)", features_text, re.I)
    if m_bath:
        bathrooms = int(m_bath.group(1))
    m_size = re.search(r"([\d.,]+)\s*m[²2]", features_text, re.I)
    if m_size:
        try:
            size_m2 = float(m_size.group(1).replace(",", "."))
        except ValueError:
            pass

    images = []
    img_node = node.css_first("img[src]") or node.css_first("img[data-src]")
    if img_node:
        img_url = img_node.attributes.get("src") or img_node.attributes.get("data-src", "")
        if img_url and img_url.startswith("http"):
            images.append(img_url)

    return ListingData(
        source_listing_id=str(lid),
        url=href,
        title=title,
        price_eur=price,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        size_m2=size_m2,
        neighborhood_raw=neighborhood_raw,
        district_raw=district_raw,
        municipality_raw="Madrid",
        images=images,
        raw={"title": title, "location": location_text},
    )


def _parse_detail(html: str, partial: ListingData) -> ListingData:
    tree = HTMLParser(html)
    desc_node = (
        tree.css_first("[class*='description']")
        or tree.css_first("article")
    )
    if desc_node:
        description = _clean(desc_node.text(strip=True))
        if description and len(description) > 2000:
            description = description[:2000]
        partial.description = description

    images = list(partial.images)
    for img in tree.css("img[src]"):
        src = img.attributes.get("src", "")
        if src and src.startswith("http") and src not in images:
            images.append(src)
        if len(images) >= 10:
            break
    partial.images = images

    return partial


def _fetch_page_html(url: str, client=None) -> str:
    """Fetch HTML via Cloudflare Browser Rendering, falling back to httpx."""
    if _cf_available():
        html = cf_fetch_html(url)
        if html:
            return html
    # Fallback to direct httpx
    if client is None:
        raise ScraperError(f"No CF credentials and no httpx client for {url}")
    resp = client.get(url, timeout=30, follow_redirects=True)
    if resp.status_code == 403:
        raise ScraperError(
            "403: DataDome protection. Set CF_ACCOUNT_ID + CF_API_TOKEN, "
            "or YAENCONTRE_COOKIE env var."
        )
    resp.raise_for_status()
    return resp.text


class YaencontreScraper(BaseScraper):
    portal_key = "yaencontre"
    rate_min = 6.0
    rate_max = 15.0

    def _build_client(self):
        import httpx
        cookie_str = os.environ.get("YAENCONTRE_COOKIE", "")
        headers = {
            "User-Agent": self._ua,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }
        if cookie_str:
            headers["Cookie"] = cookie_str
        return httpx.Client(
            headers=headers,
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        )

    def list_pages(self) -> Iterator[list[ListingData]]:
        use_cf = _cf_available()
        if not use_cf:
            cookie_str = os.environ.get("YAENCONTRE_COOKIE", "")
            if not cookie_str:
                log.warning(
                    "[yaencontre] No CF credentials and no YAENCONTRE_COOKIE. "
                    "Set CF_ACCOUNT_ID + CF_API_TOKEN for Cloudflare Browser Rendering, "
                    "or YAENCONTRE_COOKIE from a browser session."
                )
        else:
            log.info("[yaencontre] Using Cloudflare Browser Rendering for page fetches")

        for page in range(1, MAX_PAGES + 1):
            url = f"{SEARCH_URL}?page={page}" if page > 1 else SEARCH_URL
            log.info(f"[yaencontre] Fetching page {page}: {url}")

            try:
                html = _fetch_page_html(url, client=self._client)
            except Exception as e:
                log.error(f"[yaencontre] Page {page} failed: {e}")
                break

            tree = HTMLParser(html)
            cards = (
                tree.css("[class*='listing-card']")
                or tree.css("[class*='property-card']")
                or tree.css("[data-id]")
                or tree.css("article")
            )

            if not cards:
                log.info(f"[yaencontre] No cards on page {page} — stopping")
                break

            listings = []
            for card in cards:
                try:
                    data = _parse_card(card)
                    if data and data.source_listing_id:
                        listings.append(data)
                except Exception as e:
                    log.debug(f"[yaencontre] Card parse error: {e}")

            if not listings:
                log.info(f"[yaencontre] Empty page {page} — stopping")
                break

            log.info(f"[yaencontre] Page {page}: {len(listings)} listings")
            yield listings

    def fetch_detail(self, partial: ListingData) -> ListingData:
        if partial.description and partial.price_eur:
            return partial
        try:
            html = _fetch_page_html(partial.url, client=self._client)
            return _parse_detail(html, partial)
        except Exception as e:
            log.debug(f"[yaencontre] Detail skip {partial.url}: {e}")
            return partial


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    scraper = YaencontreScraper()
    stats = scraper.run()
    log.info(f"Done: {stats}")


if __name__ == "__main__":
    main()
