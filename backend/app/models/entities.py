from datetime import datetime
from decimal import Decimal

from sqlalchemy import (JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import InquiryStatus, ListingType, PropertyStatus, PropertyType, Role, sql_in


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(),
                                                 nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint(f"role IN ({sql_in(Role)})", name="ck_users_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(20), default=Role.user.value, server_default=Role.user.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Property(TimestampMixin, Base):
    __tablename__ = "properties"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_properties_price_positive"),
        CheckConstraint("area_sqft > 0", name="ck_properties_area_positive"),
        CheckConstraint("bedrooms >= 0 AND bathrooms >= 0", name="ck_properties_rooms_nonneg"),
        CheckConstraint(f"property_type IN ({sql_in(PropertyType)})", name="ck_properties_type"),
        CheckConstraint(f"listing_type IN ({sql_in(ListingType)})", name="ck_properties_listing_type"),
        CheckConstraint(f"status IN ({sql_in(PropertyStatus)})", name="ck_properties_status"),
        Index("ix_properties_search", "status", "city", "listing_type", "price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(60), index=True)
    locality: Mapped[str] = mapped_column(String(120), index=True)
    address: Mapped[str | None] = mapped_column(String(255))
    property_type: Mapped[str] = mapped_column(String(30), index=True)
    listing_type: Mapped[str] = mapped_column(String(10), index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2))  # INR; monthly rent when listing_type == 'rent'
    area_sqft: Mapped[int] = mapped_column(Integer)
    bedrooms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    bathrooms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    has_parking: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    furnishing: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default=PropertyStatus.active.value,
                                        server_default=PropertyStatus.active.value, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    images: Mapped[list["PropertyImage"]] = relationship(
        back_populates="property", cascade="all, delete-orphan", order_by="PropertyImage.position")
    amenity_rows: Mapped[list["PropertyAmenity"]] = relationship(
        back_populates="property", cascade="all, delete-orphan", order_by="PropertyAmenity.name")

    @property
    def amenities(self) -> list[str]:
        return [a.name for a in self.amenity_rows]


class PropertyAmenity(Base):
    __tablename__ = "property_amenities"
    __table_args__ = (UniqueConstraint("property_id", "name", name="uq_property_amenity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    property: Mapped[Property] = relationship(back_populates="amenity_rows")


class PropertyImage(Base):
    __tablename__ = "property_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(500))
    alt: Mapped[str | None] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    property: Mapped[Property] = relationship(back_populates="images")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "property_id", name="uq_favorite_user_property"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user: Mapped[User] = relationship(back_populates="favorites")
    property: Mapped[Property] = relationship()


class Inquiry(Base):
    __tablename__ = "inquiries"
    __table_args__ = (CheckConstraint(f"status IN ({sql_in(InquiryStatus)})", name="ck_inquiries_status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=InquiryStatus.new.value,
                                        server_default=InquiryStatus.new.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    property: Mapped[Property | None] = relationship()


class ChatSession(TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120), default="New chat")
    user: Mapped[User] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.id")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_messages_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    criteria: Mapped[dict | None] = mapped_column(JSON)
    property_ids: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    session: Mapped[ChatSession] = relationship(back_populates="messages")
