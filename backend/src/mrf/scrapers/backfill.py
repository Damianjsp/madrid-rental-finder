"""
Backfill missing detail data for existing listings.

Usage:
    python -m mrf.scrapers.backfill [--portal spotahome|pisos|enalquiler] [--limit 100] [--dry-run]

Queries listings missing description OR size_m2 OR furnished OR neighborhood,
fetches their detail pages, and updates the DB.  Always attempts the fetch and
applies any non-None enriched value to a NULL/empty DB field.  Listings that
yield zero new data are marked with ``raw.backfill_attempted = true`` so they
won't be retried forever.
"""

import argparse
import logging
import random
import time
from datetime import datetime, timezone

from sqlalchemy import or_

from mrf.db.models import Listing, Portal
from mrf.db.session import get_db
from mrf.scrapers.base import BaseScraper, ListingData

log = logging.getLogger("mrf.scrapers.backfill")

# Import concrete scrapers for their detail parsers
from mrf.scrapers.spotahome import SpotahomeScraper, _parse_detail_page as _spotahome_detail
from mrf.scrapers.pisos import PisosScraper, _parse_detail as _pisos_detail
from mrf.scrapers.enalquiler import EnalquilerScraper, _parse_detail as _enalquiler_detail

PORTAL_MAP = {
    "spotahome": (SpotahomeScraper, _spotahome_detail),
    "pisos": (PisosScraper, _pisos_detail),
    "enalquiler": (EnalquilerScraper, _enalquiler_detail),
}


def _listing_to_partial(listing: dict) -> ListingData:
    """Convert listing dict (extracted from DB) to a ListingData for re-parsing."""
    return ListingData(
        source_listing_id=listing["source_listing_id"],
        url=listing["url"],
        title=listing.get("title"),
        description=listing.get("description"),
        price_eur=listing.get("price_eur"),
        deposit_eur=None,
        expenses_included=None,
        bedrooms=listing.get("bedrooms"),
        bathrooms=listing.get("bathrooms"),
        size_m2=float(listing["size_m2"]) if listing.get("size_m2") is not None else None,
        property_type=listing.get("property_type"),
        furnished=listing.get("furnished"),
        elevator=None,
        parking=None,
        address_raw=listing.get("address_raw"),
        neighborhood_raw=listing.get("neighborhood_raw"),
        district_raw=listing.get("district_raw"),
        municipality_raw=listing.get("municipality_raw"),
        lat=listing.get("lat"),
        lon=listing.get("lon"),
        images=[],
        raw={},
    )


UPDATE_FIELDS = (
    "title", "description", "price_eur", "bedrooms", "bathrooms", "size_m2",
    "property_type", "furnished", "elevator", "parking",
    "address_raw", "neighborhood_raw", "district_raw",
    "municipality_raw", "lat", "lon",
)


def _is_empty(val) -> bool:
    """Return True when a DB value counts as 'missing'."""
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    return False


def _is_stale_neighborhood(val) -> bool:
    return isinstance(val, str) and val.strip().lower() == "madrid"


