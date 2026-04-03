"""
Tranquiler scraper — direct API pagination for Agencia Negociadora del Alquiler listings.

Run: python -m mrf.scrapers.tranquiler
"""

import copy
import logging
import random
import re
import time
from typing import Iterator

import httpx

from mrf.scrapers.base import BaseScraper, ListingData, RateLimitError, ScraperError

log = logging.getLogger("mrf.scrapers.tranquiler")

API_URL = "https://api.tranquiler.com/api/Viviendas"
BASE_WEB_URL = "https://www.agencianegociadoradelalquiler.com/buscador-pisos-madrid/"
PHOTO_BASE_URL = "https://portales.tranquiler.com"
PAGE_SIZE = 50
BOILERPLATE_START = "La Agencia Negociadora del Alquiler no cobra"


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip() or None


def _safe_int(val) -> int | None:
    try:
        if val is None or val == "":
            return None
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _safe_float(val) -> float | None:
    try:
        if val is None or val == "":
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


def _strip_boilerplate(description: str | None) -> str | None:
    text = _clean(description)
    if not text:
        return None
    idx = text.find(BOILERPLATE_START)
    if idx != -1:
        text = text[:idx].strip()
    return text or None


def _property_type(subtipo: str | None) -> str | None:
    subtipo_clean = _clean(subtipo)
    if not subtipo_clean:
        return None
    mapping = {
        "Piso": "piso",
        "Estudio": "estudio",
        "Chalet": "chalet",
    }
    return mapping.get(subtipo_clean, subtipo_clean.lower())


def _infer_furnished(description: str | None) -> bool | None:
    if not description:
        return None
    lowered = description.lower()
    if "vacía de muebles" in lowered or "vacia de muebles" in lowered or "sin muebles" in lowered:
        return False
    if "amueblad" in lowered:
        return True
    return None


def _infer_elevator(description: str | None) -> bool | None:
    if not description:
        return None
    lowered = description.lower()
    if "sin ascensor" in lowered:
        return False
    if "ascensor" in lowered:
        return True
    return None


def _infer_parking(description: str | None) -> bool | None:
    if not description:
        return None
    lowered = description.lower()
    return True if ("garaje" in lowered or "parking" in lowered) else None


def _build_address(item: dict) -> str | None:
    tipo_via = _clean((item.get("tipoVia") or {}).get("tipo"))
    via = _clean(item.get("via"))
    numero = _clean(item.get("numero"))
    parts = [part for part in [tipo_via, via] if part]
    if not parts:
        return None
    address = " ".join(parts)
    if numero:
        address = f"{address} Nº {numero}"
    return address


def _titlecase_municipality(name: str | None) -> str | None:
    cleaned = _clean(name)
    return cleaned.title() if cleaned else None


def _sanitize_raw(item: dict) -> dict:
    raw = copy.deepcopy(item)
    raw.pop("observaciones", None)
    return raw


def _parse_listing(item: dict) -> ListingData:
    listing_id = str(item["id"])
    vivienda_uid = item.get("viviendaUIDId")
    foto = _clean(item.get("foto"))
    subtipologia = item.get("subTipologia") or {}
    tipo_via = item.get("tipoVia") or {}
    poblacion = item.get("poblacion") or {}
    barrio = item.get("barrio") or {}
    barrio_distrito = barrio.get("distrito") or {}
    distritos = poblacion.get("distrito") or []

    subtype = _clean(subtipologia.get("subTipo"))
    street_type = _clean(tipo_via.get("tipo"))
    street_name = _clean(item.get("via"))
    title_bits = [subtype, "en", street_type, street_name]
    title = " ".join(bit for bit in title_bits if bit)

    description = _strip_boilerplate(item.get("descripcion"))
    # Tranquiler prices come from the JSON API field `precioAnuncio` as a numeric value
    # (or null/empty), not from a free-form price text node, so keyword guards are not needed.
    price_eur = _safe_int(item.get("precioAnuncio"))
    deposit_months = _safe_int(item.get("nmesesFianza")) or 0
    district_raw = None
    if distritos:
        district_raw = _clean((distritos[0] or {}).get("nombre"))
    if not district_raw:
        district_raw = _clean(barrio_distrito.get("nombre"))

    neighborhood_raw = _clean(barrio.get("nombre"))
    if not neighborhood_raw and distritos:
        neighborhood_raw = _clean((distritos[0] or {}).get("nombre"))

    images = []
    if vivienda_uid and foto:
        images = [f"{PHOTO_BASE_URL}/{vivienda_uid}/{foto}"]

    return ListingData(
        source_listing_id=listing_id,
        url=f"{BASE_WEB_URL}?uid={vivienda_uid}",
        title=title or None,
        description=description,
        price_eur=price_eur,
        deposit_eur=price_eur * deposit_months if price_eur is not None else None,
        bedrooms=_safe_int(item.get("nHabitaciones")),
        bathrooms=_safe_int(item.get("nBanos")),
        size_m2=_safe_float(item.get("superficie")),
        property_type=_property_type(subtype),
        furnished=_infer_furnished(description),
        elevator=_infer_elevator(description),
        parking=_infer_parking(description),
        address_raw=_build_address(item),
        neighborhood_raw=neighborhood_raw,
        district_raw=district_raw,
        municipality_raw=_titlecase_municipality(poblacion.get("nombre")),
        lat=None,
        lon=None,
        images=images,
        raw=_sanitize_raw(item),
    )


