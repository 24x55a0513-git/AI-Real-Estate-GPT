from decimal import ROUND_HALF_UP, Decimal

from app.models import Property
from app.schemas.property import CompareItem, CompareResult, PropertyOut


def price_per_sqft(prop: Property) -> Decimal | None:
    """Price / area, or None when the area is missing or not positive (never divides by zero)."""
    if not prop.area_sqft or prop.area_sqft <= 0 or prop.price is None:
        return None
    return (Decimal(prop.price) / Decimal(prop.area_sqft)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_comparison(props: list[Property]) -> CompareResult:
    items = [CompareItem(property=PropertyOut.model_validate(p), price_per_sqft=price_per_sqft(p)) for p in props]
    notes: list[str] = []

    mixed = len({p.listing_type for p in props}) > 1
    if mixed:
        notes.append("These listings mix sale prices and monthly rents, so price comparisons are not like-for-like.")
    if any(i.price_per_sqft is None for i in items):
        notes.append("Price per sq ft is unavailable for listings with no valid area.")
    notes.append("Comparison shows listed data only. It is not investment advice and does not predict value changes.")

    def best(key, pick=min):
        valid = [(key(p), p.id) for p in props if key(p) is not None]
        return pick(valid)[1] if valid and not mixed else None

    fields = {
        "city": lambda p: p.city, "locality": lambda p: p.locality, "property_type": lambda p: p.property_type,
        "listing_type": lambda p: p.listing_type, "price": lambda p: p.price, "area_sqft": lambda p: p.area_sqft,
        "bedrooms": lambda p: p.bedrooms, "bathrooms": lambda p: p.bathrooms, "has_parking": lambda p: p.has_parking,
        "furnishing": lambda p: p.furnishing, "amenities": lambda p: tuple(sorted(p.amenities)),
    }
    differing = [name for name, fn in fields.items() if len({fn(p) for p in props}) > 1]
    return CompareResult(
        items=items,
        lowest_price_id=best(lambda p: p.price),
        lowest_price_per_sqft_id=best(price_per_sqft),
        largest_area_id=best(lambda p: p.area_sqft, max) if props else None,
        differing_fields=differing, notes=notes)
