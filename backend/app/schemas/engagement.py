from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import InquiryStatus
from app.schemas.property import PropertyOut
from app.schemas.user import _check_phone


class InquiryCreate(BaseModel):
    property_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = None
    message: str = Field(min_length=10, max_length=2000)
    _ph = field_validator("phone")(_check_phone)

    @field_validator("name", "message")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class InquiryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    property_id: int | None
    property_title: str | None = None
    name: str
    email: EmailStr
    phone: str | None
    message: str
    status: InquiryStatus
    created_at: datetime


class InquiryStatusUpdate(BaseModel):
    status: InquiryStatus


class FavoriteIds(BaseModel):
    ids: list[int]


class FavoriteList(BaseModel):
    items: list[PropertyOut]
