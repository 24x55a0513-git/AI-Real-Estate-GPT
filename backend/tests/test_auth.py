from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings
from app.models import User
from tests.conftest import make_user

REG = {"email": "new@example.com", "password": "Passw0rd!", "full_name": "New User"}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["database"] == "ok"


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"


def test_register_success_and_password_is_hashed(client, db):
    r = client.post("/api/auth/register", json=REG)
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["role"] == "user" and not any("password" in k for k in body["user"])
    stored = db.query(User).filter_by(email="new@example.com").one()
    assert stored.hashed_password != REG["password"] and stored.hashed_password.startswith("$2")


def test_register_cannot_choose_admin_role(client, db):
    r = client.post("/api/auth/register", json={**REG, "role": "admin"})
    assert r.status_code == 201 and r.json()["user"]["role"] == "user"


def test_register_duplicate_email(client):
    client.post("/api/auth/register", json=REG)
    assert client.post("/api/auth/register", json=REG).status_code == 409


def test_register_validation_errors(client):
    assert client.post("/api/auth/register", json={**REG, "email": "nope"}).status_code == 422
    assert client.post("/api/auth/register", json={**REG, "password": "short1"}).status_code == 422
    assert client.post("/api/auth/register", json={**REG, "password": "onlyletters"}).status_code == 422
    assert client.post("/api/auth/register", json={**REG, "full_name": "x"}).status_code == 422


def test_login_success_and_me(client, db):
    make_user(db)
    r = client.post("/api/auth/login", json={"email": "user@example.com", "password": "Passw0rd!"})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer" and r.json()["expires_in"] > 0
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == "user@example.com"


def test_login_invalid_credentials_are_indistinguishable(client, db):
    make_user(db)
    wrong_pw = client.post("/api/auth/login", json={"email": "user@example.com", "password": "Wrong123!"})
    no_user = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "Wrong123!"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()


def test_inactive_user_cannot_login(client, db):
    u = make_user(db)
    u.is_active = False
    db.commit()
    assert client.post("/api/auth/login", json={"email": "user@example.com", "password": "Passw0rd!"}).status_code == 401


def test_me_requires_valid_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_expired_token_rejected(client, db):
    u = make_user(db)
    s = get_settings()
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    token = jwt.encode({"sub": str(u.id), "iat": past - timedelta(hours=1), "exp": past}, s.secret_key,
                       algorithm=s.jwt_algorithm)
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_signed_with_other_secret_rejected(client, db):
    u = make_user(db)
    token = jwt.encode({"sub": str(u.id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, "x" * 40,
                       algorithm="HS256")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_logout_requires_auth(client, user_headers):
    assert client.post("/api/auth/logout").status_code == 401
    assert client.post("/api/auth/logout", headers=user_headers).status_code == 204


def test_profile_update_and_password_change(client, user_headers):
    r = client.patch("/api/users/me", headers=user_headers, json={"full_name": "Renamed User", "phone": "+91 98765 43210"})
    assert r.status_code == 200 and r.json()["full_name"] == "Renamed User"
    assert client.patch("/api/users/me", headers=user_headers, json={"phone": "abc"}).status_code == 422
    bad = client.post("/api/users/me/password", headers=user_headers,
                      json={"current_password": "nope", "new_password": "NewPassw0rd"})
    assert bad.status_code == 400
    ok = client.post("/api/users/me/password", headers=user_headers,
                     json={"current_password": "Passw0rd!", "new_password": "NewPassw0rd"})
    assert ok.status_code == 204
    assert client.post("/api/auth/login", json={"email": "user@example.com", "password": "NewPassw0rd"}).status_code == 200
