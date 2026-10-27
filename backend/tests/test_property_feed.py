"""The future-provider boundary: repeatable imports, demo data kept apart from real data."""
from app.schemas.property import PropertyCreate
from app.services.property_feed import import_feed

RECORD = {
    "title": "Licensed feed apartment in Pune", "description": "A listing delivered by a (test) licensed data feed.",
    "city": "Pune", "locality": "Baner", "property_type": "apartment", "listing_type": "buy", "price": 7_500_000,
    "area_sqft": 1000, "bedrooms": 2, "bathrooms": 2,
}


class _Feed:
    name = "test-feed"

    def __init__(self, *records):
        self.records = records

    def fetch(self):
        return list(self.records)


def test_import_creates_real_listings_once(db, client):
    rec = PropertyCreate(**RECORD)
    first = import_feed(db, _Feed(rec, rec))  # the same record twice in one batch
    second = import_feed(db, _Feed(rec))
    assert (first.created, first.skipped_existing) == (1, 1)
    assert (second.created, second.skipped_existing) == (0, 1)
    items = client.get("/api/properties").json()["items"]
    assert len(items) == 1 and items[0]["is_demo"] is False


def test_feed_cannot_supply_demo_listings(db):
    report = import_feed(db, _Feed(PropertyCreate(**RECORD, is_demo=True)))
    assert report.created == 0 and len(report.rejected) == 1
