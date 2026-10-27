from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.models.enums import Furnishing, ListingType, PropertyStatus, PropertyType
from app.schemas.common import Money


class ImageIn(BaseModel):
    url: HttpUrl
    alt: str | None = Field(default=None, max_length=200)


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    url: str
    alt: str | None


class PropertyBase(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    city: str = Field(min_length=2, max_length=60)
    locality: str = Field(min_length=2, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    property_type: PropertyType
    listing_type: ListingType
    price: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    area_sqft: int = Field(gt=0, le=10_000_000)
    bedrooms: int = Field(default=0, ge=0, le=20)
    bathrooms: int = Field(default=0, ge=0, le=20)
    has_parking: bool = False
    furnishing: Furnishing | None = None
    amenities: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("title", "city", "locality")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("amenities")
    @classmethod
    def _clean_amenities(cls, v: list[str]) -> list[str]:
        seen, out = set(), []
        for a in v:
            a = a.strip()
            if not a or len(a) > 60:
                raise ValueError("Amenity names must be 1-60 characters")
            if a.lower() not in seen:
                seen.add(a.lower())
                out.append(a)
        return out


class PropertyCreate(PropertyBase):
    status: PropertyStatus = PropertyStatus.active
    is_demo: bool = False
    images: list[ImageIn] = Field(default_factory=list, max_length=10)


class PropertyUpdate(PropertyCreate):
    """Full replacement update (PUT semantics)."""


class StatusUpdate(BaseModel):
    status: PropertyStatus


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    city: str
    locality: str
    address: str | None
    property_type: PropertyType
    listing_type: ListingType
    price: Money
    area_sqft: int
    bedrooms: int
    bathrooms: int
    has_parking: bool
    furnishing: Furnishing | None
    status: PropertyStatus
    is_demo: bool
    amenities: list[str] = []
    images: list[ImageOut] = []
    created_at: datetime


class Page(BaseModel):
    items: list[PropertyOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class PropertyFilters(BaseModel):
    """Validated search filters shared by the REST search endpoint and the chat assistant."""
    city: str | None = None
    locality: str | None = None
    q: str | None = Field(default=None, max_length=100)
    listing_type: ListingType | None = None
    property_types: list[PropertyType] = Field(default_factory=list)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    min_bedrooms: int | None = Field(default=None, ge=0, le=20)
    max_bedrooms: int | None = Field(default=None, ge=0, le=20)
    min_bathrooms: int | None = Field(default=None, ge=0, le=20)
    min_area: int | None = Field(default=None, ge=0)
    max_area: int | None = Field(default=None, ge=0)
    amenities: list[str] = Field(default_factory=list, max_length=15)
    has_parking: bool | None = None
    furnishing: Furnishing | None = None
    status: PropertyStatus | None = None  # only honoured for admin queries
    sort: str = Field(default="newest", pattern="^(newest|price_asc|price_desc)$")
    page: int = Field(default=1, ge=1, le=10_000)
    page_size: int = Field(default=12, ge=1, le=50)

    @model_validator(mode="after")
    def _ranges(self) -> "PropertyFilters":
        for lo, hi, name in ((self.min_price, self.max_price, "price"), (self.min_bedrooms, self.max_bedrooms, "bedrooms"),
                             (self.min_area, self.max_area, "area")):
            if lo is not None and hi is not None and lo > hi:
                raise ValueError(f"min_{name} cannot be greater than max_{name}")
        return self


class Facets(BaseModel):
    cities: list[str]
    localities: dict[str, list[str]]
    amenities: list[str]
    property_types: list[str]


# ------------------------------------------------------------------ comparison
class CompareItem(BaseModel):
    property: PropertyOut
    price_per_sqft: Money | None


class CompareResult(BaseModel):
    items: list[CompareItem]
    lowest_price_id: int | None
    lowest_price_per_sqft_id: int | None
    largest_area_id: int | None
    differing_fields: list[str]
    notes: list[str]
