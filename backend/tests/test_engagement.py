"""Favorites, inquiries and the Real Estate GPT assistant (database-backed)."""
from tests.conftest import SAMPLE


def chat(client, message, headers=None, **extra):
    r = client.post("/api/chat/message", json={"message": message, **extra}, headers=headers or {})
    assert r.status_code == 200, r.text
    return r.json()


def localities(resp):
    return sorted(m["property"]["locality"] for m in resp["matches"])


# ------------------------------------------------------------------ favorites
def test_favorites_require_auth(client, properties):
    assert client.get("/api/favorites").status_code == 401
    assert client.put(f"/api/favorites/{properties[0].id}").status_code == 401
    assert client.delete(f"/api/favorites/{properties[0].id}").status_code == 401


def test_favorite_add_list_remove_and_no_duplicates(client, properties, user_headers):
    pid = properties[0].id
    assert client.put(f"/api/favorites/{pid}", headers=user_headers).status_code == 204
    assert client.put(f"/api/favorites/{pid}", headers=user_headers).status_code == 204  # idempotent
    assert client.get("/api/favorites/ids", headers=user_headers).json()["ids"] == [pid]
    items = client.get("/api/favorites", headers=user_headers).json()["items"]
    assert [i["id"] for i in items] == [pid]
    assert client.delete(f"/api/favorites/{pid}", headers=user_headers).status_code == 204
    assert client.get("/api/favorites/ids", headers=user_headers).json()["ids"] == []


def test_favorite_unknown_property_404(client, user_headers):
    assert client.put("/api/favorites/99999", headers=user_headers).status_code == 404


def test_favorites_are_private_per_user(client, properties, user_headers, user2_headers):
    client.put(f"/api/favorites/{properties[0].id}", headers=user_headers)
    assert client.get("/api/favorites/ids", headers=user2_headers).json()["ids"] == []


def test_favorites_persist_in_database(client, db, properties, user_headers):
    from app.models import Favorite
    client.put(f"/api/favorites/{properties[1].id}", headers=user_headers)
    assert db.query(Favorite).count() == 1


# ------------------------------------------------------------------ inquiries
INQ = {"name": "Asha Rao", "email": "asha@example.com", "phone": "+91 98765 43210",
       "message": "I would like to know more about this property."}


def test_anonymous_inquiry_saved(client, db, properties):
    from app.models import Inquiry
    r = client.post("/api/inquiries", json={**INQ, "property_id": properties[0].id})
    assert r.status_code == 201 and r.json()["status"] == "new"
    assert db.query(Inquiry).one().user_id is None


def test_inquiry_validation(client, properties):
    for patch in ({"name": "A"}, {"email": "bad"}, {"message": "short"}, {"phone": "abc"}, {"property_id": 0}):
        assert client.post("/api/inquiries", json={**INQ, **patch}).status_code == 422, patch
    assert client.post("/api/inquiries", json={**INQ, "property_id": 99999}).status_code == 404


def test_inquiry_history_is_private(client, properties, user_headers, user2_headers):
    client.post("/api/inquiries", json={**INQ, "property_id": properties[0].id}, headers=user_headers)
    mine = client.get("/api/inquiries/mine", headers=user_headers).json()
    assert len(mine) == 1 and mine[0]["property_title"] == properties[0].title
    assert client.get("/api/inquiries/mine", headers=user2_headers).json() == []
    assert client.get("/api/inquiries/mine").status_code == 401


