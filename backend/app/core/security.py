"""Password hashing (bcrypt) and JWT helpers."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

# A valid bcrypt hash used to keep login timing similar when the e-mail does not exist.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str | None) -> bool:
    """Constant-ish time: always performs one bcrypt comparison, even for unknown users."""
    try:
        ok = bcrypt.checkpw(password.encode("utf-8"), (hashed or _DUMMY_HASH).encode("utf-8"))
    except ValueError:
        return False
    return ok and hashed is not None


def create_access_token(user_id: int) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    s = get_settings()
    now = datetime.now(timezone.utc)
    expires = timedelta(minutes=s.access_token_expire_minutes)
    payload = {"sub": str(user_id), "iat": now, "exp": now + expires}
    return jwt.encode(payload, s.secret_key, algorithm=s.jwt_algorithm), int(expires.total_seconds())


def decode_access_token(token: str) -> int | None:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.secret_key, algorithms=[s.jwt_algorithm], options={"require": ["exp", "sub"]})
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return None
