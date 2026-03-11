"""One-off fixer for listings with neighborhood_raw='Madrid'.

Run:
  python scripts/fix_neighborhoods.py
"""

from __future__ import annotations

from sqlalchemy import or_

from mrf.db.models import Listing
from mrf.db.session import get_db
from mrf.neighborhoods import extract_neighborhood_from_title, match_neighborhood


def main() -> None:
    fixed = 0
    matched = 0
    scanned = 0

    with get_db() as db:
        rows = (
            db.query(Listing)
            .filter(Listing.neighborhood_raw == 'Madrid')
            .filter(Listing.title.is_not(None))
            .all()
        )

        for listing in rows:
            scanned += 1
            extracted = extract_neighborhood_from_title(listing.title)
            if not extracted:
                continue

            neighborhood_id, canonical_name, district_id = match_neighborhood(db, extracted)
            new_raw = canonical_name or extracted
            changed = False

            if listing.neighborhood_raw != new_raw:
                listing.neighborhood_raw = new_raw
                changed = True
            if neighborhood_id and listing.neighborhood_id != neighborhood_id:
                listing.neighborhood_id = neighborhood_id
                changed = True
            if district_id and listing.district_id != district_id:
                listing.district_id = district_id
                changed = True

            if changed:
                fixed += 1
            if neighborhood_id:
                matched += 1

        db.commit()

    print({"scanned": scanned, "fixed": fixed, "matched_to_db": matched})


if __name__ == '__main__':
    main()
