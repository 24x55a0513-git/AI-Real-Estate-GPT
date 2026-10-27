"""Seed FICTIONAL demonstration listings.   Run from the backend folder:  python -m scripts.seed

The script is repeatable: a listing is identified by (title, city, locality) among rows flagged is_demo, and is only
inserted when it is missing, so running it twice never creates duplicates and never touches real users' data.

Options:
  --reset            delete previously seeded demo listings first (only rows with is_demo=true). Favorites that point
                     to those listings are removed with them; inquiries keep their text (property link is cleared).
  --with-demo-users  also create two DEVELOPMENT-ONLY accounts. Only allowed when ENVIRONMENT=development. Passwords
                     come from DEMO_USER_PASSWORD / DEMO_ADMIN_PASSWORD, or are generated randomly and printed once.
"""
import argparse
import os
import secrets
import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Property, PropertyAmenity, PropertyImage, User
from app.models.enums import Role
from app.schemas.user import RegisterRequest
from app.services.auth_service import get_user_by_email, register_user

U = "https://images.unsplash.com/photo-{}?auto=format&fit=crop&w=1200&q=80"
IMG = {  # Unsplash photo ids (free to use under the Unsplash License; see README for attribution notes)
    "apartment": ["1545324418-cc1a3fa10c00", "1502672260266-1c1ef2d93688", "1522708323590-d24dbb6b0267",
                  "1560448204-e02f11c3d0e2"],
    "independent_house": ["1568605114967-8130f3a36994", "1564013799919-ab600027ffc6", "1570129477492-45c003edd2be"],
    "villa": ["1512917774080-9991f1c4c750", "1613490493576-7fde63acd811", "1600596542815-ffad4c1539a9",
              "1613977257363-707ba9348227"],
    "plot": ["1500382017468-9049fed747ef", "1472214103451-9374bd1c798e"],
    "commercial": ["1486406146926-c627a92ad1ab", "1497366216548-37526070297c"],
}
POOL, LIFT, GYM, SEC, PWR, CLUB, GARD, PLAY, GATED, BAL = (
    "Swimming Pool", "Lift", "Gym", "24x7 Security", "Power Backup", "Clubhouse", "Garden", "Play Area",
    "Gated Community", "Balcony")

