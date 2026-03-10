"""Base scraper class with rate limiting, session management, and run tracking."""

import logging
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Iterator, Optional

import httpx
from sqlalchemy.orm import Session

from mrf.db.models import Listing, ListingImage, Portal, ScraperRun
from mrf.db.session import get_db

log = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]


class ScraperError(Exception):
    pass


class RateLimitError(ScraperError):
    pass


class ParseError(ScraperError):
    pass


class ListingData:
    """Normalized listing extracted by a scraper."""

    __slots__ = (
        "source_listing_id", "url", "title", "description",
        "price_eur", "deposit_eur", "expenses_included",
        "bedrooms", "bathrooms", "size_m2",
        "property_type", "furnished", "elevator", "parking",
        "address_raw", "neighborhood_raw", "district_raw", "municipality_raw",
        "lat", "lon", "images", "raw",
    )

    def __init__(self, source_listing_id: str, url: str, **kwargs):
        self.source_listing_id = source_listing_id
        self.url = url
        self.title = kwargs.get("title")
        self.description = kwargs.get("description")
        self.price_eur = kwargs.get("price_eur")
        self.deposit_eur = kwargs.get("deposit_eur")
        self.expenses_included = kwargs.get("expenses_included")
        self.bedrooms = kwargs.get("bedrooms")
        self.bathrooms = kwargs.get("bathrooms")
        self.size_m2 = kwargs.get("size_m2")
        self.property_type = kwargs.get("property_type")
        self.furnished = kwargs.get("furnished")
        self.elevator = kwargs.get("elevator")
        self.parking = kwargs.get("parking")
        self.address_raw = kwargs.get("address_raw")
        self.neighborhood_raw = kwargs.get("neighborhood_raw")
        self.district_raw = kwargs.get("district_raw")
        self.municipality_raw = kwargs.get("municipality_raw", "Madrid")
        self.lat = kwargs.get("lat")
        self.lon = kwargs.get("lon")
        self.images: list[str] = kwargs.get("images", [])
        self.raw: dict = kwargs.get("raw", {})