def backfill(portal_key: str | None = None, limit: int = 200, dry_run: bool = False):
    """Backfill listings missing key detail fields."""
    with get_db() as db:
        query = db.query(Listing).filter(Listing.is_active.is_(True))

        # Exclude listings already marked as backfill-attempted with no new data
        query = query.filter(
            or_(
                Listing.raw["backfill_attempted"].as_boolean().is_(None),
                Listing.raw["backfill_attempted"].as_boolean().is_(False),
                ~Listing.raw.has_key("backfill_attempted"),  # noqa: W601 — SQLAlchemy JSON op
            )
        )

        query = query.filter(
            or_(
                Listing.description.is_(None),
                Listing.size_m2.is_(None),
                Listing.furnished.is_(None),
                Listing.neighborhood_raw.is_(None),
                Listing.neighborhood_raw == "Madrid",
            )
        )

        if portal_key:
            portal = db.query(Portal).filter_by(key=portal_key).first()
            if not portal:
                log.error("Portal '%s' not found", portal_key)
                return
            query = query.filter(Listing.portal_id == portal.id)

        listings = query.order_by(Listing.id).limit(limit).all()
        log.info("Found %s listings to backfill", len(listings))

        if not listings:
            return

        # Eagerly extract data while session is open to avoid DetachedInstanceError
        listing_data = [
            {"id": l.id, "portal_id": l.portal_id, "url": l.url, "source_listing_id": l.source_listing_id,
             "title": l.title, "description": l.description, "price_eur": l.price_eur,
             "bedrooms": l.bedrooms, "bathrooms": l.bathrooms, "size_m2": float(l.size_m2) if l.size_m2 else None,
             "property_type": l.property_type, "furnished": l.furnished,
             "address_raw": l.address_raw, "neighborhood_raw": l.neighborhood_raw,
             "district_raw": l.district_raw, "municipality_raw": l.municipality_raw,
             "lat": l.lat, "lon": l.lon, "raw": dict(l.raw) if l.raw else {}}
            for l in listings
        ]

        # Group by portal
        portal_ids = {ld["portal_id"] for ld in listing_data}
        portals = {p.id: p.key for p in db.query(Portal).filter(Portal.id.in_(portal_ids)).all()}

    # Process each portal group
    stats = {"total": 0, "updated": 0, "failed": 0, "skipped": 0, "marked_done": 0}

    for pid, pkey in portals.items():
        if pkey not in PORTAL_MAP:
            log.warning("No backfill support for portal '%s'", pkey)
            continue

        scraper_cls, parse_fn = PORTAL_MAP[pkey]
        scraper = scraper_cls()
        scraper._client = scraper._build_client()

        portal_listings = [ld for ld in listing_data if ld["portal_id"] == pid]
        log.info("[%s] Backfilling %s listings", pkey, len(portal_listings))

        for i, listing in enumerate(portal_listings, 1):
            stats["total"] += 1
            partial = _listing_to_partial(listing)

            # Rate limit
            delay = random.uniform(scraper.rate_min, scraper.rate_max)
            time.sleep(delay)

            try:
                resp = scraper._client.get(
                    listing["url"],
                    timeout=30,
                    follow_redirects=True,
                )
                if resp.status_code == 404:
                    log.info("[%s] %s returned 404 — marking backfill_attempted", pkey, listing["url"])
                    if not dry_run:
                        _mark_backfill_attempted(listing["id"], listing["raw"])
                    stats["marked_done"] += 1
                    continue

                if resp.status_code != 200:
                    log.warning("[%s] %s returned %s", pkey, listing["url"], resp.status_code)
                    stats["failed"] += 1
                    continue

                enriched = parse_fn(resp.text, partial)

                if dry_run:
                    log.info(
                        "[%s] DRY-RUN %s/%s: %s → desc=%s size=%s neigh=%s furn=%s lat=%s",
                        pkey, i, len(portal_listings), listing["url"],
                        bool(enriched.description), enriched.size_m2,
                        enriched.neighborhood_raw, enriched.furnished,
                        enriched.lat,
                    )
                    continue

                # Apply updates to DB — fill any NULL/empty field with enriched data
                with get_db() as db:
                    db_listing = db.get(Listing, listing["id"])
                    if not db_listing:
                        stats["skipped"] += 1
                        continue

                    changed = False
                    for field in UPDATE_FIELDS:
                        new_val = getattr(enriched, field)
                        old_val = getattr(db_listing, field)

                        should_update = False

                        # Fill NULL/empty fields with any non-None enriched value
                        if new_val is not None and _is_empty(old_val):
                            should_update = True

                        # Special: overwrite stale 'Madrid' neighborhood
                        if (field == "neighborhood_raw"
                                and _is_stale_neighborhood(old_val)
                                and new_val
                                and not _is_stale_neighborhood(new_val)):
                            should_update = True

                        if should_update:
                            setattr(db_listing, field, new_val)
                            changed = True

                    if changed:
                        db_listing.scraped_at = datetime.now(timezone.utc)
                        db.flush()
                        stats["updated"] += 1
                        log.info("[%s] Updated %s/%s: %s", pkey, i, len(portal_listings), listing["url"])
                    else:
                        # Detail page returned nothing new — mark to avoid infinite retry
                        _mark_backfill_attempted(listing["id"], dict(db_listing.raw) if db_listing.raw else {})
                        stats["marked_done"] += 1
                        log.debug("[%s] No new data for %s — marked backfill_attempted", pkey, listing["url"])

            except Exception as e:
                log.warning("[%s] Backfill failed for %s: %s", pkey, listing["url"], e)
                stats["failed"] += 1

        if scraper._client:
            scraper._client.close()

    log.info(
        "Backfill complete: total=%s updated=%s failed=%s skipped=%s marked_done=%s",
        stats["total"], stats["updated"], stats["failed"], stats["skipped"], stats["marked_done"],
    )


def _mark_backfill_attempted(listing_id: int, existing_raw: dict):
    """Set raw.backfill_attempted = true so the listing is excluded from future runs."""
    with get_db() as db:
        db_listing = db.get(Listing, listing_id)
        if db_listing:
            new_raw = {**(existing_raw or {}), "backfill_attempted": True}
            db_listing.raw = new_raw
            db.flush()


def main():
    parser = argparse.ArgumentParser(description="Backfill missing listing details")
    parser.add_argument("--portal", choices=list(PORTAL_MAP.keys()), help="Limit to a single portal")
    parser.add_argument("--limit", type=int, default=200, help="Max listings to backfill (default: 200)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing to DB")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )

    backfill(portal_key=args.portal, limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
