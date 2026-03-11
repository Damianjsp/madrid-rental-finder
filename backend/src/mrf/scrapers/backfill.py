"""
Backfill missing detail data for existing listings.

Usage:
    python -m mrf.scrapers.backfill [--portal spotahome|pisos|enalquiler] [--limit 100] [--dry-run]

Queries listings missing description OR size_m2, fetches their detail pages,
and updates the DB. Respects rate limits.
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


def _listing_to_partial(listing: Listing) -> ListingData:
    """Convert DB listing to a ListingData for re-parsing."""
    return ListingData(
        source_listing_id=listing.source_listing_id,
        url=listing.url,
        title=listing.title,
        description=listing.description,
        price_eur=listing.price_eur,
        deposit_eur=listing.deposit_eur,
        expenses_included=listing.expenses_included,
        bedrooms=listing.bedrooms,
        bathrooms=listing.bathrooms,
        size_m2=float(listing.size_m2) if listing.size_m2 is not None else None,
        property_type=listing.property_type,
        furnished=listing.furnished,
        elevator=listing.elevator,
        parking=listing.parking,
        address_raw=listing.address_raw,
        neighborhood_raw=listing.neighborhood_raw,
        district_raw=listing.district_raw,
        municipality_raw=listing.municipality_raw,
        lat=listing.lat,
        lon=listing.lon,
        images=[img.url for img in listing.images],
        raw=listing.raw or {},
    )


UPDATE_FIELDS = (
    "title", "description", "price_eur", "bedrooms", "bathrooms", "size_m2",
    "property_type", "furnished", "elevator", "parking",
    "address_raw", "neighborhood_raw", "district_raw",
    "municipality_raw", "lat", "lon",
)


def backfill(portal_key: str | None = None, limit: int = 200, dry_run: bool = False):
    """Backfill listings missing key detail fields."""
    with get_db() as db:
        query = db.query(Listing).filter(Listing.is_active.is_(True))
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

        # Group by portal
        portal_ids = {l.portal_id for l in listings}
        portals = {p.id: p.key for p in db.query(Portal).filter(Portal.id.in_(portal_ids)).all()}

    # Process each portal group
    stats = {"total": 0, "updated": 0, "failed": 0, "skipped": 0}

    for pid, pkey in portals.items():
        if pkey not in PORTAL_MAP:
            log.warning("No backfill support for portal '%s'", pkey)
            continue

        scraper_cls, parse_fn = PORTAL_MAP[pkey]
        scraper = scraper_cls()
        scraper._client = scraper._build_client()

        portal_listings = [l for l in listings if l.portal_id == pid]
        log.info("[%s] Backfilling %s listings", pkey, len(portal_listings))

        for i, listing in enumerate(portal_listings, 1):
            stats["total"] += 1
            partial = _listing_to_partial(listing)

            # Rate limit
            delay = random.uniform(scraper.rate_min, scraper.rate_max)
            time.sleep(delay)

            try:
                resp = scraper._client.get(
                    listing.url,
                    timeout=30,
                    follow_redirects=True,
                )
                if resp.status_code != 200:
                    log.warning("[%s] %s returned %s", pkey, listing.url, resp.status_code)
                    stats["failed"] += 1
                    continue

                enriched = parse_fn(resp.text, partial)

                if dry_run:
                    log.info(
                        "[%s] DRY-RUN %s/%s: %s → desc=%s size=%s neigh=%s furn=%s lat=%s",
                        pkey, i, len(portal_listings), listing.url,
                        bool(enriched.description), enriched.size_m2,
                        enriched.neighborhood_raw, enriched.furnished,
                        enriched.lat,
                    )
                    continue

                # Apply updates to DB
                with get_db() as db:
                    db_listing = db.get(Listing, listing.id)
                    if not db_listing:
                        stats["skipped"] += 1
                        continue

                    changed = False
                    for field in UPDATE_FIELDS:
                        new_val = getattr(enriched, field)
                        old_val = getattr(db_listing, field)
                        # Only update if new is non-None and old is None/empty
                        if new_val is not None and (old_val is None or (isinstance(old_val, str) and not old_val.strip())):
                            setattr(db_listing, field, new_val)
                            changed = True
                        # Special: update neighborhood_raw if it was just "Madrid"
                        if field == "neighborhood_raw" and old_val == "Madrid" and new_val and new_val.strip().lower() != "madrid":
                            setattr(db_listing, field, new_val)
                            changed = True

                    if changed:
                        db_listing.scraped_at = datetime.now(timezone.utc)
                        db.flush()
                        stats["updated"] += 1
                        log.info("[%s] Updated %s/%s: %s", pkey, i, len(portal_listings), listing.url)
                    else:
                        stats["skipped"] += 1

            except Exception as e:
                log.warning("[%s] Backfill failed for %s: %s", pkey, listing.url, e)
                stats["failed"] += 1

        if scraper._client:
            scraper._client.close()

    log.info(
        "Backfill complete: total=%s updated=%s failed=%s skipped=%s",
        stats["total"], stats["updated"], stats["failed"], stats["skipped"],
    )


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
