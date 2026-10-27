from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.engagement import FavoriteIds, FavoriteList
from app.services import engagement_service as svc

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=FavoriteList)
def list_favorites(user: CurrentUser, db: DbSession):
    return FavoriteList(items=svc.favorite_properties(db, user.id))


@router.get("/ids", response_model=FavoriteIds)
def ids(user: CurrentUser, db: DbSession):
    return FavoriteIds(ids=svc.favorite_ids(db, user.id))


@router.put("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def add(property_id: int, user: CurrentUser, db: DbSession) -> Response:
    if not svc.add_favorite(db, user.id, property_id):
        raise HTTPException(404, "Property not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(property_id: int, user: CurrentUser, db: DbSession) -> Response:
    svc.remove_favorite(db, user.id, property_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
