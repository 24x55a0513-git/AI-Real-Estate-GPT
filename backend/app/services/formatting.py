from decimal import Decimal


def format_inr(amount: Decimal | int | float, listing_type: str | None = None) -> str:
    """Human-friendly INR: ₹1.5 crore, ₹60 lakh, ₹25,000 (+ '/month' for rent)."""
    value = Decimal(str(amount))
    suffix = "/month" if listing_type == "rent" else ""
    if listing_type == "rent" or value < Decimal(100_000):
        return f"₹{int(value):,}{suffix}"
    if value >= Decimal(10_000_000):
        n, unit = value / Decimal(10_000_000), "crore"
    else:
        n, unit = value / Decimal(100_000), "lakh"
    text = f"{n:.2f}".rstrip("0").rstrip(".")
    return f"₹{text} {unit}{suffix}"
