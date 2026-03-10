"""
Pisos.com scraper — httpx + selectolax SSR parsing.

Run: python -m mrf.scrapers.pisos

URL: https://www.pisos.com/alquiler/pisos-madrid_capital_zona_urbana/?numpagina=N
Card selector: div.ad-preview (id = listing id)
"""

import logging
import re
from typing import Iterator

from selectolax.parser import HTMLParser

from mrf.scrapers.base import BaseScraper, ListingData

log = logging.getLogger("mrf.scrapers.pisos")

BASE_URL = "https://www.pisos.com"
SEARCH_URL = f"{BASE_URL}/alquiler/pisos-madrid_capital_zona_urbana/"
MAX_PAGES = 100


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip() or None


def _parse_price(text: str | None) -> int | None:
    if not text:
        return None
    # Remove dots used as thousands separators in Spanish
    text = text.replace(".", "")
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _parse_int(text: str | None) -> int | None:
    if not text:
        return None
    m = re.search(r"\d+", text)
    return int(m.group()) if m else None


def _parse_float(text: str | None) -> float | None:
    if not text:
        return None
    t = text.replace(",", ".")
    m = re.search(r"([\d.]+)", t)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _parse_card(node) -> ListingData | None:
    """
    Parse a div.ad-preview card.
    The id attribute IS the listing ID.
    The data-lnk-href attribute has the URL path.
    """
    lid = node.attributes.get("id", "")
    if not lid:
        return None
    # Normalize: pisos uses dots in id like "61749366628.109300" → "61749366628_109300"
    lid_normalized = lid.replace(".", "_")

    href = node.attributes.get("data-lnk-href", "")
    if not href:
        # Try link
        link = node.css_first("a[href*='/alquilar/']") or node.css_first("a[href]")
        if link:
            href = link.attributes.get("href", "")
    if href.startswith("/"):
        href = BASE_URL + href
    if not href:
        return None

    # Price — look for span/div with price text
    price = None
    for el in node.css("[class*='price'], [class*='Price']"):
        t = el.text(strip=True)
        if "€" in t or "/mes" in t.lower():
            p = _parse_price(t)
            if p and 100 <= p <= 100000:
                price = p
                break

    # Also try data-ad-price attribute nearby
    price_attr_node = node.css_first("[data-ad-price]")
    if not price and price_attr_node:
        price = _safe_int(price_attr_node.attributes.get("data-ad-price"))

    # Title — first meaningful link text or h2
    title = None
    title_node = (
        node.css_first("h2.ad-preview__title")
        or node.css_first("a.ad-preview__title")
        or node.css_first("[class*='title']")
        or node.css_first("h2")
        or node.css_first("h3")
    )
    if title_node:
        title = _clean(title_node.text(strip=True))

    # Location — pisos.com shows "Barrio (Distrito X. Madrid Capital)"
    location_node = (
        node.css_first("[class*='subtitle']")
        or node.css_first("[class*='location']")
        or node.css_first("[class*='address']")
        or node.css_first("p.ad-preview__subtitle")
    )
    location_text = _clean(location_node.text(strip=True) if location_node else None)
    neighborhood_raw = None
    district_raw = None
    if location_text:
        # Format: "Portazgo (Distrito Puente de Vallecas. Madrid Capital)"
        m = re.match(r"^(.+?)\s*\(Distrito\s+(.+?)\.", location_text, re.I)
        if m:
            neighborhood_raw = m.group(1).strip()
            district_raw = m.group(2).strip()
        else:
            parts = [p.strip() for p in re.split(r"[.(]", location_text)]
            parts = [p for p in parts if p]
            if len(parts) >= 2:
                neighborhood_raw = parts[0]
                district_raw = parts[1]
            elif parts:
                district_raw = parts[0]

    # Features — bedrooms, bathrooms, size
    bedrooms = None
    bathrooms = None
    size_m2 = None

    all_text = node.text(strip=True)
    m_bed = re.search(r"(\d+)\s*(?:hab(?:itaci[oó]n)?|dorm)", all_text, re.I)
    if m_bed:
        bedrooms = int(m_bed.group(1))
    m_bath = re.search(r"(\d+)\s*(?:ba[ñn](?:o)?|wc)", all_text, re.I)
    if m_bath:
        bathrooms = int(m_bath.group(1))
    m_size = re.search(r"([\d.]+)\s*m[²2]", all_text, re.I)
    if m_size:
        try:
            size_m2 = float(m_size.group(1))
        except ValueError:
            pass

    # Images — pisos uses img inside carousel
    images = []
    for img in node.css("img[src], source[srcset]"):
        src = img.attributes.get("src") or img.attributes.get("srcset", "")
        # srcset may have multiple sizes; take first URL
        if src and "," in src:
            src = src.split(",")[0].strip().split(" ")[0]
        if src and src.startswith("http") and "placeholder" not in src.lower():
            images.append(src)
        if len(images) >= 5:
            break

    # Property type from title
    property_type = "piso"
    if title:
        t_lower = title.lower()
        if "estudio" in t_lower:
            property_type = "estudio"
        elif "habitaci" in t_lower:
            property_type = "habitacion"
        elif "chalet" in t_lower or "villa" in t_lower:
            property_type = "chalet"
        elif "dúplex" in t_lower or "duplex" in t_lower:
            property_type = "duplex"

    return ListingData(
        source_listing_id=lid_normalized,
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
        raw={"id": lid, "location": location_text, "price_text": str(price)},
    )


