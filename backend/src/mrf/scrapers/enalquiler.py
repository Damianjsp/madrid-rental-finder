"""
Enalquiler scraper — httpx + selectolax SSR parsing with robust detail extraction.

Run: python -m mrf.scrapers.enalquiler

URL pattern:
  Page 1: https://www.enalquiler.com/alquiler-pisos-madrid-30-2-0-27745.html
  Page N: https://www.enalquiler.com/alquiler-pisos-madrid_30_27745_2/{N}/

Card selector: li.propertyCard[list-item="<id>"]
"""

import logging
import re
from typing import Iterator

from selectolax.parser import HTMLParser

from mrf.scrapers.base import BaseScraper, ListingData

log = logging.getLogger("mrf.scrapers.enalquiler")

BASE_URL = "https://www.enalquiler.com"
SEARCH_URL_PAGE1 = f"{BASE_URL}/alquiler-pisos-madrid-30-2-0-27745.html"
SEARCH_URL_PAGN = f"{BASE_URL}/alquiler-pisos-madrid_30_27745_2/{{page}}/"
MAX_PAGES = 250


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip() or None


def _parse_price(text: str | None) -> int | None:
    if not text:
        return None
    normalized = text.strip().lower()
    # This guard only evaluates the dedicated price text extracted by the CSS selector,
    # not the full listing HTML, so contact details elsewhere in the card will not
    # trigger a false positive here. Match whole-text call-for-price labels only.
    if normalized in {"consultar", "llamar", "a consultar", "contacto", "a convenir"}:
        return None
    text = text.replace(".", "").replace(",", "")
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _safe_float(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _parse_card(node) -> ListingData | None:
    lid = (
        node.attributes.get("list-item")
        or node.attributes.get("data-id")
        or node.attributes.get("id", "").replace("property-", "")
    )
    if not lid:
        return None

    link_node = node.css_first("a[href]")
    if not link_node:
        return None
    href = link_node.attributes.get("href", "")
    if not href:
        return None
    if href.startswith("/"):
        href = BASE_URL + href

    # Price
    price_node = (
        node.css_first("[class*='price--value']")
        or node.css_first("[class*='price']")
    )
    price = _parse_price(price_node.text(strip=True) if price_node else None)

    # Title
    title_node = (
        node.css_first("[class*='title']")
        or node.css_first("[class*='description']")
        or node.css_first("h2")
        or node.css_first("h3")
    )
    title = _clean(title_node.text(strip=True) if title_node else None)
    if not title:
        title = _clean(link_node.text(strip=True))

    # Location
    location_node = (
        node.css_first("[class*='location']")
        or node.css_first("[class*='address']")
        or node.css_first("[class*='zona']")
        or node.css_first("[itemprop='address']")
    )
    location_text = _clean(location_node.text(strip=True) if location_node else None)
    neighborhood_raw = None
    district_raw = None
    if location_text:
        parts = [p.strip() for p in location_text.split(",")]
        parts = [p for p in parts if p]
        if len(parts) >= 3:
            neighborhood_raw = parts[0]
            district_raw = parts[1]
        elif len(parts) == 2:
            neighborhood_raw = parts[0]
            district_raw = parts[1]
        elif parts:
            district_raw = parts[0]

    # Features
    all_text = node.text(strip=True)
    bedrooms = None
    bathrooms = None
    size_m2 = None

    for el in node.css("span, li, strong"):
        t = el.text(strip=True)
        if not bedrooms:
            m = re.match(r"^(\d+)\s*(?:Hab|hab|dorm)", t)
            if m:
                bedrooms = int(m.group(1))
        if not bathrooms:
            m = re.match(r"^(\d+)\s*Ba[ñn]", t)
            if m:
                bathrooms = int(m.group(1))
        if not size_m2:
            m = re.match(r"^(\d+)\s*m2$", t, re.I)
            if m:
                try:
                    size_m2 = float(m.group(1))
                except ValueError:
                    pass

    if not bedrooms:
        m_bed = re.search(r"(\d+)\s+(?:hab(?:itaci[oó]n)?|dorm|Hab)\b", all_text, re.I)
        if m_bed:
            bedrooms = int(m_bed.group(1))
    if not bathrooms:
        m_bath = re.search(r"(\d+)\s+Ba[ñn]", all_text)
        if m_bath:
            bathrooms = int(m_bath.group(1))
    m_size = re.search(r"(\d+)\s*m2\b", all_text, re.I)
    if m_size:
        try:
            size_m2 = float(m_size.group(1))
        except ValueError:
            pass

    # Property type
    property_type = "piso"
    all_lower = all_text.lower()
    if "estudio" in all_lower:
        property_type = "estudio"
    elif "habitaci" in all_lower and "hab" in all_lower[:50]:
        property_type = "habitacion"
    elif "chalet" in all_lower:
        property_type = "chalet"
    elif "ático" in all_lower or "atico" in all_lower:
        property_type = "atico"

    # Images
    images = []
    carousel = node.css_first("[class*='carousel']")
    if carousel:
        for img in carousel.css("img[src], source[srcset]"):
            src = img.attributes.get("src") or img.attributes.get("srcset", "")
            if src and "," in src:
                src = src.split(",")[0].strip().split(" ")[0]
            if src and src.startswith("http") and "placeholder" not in src.lower():
                images.append(src)
            if len(images) >= 5:
                break
    images_path = node.attributes.get("images-path")
    if not images and images_path:
        img_url = images_path.replace("{width}", "zm")
        images = [img_url]

    return ListingData(
        source_listing_id=str(lid),
        url=href,
        title=title,
        price_eur=price,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        size_m2=size_m2,
        property_type=property_type,
        neighborhood_raw=neighborhood_raw,
        district_raw=district_raw,
        municipality_raw="Madrid",
        images=images,
        raw={"id": lid, "location": location_text},
    )


def _parse_detail(html: str, partial: ListingData) -> ListingData:
    """Extract rich data from enalquiler detail page."""
    tree = HTMLParser(html)
    lowered = html.lower()

    # ---- Description ----
    if not partial.description:
        desc_node = (
            tree.css_first("[class*='description']")
            or tree.css_first("[id*='description']")
            or tree.css_first("[itemprop='description']")
        )
        if desc_node:
            partial.description = _clean(desc_node.text(strip=True))
        if not partial.description:
            meta = re.search(
                r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html, re.I
            )
            if meta:
                partial.description = _clean(meta.group(1))
    if partial.description and len(partial.description) > 2000:
        partial.description = partial.description[:2000]

    # ---- Address from <address> block ----
    address_node = tree.css_first("address")
    if address_node:
        for div in address_node.css("div"):
            txt = _clean(div.text(strip=True))
            if not txt:
                continue
            if "barrio:" in txt.lower():
                val = re.sub(r"^barrio:\s*", "", txt, flags=re.I).strip()
                if val:
                    partial.neighborhood_raw = partial.neighborhood_raw or val
            elif "distrito" in txt.lower() or "zona" in txt.lower():
                val = re.sub(r"^distrito/zona:\s*|^distrito:\s*|^zona:\s*", "", txt, flags=re.I).strip()
                if val:
                    partial.district_raw = partial.district_raw or val
            elif "población:" in txt.lower():
                val = re.sub(r"^poblaci[oó]n:\s*", "", txt, flags=re.I).strip()
                if val and not partial.address_raw:
                    partial.address_raw = val

    # ---- Coordinates from map ----
    if partial.lat is None or partial.lon is None:
        m = re.search(r'map-latitude="([-\d.]+)"', html)
        if m:
            partial.lat = _safe_float(m.group(1))
        m = re.search(r'map-longitude=\s*"([-\d.]+)"', html)
        if m:
            partial.lon = _safe_float(m.group(1))

    # ---- Furnished ----
    if partial.furnished is None:
        if re.search(r'\bamueblado\b', lowered):
            partial.furnished = True
        elif re.search(r'sin amueblar|no amueblado', lowered):
            partial.furnished = False
        elif re.search(r'\bmuebles\b.*\binclu', lowered):
            partial.furnished = True

    # ---- Size from detail page ----
    if partial.size_m2 is None:
        m = re.search(r"(\d+)\s*m(?:2|²)", html, re.I)
        if m:
            partial.size_m2 = _safe_float(m.group(1))

    # ---- Elevator ----
    if partial.elevator is None:
        if re.search(r'\bascensor\b', lowered):
            partial.elevator = True

    # ---- Images ----
    images = list(partial.images)
    for img in tree.css("img[src]"):
        src = img.attributes.get("src", "")
        if src.startswith("http") and "enalquiler" in src and src not in images:
            images.append(src)
        if len(images) >= 12:
            break
    partial.images = images

    return partial


class EnalquilerScraper(BaseScraper):
    portal_key = "enalquiler"
    rate_min = 4.0
    rate_max = 10.0

    def list_pages(self) -> Iterator[list[ListingData]]:
        for page in range(1, MAX_PAGES + 1):
            url = (
                SEARCH_URL_PAGE1
                if page == 1
                else SEARCH_URL_PAGN.format(page=page)
            )
            log.info("[enalquiler] Fetching page %s: %s", page, url)
            try:
                resp = self._get(url)
            except Exception as e:
                log.error("[enalquiler] Page %s failed: %s", page, e)
                break

            tree = HTMLParser(resp.text)
            cards = tree.css("li.propertyCard") or tree.css("[list-item]")
            if not cards:
                log.info("[enalquiler] No cards on page %s — stopping", page)
                break

            listings = []
            for card in cards:
                try:
                    data = _parse_card(card)
                    if data and data.source_listing_id:
                        listings.append(data)
                except Exception as e:
                    log.debug("[enalquiler] Card parse error: %s", e)

            if not listings:
                log.info("[enalquiler] Empty page %s — stopping", page)
                break

            log.info("[enalquiler] Page %s: %s listings", page, len(listings))
            yield listings

    def fetch_detail(self, partial: ListingData) -> ListingData:
        """Always fetch detail — address, coords, description are only on detail."""
        try:
            resp = self._get(partial.url, retries=3, retry_backoff=2.0)
            return _parse_detail(resp.text, partial)
        except Exception as e:
            log.warning("[enalquiler] Detail fetch failed for %s: %s", partial.url, e)
            return partial


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    scraper = EnalquilerScraper()
    stats = scraper.run()
    log.info("Done: %s", stats)


if __name__ == "__main__":
    main()
