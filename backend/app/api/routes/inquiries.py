from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.engagement import InquiryCreate, InquiryOut
from app.services import engagement_service as svc

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


def to_out(i) -> InquiryOut:
    out = InquiryOut.model_validate(i)
    out.property_title = i.property.title if i.property else None
    return out


@router.post("", response_model=InquiryOut, status_code=status.HTTP_201_CREATED,
             summary="Submit an inquiry (stored in the database; no e-mail is sent)")
def create(data: InquiryCreate, db: DbSession, user: CurrentUser):
    try:
        inquiry = svc.create_inquiry(db, data, user.id)
    except svc.PropertyNotFound:
        raise HTTPException(404, "Property not found")
    return to_out(inquiry)


@router.get("/mine", response_model=list[InquiryOut])
def mine(user: CurrentUser, db: DbSession, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    rows, _ = svc.list_inquiries(db, user_id=user.id, limit=limit, offset=offset)
    return [to_out(i) for i in rows]
