"""CORS behaviour and the health endpoint (the two things behind the original "blocked by CORS policy" symptom)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db, make_engine
from app.main import app

ORIGIN = "http://localhost:5173"
VITE_FALLBACK = "http://localhost:5174"  # what Vite uses when 5173 is already taken


class _BrokenSession:
    """Behaves like a session whose MySQL server is unreachable (error 2003)."""

    def _boom(self, *args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception(2003, "Can't connect to MySQL server"))

    scalar = scalars = execute = get_bind = _boom

    def close(self):
        pass


def _broken_db():
    yield _BrokenSession()


# ------------------------------------------------------------------ CORS
def test_configured_origin_gets_cors_header(client):
    r = client.get("/api/properties/facets", headers={"Origin": ORIGIN})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == ORIGIN


@pytest.mark.parametrize("origin", [VITE_FALLBACK, "http://127.0.0.1:5199", "http://localhost:3000"])
def test_any_localhost_port_is_allowed_in_development(client, origin):
    r = client.get("/api/health", headers={"Origin": origin})
    assert r.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("origin", ["https://evil.example.com", "http://localhost.evil.com", "http://localhost:5174.evil.com"])
def test_foreign_origin_is_not_allowed(client, origin):
    r = client.get("/api/health", headers={"Origin": origin})
    assert "access-control-allow-origin" not in r.headers


def test_preflight_request_is_answered(client):
    r = client.options("/api/properties", headers={
        "Origin": VITE_FALLBACK, "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization,content-type"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == VITE_FALLBACK
    assert "authorization" in r.headers["access-control-allow-headers"].lower()


def test_error_responses_also_carry_cors_headers(client):
    not_found = client.get("/api/properties/99999", headers={"Origin": VITE_FALLBACK})
    invalid = client.get("/api/properties/abc", headers={"Origin": VITE_FALLBACK})
    unauth = client.get("/api/auth/me", headers={"Origin": VITE_FALLBACK})
    assert (not_found.status_code, invalid.status_code, unauth.status_code) == (404, 422, 401)
    for r in (not_found, invalid, unauth):
        assert r.headers["access-control-allow-origin"] == VITE_FALLBACK


def test_database_outage_is_a_503_with_cors_header_not_a_masked_error(client):
    app.dependency_overrides[get_db] = _broken_db
    r = client.get("/api/properties", headers={"Origin": VITE_FALLBACK})
    assert r.status_code == 503
    assert r.json()["code"] == "unreachable" and "MySQL" in r.json()["detail"]
    assert r.headers["access-control-allow-origin"] == VITE_FALLBACK


def test_unexpected_exception_is_generic_json_500_with_cors_header():
    def boom():
        raise RuntimeError("secret internal detail")

    app.add_api_route("/api/_boom", boom)
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.get("/api/_boom", headers={"Origin": VITE_FALLBACK})
    finally:
        app.router.routes.pop()  # remove the temporary route again
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal server error"} and "secret" not in r.text
    assert r.headers["access-control-allow-origin"] == VITE_FALLBACK


# ------------------------------------------------------------------ health
def test_health_ok_reports_real_database_and_schema(client):
    r = client.get("/api/health")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ok" and body["database"] == "ok" and body["schema"] == "ok"
    assert "password" not in r.text.lower()


def test_health_reports_database_down(client):
    app.dependency_overrides[get_db] = _broken_db
    r = client.get("/api/health", headers={"Origin": ORIGIN})
    body = r.json()
    assert r.status_code == 503
    assert body["status"] == "error" and body["database"] == "unavailable" and body["code"] == "unreachable"
    assert r.headers["access-control-allow-origin"] == ORIGIN


def test_health_reports_missing_tables(client):
    empty_engine = make_engine("sqlite+pysqlite:///:memory:")  # reachable, but no migrations applied
    session_factory = sessionmaker(bind=empty_engine)

    def _empty_db():
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = _empty_db
    r = client.get("/api/health")
    body = r.json()
    assert r.status_code == 503
    assert body["database"] == "ok" and body["schema"] == "missing" and "users" in body["missing_tables"]
    assert "alembic upgrade head" in body["detail"]
