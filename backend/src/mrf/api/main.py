"""FastAPI application — read-only API for Madrid Rental Finder."""

import logging
import re
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload

from mrf.api.schemas import (
    ListingDetailOut,
    ListingImageOut,
    ListingsPage,
    ListingOut,
    NeighborhoodOut,
    PortalOut,
    StatsOut,
    DistrictStatsOut,
    NeighborhoodStatsOut,
    CostBenchmarkOut,
)
from mrf.db.models import (
    CostBenchmark,
    District,
    Listing,
    ListingImage,
    Neighborhood,
    Portal,
    ScraperRun,
)
from mrf.core.config import settings
from mrf.db.session import get_db_dep

log = logging.getLogger("mrf.api")


def _escape_like(value: str) -> str:
    return re.sub(r"([%_\\])", lambda m: "\\" + m.group(1), value)


app = FastAPI(
    title="Madrid Rental Finder API",
    description="Read-only API for Madrid rental listings.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/healthz", tags=["system"])
def healthz(db: Session = Depends(get_db_dep)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail={"status": "error"})


# ---------------------------------------------------------------------------
# Portals
# ---------------------------------------------------------------------------


@app.get("/api/portals", response_model=list[PortalOut], tags=["portals"])
def list_portals(db: Session = Depends(get_db_dep)):
    portals = db.query(Portal).order_by(Portal.tier, Portal.name).all()
    result = []
    for p in portals:
        # Get last scrape run
        last_run = (
            db.query(ScraperRun)
            .filter_by(portal_id=p.id)
            .order_by(ScraperRun.started_at.desc())
            .first()
        )
        total = db.query(func.count(Listing.id)).filter_by(portal_id=p.id).scalar() or 0
        out = PortalOut.model_validate(p)
        out.last_scrape_status = last_run.status if last_run else None
        out.last_scrape_at = last_run.finished_at if last_run else None
        out.total_listings = total
        result.append(out)
    return result


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------


