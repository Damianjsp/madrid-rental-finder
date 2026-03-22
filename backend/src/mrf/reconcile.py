"""Listing reconciliation helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from mrf.db.models import Listing
from mrf.db.session import get_db


def reconcile_listings(stale_after_days: int = 7) -> dict[str, int]:
    """Mark stale active listings inactive and return a summary."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=stale_after_days)
    with get_db() as db:
        stale_listings = (
            db.query(Listing)
            .filter(Listing.is_active.is_(True), Listing.last_seen_at < cutoff)
            .all()
        )
        deactivated = 0
        for listing in stale_listings:
            listing.is_active = False
            deactivated += 1
        db.flush()
    return {"deactivated": deactivated, "cutoff_days": stale_after_days}
