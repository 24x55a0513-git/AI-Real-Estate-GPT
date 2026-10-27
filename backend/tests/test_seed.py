"""The seed script must be repeatable, must not touch real data, and must feed the assistant real results."""
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import Property
from scripts.seed import ROWS, seed_demo_users, seed_properties


def count(db, *where) -> int:
    return db.scalar(select(func.count(Property.id)).where(*where))


def test_seed_is_repeatable_and_creates_no_duplicates(db):
    assert seed_properties(db, reset=False) == len(ROWS)
    assert seed_properties(db, reset=False) == 0
    assert count(db) == len(ROWS)


def test_every_seeded_listing_is_labelled_as_fictional_demo_data(db):
    seed_properties(db, reset=False)
    props = db.scalars(select(Property)).all()
    assert props and all(p.is_demo and "fictional" in p.description.lower() for p in props)
    assert len({p.city for p in props}) >= 4


def test_reset_only_removes_demo_rows(db):
    db.add(Property(title="Real user listing", description="A non-demo listing that must survive a reset.",
                    city="Pune", locality="Baner", property_type="apartment", listing_type="buy",
                    price=Decimal(1_000_000), area_sqft=900, is_demo=False))
    db.commit()
    seed_properties(db, reset=False)
    seed_properties(db, reset=True)
    assert count(db) == len(ROWS) + 1
    assert count(db, Property.title == "Real user listing") == 1


def test_demo_users_are_refused_outside_development(db):
    with pytest.raises(SystemExit):  # the test run uses ENVIRONMENT=test
        seed_demo_users(db)


# ------------------------------------------------------------------ assistant on top of the seeded data
def ask(client, message):
    r = client.post("/api/chat/message", json={"message": message})
    assert r.status_code == 200, r.text
    return r.json()


def titles(body):
    return [m["property"]["title"] for m in body["matches"]]


def test_assistant_2bhk_hyderabad_under_60_lakh(client, db):
    seed_properties(db, reset=False)
    body = ask(client, "Find a 2BHK apartment in Hyderabad under ₹60 lakh")
    assert body["parser"] == "rule-based"
    assert titles(body) == ["Bright 2BHK near the Financial District"]
    assert all(m["property"]["is_demo"] for m in body["matches"])


def test_assistant_rentals_below_25000(client, db):
    seed_properties(db, reset=False)
    body = ask(client, "Show rental flats below ₹25,000 per month")
    assert titles(body) == ["Compact 1BHK for commuters", "Affordable 2BHK family flat", "2BHK for rent close to the metro"]


def test_assistant_villas_between_80_lakh_and_1_5_crore(client, db):
    seed_properties(db, reset=False)
    body = ask(client, "Find villas between ₹80 lakh and ₹1.5 crore")
    assert titles(body) == ["3-bedroom villa in a gated layout", "Contemporary 3-bedroom villa with clubhouse"]


def test_assistant_parking_and_two_bedrooms(client, db):
    seed_properties(db, reset=False)
    body = ask(client, "Show properties with parking and at least two bedrooms")
    assert body["total_matches"] > 0
    assert all(m["property"]["has_parking"] and m["property"]["bedrooms"] >= 2 for m in body["matches"])


def test_assistant_does_not_invent_listings_for_unknown_city(client, db):
    seed_properties(db, reset=False)
    body = ask(client, "Find a 4BHK villa in Mumbai under 5 crore")
    assert body["matches"] == [] and "no listings in Mumbai" in body["reply"]


def test_assistant_says_so_and_offers_to_relax_when_nothing_matches(client, db):
    seed_properties(db, reset=False)
    body = ask(client, "Find a 4BHK villa in Pune under 1 crore")
    assert body["matches"] == [] and "couldn't find any matching" in body["reply"]
    assert all(s["match_count"] > 0 for s in body["suggestions"])
