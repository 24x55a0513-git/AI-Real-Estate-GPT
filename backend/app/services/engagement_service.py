"""Favorites, inquiries and per-user summary."""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import ChatSession, Favorite, Inquiry, Property
from app.models.enums import PropertyStatus
from app.schemas.engagement import InquiryCreate


# ---------------------------------------------------------------- favorites
def add_favorite(db: Session, user_id: int, property_id: int) -> bool:
    """Idempotent. Returns False if the property doesn't exist / isn't active."""
    prop = db.get(Property, property_id)
    if not prop or prop.status != PropertyStatus.active.value:
        return False
    exists = db.scalar(select(Favorite.id).where(Favorite.user_id == user_id, Favorite.property_id == property_id))
    if not exists:
        db.add(Favorite(user_id=user_id, property_id=property_id))
        try:
            db.commit()
        except IntegrityError:  # concurrent duplicate: unique constraint protects us
            db.rollback()
    return True


def remove_favorite(db: Session, user_id: int, property_id: int) -> None:
    fav = db.scalars(select(Favorite).where(Favorite.user_id == user_id, Favorite.property_id == property_id)).first()
    if fav:
        db.delete(fav)
        db.commit()


def favorite_ids(db: Session, user_id: int) -> list[int]:
    return list(db.scalars(select(Favorite.property_id).where(Favorite.user_id == user_id)
                           .order_by(Favorite.created_at.desc(), Favorite.id.desc())).all())


def favorite_properties(db: Session, user_id: int) -> list[Property]:
    stmt = (select(Property).join(Favorite, Favorite.property_id == Property.id)
            .where(Favorite.user_id == user_id, Property.status == PropertyStatus.active.value)
            .options(selectinload(Property.images), selectinload(Property.amenity_rows))
            .order_by(Favorite.created_at.desc(), Favorite.id.desc()))
    return list(db.scalars(stmt).all())


# ---------------------------------------------------------------- inquiries
class PropertyNotFound(Exception):
    pass


def create_inquiry(db: Session, data: InquiryCreate, user_id: int | None) -> Inquiry:
    if data.property_id is not None:
        prop = db.get(Property, data.property_id)
        if not prop or prop.status != PropertyStatus.active.value:
            raise PropertyNotFound
    inquiry = Inquiry(user_id=user_id, property_id=data.property_id, name=data.name, email=data.email.lower(),
                      phone=data.phone, message=data.message)
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    return inquiry


def list_inquiries(db: Session, user_id: int | None = None, status: str | None = None,
                   limit: int = 50, offset: int = 0) -> tuple[list[Inquiry], int]:
    conds = []
    if user_id is not None:
        conds.append(Inquiry.user_id == user_id)
    if status:
        conds.append(Inquiry.status == status)
    total = db.scalar(select(func.count(Inquiry.id)).where(*conds)) or 0
    rows = db.scalars(select(Inquiry).where(*conds).options(selectinload(Inquiry.property))
                      .order_by(Inquiry.created_at.desc(), Inquiry.id.desc()).limit(limit).offset(offset)).all()
    return list(rows), total


def user_summary(db: Session, user_id: int) -> dict:
    def c(model, col):
        return db.scalar(select(func.count(model.id)).where(col == user_id)) or 0
    return {"favorites": c(Favorite, Favorite.user_id), "inquiries": c(Inquiry, Inquiry.user_id),
            "chat_sessions": c(ChatSession, ChatSession.user_id)}