class TranquilerScraper(BaseScraper):
    portal_key = "tranquiler"
    rate_min = 1.0
    rate_max = 2.0

    def _build_client(self) -> httpx.Client:
        return httpx.Client(
            headers={
                "User-Agent": self._ua,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": "https://www.agencianegociadoradelalquiler.com",
                "Referer": BASE_WEB_URL,
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            http2=False,
        )

    def _post(self, url: str, data: dict, retries: int = 3, retry_backoff: float = 2.0, **kwargs) -> httpx.Response:
        assert self._client is not None
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            delay = random.uniform(self.rate_min, self.rate_max)
            log.debug("Sleeping %.1fs before POST %s (attempt %s/%s)", delay, url, attempt, retries)
            time.sleep(delay)
            try:
                resp = self._client.post(url, data=data, **kwargs)
                if resp.status_code == 429:
                    wait_s = min(60, retry_backoff * attempt * 5)
                    log.warning("429 from %s — backing off %.1fs (attempt %s/%s)", url, wait_s, attempt, retries)
                    time.sleep(wait_s)
                    raise RateLimitError(f"429 from {url}")
                if resp.status_code == 403:
                    log.error("403 from %s — stopping scraper", url)
                    raise ScraperError(f"403 Forbidden: {url}")
                resp.raise_for_status()
                return resp
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError, RateLimitError) as e:
                last_error = e
                if attempt >= retries or isinstance(e, ScraperError) and not isinstance(e, RateLimitError):
                    break
                sleep_s = retry_backoff * attempt
                log.warning("POST failed for %s (attempt %s/%s): %s — retrying in %.1fs", url, attempt, retries, e, sleep_s)
                time.sleep(sleep_s)
        if last_error:
            raise last_error
        raise ScraperError(f"POST failed for {url}")

    def list_pages(self) -> Iterator[list[ListingData]]:
        start = 0
        total = None

        while total is None or start < total:
            payload = {
                "draw": "1",
                "start": str(start),
                "length": str(PAGE_SIZE),
                "transaccion": "false",
                "preciomax": "",
                "preciomin": "",
                "habmin": "",
                "tipologia": "",
                "provincia": "",
                "poblacion": "",
                "distrito": "",
                "barrio": "",
            }
            log.info("[tranquiler] Fetching page start=%s length=%s", start, PAGE_SIZE)
            resp = self._post(API_URL, data=payload, retries=3)
            body = resp.json()
            total = _safe_int(body.get("recordsTotal")) or 0
            items = body.get("data") or []
            if not items:
                log.info("[tranquiler] No listings at start=%s — stopping", start)
                break

            listings: list[ListingData] = []
            for item in items:
                if item.get("venta") is True:
                    continue
                try:
                    listings.append(_parse_listing(item))
                except Exception as e:
                    log.debug("[tranquiler] Listing parse error for id=%s: %s", item.get("id"), e)

            if not listings:
                log.info("[tranquiler] No rental listings parsed at start=%s — stopping", start)
                break

            yield listings
            start += PAGE_SIZE

    def fetch_detail(self, partial: ListingData) -> ListingData:
        return partial


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    scraper = TranquilerScraper()
    stats = scraper.run()
    log.info("Done: %s", stats)


if __name__ == "__main__":
    main()