# city, locality, type, listing, title, price(INR), sqft, beds, baths, parking, furnishing, amenities
ROWS = [
    ("Hyderabad", "Gachibowli", "apartment", "buy", "Bright 2BHK near the Financial District", 5_800_000, 1150, 2, 2, True, "semi_furnished", [GYM, LIFT, SEC, PWR, CLUB]),
    ("Hyderabad", "Kondapur", "apartment", "buy", "Spacious 3BHK with clubhouse access", 8_900_000, 1650, 3, 3, True, "unfurnished", [POOL, GYM, LIFT, CLUB, PLAY]),
    ("Hyderabad", "Jubilee Hills", "villa", "buy", "Luxury 4-bedroom villa with private garden", 45_000_000, 4200, 4, 5, True, "furnished", [GARD, POOL, SEC, PWR]),
    ("Hyderabad", "Madhapur", "apartment", "rent", "Modern 2BHK for rent near tech parks", 32_000, 1200, 2, 2, True, "semi_furnished", [LIFT, GYM, SEC]),
    ("Hyderabad", "Kukatpally", "apartment", "rent", "Affordable 2BHK family flat", 18_500, 1000, 2, 2, True, "unfurnished", [LIFT, PWR, BAL]),
    ("Hyderabad", "Miyapur", "plot", "buy", "Gated-community residential plot", 4_200_000, 1800, 0, 0, False, None, [GATED]),
    ("Hyderabad", "Banjara Hills", "commercial", "rent", "Furnished office floor in a prime location", 125_000, 1500, 0, 2, True, "furnished", [LIFT, PWR, SEC]),
    ("Hyderabad", "Gachibowli", "apartment", "rent", "Premium 3BHK for rent with pool access", 45_000, 1800, 3, 3, True, "furnished", [GYM, POOL, CLUB, LIFT]),
    ("Bengaluru", "Whitefield", "apartment", "buy", "3BHK in a resort-style community", 11_500_000, 1700, 3, 3, True, "semi_furnished", [POOL, GYM, CLUB, LIFT]),
    ("Bengaluru", "Indiranagar", "apartment", "rent", "Stylish 2BHK in the heart of Indiranagar", 48_000, 1100, 2, 2, True, "furnished", [LIFT, SEC, BAL]),
    ("Bengaluru", "Sarjapur Road", "villa", "buy", "3-bedroom villa in a gated layout", 9_800_000, 2000, 3, 4, True, "unfurnished", [GARD, GATED, CLUB, PLAY]),
    ("Bengaluru", "HSR Layout", "apartment", "buy", "Well-planned 2BHK close to parks", 9_200_000, 1150, 2, 2, True, "semi_furnished", [LIFT, PWR, SEC]),
    ("Bengaluru", "Koramangala", "independent_house", "buy", "4-bedroom independent house on a quiet street", 28_000_000, 3000, 4, 4, True, "unfurnished", [GARD, BAL]),
    ("Bengaluru", "Electronic City", "apartment", "rent", "Compact 1BHK for commuters", 14_000, 650, 1, 1, False, "semi_furnished", [LIFT, SEC]),
    ("Bengaluru", "Whitefield", "villa", "buy", "Contemporary 3-bedroom villa with clubhouse", 13_500_000, 2800, 3, 4, True, "semi_furnished", [POOL, GYM, GARD, CLUB]),
    ("Chennai", "Adyar", "apartment", "buy", "Neat 2BHK near the river and schools", 8_500_000, 1050, 2, 2, True, "semi_furnished", [LIFT, SEC, PWR]),
    ("Chennai", "Velachery", "apartment", "rent", "2BHK for rent close to the metro", 24_000, 1000, 2, 2, True, "unfurnished", [LIFT, PWR]),
    ("Chennai", "OMR", "villa", "buy", "Gated 4-bedroom villa off the IT corridor", 19_500_000, 3300, 4, 5, True, "furnished", [POOL, GARD, CLUB, GATED]),
    ("Chennai", "Anna Nagar", "independent_house", "buy", "Traditional 3-bedroom independent house", 16_000_000, 1800, 3, 3, True, "unfurnished", [GARD, BAL]),
    ("Chennai", "Porur", "apartment", "buy", "3BHK with gym and play area", 7_400_000, 1400, 3, 2, True, "semi_furnished", [GYM, LIFT, PLAY]),
    ("Pune", "Hinjewadi", "apartment", "rent", "Furnished-ready 2BHK near IT parks", 26_000, 1050, 2, 2, True, "semi_furnished", [GYM, LIFT, POOL]),
    ("Pune", "Baner", "apartment", "buy", "Elegant 2BHK with amenities floor", 7_900_000, 1020, 2, 2, True, "semi_furnished", [CLUB, LIFT, GYM, POOL]),
    ("Pune", "Kothrud", "independent_house", "buy", "Quiet 3-bedroom independent house", 13_800_000, 1600, 3, 3, True, "unfurnished", [GARD]),
    ("Pune", "Wakad", "plot", "buy", "Corner plot in a gated township", 5_600_000, 2000, 0, 0, False, None, [GATED]),
    ("Pune", "Viman Nagar", "commercial", "buy", "Ready-to-use office space near the airport", 18_500_000, 1200, 0, 2, True, "unfurnished", [LIFT, PWR, SEC]),
]
# Additional fictional demo listings across India.
# The original 25 rows remain unchanged.