class BaseScraper(ABC):
    """Base scraper with rate limiting, retry logic, and DB upsert."""

    portal_key: str
    rate_min: float = 5.0
    rate_max: float = 15.0

    def __init__(self):
        self._ua = random.choice(USER_AGENTS)
        self._client: Optional[httpx.Client] = None
        self._portal_id: Optional[int] = None
        self._run_id: Optional[int] = None

    # ---- helpers ----

    @staticmethod
    def _dedupe_images(images: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for img in images:
            if img and img not in seen:
                seen.add(img)
                out.append(img)
        return out

    # ---- HTTP client ----

    def _build_client(self) -> httpx.Client:
        return httpx.Client(
            headers={
                "User-Agent": self._ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            http2=False,
        )

    def _get(self, url: str, **kwargs) -> httpx.Response:
        delay = random.uniform(self.rate_min, self.rate_max)
        log.debug("Sleeping %.1fs before %s", delay, url)
        time.sleep(delay)
        assert self._client is not None
        resp = self._client.get(url, **kwargs)
        if resp.status_code == 429:
            log.warning("429 from %s — backing off 60s", url)
            time.sleep(60)
            raise RateLimitError(f"429 from {url}")
        if resp.status_code == 403:
            log.error("403 from %s — stopping scraper", url)
            raise ScraperError(f"403 Forbidden: {url}")
        resp.raise_for_status()
        return resp

    # ---- Portal / Run management ----

    def _get_portal_id(self, db: Session) -> int:
        portal = db.query(Portal).filter_by(key=self.portal_key).first()
        if not portal:
            raise ScraperError(f"Portal '{self.portal_key}' not found in DB. Run seed first.")
        return portal.id

    def _start_run(self, db: Session) -> int:
        run = ScraperRun(portal_id=self._portal_id, status="running")
        db.add(run)
        db.flush()
        db.refresh(run)
        log.info("[%s] Scraper run #%s started", self.portal_key, run.id)
        return run.id

    def _finish_run(self, db: Session, run_id: int, stats: dict, error: Optional[str] = None):
        run = db.get(ScraperRun, run_id)
        if not run:
            return
        run.finished_at = datetime.now(timezone.utc)
        run.status = "error" if error else "success"
        run.listings_seen = stats.get("seen", 0)
        run.listings_new = stats.get("new", 0)
        run.listings_updated = stats.get("updated", 0)
        run.error_message = error
        db.flush()
        log.info(
            "[%s] Run #%s finished: seen=%s new=%s updated=%s",
            self.portal_key, run_id,
            run.listings_seen, run.listings_new, run.listings_updated,
        )

    # ---- Upsert ----

    _UPDATE_FIELDS = (
        "url", "title", "description", "price_eur", "deposit_eur",
        "expenses_included", "bedrooms", "bathrooms", "size_m2",
        "property_type", "furnished", "elevator", "parking",
        "address_raw", "neighborhood_raw", "district_raw",
        "municipality_raw", "lat", "lon",
    )

    def _upsert_listing(self, db: Session, data: ListingData) -> tuple[bool, bool]:
        """Upsert by (portal_id, source_listing_id). Returns (is_new, was_updated)."""
        existing: Optional[Listing] = (
            db.query(Listing)
            .filter_by(portal_id=self._portal_id, source_listing_id=data.source_listing_id)
            .first()
        )
        now = datetime.now(timezone.utc)
        images = self._dedupe_images(data.images)

        if existing is None:
            listing = Listing(
                portal_id=self._portal_id,
                source_listing_id=data.source_listing_id,
                url=data.url, title=data.title, description=data.description,
                price_eur=data.price_eur, deposit_eur=data.deposit_eur,
                expenses_included=data.expenses_included,
                bedrooms=data.bedrooms, bathrooms=data.bathrooms, size_m2=data.size_m2,
                property_type=data.property_type, furnished=data.furnished,
                elevator=data.elevator, parking=data.parking,
                address_raw=data.address_raw, neighborhood_raw=data.neighborhood_raw,
                district_raw=data.district_raw, municipality_raw=data.municipality_raw,
                lat=data.lat, lon=data.lon,
                first_seen_at=now, last_seen_at=now, scraped_at=now,
                is_active=True, scraper_run_id=self._run_id, raw=data.raw or {},
            )
            db.add(listing)
            db.flush()
            db.refresh(listing)
            for pos, img_url in enumerate(images):
                db.add(ListingImage(listing_id=listing.id, url=img_url, position=pos))
            db.flush()
            return True, False

        # --- update existing ---
        updated = False
        for field in self._UPDATE_FIELDS:
            new_val = getattr(data, field)
            if new_val is not None and getattr(existing, field) != new_val:
                setattr(existing, field, new_val)
                updated = True
        existing.last_seen_at = now
        existing.scraped_at = now
        existing.is_active = True
        existing.scraper_run_id = self._run_id
        if data.raw:
            existing.raw = data.raw

        # Merge images
        if images:
            current_urls = {img.url for img in existing.images}
            max_pos = max((img.position or 0 for img in existing.images), default=-1) + 1
            for img_url in images:
                if img_url not in current_urls:
                    db.add(ListingImage(
                        listing_id=existing.id, url=img_url, position=max_pos,
                    ))
                    max_pos += 1
                    updated = True

        db.flush()
        return False, updated

    # ---- Abstract interface ----

    @abstractmethod
    def list_pages(self) -> Iterator[list[ListingData]]:
        """Yield pages of partial listing data (list stage)."""
        ...

    @abstractmethod
    def fetch_detail(self, partial: ListingData) -> ListingData:
        """Fetch full listing details (detail stage). May return partial unchanged."""
        ...

    # ---- Main run loop ----

    def _needs_detail(self, partial: ListingData, existing: Optional[Listing]) -> bool:
        """Two-stage: fetch detail only for new listings or those missing key fields."""
        if existing is None:
            return True
        # Re-fetch if key fields are still missing
        return not all([
            existing.description, existing.bedrooms,
            existing.size_m2, existing.neighborhood_raw,
        ])

    def run(self) -> dict:
        stats = {"seen": 0, "new": 0, "updated": 0}
        error_msg = None

        with get_db() as db:
            self._portal_id = self._get_portal_id(db)
            self._run_id = self._start_run(db)
            db.commit()

        self._client = self._build_client()

        try:
            with get_db() as db:
                self._portal_id = self._get_portal_id(db)
                for page_listings in self.list_pages():
                    for partial in page_listings:
                        stats["seen"] += 1

                        # Check if detail fetch is needed
                        existing = (
                            db.query(Listing)
                            .filter_by(
                                portal_id=self._portal_id,
                                source_listing_id=partial.source_listing_id,
                            )
                            .first()
                        )
                        full = partial
                        if self._needs_detail(partial, existing):
                            try:
                                full = self.fetch_detail(partial)
                            except (ScraperError, httpx.HTTPError) as e:
                                log.warning("Detail fetch failed for %s: %s", partial.url, e)

                        is_new, was_updated = self._upsert_listing(db, full)
                        if is_new:
                            stats["new"] += 1
                        elif was_updated:
                            stats["updated"] += 1

                    db.commit()

                self._finish_run(db, self._run_id, stats)
                db.commit()
        except RateLimitError as e:
            error_msg = str(e)
            log.error("[%s] Rate limited: %s", self.portal_key, e)
        except Exception as e:
            error_msg = str(e)
            log.exception("[%s] Unexpected error", self.portal_key)
        finally:
            if self._client:
                self._client.close()
            if error_msg:
                with get_db() as db:
                    self._finish_run(db, self._run_id, stats, error=error_msg)
                    db.commit()

        return stats