def test_admin_sees_and_updates_inquiries(client, properties, user_headers, admin_headers):
    iid = client.post("/api/inquiries", json=INQ, headers=user_headers).json()["id"]
    assert client.get("/api/admin/inquiries", headers=user_headers).status_code == 403
    assert len(client.get("/api/admin/inquiries", headers=admin_headers).json()) == 1
    r = client.patch(f"/api/admin/inquiries/{iid}", json={"status": "contacted"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["status"] == "contacted"
    assert client.patch(f"/api/admin/inquiries/{iid}", json={"status": "bogus"}, headers=admin_headers).status_code == 422


def test_user_summary(client, properties, user_headers):
    client.put(f"/api/favorites/{properties[0].id}", headers=user_headers)
    client.post("/api/inquiries", json=INQ, headers=user_headers)
    assert client.get("/api/users/me/summary", headers=user_headers).json() == {
        "favorites": 1, "inquiries": 1, "chat_sessions": 0}


# ------------------------------------------------------------------ assistant
def test_assistant_buy_query_returns_database_records(client, properties):
    r = chat(client, "Find a 2BHK apartment in Hyderabad under ₹60 lakh with parking.")
    assert r["parser"] == "rule-based" and r["intent"] == "search"
    c = r["criteria"]
    assert c["city"] == "Hyderabad" and c["property_types"] == ["apartment"] and c["has_parking"] is True
    assert c["min_bedrooms"] == c["max_bedrooms"] == 2 and c["max_price"] == 6_000_000
    assert r["total_matches"] == 1 and localities(r) == ["Gachibowli"]
    m = r["matches"][0]
    assert m["property"]["id"] == properties[0].id and "Parking available" in m["reasons"]
    assert any("within your budget" in x for x in m["reasons"])


def test_assistant_rent_query_not_confused_with_sale(client, properties):
    r = chat(client, "Find a rental flat in Hyderabad under ₹25,000 per month.")
    assert r["criteria"]["listing_type"] == "rent" and localities(r) == ["Kukatpally"]


def test_assistant_villas_between_range(client, properties):
    r = chat(client, "Show villas in Bengaluru between ₹80 lakh and ₹1.5 crore.")
    assert localities(r) == ["Whitefield"]


def test_assistant_no_matches_suggests_relaxations(client, properties):
    r = chat(client, "2BHK apartment in Hyderabad under ₹30 lakh")
    assert r["total_matches"] == 0 and r["matches"] == []
    assert "couldn't find any matching demo properties" in r["reply"]
    assert r["suggestions"] and all(s["match_count"] > 0 for s in r["suggestions"])
    # clicking a suggestion re-runs the exact relaxed criteria against the database
    follow = chat(client, r["suggestions"][0]["label"], criteria_override=r["suggestions"][0]["criteria"])
    assert follow["total_matches"] == r["suggestions"][0]["match_count"]


def test_assistant_never_invents_listings_for_unsupported_city(client, properties):
    r = chat(client, "flat in Mumbai under 1 crore")
    assert r["matches"] == [] and "no listings in Mumbai" in r["reply"]


def test_assistant_compare_uses_previous_context(client, properties):
    first = chat(client, "Show apartments in Hyderabad to buy")
    assert first["total_matches"] == 2
    r = chat(client, "Compare the cheapest matching properties", context_criteria=first["criteria"])
    assert r["intent"] == "compare" and r["compare_ids"] == [properties[0].id, properties[1].id]
    cmp = client.get("/api/properties/compare", params={"ids": ",".join(map(str, r["compare_ids"]))})
    assert cmp.status_code == 200


def test_assistant_compare_without_context_asks_for_search(client, properties):
    r = chat(client, "Compare the cheapest matching properties")
    assert r["compare_ids"] == [] and "search for first" in r["reply"]


def test_assistant_follow_up_refines_previous_search(client, properties):
    first = chat(client, "apartments in Hyderabad to buy")
    r = chat(client, "with a swimming pool", context_criteria=first["criteria"])
    assert localities(r) == ["Kondapur"] and r["criteria"]["city"] == "Hyderabad"


def test_assistant_ambiguous_and_greeting(client, properties):
    assert chat(client, "buy or rent a flat in Pune")["intent"] == "clarify"
    assert chat(client, "hello")["intent"] == "greeting"
    assert chat(client, "asdf qwer")["intent"] == "unclear"
    warn = chat(client, "buy a flat in Pune under 25000")
    assert warn["warnings"]


def test_assistant_input_validation(client):
    assert client.post("/api/chat/message", json={"message": ""}).status_code == 422
    assert client.post("/api/chat/message", json={"message": "x" * 1001}).status_code == 422


def test_assistant_ignores_inactive_properties(client, properties, admin_headers):
    client.patch(f"/api/admin/properties/{properties[0].id}/status", json={"status": "inactive"}, headers=admin_headers)
    r = chat(client, "2BHK apartment in Hyderabad under ₹60 lakh")
    assert r["total_matches"] == 0


def test_chat_history_persisted_and_isolated(client, properties, user_headers, user2_headers):
    r = chat(client, "Find a 2BHK apartment in Hyderabad under ₹60 lakh", headers=user_headers)
    sid = r["session_id"]
    assert sid is not None
    chat(client, "with parking", headers=user_headers, session_id=sid, context_criteria=r["criteria"])
    detail = client.get(f"/api/chat/sessions/{sid}", headers=user_headers).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant", "user", "assistant"]
    assert len(client.get("/api/chat/sessions", headers=user_headers).json()) == 1
    # another user cannot read, write to, or delete it
    assert client.get(f"/api/chat/sessions/{sid}", headers=user2_headers).status_code == 404
    assert client.get("/api/chat/sessions", headers=user2_headers).json() == []
    assert client.post("/api/chat/message", json={"message": "hi", "session_id": sid},
                       headers=user2_headers).status_code == 404
    assert client.delete(f"/api/chat/sessions/{sid}", headers=user2_headers).status_code == 404
    assert client.delete(f"/api/chat/sessions/{sid}", headers=user_headers).status_code == 204


def test_anonymous_chat_is_not_persisted(client, db, properties):
    from app.models import ChatMessage
    assert chat(client, "flat in Pune under 1 crore")["session_id"] is None
    assert db.query(ChatMessage).count() == 0


def test_sample_data_sanity():
    assert len(SAMPLE) == 6