CITY_LOCALITIES = {
    "Hyderabad": ["Gachibowli", "Kondapur", "Madhapur", "Miyapur", "Kukatpally", "Nallagandla"],
    "Bengaluru": ["Whitefield", "Electronic City", "Sarjapur Road", "HSR Layout", "Yelahanka", "Marathahalli"],
    "Chennai": ["Adyar", "Velachery", "OMR", "Porur", "Anna Nagar", "Tambaram"],
    "Mumbai": ["Andheri West", "Powai", "Thane West", "Chembur", "Kandivali", "Panvel"],
    "Pune": ["Hinjewadi", "Baner", "Wakad", "Kharadi", "Kothrud", "Hadapsar"],
    "Delhi": ["Dwarka", "Rohini", "Saket", "Vasant Kunj", "Mayur Vihar", "Pitampura"],
    "Gurugram": ["Sector 56", "Sector 65", "Golf Course Road", "Sohna Road", "Sector  Gurgaon 57"],
    "Noida": ["Sector 50", "Sector 62", "Sector 75", "Sector 137", "Greater Noida West"],
    "Kolkata": ["New Town", "Salt Lake", "Tollygunge", "Behala", "Rajarhat"],
    "Ahmedabad": ["Satellite", "Prahlad Nagar", "Bopal", "Gota", "Chandkheda"],
    "Jaipur": ["Vaishali Nagar", "Mansarovar", "Jagatpura", "Malviya Nagar"],
    "Lucknow": ["Gomti Nagar", "Indira Nagar", "Aliganj", "Sushant Golf City"],
    "Kochi": ["Kakkanad", "Edappally", "Vyttila", "Marine Drive"],
    "Visakhapatnam": ["Madhurawada", "MVP Colony", "Gajuwaka", "Rushikonda"],
    "Vijayawada": ["Benz Circle", "Poranki", "Kanuru", "Gannavaram"],
    "Coimbatore": ["Peelamedu", "Saravanampatti", "RS Puram", "Singanallur"],
    "Bhubaneswar": ["Patia", "Khandagiri", "Nayapalli", "Chandrasekharpur"],
    "Indore": ["Vijay Nagar", "Rau", "AB Road", "Super Corridor"],
    "Bhopal": ["Arera Colony", "Kolar Road", "Hoshangabad Road"],
    "Nagpur": ["Dharampeth", "Manish Nagar", "Wardha Road"],
    "Surat": ["Vesu", "Adajan", "Pal", "Piplod"],
    "Vadodara": ["Alkapuri", "Gotri", "Manjalpur"],
    "Patna": ["Kankarbagh", "Boring Road", "Danapur"],
    "Ranchi": ["Harmu", "Morabadi", "Lalpur"],
    "Guwahati": ["Beltola", "Khanapara", "Six Mile"],
    "Chandigarh": ["Sector 20", "Sector 34", "Manimajra"],
    "Dehradun": ["Rajpur Road", "Sahastradhara Road", "Clement Town"],
    "Mysuru": ["Vijayanagar", "Hebbal", "Dattagalli"],
    "Thiruvananthapuram": ["Kazhakoottam", "Pattom", "Vazhuthacaud"],
    "Nashik": ["Gangapur Road", "Indira Nagar", "Pathardi Phata"],
}

PROPERTY_TYPES = ["apartment", "independent_house", "villa", "plot", "commercial"]
LISTING_TYPES = ["buy", "rent"]

# Approximate demo prices, in INR.
CITY_BUY_BASE = {
    "Mumbai": 12_000_000,
    "Delhi": 9_000_000,
    "Gurugram": 9_000_000,
    "Noida": 6_500_000,
    "Bengaluru": 8_000_000,
    "Hyderabad": 7_000_000,
    "Chennai": 6_500_000,
    "Pune": 6_500_000,
    "Kolkata": 5_000_000,
    "Ahmedabad": 4_500_000,
}

DEFAULT_BUY_BASE = 4_000_000

TYPE_MULTIPLIER = {
    "apartment": 1.0,
    "independent_house": 1.8,
    "villa": 2.4,
    "plot": 0.7,
    "commercial": 1.5,
}

AMENITY_POOL = [POOL, LIFT, GYM, SEC, PWR, CLUB, GARD, PLAY, GATED, BAL]