def _safe_int(val) -> int | None:
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _parse_detail(html: str, partial: ListingData) -> ListingData:
    tree = HTMLParser(html)

    desc_node = (
        tree.css_first("[class*='description']")
        or tree.css_first("[id='description']")
        or tree.css_first("div.ad-detail__description")
        or tree.css_first("section[class*='description']")
    )
    if desc_node:
        description = _clean(desc_node.text(strip=True))
        if description and len(description) > 2000:
            description = description[:2000]
        partial.description = description

    images = list(partial.images)
    for img in tree.css("img[src]"):
        src = img.attributes.get("src", "")
        if src.startswith("http") and src not in images and "placeholder" not in src.lower():
            images.append(src)
        if len(images) >= 10:
            break
    partial.images = images

    return partial


class PisosScraper(BaseScraper):
    portal_key = "pisos"
    rate_min = 6.0
    rate_max = 15.0

    def list_pages(self) -> Iterator[list[ListingData]]:
        for page in range(1, MAX_PAGES + 1):
            url = f"{SEARCH_URL}?numpagina={page}" if page > 1 else SEARCH_URL
            log.info(f"[pisos] Fetching page {page}: {url}")

            try:
                resp = self._get(url)
            except Exception as e:
                log.error(f"[pisos] Page {page} failed: {e}")
                break

            tree = HTMLParser(resp.text)
            cards = tree.css("div.ad-preview")

            if not cards:
                log.info(f"[pisos] No cards on page {page} — stopping")
                break

            listings = []
            for card in cards:
                try:
                    data = _parse_card(card)
                    if data and data.source_listing_id:
                        listings.append(data)
                except Exception as e:
                    log.debug(f"[pisos] Card parse error: {e}")

            if not listings:
                log.info(f"[pisos] No listings parsed on page {page} — stopping")
                break

            log.info(f"[pisos] Page {page}: {len(listings)} listings")
            yield listings

            # Check for next page
            pagination = tree.css_first("[class*='pagination']") or tree.css_first("nav[aria-label]")
            if pagination:
                next_btn = (
                    pagination.css_first("a[rel='next']")
                    or pagination.css_first("[class*='next']")
                    or pagination.css_first("[class*='siguiente']")
                )
                if not next_btn:
                    log.info(f"[pisos] No next page after page {page}")
                    break

    def fetch_detail(self, partial: ListingData) -> ListingData:
        # Pisos.com cards already have price, bedrooms, size — skip detail
        if partial.price_eur and partial.bedrooms:
            return partial
        try:
            resp = self._get(partial.url)
            return _parse_detail(resp.text, partial)
        except Exception as e:
            log.debug(f"[pisos] Detail skip {partial.url}: {e}")
            return partial


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    scraper = PisosScraper()
    stats = scraper.run()
    log.info(f"Done: {stats}")


if __name__ == "__main__":
    main()
