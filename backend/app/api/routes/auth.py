from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_for(user) -> TokenResponse:
    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: DbSession):
    """Create a normal user account (role is always `user`; admins are created with a server-side script)."""
    try:
        user = auth_service.register_user(db, data)
    except auth_service.EmailAlreadyRegistered:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this e-mail already exists")
    return _token_for(user)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: DbSession):
    user = auth_service.authenticate(db, data.email, data.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect e-mail or password")
    return _token_for(user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(_: CurrentUser) -> Response:
    """Tokens are stateless; the client discards its token. (Server-side revocation is a documented limitation.)"""
    return Response(status_code=status.HTTP_204_NO_CONTENT)
