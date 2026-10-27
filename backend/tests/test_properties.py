from decimal import Decimal

from app.services.compare_service import price_per_sqft
from app.services.formatting import format_inr
from types import SimpleNamespace

NEW_PROPERTY = {
    "title": "Test villa in Pune", "description": "A fictional villa used by automated tests.", "city": "Pune",
    "locality": "Baner", "property_type": "villa", "listing_type": "buy", "price": 12500000, "area_sqft": 2200,
    "bedrooms": 3, "bathrooms": 3, "has_parking": True, "furnishing": "furnished",
    "amenities": ["Garden", "garden", "Gym"], "images": [{"url": "https://example.com/v.jpg", "alt": "villa"}],
}


def ids(resp):
    return [i["id"] for i in resp.json()["items"]]


# ------------------------------------------------------------------ admin create/read
def test_create_requires_admin(client, user_headers, admin_headers):
    assert client.post("/api/admin/properties", json=NEW_PROPERTY).status_code == 401
    assert client.post("/api/admin/properties", json=NEW_PROPERTY, headers=user_headers).status_code == 403
    r = client.post("/api/admin/properties", json=NEW_PROPERTY, headers=admin_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["amenities"] == ["Garden", "Gym"]  # de-duplicated case-insensitively
    assert body["price"] == 12500000
    got = client.get(f"/api/properties/{body['id']}")
    assert got.status_code == 200 and got.json()["title"] == NEW_PROPERTY["title"]


def test_create_validation(client, admin_headers):
    for patch in ({"price": 0}, {"price": -5}, {"area_sqft": 0}, {"property_type": "castle"}, {"title": "x"},
                  {"bedrooms": -1}, {"images": [{"url": "not-a-url"}]}):
        r = client.post("/api/admin/properties", json={**NEW_PROPERTY, **patch}, headers=admin_headers)
        assert r.status_code == 422, patch


def test_get_missing_or_invalid_id(client):
    assert client.get("/api/properties/99999").status_code == 404
    assert client.get("/api/properties/abc").status_code == 422


# ------------------------------------------------------------------ search filters
def test_list_returns_all_active_with_pagination_meta(client, properties):
    r = client.get("/api/properties")
    assert r.status_code == 200
    b = r.json()
    assert b["total"] == 6 and b["page"] == 1 and b["total_pages"] == 1 and len(b["items"]) == 6


def test_filter_by_city_case_insensitive(client, properties):
    assert client.get("/api/properties", params={"city": "hyderabad"}).json()["total"] == 4


def test_sale_vs_rent_filter(client, properties):
    assert client.get("/api/properties", params={"listing_type": "rent"}).json()["total"] == 2
    assert client.get("/api/properties", params={"listing_type": "buy"}).json()["total"] == 4


def test_price_range(client, properties):
    r = client.get("/api/properties", params={"listing_type": "buy", "min_price": 6_000_000, "max_price": 9_000_000})
    assert sorted(i["locality"] for i in r.json()["items"]) == ["Baner", "Kondapur"]


def test_price_range_inclusive(client, properties):
    r = client.get("/api/properties", params={"max_price": 5_800_000, "listing_type": "buy"})
    assert [i["locality"] for i in r.json()["items"]] == ["Gachibowli"]


def test_min_greater_than_max_is_422(client):
    r = client.get("/api/properties", params={"min_price": 10, "max_price": 5})
    assert r.status_code == 422


def test_type_bedrooms_parking_amenity_filters(client, properties):
    assert client.get("/api/properties", params={"property_type": "villa"}).json()["total"] == 1
    assert client.get("/api/properties", params={"bedrooms": 3}).json()["total"] == 2
    assert client.get("/api/properties", params={"has_parking": "true", "city": "Hyderabad"}).json()["total"] == 3
    r = client.get("/api/properties", params={"amenity": ["Gym"]})
    assert sorted(i["locality"] for i in r.json()["items"]) == ["Gachibowli", "Whitefield"]
    r = client.get("/api/properties", params={"amenity": ["Gym", "Garden"]})
    assert [i["locality"] for i in r.json()["items"]] == ["Whitefield"]  # AND semantics


def test_area_and_keyword_filters(client, properties):
    assert client.get("/api/properties", params={"min_area": 2000}).json()["total"] == 1
    assert client.get("/api/properties", params={"q": "baner"}).json()["total"] == 1
    assert client.get("/api/properties", params={"q": "100%"}).json()["total"] == 0  # wildcard is escaped


def test_sorting(client, properties):
    low = client.get("/api/properties", params={"listing_type": "buy", "sort": "price_asc"}).json()["items"]
    assert [i["price"] for i in low] == sorted(i["price"] for i in low)
    high = client.get("/api/properties", params={"listing_type": "buy", "sort": "price_desc"}).json()["items"]
    assert high[0]["price"] == 13_500_000
    assert client.get("/api/properties", params={"sort": "bogus"}).status_code == 422


def test_pagination(client, properties):
    p1 = client.get("/api/properties", params={"page_size": 4, "page": 1, "sort": "price_asc"}).json()
    p2 = client.get("/api/properties", params={"page_size": 4, "page": 2, "sort": "price_asc"}).json()
    assert p1["total"] == p2["total"] == 6 and p1["total_pages"] == 2
    assert len(p1["items"]) == 4 and len(p2["items"]) == 2
    assert not set(i["id"] for i in p1["items"]) & set(i["id"] for i in p2["items"])
    assert client.get("/api/properties", params={"page_size": 500}).status_code == 422
    assert client.get("/api/properties", params={"page": 0}).status_code == 422


def test_empty_results(client, properties):
    r = client.get("/api/properties", params={"city": "Hyderabad", "max_price": 1000})
    assert r.status_code == 200 and r.json()["items"] == [] and r.json()["total"] == 0


def test_facets(client, properties):
    f = client.get("/api/properties/facets").json()
    assert set(f["cities"]) == {"Hyderabad", "Bengaluru", "Pune"} and "Gym" in f["amenities"]


# ------------------------------------------------------------------ admin lifecycle / visibility
def test_inactive_hidden_from_public_but_visible_to_admin(client, properties, admin_headers):
    pid = properties[0].id
    r = client.patch(f"/api/admin/properties/{pid}/status", json={"status": "inactive"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["status"] == "inactive"
    assert client.get(f"/api/properties/{pid}").status_code == 404
    assert client.get("/api/properties").json()["total"] == 5
    assert client.get(f"/api/admin/properties/{pid}", headers=admin_headers).status_code == 200
    assert client.get("/api/admin/properties", headers=admin_headers).json()["total"] == 6
    assert client.get("/api/admin/properties", params={"status": "inactive"}, headers=admin_headers).json()["total"] == 1


def test_admin_update_and_delete(client, properties, admin_headers):
    pid = properties[0].id
    r = client.put(f"/api/admin/properties/{pid}", json={**NEW_PROPERTY, "title": "Renamed listing"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["title"] == "Renamed listing" and r.json()["city"] == "Pune"
    assert client.put("/api/admin/properties/99999", json=NEW_PROPERTY, headers=admin_headers).status_code == 404
    assert client.delete(f"/api/admin/properties/{pid}", headers=admin_headers).status_code == 204
    assert client.get(f"/api/properties/{pid}").status_code == 404
    assert client.delete(f"/api/admin/properties/{pid}", headers=admin_headers).status_code == 404


def test_admin_endpoints_enforced_on_server(client, properties, user_headers):
    pid = properties[0].id
    calls = [("get", "/api/admin/stats"), ("get", "/api/admin/properties"), ("get", "/api/admin/inquiries"),
             ("delete", f"/api/admin/properties/{pid}"), ("patch", f"/api/admin/properties/{pid}/status")]
    for method, url in calls:
        kwargs = {"json": {"status": "inactive"}} if method == "patch" else {}
        assert getattr(client, method)(url, **kwargs).status_code == 401, url
        assert getattr(client, method)(url, headers=user_headers, **kwargs).status_code == 403, url
    assert client.get(f"/api/properties/{pid}").status_code == 200  # nothing was changed


def test_admin_stats(client, properties, admin_headers):
    s = client.get("/api/admin/stats", headers=admin_headers).json()
    assert s["total_properties"] == 6 and s["sale_listings"] == 4 and s["rental_listings"] == 2
    assert s["by_city"]["Hyderabad"] == 4


# ------------------------------------------------------------------ comparison
def test_compare_two_and_price_per_sqft(client, properties):
    a, b = properties[0], properties[1]
    r = client.get("/api/properties/compare", params={"ids": f"{a.id},{b.id}"})
    assert r.status_code == 200
    body = r.json()
    ppsf = {i["property"]["id"]: i["price_per_sqft"] for i in body["items"]}
    assert ppsf[a.id] == 5043.48 and ppsf[b.id] == 5393.94  # 5.8M/1150, 8.9M/1650
    assert body["lowest_price_id"] == a.id and body["lowest_price_per_sqft_id"] == a.id
    assert body["largest_area_id"] == b.id
    assert {"price", "locality", "bedrooms"} <= set(body["differing_fields"])


def test_compare_limits_and_errors(client, properties):
    ids_ = [p.id for p in properties]
    assert client.get("/api/properties/compare", params={"ids": str(ids_[0])}).status_code == 422
    assert client.get("/api/properties/compare", params={"ids": ",".join(map(str, ids_[:5]))}).status_code == 422
    assert client.get("/api/properties/compare", params={"ids": "a,b"}).status_code == 422
    assert client.get("/api/properties/compare", params={"ids": f"{ids_[0]},99999"}).status_code == 404
    assert client.get("/api/properties/compare", params={"ids": f"{ids_[0]},{ids_[0]}"}).status_code == 422


def test_compare_mixed_sale_and_rent_adds_note(client, properties):
    r = client.get("/api/properties/compare", params={"ids": f"{properties[0].id},{properties[2].id}"}).json()
    assert r["lowest_price_id"] is None and any("not like-for-like" in n for n in r["notes"])


def test_price_per_sqft_handles_missing_or_zero_area():
    assert price_per_sqft(SimpleNamespace(price=Decimal(1000), area_sqft=0)) is None
    assert price_per_sqft(SimpleNamespace(price=Decimal(1000), area_sqft=None)) is None
    assert price_per_sqft(SimpleNamespace(price=Decimal(1000), area_sqft=3)) == Decimal("333.33")


def test_format_inr():
    assert format_inr(6_000_000) == "₹60 lakh"
    assert format_inr(15_000_000) == "₹1.5 crore"
    assert format_inr(25_000, "rent") == "₹25,000/month"
    assert format_inr(8_500_000) == "₹85 lakh"
