"""Test fixtures. Tests NEVER use the development database.

By default they run on an in-memory SQLite database (fast, isolated). To run them against a throw-away MySQL
schema instead, set TEST_DATABASE_URL to a database whose NAME CONTAINS 'test' (a guard enforces this).
"""
import os
from decimal import Decimal

TEST_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
if not TEST_URL.startswith("sqlite") and "test" not in TEST_URL.rsplit("/", 1)[-1].lower():
    raise RuntimeError("TEST_DATABASE_URL must point to a database whose name contains 'test'.")
os.environ["DATABASE_URL"] = TEST_URL  # overrides any real .env value on purpose
os.environ["SECRET_KEY"] = "unit-test-secret-key-unit-test-secret-key"
os.environ["ENVIRONMENT"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_db, make_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Property, PropertyAmenity, PropertyImage, User  # noqa: E402
from app.models.enums import Role  # noqa: E402
from app.core.security import hash_password  # noqa: E402

engine = make_engine(TEST_URL)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

SAMPLE = [  # city, locality, type, listing, price, sqft, beds, baths, parking, furnishing, amenities
    ("Hyderabad", "Gachibowli", "apartment", "buy", 5_800_000, 1150, 2, 2, True, "semi_furnished", ["Gym", "Lift"]),
    ("Hyderabad", "Kondapur", "apartment", "buy", 8_900_000, 1650, 3, 3, True, "unfurnished", ["Swimming Pool"]),
    ("Hyderabad", "Madhapur", "apartment", "rent", 32_000, 1200, 2, 2, True, "furnished", ["Lift"]),
    ("Hyderabad", "Kukatpally", "apartment", "rent", 18_500, 1000, 2, 2, False, "unfurnished", []),
    ("Bengaluru", "Whitefield", "villa", "buy", 13_500_000, 2800, 3, 4, True, "semi_furnished", ["Garden", "Gym"]),
    ("Pune", "Baner", "apartment", "buy", 7_900_000, 1020, 2, 2, True, "semi_furnished", ["Clubhouse"]),
]


@pytest.fixture(autouse=True)
def _schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db():
    with TestingSession() as s:
        yield s


@pytest.fixture()
def client(db):
    def _override():
        with TestingSession() as s:
            yield s
    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def properties(db):
    out = []
    for i, (city, loc, ptype, lt, price, sqft, beds, baths, parking, furn, amen) in enumerate(SAMPLE):
        p = Property(title=f"Sample {ptype} in {loc}", description="Fictional test listing for automated tests.",
                     city=city, locality=loc, property_type=ptype, listing_type=lt, price=Decimal(price),
                     area_sqft=sqft, bedrooms=beds, bathrooms=baths, has_parking=parking, furnishing=furn)
        p.amenity_rows = [PropertyAmenity(name=a) for a in amen]
        p.images = [PropertyImage(url="https://example.com/a.jpg", alt="x", position=0)]
        db.add(p)
        out.append(p)
    db.commit()
    return out


def make_user(db, email="user@example.com", password="Passw0rd!", role=Role.user, name="Test User"):
    u = User(email=email, hashed_password=hash_password(password), full_name=name, role=role.value)
    db.add(u)
    db.commit()
    return u


def login(client, email="user@example.com", password="Passw0rd!") -> dict:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def user_headers(client, db):
    make_user(db)
    return login(client)


@pytest.fixture()
def user2_headers(client, db):
    make_user(db, email="other@example.com")
    return login(client, email="other@example.com")


@pytest.fixture()
def admin_headers(client, db):
    make_user(db, email="admin@example.com", role=Role.admin, name="Admin")
    return login(client, email="admin@example.com")