@app.get("/api/listings", response_model=ListingsPage, tags=["listings"])
def list_listings(
    price_min: Optional[int] = Query(None, ge=0),
    price_max: Optional[int] = Query(None, ge=0),
    bedrooms: Optional[int] = Query(None, ge=0),
    size_min: Optional[float] = Query(None, ge=0),
    size_max: Optional[float] = Query(None, ge=0),
    district: Optional[str] = Query(None, description="District name (partial match)"),
    neighborhood: Optional[str] = Query(None, description="Neighborhood name (partial match)"),
    portal: Optional[str] = Query(None, description="Portal key e.g. 'pisos'"),
    active_only: bool = Query(True),
    sort: str = Query("newest", pattern="^(newest|price|price_desc|size|size_desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db_dep),
):
    q = db.query(Listing)

    if active_only:
        q = q.filter(Listing.is_active.is_(True))
    if price_min is not None:
        q = q.filter(Listing.price_eur >= price_min)
    if price_max is not None:
        q = q.filter(Listing.price_eur <= price_max)
    if bedrooms is not None:
        q = q.filter(Listing.bedrooms == bedrooms)
    if size_min is not None:
        q = q.filter(Listing.size_m2 >= size_min)
    if size_max is not None:
        q = q.filter(Listing.size_m2 <= size_max)
    if district:
        q = q.filter(Listing.district_raw.ilike(f"%{_escape_like(district)}%", escape="\\"))
    if neighborhood:
        q = q.filter(Listing.neighborhood_raw.ilike(f"%{_escape_like(neighborhood)}%", escape="\\"))
    if portal:
        p_obj = db.query(Portal).filter_by(key=portal).first()
        if p_obj:
            q = q.filter(Listing.portal_id == p_obj.id)

    # Sort
    if sort == "newest":
        q = q.order_by(Listing.last_seen_at.desc())
    elif sort == "price":
        q = q.order_by(Listing.price_eur.asc().nulls_last())
    elif sort == "price_desc":
        q = q.order_by(Listing.price_eur.desc().nulls_last())
    elif sort == "size":
        q = q.order_by(Listing.size_m2.asc().nulls_last())
    elif sort == "size_desc":
        q = q.order_by(Listing.size_m2.desc().nulls_last())

    total = q.count()
    offset = (page - 1) * page_size
    items = q.offset(offset).limit(page_size).all()

    # Enrich with portal key
    portal_keys = {p.id: p.key for p in db.query(Portal).all()}

    result_items = []
    for listing in items:
        out = ListingOut.model_validate(listing)
        out.portal_key = portal_keys.get(listing.portal_id)
        result_items.append(out)

    return ListingsPage(total=total, page=page, page_size=page_size, items=result_items)


@app.get("/api/listings/{listing_id}", response_model=ListingDetailOut, tags=["listings"])
def get_listing(listing_id: int, db: Session = Depends(get_db_dep)):
    listing = (
        db.query(Listing)
        .options(joinedload(Listing.images))
        .filter(Listing.id == listing_id)
        .first()
    )
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    portal = db.get(Portal, listing.portal_id)
    out = ListingDetailOut.model_validate(listing)
    out.portal_key = portal.key if portal else None
    out.images = [
        ListingImageOut(id=img.id, url=img.url, position=img.position)
        for img in sorted(listing.images, key=lambda i: i.position or 999)
    ]
    return out


# ---------------------------------------------------------------------------
# Neighborhoods
# ---------------------------------------------------------------------------


@app.get("/api/neighborhoods", response_model=list[NeighborhoodOut], tags=["neighborhoods"])
def list_neighborhoods(
    municipality: Optional[str] = Query(None),
    min_safety: Optional[int] = Query(None, ge=1, le=5),
    min_transport: Optional[int] = Query(None, ge=1, le=5),
    db: Session = Depends(get_db_dep),
):
    q = db.query(Neighborhood)
    if municipality:
        q = q.filter(Neighborhood.municipality.ilike(f"%{_escape_like(municipality)}%", escape="\\"))
    if min_safety is not None:
        q = q.filter(Neighborhood.safety_score >= min_safety)
    if min_transport is not None:
        q = q.filter(Neighborhood.transport_score >= min_transport)

    neighborhoods = q.order_by(Neighborhood.municipality, Neighborhood.name).all()

    # Build district name map
    district_map = {d.id: d.name for d in db.query(District).all()}

    # Cost benchmark lookup (latest per scope_name)
    benchmarks: dict[str, CostBenchmark] = {}
    for cb in db.query(CostBenchmark).order_by(CostBenchmark.observed_at.desc()).all():
        if cb.scope_name not in benchmarks:
            benchmarks[cb.scope_name] = cb

    # Listing counts per neighborhood
    counts_q = (
        db.query(Listing.neighborhood_id, func.count(Listing.id))
        .filter(Listing.is_active.is_(True))
        .group_by(Listing.neighborhood_id)
        .all()
    )
    listing_counts = {nid: cnt for nid, cnt in counts_q if nid is not None}

    result = []
    for n in neighborhoods:
        out = NeighborhoodOut.model_validate(n)
        out.district_name = district_map.get(n.district_id) if n.district_id else None
        out.listing_count = listing_counts.get(n.id, 0)

        # Try to find benchmark: by neighborhood name first, then district name
        cb = benchmarks.get(n.name) or benchmarks.get(out.district_name or "")
        if cb:
            out.cost_benchmark = CostBenchmarkOut.model_validate(cb)

        result.append(out)

    return result


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@app.get("/api/stats", response_model=StatsOut, tags=["stats"])
def get_stats(db: Session = Depends(get_db_dep)):
    total = db.query(func.count(Listing.id)).scalar() or 0
    active = db.query(func.count(Listing.id)).filter(Listing.is_active.is_(True)).scalar() or 0
    portals_active = (
        db.query(func.count(func.distinct(Listing.portal_id)))
        .filter(Listing.is_active.is_(True))
        .scalar()
        or 0
    )

    # By district (using raw field since many listings won't have district_id yet)
    district_rows = (
        db.query(
            Listing.district_id,
            Listing.district_raw,
            func.count(Listing.id).label("total"),
            func.count(Listing.id).filter(Listing.is_active.is_(True)).label("active"),
            func.avg(Listing.price_eur).label("avg_price"),
            func.min(Listing.price_eur).label("min_price"),
            func.max(Listing.price_eur).label("max_price"),
        )
        .group_by(Listing.district_id, Listing.district_raw)
        .order_by(func.count(Listing.id).desc())
        .limit(50)
        .all()
    )

    district_map = {d.id: d.name for d in db.query(District).all()}

    by_district = []
    for row in district_rows:
        name = district_map.get(row.district_id) if row.district_id else (row.district_raw or "Unknown")
        by_district.append(
            DistrictStatsOut(
                district_id=row.district_id,
                district_name=name,
                total_listings=row.total,
                active_listings=row.active,
                avg_price=round(float(row.avg_price), 0) if row.avg_price else None,
                min_price=row.min_price,
                max_price=row.max_price,
            )
        )

    # By neighborhood
    neighborhood_rows = (
        db.query(
            Listing.neighborhood_id,
            Listing.neighborhood_raw,
            Listing.district_raw,
            func.count(Listing.id).label("total"),
            func.count(Listing.id).filter(Listing.is_active.is_(True)).label("active"),
            func.avg(Listing.price_eur).label("avg_price"),
        )
        .group_by(Listing.neighborhood_id, Listing.neighborhood_raw, Listing.district_raw)
        .order_by(func.count(Listing.id).desc())
        .limit(100)
        .all()
    )

    neighborhood_map = {n.id: n.name for n in db.query(Neighborhood).all()}

    by_neighborhood = []
    for row in neighborhood_rows:
        name = (
            neighborhood_map.get(row.neighborhood_id)
            if row.neighborhood_id
            else (row.neighborhood_raw or "Unknown")
        )
        by_neighborhood.append(
            NeighborhoodStatsOut(
                neighborhood_id=row.neighborhood_id,
                neighborhood_name=name,
                district_name=row.district_raw,
                total_listings=row.total,
                active_listings=row.active,
                avg_price=round(float(row.avg_price), 0) if row.avg_price else None,
            )
        )

    return StatsOut(
        total_listings=total,
        active_listings=active,
        portals_active=portals_active,
        by_district=by_district,
        by_neighborhood=by_neighborhood,
    )


def run():
    import uvicorn
    from mrf.core.config import settings

    uvicorn.run("mrf.api.main:app", host="0.0.0.0", port=settings.api_port, reload=False)


if __name__ == "__main__":
    run()
