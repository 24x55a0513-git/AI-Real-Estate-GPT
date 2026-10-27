from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, DbSession, get_filters
from app.api.routes.inquiries import to_out
from app.models import Inquiry, User
from app.repositories.property_repository import PropertyRepository
from app.schemas.chat import AdminStats
from app.schemas.engagement import InquiryOut, InquiryStatusUpdate
from app.schemas.property import Page, PropertyCreate, PropertyFilters, PropertyOut, PropertyUpdate, StatusUpdate
from app.services import engagement_service as svc

# every route below declares the AdminUser dependency (HTTP 401 if anonymous, 403 if not an admin)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
def stats(_: AdminUser, db: DbSession):
    data = PropertyRepository(db).stats()
    data["total_users"] = db.scalar(select(func.count(User.id))) or 0
    data["total_inquiries"] = db.scalar(select(func.count(Inquiry.id))) or 0
    data["new_inquiries"] = db.scalar(select(func.count(Inquiry.id)).where(Inquiry.status == "new")) or 0
    return data


@router.get("/properties", response_model=Page, summary="All properties, any status")
def list_all(_: AdminUser, filters: Annotated[PropertyFilters, Depends(get_filters)], db: DbSession):
    repo = PropertyRepository(db)
    items, total = repo.search(filters, admin=True)
    return Page(items=[PropertyOut.model_validate(p) for p in items], total=total, page=filters.page,
                page_size=filters.page_size, total_pages=repo.total_pages(total, filters.page_size))


@router.get("/properties/{property_id}", response_model=PropertyOut)
def get_any(property_id: int, _: AdminUser, db: DbSession):
    prop = PropertyRepository(db).get(property_id, include_inactive=True)
    if prop is None:
        raise HTTPException(404, "Property not found")
    return prop


@router.post("/properties", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
def create_property(data: PropertyCreate, admin: AdminUser, db: DbSession):
    return PropertyRepository(db).create(data, created_by=admin.id)


@router.put("/properties/{property_id}", response_model=PropertyOut)
def update_property(property_id: int, data: PropertyUpdate, _: AdminUser, db: DbSession):
    repo = PropertyRepository(db)
    prop = repo.get(property_id, include_inactive=True)
    if prop is None:
        raise HTTPException(404, "Property not found")
    return repo.update(prop, data)


@router.patch("/properties/{property_id}/status", response_model=PropertyOut,
              summary="Activate / deactivate / mark sold or rented")
def set_status(property_id: int, data: StatusUpdate, _: AdminUser, db: DbSession):
    repo = PropertyRepository(db)
    prop = repo.get(property_id, include_inactive=True)
    if prop is None:
        raise HTTPException(404, "Property not found")
    return repo.set_status(prop, data.status)


@router.delete("/properties/{property_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Permanently delete (use PATCH status=inactive to merely hide)")
def delete_property(property_id: int, _: AdminUser, db: DbSession) -> Response:
    repo = PropertyRepository(db)
    prop = repo.get(property_id, include_inactive=True)
    if prop is None:
        raise HTTPException(404, "Property not found")
    repo.delete(prop)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/inquiries", response_model=list[InquiryOut])
def all_inquiries(_: AdminUser, db: DbSession, status_: str | None = Query(None, alias="status",
                  pattern="^(new|contacted|closed)$"), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    rows, _total = svc.list_inquiries(db, status=status_, limit=limit, offset=offset)
    return [to_out(i) for i in rows]


@router.patch("/inquiries/{inquiry_id}", response_model=InquiryOut)
def update_inquiry(inquiry_id: int, data: InquiryStatusUpdate, _: AdminUser, db: DbSession):
    inquiry = db.get(Inquiry, inquiry_id)
    if inquiry is None:
        raise HTTPException(404, "Inquiry not found")
    inquiry.status = data.status.value
    db.commit()
    db.refresh(inquiry)
    return to_out(inquiry)
