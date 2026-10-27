from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core.security import hash_password, verify_password
from app.schemas.user import PasswordChange, ProfileUpdate, UserOut, UserSummary
from app.services import engagement_service

router = APIRouter(prefix="/users/me", tags=["users"])


@router.patch("", response_model=UserOut)
def update_profile(data: ProfileUpdate, user: CurrentUser, db: DbSession):
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: PasswordChange, user: CurrentUser, db: DbSession) -> Response:
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.hashed_password = hash_password(data.new_password)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary", response_model=UserSummary)
def summary(user: CurrentUser, db: DbSession):
    return engagement_service.user_summary(db, user.id)
