from types import SimpleNamespace

from mrf.scrapers.base import BaseScraper, ListingData
from mrf.scrapers.enalquiler import _parse_price as parse_enalquiler_price
from mrf.scrapers.habitaclia import _parse_price as parse_habitaclia_price
from mrf.scrapers.pisos import _parse_price as parse_pisos_price
from mrf.scrapers.yaencontre import _parse_price as parse_yaencontre_price


class DummyScraper(BaseScraper):
    portal_key = "dummy"

    def __init__(self, listings: list[ListingData]):
        super().__init__()
        self._listings = listings
        self.upserted: list[ListingData] = []

    def list_pages(self):
        yield self._listings

    def fetch_detail(self, partial: ListingData) -> ListingData:
        return partial

    def _get_portal_id(self, db):
        return 1

    def _start_run(self, db):
        return 99

    def _finish_run(self, db, run_id, stats, error=None):
        return None

    def _upsert_listing(self, db, data: ListingData):
        self.upserted.append(data)
        return True, False


class DummyDbSession:
    def __init__(self):
        self.commits = 0

    def query(self, model):
        return self

    def filter_by(self, **kwargs):
        return self

    def first(self):
        return None

    def commit(self):
        self.commits += 1


class DummyDbContext:
    def __init__(self, session: DummyDbSession):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


CALL_FOR_PRICE_TEXTS = ["Consultar", "Llamar", "A consultar", "contacto", "a convenir"]
NORMAL_PRICE_TEXT = "1.200 €/mes"


def test_run_skips_listings_without_price_and_counts_stat(monkeypatch):
    scraper = DummyScraper(
        listings=[
            ListingData(
                source_listing_id="listing-no-price",
                url="https://example.com/listing-no-price",
                title="Call for price listing",
                price_eur=None,
            )
        ]
    )
    dummy_db = DummyDbSession()

    monkeypatch.setattr(scraper, "_build_client", lambda: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr("mrf.scrapers.base.get_db", lambda: DummyDbContext(dummy_db))

    stats = scraper.run()

    assert stats == {"seen": 1, "new": 0, "updated": 0, "skipped_no_price": 1}
    assert scraper.upserted == []
    assert scraper._quality_counts["total"] == 0
    assert dummy_db.commits >= 2


def test_parse_price_keyword_guards_pisos():
    for text in CALL_FOR_PRICE_TEXTS:
        assert parse_pisos_price(text) is None
    assert parse_pisos_price(NORMAL_PRICE_TEXT) == 1200


def test_parse_price_keyword_guards_enalquiler():
    for text in CALL_FOR_PRICE_TEXTS:
        assert parse_enalquiler_price(text) is None
    assert parse_enalquiler_price(NORMAL_PRICE_TEXT) == 1200


def test_parse_price_keyword_guards_habitaclia():
    for text in CALL_FOR_PRICE_TEXTS:
        assert parse_habitaclia_price(text) is None
    assert parse_habitaclia_price(NORMAL_PRICE_TEXT) == 1200


def test_parse_price_keyword_guards_yaencontre():
    for text in CALL_FOR_PRICE_TEXTS:
        assert parse_yaencontre_price(text) is None
    assert parse_yaencontre_price(NORMAL_PRICE_TEXT) == 1200
