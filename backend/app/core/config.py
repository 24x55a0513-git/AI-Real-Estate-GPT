"""Application settings, loaded from environment variables / ``backend/.env`` (never from source code)."""
import sys
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/  (the folder that contains app/, alembic/, .env). Resolving .env relative to THIS file means the
# settings load correctly no matter which directory uvicorn / alembic / pytest is started from.
BACKEND_DIR = Path(__file__).resolve().parents[2]

# In development the Vite dev server may land on 5173, 5174, 5175 ... (it picks the next free port), so any
# localhost / 127.0.0.1 / [::1] origin is accepted. This regex is NEVER applied in production.
DEV_CORS_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d{1,5})?$"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"
    # Comma-separated exact origins (scheme + host + port, no trailing slash).
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Optional regex of additionally allowed origins. Leave empty to use the safe default for the environment:
    # any localhost port in development/test, nothing extra in production.
    cors_origin_regex: str | None = None

    @field_validator("database_url")
    @classmethod
    def _check_database_url(cls, v: str) -> str:
        v = v.strip()
        if v.startswith("mysql://"):  # bare "mysql://" would make SQLAlchemy look for the C driver (mysqlclient)
            v = "mysql+pymysql://" + v.removeprefix("mysql://")
        if not (v.startswith("mysql+pymysql://") or v.startswith("sqlite")):  # sqlite: automated tests only
            raise ValueError("DATABASE_URL must look like mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4")
        if "CHANGE_ME" in v:
            raise ValueError("DATABASE_URL still contains the CHANGE_ME placeholder. Put your real MySQL password "
                             "in backend/.env (URL-encode special characters, e.g. @ becomes %40).")
        return v

    @field_validator("access_token_expire_minutes")
    @classmethod
    def _positive_expiry(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
        return v

    @field_validator("cors_origin_regex")
    @classmethod
    def _blank_regex_is_none(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v else None

    @model_validator(mode="after")
    def _check_production_secret(self) -> "Settings":
        if self.environment.lower() == "production":
            if len(self.secret_key) < 32 or self.secret_key.startswith("CHANGE_ME"):
                raise ValueError("SECRET_KEY must be a random string of 32+ characters in production")
            if self.cors_origin_regex and self.cors_origin_regex.strip() in (".*", "^.*$", ".+"):
                raise ValueError("CORS_ORIGIN_REGEX must not allow every origin in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_cors_origin_regex(self) -> str | None:
        if self.cors_origin_regex:
            return self.cors_origin_regex
        return None if self.is_production else DEV_CORS_ORIGIN_REGEX

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        lines = ["", "Real Estate GPT cannot start: invalid or missing configuration.", ""]
        for err in exc.errors():
            name = ".".join(str(p) for p in err["loc"]).upper() or "SETTINGS"
            msg = "is missing" if err["type"] == "missing" else err["msg"].removeprefix("Value error, ")
            lines.append(f"  - {name}: {msg}")
        lines += ["", f"Fix: copy backend/.env.example to backend/.env and edit it (expected at: {BACKEND_DIR / '.env'}).", ""]
        raise SystemExit("\n".join(lines)) from None