def generate_additional_rows(target_total=1000):
    """Generate deterministic fictional listings, without changing the original ROWS."""
    generated = []
    used = {(row[4], row[0], row[1]) for row in ROWS}
    rng = random.Random(20261025)

    cities = sorted(CITY_LOCALITIES)
    type_names = {
        "apartment": ["Apartment", "Flat", "Residency"],
        "independent_house": ["Independent House", "Family House", "Duplex House"],
        "villa": ["Villa", "Garden Villa", "Premium Villa"],
        "plot": ["Residential Plot", "Corner Plot", "Gated Plot"],
        "commercial": ["Office Space", "Commercial Unit", "Business Property"],
    }

    while len(ROWS) + len(generated) < target_total:
        index = len(ROWS) + len(generated)
        city = cities[index % len(cities)]
        locality = CITY_LOCALITIES[city][(index // len(cities)) % len(CITY_LOCALITIES[city])]
        ptype = PROPERTY_TYPES[(index // 3) % len(PROPERTY_TYPES)]
        listing = LISTING_TYPES[(index // 2) % 2]

        title = f"{rng.choice(type_names[ptype])} {index + 1:04d} in {locality}"
        key = (title, city, locality)
        if key in used:
            continue
        used.add(key)

        beds = 0 if ptype in ("plot", "commercial") else rng.randint(1, 5)
        baths = 0 if ptype == "plot" else (rng.randint(1, 5) if beds else rng.randint(1, 3))
        sqft = rng.randrange(600, 4501, 50)

        if listing == "rent":
            if ptype == "commercial":
                price = rng.randrange(20_000, 250_001, 5_000)
            else:
                price = rng.randrange(8_000, 100_001, 1_000)
        else:
            base = CITY_BUY_BASE.get(city, DEFAULT_BUY_BASE)
            price = int(base * TYPE_MULTIPLIER[ptype] * rng.uniform(0.55, 1.8))
            price = max(500_000, round(price / 50_000) * 50_000)

        furnishing = None if ptype == "plot" else rng.choice(
            ["unfurnished", "semi_furnished", "furnished"]
        )
        amenities = rng.sample(AMENITY_POOL, k=rng.randint(2, 5))

        generated.append((
            city, locality, ptype, listing, title, price, sqft, beds, baths,
            rng.choice([True, False]), furnishing, amenities
        ))

    return generated


# Keep the original 25 records and generate only the additional 975.
ROWS.extend(generate_additional_rows(1000))

def seed_properties(db, reset: bool) -> int:
    """Insert the demo listings that are not present yet. Returns how many were created."""
    if reset:
        db.execute(delete(Property).where(Property.is_demo.is_(True)))
        db.commit()
    existing = {(t, c, loc) for t, c, loc in db.execute(
        select(Property.title, Property.city, Property.locality).where(Property.is_demo.is_(True))).all()}
    now = datetime.now()
    created = 0
    for i, (city, loc, ptype, listing, title, price, sqft, beds, baths, parking, furn, amen) in enumerate(ROWS):
        if (title, city, loc) in existing:
            continue
        photos = IMG[ptype]
        prop = Property(
            title=title, city=city, locality=loc, address=f"{loc}, {city} (approximate location)",
            description=(f"{title} in {loc}, {city}. {sqft:,} sq ft"
                         f"{f', {beds} bedrooms, {baths} bathrooms' if beds else ''}. "
                         "DEMONSTRATION LISTING: this is fictional sample data and not a real, verified property."),
            property_type=ptype, listing_type=listing, price=Decimal(price), area_sqft=sqft, bedrooms=beds,
            bathrooms=baths, has_parking=parking, furnishing=furn, is_demo=True,
            created_at=now - timedelta(days=i, hours=i), updated_at=now)
        prop.amenity_rows = [PropertyAmenity(name=a) for a in amen]
        prop.images = [PropertyImage(url=U.format(photos[(i + k) % len(photos)]), alt=f"{title} (sample image)",
                                     position=k) for k in range(min(3, len(photos)))]
        db.add(prop)
        created += 1
    db.commit()
    if created == 0:
        print("All demo listings already exist - nothing to add (use --reset to recreate them).")
    return created


def _demo_password(env_name: str) -> tuple[str, bool]:
    """Password from the environment, or a random one (letters + digits, satisfies the app's password rules)."""
    given = os.getenv(env_name)
    return (given, False) if given else (secrets.token_urlsafe(12) + "a1", True)


def seed_demo_users(db) -> None:
    if get_settings().environment.lower() != "development":
        raise SystemExit("Demo users are only created when ENVIRONMENT=development (refusing for anything else).")
    for email, name, env_name, role in (("demo.user@example.com", "Demo User", "DEMO_USER_PASSWORD", Role.user),
                                        ("demo.admin@example.com", "Demo Admin", "DEMO_ADMIN_PASSWORD", Role.admin)):
        if get_user_by_email(db, email):
            print(f"Demo account {email} already exists (password unchanged).")
            continue
        password, generated = _demo_password(env_name)
        register_user(db, RegisterRequest(email=email, password=password, full_name=name), role=role)
        shown = password if generated else f"(taken from {env_name})"
        print(f"Created DEV-ONLY {role.value}: {email}   password: {shown}")
        if generated:
            print("  ^ shown only now - copy it. Delete or change this account before any deployment.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--with-demo-users", action="store_true")
    args = ap.parse_args()
    with SessionLocal() as session:
        created = seed_properties(session, args.reset)
        if args.with_demo_users:
            seed_demo_users(session)
        total = session.scalar(select(func.count(Property.id)))
        users = session.scalar(select(func.count(User.id)))
    print(f"Seeded {created} demo properties. Totals -> properties: {total}, users: {users}.")
