"""
Enalquiler scraper — httpx + selectolax SSR parsing.

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
MAX_PAGES = 250  # ~3750 listings at 15/page


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip() or None


def _parse_price(text: str | None) -> int | None:
    if not text:
        return None
    # Remove dots and euro sign, handle "2.300€" → 2300
    text = text.replace(".", "").replace(",", "")
    # Remove euro symbol (could be unicode \x80 in some encodings)
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _parse_card(node) -> ListingData | None:
    lid = (
        node.attributes.get("list-item")
        or node.attributes.get("data-id")
        or node.attributes.get("id", "").replace("property-", "")
    )
    if not lid:
        return None

    # Link
    link_node = node.css_first("a[href]")
    if not link_node:
        return None
    href = link_node.attributes.get("href", "")
    if not href:
        return None
    if href.startswith("/"):
        href = BASE_URL + href

    # Price — propertyCard__price--value
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
        # Use link text as fallback
        title = _clean(link_node.text(strip=True))

    # Location — "Barrio, Distrito, Madrid"
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

    # Features from card text
    all_text = node.text(strip=True)
    bedrooms = None
    bathrooms = None
    size_m2 = None

    # Use structured feature spans if available
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

    # Fallback: regex on full text with word boundaries
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

    # Images from carousel
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
    # Also try images-path attribute for template URL
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
    tree = HTMLParser(html)

    desc_node = (
        tree.css_first("[class*='description']")
        or tree.css_first("[id*='description']")
        or tree.css_first("[itemprop='description']")
    )
    if desc_node:
        description = _clean(desc_node.text(strip=True))
        if description and len(description) > 2000:
            description = description[:2000]
        partial.description = description

    images = list(partial.images)
    for img in tree.css("img[src]"):
        src = img.attributes.get("src", "")
        if src.startswith("http") and "images.enalquiler.com" in src and src not in images:
            images.append(src)
        if len(images) >= 10:
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
            log.info(f"[enalquiler] Fetching page {page}: {url}")

            try:
                resp = self._get(url)
            except Exception as e:
                log.error(f"[enalquiler] Page {page} failed: {e}")
                break

            tree = HTMLParser(resp.text)
            cards = tree.css("li.propertyCard") or tree.css("[list-item]")

            if not cards:
                log.info(f"[enalquiler] No cards on page {page} — stopping")
                break

            listings = []
            for card in cards:
                try:
                    data = _parse_card(card)
                    if data and data.source_listing_id:
                        listings.append(data)
                except Exception as e:
                    log.debug(f"[enalquiler] Card parse error: {e}")

            if not listings:
                log.info(f"[enalquiler] Empty page {page} — stopping")
                break

            log.info(f"[enalquiler] Page {page}: {len(listings)} listings")
            yield listings

    def fetch_detail(self, partial: ListingData) -> ListingData:
        # Enalquiler cards already have title+price+features
        if partial.price_eur and partial.district_raw:
            return partial
        try:
            resp = self._get(partial.url)
            return _parse_detail(resp.text, partial)
        except Exception as e:
            log.debug(f"[enalquiler] Detail skip {partial.url}: {e}")
            return partial


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    scraper = EnalquilerScraper()
    stats = scraper.run()
    log.info(f"Done: {stats}")


if __name__ == "__main__":
    main()
