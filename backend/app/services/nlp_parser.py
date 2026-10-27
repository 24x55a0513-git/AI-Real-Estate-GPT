"""Rule-based natural-language parser for Indian real-estate search requests.

This module is intentionally dependency-free and does NOT touch the database. It turns free text such as
"Find a 2BHK apartment in Hyderabad under 60 lakh with parking" into a structured ``ParsedQuery``.
It is a deterministic rule-based parser, NOT a large language model.

Documented defaults (also surfaced to users via ``assumptions`` / ``warnings``):
  * A bare amount with no qualifier ("60 lakh budget") is treated as a MAXIMUM budget.
  * "around/about X" means X -10% .. X +10%.
  * "2 BHK" / "three bedrooms" means EXACTLY that many bedrooms; "at least 3 bedrooms" / "3+" means a minimum.
  * An area with no qualifier ("1,500 sq ft") is treated as a MINIMUM area.
  * With no buy/rent words, an amount below Rs 1 lakh is assumed to be monthly rent; otherwise a sale price.
  * Amounts that look inconsistent with the listing type (e.g. "buy ... under 25,000") produce a warning.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

# ----------------------------------------------------------------------------- vocabulary
CITY_ALIASES = {
    "hyderabad": "Hyderabad",
    "bengaluru": "Bengaluru", "bangalore": "Bengaluru",
    "chennai": "Chennai", "madras": "Chennai",
    "pune": "Pune",
}
# Cities we recognise but have no demo data for (so we can say so honestly instead of ignoring them).
OTHER_CITIES = ["mumbai", "delhi", "new delhi", "kolkata", "ahmedabad", "noida", "gurgaon", "gurugram",
                "jaipur", "kochi", "coimbatore", "visakhapatnam", "indore", "lucknow", "chandigarh"]

TYPE_PATTERNS = [
    ("villa", r"\bvillas?\b"),
    ("independent_house", r"\b(?:independent\s+)?(?:house|houses|bungalows?|row\s+houses?)\b"),
    ("plot", r"\b(?:plots?|land|lands)\b"),
    ("commercial", r"\b(?:commercial|offices?|shops?|showrooms?|warehouses?)\b"),
    ("apartment", r"\b(?:apartments?|flats?|condos?|condominiums?)\b"),
]

AMENITY_KEYWORDS = {
    "Swimming Pool": r"swimming\s*pool|\bpool\b",
    "Gym": r"\bgym\b|fitness\s*cent(?:re|er)",
    "24x7 Security": r"\bsecurity\b|24\s*x\s*7",
    "Lift": r"\blifts?\b|\belevators?\b",
    "Power Backup": r"power\s*backup|generator",
    "Garden": r"\bgarden\b",
    "Clubhouse": r"club\s*house",
    "Gated Community": r"gated",
    "Balcony": r"\bbalcon(?:y|ies)\b",
    "Play Area": r"play\s*area|children'?s?\s*play",
}

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
UNIT_MULTIPLIER = {
    "crore": Decimal(10_000_000), "crores": Decimal(10_000_000), "cr": Decimal(10_000_000),
    "lakh": Decimal(100_000), "lakhs": Decimal(100_000), "lac": Decimal(100_000), "lacs": Decimal(100_000),
    "thousand": Decimal(1_000), "k": Decimal(1_000),
}

MAX_WORDS = r"under|below|less\s+than|upto|up\s+to|within|maximum|max|at\s+most|not\s+more\s+than|no\s+more\s+than"
MIN_WORDS = r"above|over|more\s+than|at\s+least|atleast|minimum|min|starting\s+from|from"
APPROX_WORDS = r"around|about|approx(?:imately)?|roughly"

_NUM = r"\d+(?:,\d+)*(?:\.\d+)?"
_UNIT = r"(?:crores?|cr|lakhs?|lacs?|thousand|k)\b"
_CUR = r"(?:₹|rs\.?|inr)"

# ----------------------------------------------------------------------------- compiled patterns
AREA_RANGE_RE = re.compile(rf"(?:between\s+)?(?P<a>{_NUM})\s*(?:and|to|-|–)\s*(?P<b>{_NUM})\s*(?:sqft|sft)\b")
AREA_RE = re.compile(rf"(?:(?P<q>{MAX_WORDS}|{MIN_WORDS}|{APPROX_WORDS})\s+)?(?P<n>{_NUM})\s*(?:sqft|sft)\b")

_BED_NUM = r"\d+|one|two|three|four|five|six"
BED_RE = re.compile(
    rf"(?:(?P<q>{MAX_WORDS}|at\s+least|atleast|minimum|min|more\s+than|over)\s+)?"
    rf"(?:(?P<lo>{_BED_NUM})\s*(?:to|-|–|or)\s*)?(?P<n>{_BED_NUM})\s*(?P<plus>\+)?\s*[- ]?"
    rf"(?:bhks?|bedrooms?|beds?|br)\b")
BATH_RE = re.compile(
    rf"(?:(?P<q>{MAX_WORDS}|at\s+least|atleast|minimum|min|more\s+than|over)\s+)?"
    rf"(?P<n>{_BED_NUM})\s*\+?\s*(?:bathrooms?|baths?|washrooms?|toilets?)\b")

MONEY_RANGE_RE = re.compile(
    rf"(?P<between>between\s+)?(?P<c1>{_CUR})?\s*(?P<n1>{_NUM})\s*(?P<u1>{_UNIT})?\s*(?:and|to|-|–)\s*"
    rf"(?P<c2>{_CUR})?\s*(?P<n2>{_NUM})\s*(?P<u2>{_UNIT})?")
MONEY_RE = re.compile(
    rf"(?:(?P<q>{MAX_WORDS}|{MIN_WORDS}|{APPROX_WORDS}|budget\s+of|budget|for)\s+)?"
    rf"(?P<cur>{_CUR})?\s*(?P<n>{_NUM})\s*(?P<u>{_UNIT})?(?P<tail>\s*(?:rupees|rs|inr)\b)?")

RENT_RE = re.compile(r"\b(?:rent|rental|rentals|renting|lease|leased|per\s+month|a\s+month|monthly|/\s*month|pm)\b")
BUY_RE = re.compile(r"\b(?:buy|buying|purchase|purchasing|for\s+sale|sale|own)\b")
COMPARE_RE = re.compile(r"\b(?:compare|comparison|versus|vs)\b")
GREETING_RE = re.compile(r"^\s*(?:hi|hello|hey|namaste|help|what can you do|good\s+(?:morning|evening|afternoon))\b")


@dataclass
class ParsedQuery:
    city: str | None = None
    locality: str | None = None
    listing_type: str | None = None          # "buy" | "rent"
    property_types: list[str] = field(default_factory=list)
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    min_bedrooms: int | None = None
    max_bedrooms: int | None = None
    min_bathrooms: int | None = None
    min_area: int | None = None
    max_area: int | None = None
    has_parking: bool | None = None
    furnishing: str | None = None
    amenities: list[str] = field(default_factory=list)
    sort: str | None = None                   # "price_asc" | "price_desc" | "newest"
    intent: str = "search"                    # search | compare | greeting | unclear
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def has_criteria(self) -> bool:
        return any([self.city, self.locality, self.listing_type, self.property_types, self.min_price is not None,
                    self.max_price is not None, self.min_bedrooms is not None, self.max_bedrooms is not None,
                    self.min_bathrooms is not None, self.min_area is not None, self.max_area is not None,
                    self.has_parking, self.furnishing, self.amenities])


# ----------------------------------------------------------------------------- helpers
def _to_decimal(num: str) -> Decimal:
    return Decimal(num.replace(",", ""))


def _amount(num: str, unit: str | None) -> Decimal:
    value = _to_decimal(num)
    if unit:
        value *= UNIT_MULTIPLIER[unit.lower()]
    return value


def _word_or_int(token: str) -> int:
    return NUMBER_WORDS.get(token.lower()) or int(token)


def _norm_qual(q: str | None) -> str | None:
    if not q:
        return None
    q = re.sub(r"\s+", " ", q.strip().lower())
    if re.fullmatch(MAX_WORDS.replace(r"\s+", " "), q) or re.fullmatch(MAX_WORDS, q):
        return "max"
    if re.fullmatch(MIN_WORDS, q) or re.fullmatch(MIN_WORDS.replace(r"\s+", " "), q):
        return "min"
    if re.fullmatch(APPROX_WORDS, q):
        return "approx"
    return "budget"  # "budget", "budget of", "for"


def _mask(pattern: re.Pattern, text: str) -> str:
    return pattern.sub(" ", text)


def normalize(message: str) -> str:
    t = message.lower()
    t = t.replace("₹", " ₹ ").replace("–", "-").replace("—", "-")
    t = re.sub(r"\bsq\.?\s*(?:ft|feet|foot)\.?", "sqft", t)
    t = re.sub(r"\bsquare\s*(?:feet|foot|ft)\b", "sqft", t)
    t = re.sub(r"\bsqft\.", "sqft", t)
    t = re.sub(r"\b(\d+)\s*(?:k)\b", r"\1k", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


# ----------------------------------------------------------------------------- main entry point
def parse_query(message: str, known_localities: dict[str, tuple[str, str]] | None = None) -> ParsedQuery:
    """Parse ``message``.

    ``known_localities`` maps lower-case locality -> (canonical locality, city); it is supplied by the service
    layer (from the database) so this module stays independent of storage.
    """
    q = ParsedQuery()
    text = normalize(message)

    if COMPARE_RE.search(text):
        q.intent = "compare"

    # ---- city
    for alias, canonical in CITY_ALIASES.items():
        if re.search(rf"\b{alias}\b", text):
            q.city = canonical
            break
    if not q.city:
        for other in OTHER_CITIES:
            if re.search(rf"\b{other}\b", text):
                q.city = other.title()
                break

    # ---- locality (longest names first)
    if known_localities:
        for key in sorted(known_localities, key=len, reverse=True):
            if re.search(rf"\b{re.escape(key)}\b", text):
                canonical, city = known_localities[key]
                q.locality = canonical
                q.city = q.city or city
                break

    # ---- property type(s)
    for ptype, pattern in TYPE_PATTERNS:
        if re.search(pattern, text) and ptype not in q.property_types:
            q.property_types.append(ptype)

    # ---- furnishing (check "un/semi" first)
    if re.search(r"\bunfurnished\b", text):
        q.furnishing = "unfurnished"
    elif re.search(r"\bsemi[- ]?furnished\b", text):
        q.furnishing = "semi_furnished"
    elif re.search(r"\b(?:fully[- ]?)?furnished\b", text):
        q.furnishing = "furnished"

    # ---- parking & amenities
    if re.search(r"\bno\s+parking\b", text):
        pass
    elif re.search(r"\bparking\b|\bgarage\b|car\s*park", text):
        q.has_parking = True
    for name, pattern in AMENITY_KEYWORDS.items():
        if re.search(pattern, text):
            q.amenities.append(name)

    # ---- sort
    if re.search(r"\b(?:cheapest|lowest\s+price|least\s+expensive|lowest\s+priced)\b", text):
        q.sort = "price_asc"
    elif re.search(r"\b(?:most\s+expensive|highest\s+price|highest\s+priced)\b", text):
        q.sort = "price_desc"
    elif re.search(r"\b(?:newest|latest|most\s+recent|new\s+listings)\b", text):
        q.sort = "newest"

    # ---- area (extract + mask so numbers are not mistaken for money)
    m = AREA_RANGE_RE.search(text)
    if m:
        a, b = int(_to_decimal(m["a"])), int(_to_decimal(m["b"]))
        q.min_area, q.max_area = min(a, b), max(a, b)
    else:
        for m in AREA_RE.finditer(text):
            n = int(_to_decimal(m["n"]))
            kind = _norm_qual(m["q"])
            if kind == "max":
                q.max_area = n
            elif kind == "approx":
                q.min_area, q.max_area = int(n * Decimal("0.9")), int(n * Decimal("1.1"))
            else:
                q.min_area = n
                if kind is None:
                    q.assumptions.append(f"Treated {n:,} sq ft as a minimum area.")
    text = _mask(AREA_RANGE_RE, text)
    text = _mask(AREA_RE, text)

    # ---- bedrooms
    m = BED_RE.search(text)
    if m:
        n = _word_or_int(m["n"])
        kind = _norm_qual(m["q"])
        qual = (m["q"] or "").strip()
        if m["lo"]:
            q.min_bedrooms, q.max_bedrooms = sorted((_word_or_int(m["lo"]), n))[0], max(_word_or_int(m["lo"]), n)
        elif m["plus"] or kind == "min":
            q.min_bedrooms = n + 1 if re.match(r"(?:more\s+than|over|above)", qual) else n
        elif kind == "max":
            q.max_bedrooms = n
        else:
            q.min_bedrooms = q.max_bedrooms = n
    text = _mask(BED_RE, text)

    m = BATH_RE.search(text)
    if m:
        q.min_bathrooms = _word_or_int(m["n"])
    text = _mask(BATH_RE, text)

    # ---- listing type (from words) -----------------------------------------------------------
    wants_rent = bool(RENT_RE.search(text))
    wants_buy = bool(BUY_RE.search(text))
    if wants_rent and wants_buy:
        q.warnings.append("Your message mentions both buying and renting. Do you want to buy or rent?")
    elif wants_rent:
        q.listing_type = "rent"
    elif wants_buy:
        q.listing_type = "buy"
    text = RENT_RE.sub(" ", text)  # "per month" must not be left dangling next to numbers

    # ---- money --------------------------------------------------------------------------------
    money_found = False
    m = MONEY_RANGE_RE.search(text)
    if m:
        has_context = bool(m["between"] or m["u1"] or m["u2"] or m["c1"] or m["c2"])
        n1, n2 = _to_decimal(m["n1"]), _to_decimal(m["n2"])
        if has_context and (m["u1"] or m["u2"] or m["c1"] or m["c2"] or (n1 >= 1000 and n2 >= 1000)):
            u1, u2 = m["u1"] or m["u2"], m["u2"] or m["u1"]
            lo, hi = _amount(m["n1"], u1), _amount(m["n2"], u2)
            q.min_price, q.max_price = min(lo, hi), max(lo, hi)
            money_found = True
            text = text[:m.start()] + " " + text[m.end():]
    if not money_found:
        for m in MONEY_RE.finditer(text):
            unit, cur, tail = m["u"], m["cur"], m["tail"]
            kind = _norm_qual(m["q"])
            value = _amount(m["n"], unit)
            has_marker = bool(unit or cur or tail)
            if not has_marker and not (kind in ("max", "min", "approx", "budget") and value >= 1000):
                continue  # a bare small number such as "2" is not money
            if kind == "min":
                q.min_price = value
            elif kind == "approx":
                q.min_price, q.max_price = value * Decimal("0.9"), value * Decimal("1.1")
            else:
                q.max_price = value
                if kind is None or kind == "budget":
                    q.assumptions.append("Treated the amount as your maximum budget.")
            money_found = True
            break

    # ---- resolve / sanity-check listing type vs amount -----------------------------------------
    amount = q.max_price if q.max_price is not None else q.min_price
    if q.listing_type is None and amount is not None and not q.warnings:
        if amount < Decimal(100_000):
            q.listing_type = "rent"
            q.assumptions.append("No buy/rent given; an amount below ₹1 lakh was assumed to be monthly rent.")
        else:
            q.listing_type = "buy"
            q.assumptions.append("No buy/rent given; the amount was assumed to be a sale price.")
    elif q.listing_type == "buy" and amount is not None and amount < Decimal(100_000):
        q.warnings.append("That amount looks like a monthly rent, not a sale price. Did you mean to rent?")
    elif q.listing_type == "rent" and amount is not None and amount >= Decimal(2_000_000):
        q.warnings.append("That amount looks like a sale price, not a monthly rent. Did you mean to buy?")

    if q.intent != "compare":
        if GREETING_RE.search(text) and not q.has_criteria():
            q.intent = "greeting"
        elif not q.has_criteria():
            q.intent = "unclear"
    return q
