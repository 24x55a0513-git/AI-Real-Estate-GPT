"""Pure-Python tests for the language parser (no database / web framework needed)."""
from decimal import Decimal

import pytest

from app.services.nlp_parser import parse_query

LOCALITIES = {"gachibowli": ("Gachibowli", "Hyderabad"), "whitefield": ("Whitefield", "Bengaluru")}


def test_example_1_two_bhk_apartment_under_60_lakh_with_parking():
    q = parse_query("Find a 2BHK apartment in Hyderabad under ₹60 lakh with parking.")
    assert q.city == "Hyderabad"
    assert q.property_types == ["apartment"]
    assert q.min_bedrooms == q.max_bedrooms == 2
    assert q.max_price == Decimal(6_000_000)
    assert q.has_parking is True
    assert q.listing_type == "buy"          # inferred from amount; documented in assumptions
    assert q.intent == "search"


def test_example_2_villas_between_80_lakh_and_1_5_crore():
    q = parse_query("Show villas in Bengaluru between ₹80 lakh and ₹1.5 crore.")
    assert q.city == "Bengaluru" and q.property_types == ["villa"]
    assert q.min_price == Decimal(8_000_000)
    assert q.max_price == Decimal(15_000_000)


def test_example_3_rental_flat_under_25000_per_month():
    q = parse_query("Find a rental flat in Hyderabad under ₹25,000 per month.")
    assert q.listing_type == "rent"
    assert q.max_price == Decimal(25_000)
    assert q.property_types == ["apartment"]


def test_example_4_three_bedroom_houses_min_area():
    q = parse_query("Show houses with three bedrooms and at least 1,500 square feet.")
    assert q.property_types == ["independent_house"]
    assert q.min_bedrooms == q.max_bedrooms == 3
    assert q.min_area == 1500
    assert q.min_price is None and q.max_price is None   # 1,500 must not be read as money


def test_example_5_compare_cheapest():
    q = parse_query("Compare the cheapest matching properties.")
    assert q.intent == "compare" and q.sort == "price_asc"


@pytest.mark.parametrize("text,expected", [
    ("under ₹50,000", Decimal(50_000)),
    ("under 50000 rupees", Decimal(50_000)),
    ("under 50 thousand", Decimal(50_000)),
    ("under 50k", Decimal(50_000)),
    ("under 25 lakh", Decimal(2_500_000)),
    ("under 60 lakhs", Decimal(6_000_000)),
    ("under 1 crore", Decimal(10_000_000)),
    ("under 1.5 crore", Decimal(15_000_000)),
    ("below Rs. 75 lac", Decimal(7_500_000)),
])
def test_indian_currency_expressions(text, expected):
    assert parse_query(f"flat in Pune {text}").max_price == expected


def test_between_with_unit_only_on_second_number():
    q = parse_query("flat in Pune between 50 and 80 lakh")
    assert (q.min_price, q.max_price) == (Decimal(5_000_000), Decimal(8_000_000))


def test_min_budget():
    assert parse_query("villa in Chennai above 2 crore").min_price == Decimal(20_000_000)


def test_around_gives_ten_percent_band():
    q = parse_query("apartment in Pune around 50 lakh")
    assert q.min_price == Decimal(4_500_000) and q.max_price == Decimal(5_500_000)


def test_bedroom_range_and_minimum():
    q = parse_query("2 to 3 bhk flat in Pune")
    assert (q.min_bedrooms, q.max_bedrooms) == (2, 3)
    q = parse_query("at least 3 bedrooms in Chennai")
    assert q.min_bedrooms == 3 and q.max_bedrooms is None
    q = parse_query("3+ bhk in Chennai")
    assert q.min_bedrooms == 3 and q.max_bedrooms is None


def test_bedroom_count_is_not_money():
    q = parse_query("2 bhk flat to rent in Pune")
    assert q.min_price is None and q.max_price is None and q.listing_type == "rent"


def test_rent_vs_sale_not_confused():
    assert parse_query("flat for rent in Pune under 30000").listing_type == "rent"
    assert parse_query("buy a flat in Pune under 30 lakh").listing_type == "buy"


def test_buy_with_monthly_sized_amount_warns():
    q = parse_query("buy a flat in Pune under 25000")
    assert q.listing_type == "buy" and q.warnings


def test_rent_with_sale_sized_amount_warns():
    q = parse_query("rent a flat in Pune under 1 crore")
    assert q.listing_type == "rent" and q.warnings


def test_both_buy_and_rent_asks_clarification():
    q = parse_query("buy or rent a flat in Pune")
    assert q.listing_type is None and q.warnings


def test_amount_without_listing_word_assumes_and_documents():
    q = parse_query("flat in Pune under 20000")
    assert q.listing_type == "rent" and q.assumptions


def test_locality_resolves_city():
    q = parse_query("2bhk in Gachibowli", LOCALITIES)
    assert q.locality == "Gachibowli" and q.city == "Hyderabad"


def test_furnishing_order():
    assert parse_query("unfurnished flat in Pune").furnishing == "unfurnished"
    assert parse_query("semi furnished flat in Pune").furnishing == "semi_furnished"
    assert parse_query("fully furnished flat in Pune").furnishing == "furnished"


def test_amenities():
    q = parse_query("flat in Pune with gym and swimming pool and power backup")
    assert set(q.amenities) == {"Gym", "Swimming Pool", "Power Backup"}


def test_area_range():
    q = parse_query("house in Chennai between 1000 and 1500 sq ft")
    assert (q.min_area, q.max_area) == (1000, 1500)


def test_unsupported_city_is_kept_not_ignored():
    assert parse_query("flat in Mumbai under 1 crore").city == "Mumbai"


def test_greeting_and_unclear():
    assert parse_query("hello").intent == "greeting"
    assert parse_query("blah blah").intent == "unclear"


def test_unit_k_does_not_crash_on_plain_numbers():
    q = parse_query("show me 2 flats")
    assert q.max_price is None
