from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User
from app.models.enums import ListingType, Furnishing, PropertyStatus, PropertyType, Role
from app.schemas.property import PropertyFilters

bearer = HTTPBearer(auto_error=False, description="Paste the access_token returned by /api/auth/login")
DbSession = Annotated[Session, Depends(get_db)]


def _user_from_credentials(creds: HTTPAuthorizationCredentials | None, db: Session) -> User | None:
    if creds is None:
        return None
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        return None
    user = db.get(User, user_id)
    return user if user and user.is_active else None


def get_optional_user(db: DbSession, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User | None:
    return _user_from_credentials(creds, db)


def get_current_user(db: DbSession, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    user = _user_from_credentials(creds, db)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated or session expired",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != Role.admin.value:  # authorisation decided on the server, from the database row
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator access required")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
AdminUser = Annotated[User, Depends(require_admin)]


def get_filters(
    city: str | None = Query(None, max_length=60), locality: str | None = Query(None, max_length=120),
    q: str | None = Query(None, max_length=100, description="Keyword search"),
    listing_type: ListingType | None = None,
    property_type: list[PropertyType] = Query(default=[]),
    min_price: float | None = Query(None, ge=0), max_price: float | None = Query(None, ge=0),
    bedrooms: int | None = Query(None, ge=0, le=20, description="Minimum bedrooms"),
    bathrooms: int | None = Query(None, ge=0, le=20, description="Minimum bathrooms"),
    min_area: int | None = Query(None, ge=0), max_area: int | None = Query(None, ge=0),
    amenity: list[str] = Query(default=[], max_length=15), has_parking: bool | None = None,
    furnishing: Furnishing | None = None, status_: PropertyStatus | None = Query(None, alias="status"),
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc)$"),
    page: int = Query(1, ge=1, le=10_000), page_size: int = Query(12, ge=1, le=50),
) -> PropertyFilters:
    try:
        return PropertyFilters(
            city=city, locality=locality, q=q, listing_type=listing_type, property_types=property_type,
            min_price=min_price, max_price=max_price, min_bedrooms=bedrooms, min_bathrooms=bathrooms,
            min_area=min_area, max_area=max_area, amenities=amenity, has_parking=has_parking,
            furnishing=furnishing, status=status_, sort=sort, page=page, page_size=page_size)
    except ValidationError as exc:
        msg = "; ".join(e["msg"].removeprefix("Value error, ") for e in exc.errors())
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, msg) from exc
