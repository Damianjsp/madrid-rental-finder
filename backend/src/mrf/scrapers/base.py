"""Base scraper class with rate limiting, session management, and run tracking."""

import logging
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from collections import Counter
from typing import Iterator, Optional

import httpx
from sqlalchemy.orm import Session

from mrf.db.models import District, Listing, ListingImage, Neighborhood, Portal, ScraperRun
from mrf.db.session import get_db
from mrf.neighborhoods import match_neighborhood

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
        self._quality_counts: Counter[str] = Counter()

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

    def _get(self, url: str, retries: int = 3, retry_backoff: float = 2.0, **kwargs) -> httpx.Response:
        assert self._client is not None
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            delay = random.uniform(self.rate_min, self.rate_max)
            log.debug("Sleeping %.1fs before %s (attempt %s/%s)", delay, url, attempt, retries)
            time.sleep(delay)
            try:
                resp = self._client.get(url, **kwargs)
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
                log.warning("GET failed for %s (attempt %s/%s): %s — retrying in %.1fs", url, attempt, retries, e, sleep_s)
                time.sleep(sleep_s)
        if last_error:
            raise last_error
        raise ScraperError(f"GET failed for {url}")

    # ---- Portal / Run management ----

    def _get_portal_id(self, db: Session) -> int:
        portal = db.query(Portal).filter_by(key=self.portal_key).first()
        if not portal:
            raise ScraperError(f"Portal '{self.portal_key}' not found in DB. Run seed first.")
        return portal.id

    def _cleanup_interrupted_runs(self, db: Session) -> int:
        stale_runs = (
            db.query(ScraperRun)
            .filter(
                ScraperRun.portal_id == self._portal_id,
                ScraperRun.status == "running",
                ScraperRun.finished_at.is_(None),
            )
            .all()
        )
        cleaned = 0
        now = datetime.now(timezone.utc)
        current_run_id = self._run_id
        for stale_run in stale_runs:
            if current_run_id is not None and stale_run.id == current_run_id:
                continue
            stale_run.status = "stale"
            stale_run.finished_at = now
            stale_run.error_message = "interrupted — cleaned up by new run"
            cleaned += 1
        if cleaned:
            log.warning("[%s] Cleaned up %s interrupted run(s)", self.portal_key, cleaned)
        db.flush()
        return cleaned

    def _start_run(self, db: Session) -> int:
        self._cleanup_interrupted_runs(db)
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
        skipped_no_price = stats.get("skipped_no_price")
        log_parts = [
            f"[{self.portal_key}] Run #{run_id} finished: seen={run.listings_seen} new={run.listings_new} updated={run.listings_updated}"
        ]
        if skipped_no_price:
            log_parts.append(f"skipped_no_price={skipped_no_price}")
        log.info(" ".join(log_parts))

    # ---- Upsert ----

    _UPDATE_FIELDS = (
        "url", "title", "description", "price_eur", "deposit_eur",
        "expenses_included", "bedrooms", "bathrooms", "size_m2",
        "property_type", "furnished", "elevator", "parking",
        "address_raw", "neighborhood_raw", "district_raw",
        "municipality_raw", "lat", "lon",
    )

    def _resolve_location_ids(self, db: Session, data: ListingData) -> tuple[int | None, int | None]:
        neighborhood_id, canonical_name, district_id = match_neighborhood(db, data.neighborhood_raw)
        if canonical_name:
            data.neighborhood_raw = canonical_name
        if district_id and not data.district_raw:
            district = db.get(District, district_id)
            if district:
                data.district_raw = district.name
        return neighborhood_id, district_id

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
            neighborhood_id, district_id = self._resolve_location_ids(db, data)
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
                neighborhood_id=neighborhood_id, district_id=district_id,
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
        neighborhood_id, district_id = self._resolve_location_ids(db, data)
        for field in self._UPDATE_FIELDS:
            new_val = getattr(data, field)
            if new_val is not None and getattr(existing, field) != new_val:
                setattr(existing, field, new_val)
                updated = True
        if neighborhood_id is not None and existing.neighborhood_id != neighborhood_id:
            existing.neighborhood_id = neighborhood_id
            updated = True
        if district_id is not None and existing.district_id != district_id:
            existing.district_id = district_id
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
        return any([
            not existing.description,
            existing.bedrooms is None,
            existing.size_m2 is None,
            not existing.neighborhood_raw,
            existing.furnished is None,
            not existing.address_raw,
            existing.lat is None or existing.lon is None,
        ])

    def _quality_score(self, data: ListingData) -> int:
        checks = [
            data.price_eur is not None,
            data.bedrooms is not None,
            data.size_m2 is not None,
            bool(data.neighborhood_raw and data.neighborhood_raw.strip() and data.neighborhood_raw.strip().lower() != "madrid"),
            bool(data.description and data.description.strip()),
            data.furnished is not None,
        ]
        return int(sum(checks) / len(checks) * 100)

    def _track_quality(self, data: ListingData):
        self._quality_counts["total"] += 1
        if data.price_eur is None:
            self._quality_counts["missing_price"] += 1
        if data.bedrooms is None:
            self._quality_counts["missing_bedrooms"] += 1
        if data.size_m2 is None:
            self._quality_counts["missing_size_m2"] += 1
        if not data.neighborhood_raw or data.neighborhood_raw.strip().lower() == "madrid":
            self._quality_counts["missing_neighborhood"] += 1
        if not data.description:
            self._quality_counts["missing_description"] += 1
        if data.furnished is None:
            self._quality_counts["missing_furnished"] += 1
        if self._quality_score(data) >= 80:
            self._quality_counts["complete"] += 1

    def _log_quality_warning(self, data: ListingData):
        missing = []
        if data.price_eur is None:
            missing.append("price")
        if data.bedrooms is None:
            missing.append("bedrooms")
        if data.size_m2 is None:
            missing.append("size_m2")
        if not data.neighborhood_raw or data.neighborhood_raw.strip().lower() == "madrid":
            missing.append("neighborhood")
        if missing:
            log.warning("[%s] Listing %s missing critical fields: %s", self.portal_key, data.url, ", ".join(missing))

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

                        # Skip listings without a price ("Consultar" / call-for-price)
                        if full.price_eur is None:
                            stats.setdefault("skipped_no_price", 0)
                            stats["skipped_no_price"] += 1
                            log.info("[%s] Skipping %s — no price (call-for-price)", self.portal_key, full.url)
                            continue

                        quality_score = self._quality_score(full)
                        if full.raw is None:
                            full.raw = {}
                        full.raw = {**(full.raw or {}), "data_quality_score": quality_score}
                        self._track_quality(full)
                        self._log_quality_warning(full)

                        is_new, was_updated = self._upsert_listing(db, full)
                        if is_new:
                            stats["new"] += 1
                        elif was_updated:
                            stats["updated"] += 1

                    db.commit()

                log.info("[%s] Quality stats: complete=%s total=%s missing_size=%s missing_description=%s missing_neighborhood=%s missing_furnished=%s", self.portal_key, self._quality_counts.get("complete", 0), self._quality_counts.get("total", 0), self._quality_counts.get("missing_size_m2", 0), self._quality_counts.get("missing_description", 0), self._quality_counts.get("missing_neighborhood", 0), self._quality_counts.get("missing_furnished", 0))
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
