"""
Pisos.com scraper — httpx + selectolax SSR parsing with robust detail extraction.

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
    if any(kw in text.lower() for kw in ("consultar", "llamar", "contacto", "a convenir")):
        return None
    text = text.replace(".", "").replace(",", "")
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


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


def _parse_card(node) -> ListingData | None:
    lid = node.attributes.get("id", "")
    if not lid:
        return None
    lid_normalized = lid.replace(".", "_")

    href = node.attributes.get("data-lnk-href", "")
    if not href:
        link = node.css_first("a[href*='/alquilar/']") or node.css_first("a[href]")
        if link:
            href = link.attributes.get("href", "")
    if href.startswith("/"):
        href = BASE_URL + href
    if not href:
        return None

    # Price
    price = None
    for el in node.css("[class*='price'], [class*='Price']"):
        t = el.text(strip=True)
        if "€" in t or "/mes" in t.lower():
            p = _parse_price(t)
            if p and 100 <= p <= 100000:
                price = p
                break
    if not price:
        price_attr_node = node.css_first("[data-ad-price]")
        if price_attr_node:
            price = _safe_int(price_attr_node.attributes.get("data-ad-price"))

    # Title
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

    # Location — "Barrio (Distrito X. Madrid Capital)"
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

    # Features
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

    # Images
    images = []
    for img in node.css("img[src], source[srcset]"):
        src = img.attributes.get("src") or img.attributes.get("srcset", "")
        if src and "," in src:
            src = src.split(",")[0].strip().split(" ")[0]
        if src and src.startswith("http") and "placeholder" not in src.lower():
            images.append(src)
        if len(images) >= 5:
            break

    # Property type
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
        elif "ático" in t_lower or "atico" in t_lower:
            property_type = "atico"

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


def _parse_detail(html: str, partial: ListingData) -> ListingData:
    """Extract all available fields from a pisos.com detail page."""
    tree = HTMLParser(html)
    lowered = html.lower()

    # ---- Description ----
    if not partial.description:
        desc_node = (
            tree.css_first("div.description")
            or tree.css_first("[class*='description']")
            or tree.css_first("[id='description']")
            or tree.css_first("div.ad-detail__description")
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

    # ---- Features section: size, bedrooms, bathrooms ----
    features_nodes = tree.css("div.features__feature")
    for feat in features_nodes:
        label_node = feat.css_first(".features__label")
        value_node = feat.css_first(".features__value")
        if not label_node:
            continue
        label = _clean(label_node.text(strip=True)) or ""
        value = _clean(value_node.text(strip=True)) if value_node else ""
        label_lc = label.lower()

        if "superficie construida" in label_lc or "superficie útil" in label_lc:
            if partial.size_m2 is None:
                m = re.search(r"([\d.,]+)", value or "")
                if m:
                    partial.size_m2 = _safe_float(m.group(1).replace(",", "."))
        elif "habitaci" in label_lc or "dormitorio" in label_lc:
            if partial.bedrooms is None:
                partial.bedrooms = _safe_int(re.sub(r"[^\d]", "", value or ""))
        elif "baño" in label_lc:
            if partial.bathrooms is None:
                partial.bathrooms = _safe_int(re.sub(r"[^\d]", "", value or ""))

    # ---- Furnished ----
    if partial.furnished is None:
        if re.search(r'\bamueblado\b', lowered):
            partial.furnished = True
        elif re.search(r'sin amueblar|no amueblado', lowered):
            partial.furnished = False

    # ---- Elevator ----
    if partial.elevator is None:
        if re.search(r'ascensor', lowered):
            partial.elevator = True

    # ---- Coordinates from map data ----
    if partial.lat is None or partial.lon is None:
        m = re.search(r'latitude=([-\d.]+).*?longitude=([-\d.]+)', html)
        if m:
            partial.lat = _safe_float(m.group(1))
            partial.lon = _safe_float(m.group(2))

    # ---- Address / location ----
    if not partial.address_raw:
        # Try h1 which often has "Piso en alquiler en Barrio" or breadcrumb
        h1 = tree.css_first("h1")
        if h1:
            partial.address_raw = _clean(h1.text(strip=True))

    # ---- Neighborhood / district from breadcrumb ----
    if not partial.neighborhood_raw or not partial.district_raw:
        for bc in tree.css("nav.breadcrumb a, [class*='breadcrumb'] a"):
            txt = _clean(bc.text(strip=True))
            if txt and txt.lower() not in {"inicio", "pisos.com", "alquiler"}:
                if not partial.district_raw:
                    partial.district_raw = txt
                elif not partial.neighborhood_raw:
                    partial.neighborhood_raw = txt

    # ---- Images ----
    images = list(partial.images)
    for img in tree.css("img[src]"):
        src = img.attributes.get("src", "")
        if src.startswith("http") and src not in images and "placeholder" not in src.lower():
            images.append(src)
        if len(images) >= 12:
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
            log.info("[pisos] Fetching page %s: %s", page, url)
            try:
                resp = self._get(url)
            except Exception as e:
                log.error("[pisos] Page %s failed: %s", page, e)
                break

            tree = HTMLParser(resp.text)
            cards = tree.css("div.ad-preview")
            if not cards:
                log.info("[pisos] No cards on page %s — stopping", page)
                break

            listings = []
            for card in cards:
                try:
                    data = _parse_card(card)
                    if data and data.source_listing_id:
                        listings.append(data)
                except Exception as e:
                    log.debug("[pisos] Card parse error: %s", e)

            if not listings:
                log.info("[pisos] No listings parsed on page %s — stopping", page)
                break

            log.info("[pisos] Page %s: %s listings", page, len(listings))
            yield listings

            pagination = tree.css_first("[class*='pagination']") or tree.css_first("nav[aria-label]")
            if pagination:
                next_btn = (
                    pagination.css_first("a[rel='next']")
                    or pagination.css_first("[class*='next']")
                    or pagination.css_first("[class*='siguiente']")
                )
                if not next_btn:
                    log.info("[pisos] No next page after page %s", page)
                    break

    def fetch_detail(self, partial: ListingData) -> ListingData:
        """Always fetch detail — description, coords, furnished are only on detail page."""
        try:
            resp = self._get(partial.url, retries=3, retry_backoff=2.0)
            return _parse_detail(resp.text, partial)
        except Exception as e:
            log.warning("[pisos] Detail fetch failed for %s: %s", partial.url, e)
            return partial


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    scraper = PisosScraper()
    stats = scraper.run()
    log.info("Done: %s", stats)


if __name__ == "__main__":
    main()
