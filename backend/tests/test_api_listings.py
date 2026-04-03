from datetime import datetime, timezone

from fastapi.testclient import TestClient

from mrf.api.main import app
from mrf.db.models import Listing, Portal
from mrf.db.session import get_db_dep


class FakeQuery:
    def __init__(self, items):
        self._items = list(items)

    def filter(self, *criteria):
        filtered = self._items
        for criterion in criteria:
            filtered = [item for item in filtered if _matches(item, criterion)]
        return FakeQuery(filtered)

    def filter_by(self, **kwargs):
        filtered = [
            item for item in self._items
            if all(getattr(item, key) == value for key, value in kwargs.items())
        ]
        return FakeQuery(filtered)

    def order_by(self, *args, **kwargs):
        return self

    def count(self):
        return len(self._items)

    def offset(self, value):
        return FakeQuery(self._items[value:])

    def limit(self, value):
        return FakeQuery(self._items[:value])

    def all(self):
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None


def _matches(item, criterion) -> bool:
    compiled = str(criterion.compile(compile_kwargs={"literal_binds": True}))
    if "price_eur IS NOT NULL" in compiled:
        return item.price_eur is not None
    if "is_active IS true" in compiled or "is_active IS 1" in compiled:
        return item.is_active is True
    if "property_type IN" in compiled:
        return item.property_type in {"piso", "estudio"}
    raise AssertionError(f"Unhandled SQLAlchemy criterion in test double: {compiled}")


class FakeDbSession:
    def __init__(self, listings, portals):
        self._listings = listings
        self._portals = portals

    def query(self, model):
        if model is Listing:
            return FakeQuery(self._listings)
        if model is Portal:
            return FakeQuery(self._portals)
        raise AssertionError(f"Unexpected model query: {model}")


def test_api_listings_excludes_rows_without_price():
    portal = Portal(id=1, key="pisos", name="Pisos", tier=1)
    timestamp = datetime.now(timezone.utc)
    priced_listing = Listing(
        id=1,
        portal_id=portal.id,
        source_listing_id="priced",
        url="https://example.com/priced",
        title="Priced listing",
        price_eur=1200,
        property_type="piso",
        municipality_raw="Madrid",
        is_active=True,
        first_seen_at=timestamp,
        last_seen_at=timestamp,
        scraped_at=timestamp,
        raw={},
    )
    missing_price_listing = Listing(
        id=2,
        portal_id=portal.id,
        source_listing_id="no-price",
        url="https://example.com/no-price",
        title="No price listing",
        price_eur=None,
        property_type="piso",
        municipality_raw="Madrid",
        is_active=True,
        first_seen_at=timestamp,
        last_seen_at=timestamp,
        scraped_at=timestamp,
        raw={},
    )
    fake_db = FakeDbSession([priced_listing, missing_price_listing], [portal])

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db_dep] = lambda: fake_db

    with TestClient(app) as client:
        response = client.get("/api/listings")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["source_listing_id"] for item in payload["items"]] == ["priced"]
