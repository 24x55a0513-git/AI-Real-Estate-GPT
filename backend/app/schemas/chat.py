from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Furnishing, ListingType, PropertyType
from app.schemas.common import Money
from app.schemas.property import PropertyOut


class SearchCriteria(BaseModel):
    """Structured criteria produced by the language parser (the assistant's 'understanding')."""
    city: str | None = None
    locality: str | None = None
    listing_type: ListingType | None = None
    property_types: list[PropertyType] = Field(default_factory=list)
    min_price: Money | None = None
    max_price: Money | None = None
    min_bedrooms: int | None = Field(default=None, ge=0, le=20)
    max_bedrooms: int | None = Field(default=None, ge=0, le=20)
    min_bathrooms: int | None = Field(default=None, ge=0, le=20)
    min_area: int | None = Field(default=None, ge=0)
    max_area: int | None = Field(default=None, ge=0)
    has_parking: bool | None = None
    furnishing: Furnishing | None = None
    amenities: list[str] = Field(default_factory=list, max_length=15)
    sort: str | None = Field(default=None, pattern="^(newest|price_asc|price_desc)$")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: int | None = Field(default=None, gt=0)
    # criteria from the previous turn, so short follow-ups ("with parking") refine the search
    context_criteria: SearchCriteria | None = None
    # when set (e.g. user clicked "relax budget"), skip parsing and run exactly these criteria
    criteria_override: SearchCriteria | None = None


class Suggestion(BaseModel):
    label: str
    criteria: SearchCriteria
    match_count: int


class PropertyMatch(BaseModel):
    property: PropertyOut
    reasons: list[str]


class ChatResponse(BaseModel):
    session_id: int | None
    intent: str
    reply: str
    parser: str = "rule-based"
    criteria: SearchCriteria
    matches: list[PropertyMatch]
    total_matches: int
    suggestions: list[Suggestion] = []
    assumptions: list[str] = []
    warnings: list[str] = []
    compare_ids: list[int] = []


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    criteria: dict | None
    property_ids: list[int] | None
    created_at: datetime


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    updated_at: datetime


class ChatSessionDetail(ChatSessionOut):
    messages: list[ChatMessageOut]


class AdminStats(BaseModel):
    total_properties: int
    active_properties: int
    sale_listings: int
    rental_listings: int
    inactive_properties: int
    total_users: int
    total_inquiries: int
    new_inquiries: int
    by_city: dict[str, int]
    by_type: dict[str, int]
