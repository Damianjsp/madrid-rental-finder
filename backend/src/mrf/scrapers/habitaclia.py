"""
Habitaclia scraper — httpx + selectolax SSR parsing.

Run: python -m mrf.scrapers.habitaclia

NOTE: Habitaclia uses Imperva bot protection. Direct scraping from a server IP
will return a bot-detection page. The scraper code is correct for the page structure
once you have a valid session.

URL pattern: https://www.habitaclia.com/alquiler-pisos-madrid.htm
             https://www.habitaclia.com/alquiler-pisos-madrid-{N}.htm

To use: set HABITACLIA_COOKIE env var with cookies from a browser session.
"""

import logging
import os
import re
from typing import Iterator

from selectolax.parser import HTMLParser

from mrf.scrapers.base import BaseScraper, ListingData, ScraperError

log = logging.getLogger("mrf.scrapers.habitaclia")

BASE_URL = "https://www.habitaclia.com"
SEARCH_URL_PAGE1 = f"{BASE_URL}/alquiler-pisos-madrid.htm"
SEARCH_URL_PAGN = f"{BASE_URL}/alquiler-pisos-madrid-{{page}}.htm"
MAX_PAGES = 100


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
        or node.attributes.get("data-property-id")
        or node.attributes.get("id")
    )

    link_node = (
        node.css_first("a.list-item-title")
        or node.css_first("h2 a")
        or node.css_first("h3 a")
        or node.css_first("a[href*='/alquiler']")
        or node.css_first("a[href]")
    )
    if not link_node:
        return None

    href = link_node.attributes.get("href", "")
    if not href:
        return None
    if href.startswith("/"):
        href = BASE_URL + href

    if not lid:
        m = re.search(r"-(\d{6,})\.htm", href)
        lid = m.group(1) if m else href.split("-")[-1].replace(".htm", "")

    title = _clean(link_node.text(strip=True))

    price_node = (
        node.css_first("[class*='price']")
        or node.css_first("[class*='precio']")
    )
    price = _parse_price(price_node.text(strip=True) if price_node else None)

    location_node = (
        node.css_first("[class*='location']")
        or node.css_first("[class*='address']")
        or node.css_first("p[class*='item-address']")
    )
    location_text = _clean(location_node.text(strip=True) if location_node else None)
    neighborhood_raw = None
    district_raw = None
    if location_text:
        parts = [p.strip() for p in re.split(r"[,·|]", location_text)]
        parts = [p for p in parts if p and p.lower() not in ("madrid",)]
        if len(parts) >= 2:
            neighborhood_raw = parts[0]
            district_raw = parts[1]
        elif parts:
            neighborhood_raw = parts[0]

    bedrooms = None
    bathrooms = None
    size_m2 = None
    all_text = node.text(strip=True)

    m_bed = re.search(r"(\d+)\s*(?:hab|dorm|room|bed)", all_text, re.I)
    if m_bed:
        bedrooms = int(m_bed.group(1))
    m_bath = re.search(r"(\d+)\s*(?:ba[ñn]|wc|bath)", all_text, re.I)
    if m_bath:
        bathrooms = int(m_bath.group(1))
    m_size = re.search(r"([\d.]+)\s*m[²2]", all_text, re.I)
    if m_size:
        try:
            size_m2 = float(m_size.group(1).replace(",", "."))
        except ValueError:
            pass

    images = []
    for img in node.css("img[src], img[data-src]"):
        src = img.attributes.get("src") or img.attributes.get("data-src", "")
        if src and src.startswith("http") and "placeholder" not in src.lower():
            images.append(src)
        if len(images) >= 5:
            break

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
        or tree.css_first("[id='description']")
        or tree.css_first("div[class*='desc']")
    )
    if desc_node:
        description = _clean(desc_node.text(strip=True))
        if description and len(description) > 2000:
            description = description[:2000]
        partial.description = description

    images = list(partial.images)
    for img in tree.css("img[src]"):
        src = img.attributes.get("src", "")
        if src.startswith("http") and src not in images:
            images.append(src)
        if len(images) >= 10:
            break
    partial.images = images

    return partial


class HabitacliaScraper(BaseScraper):
    portal_key = "habitaclia"
    rate_min = 6.0
    rate_max = 15.0

    def _build_client(self):
        import httpx
        cookie_str = os.environ.get("HABITACLIA_COOKIE", "")
        headers = {
            "User-Agent": self._ua,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8",
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
        cookie_str = os.environ.get("HABITACLIA_COOKIE", "")
        if not cookie_str:
            log.warning(
                "[habitaclia] No HABITACLIA_COOKIE env var. "
                "Habitaclia uses Imperva bot protection. "
                "Set HABITACLIA_COOKIE=<cookie-value> from a browser session."
            )

        for page in range(1, MAX_PAGES + 1):
            url = (
                SEARCH_URL_PAGE1
                if page == 1
                else SEARCH_URL_PAGN.format(page=page)
            )
            log.info(f"[habitaclia] Fetching page {page}: {url}")

            try:
                resp = self._get(url)
            except Exception as e:
                log.error(f"[habitaclia] Page {page} failed: {e}")
                break

            # Detect bot protection page
            if "bot" in resp.text[:3000].lower() or "imperva" in resp.text[:3000].lower():
                log.error(
                    "[habitaclia] Bot protection detected. "
                    "Set HABITACLIA_COOKIE from a browser session and retry."
                )
                raise ScraperError("Imperva bot protection. Set HABITACLIA_COOKIE env var.")

            tree = HTMLParser(resp.text)
            cards = (
                tree.css("article[class*='list-item']")
                or tree.css("li[class*='list-item']")
                or tree.css("[class*='property-card']")
                or tree.css("[data-id]")
                or tree.css("article")
            )

            if not cards:
                log.info(f"[habitaclia] No cards on page {page} — stopping")
                break

            listings = []
            for card in cards:
                try:
                    data = _parse_card(card)
                    if data and data.source_listing_id:
                        listings.append(data)
                except Exception as e:
                    log.debug(f"[habitaclia] Card parse error: {e}")

            if not listings:
                log.info(f"[habitaclia] Empty page {page} — stopping")
                break

            log.info(f"[habitaclia] Page {page}: {len(listings)} listings")
            yield listings

    def fetch_detail(self, partial: ListingData) -> ListingData:
        if partial.description and partial.price_eur:
            return partial
        try:
            resp = self._get(partial.url)
            return _parse_detail(resp.text, partial)
        except Exception as e:
            log.debug(f"[habitaclia] Detail skip {partial.url}: {e}")
            return partial


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    scraper = HabitacliaScraper()
    stats = scraper.run()
    log.info(f"Done: {stats}")


if __name__ == "__main__":
    main()
