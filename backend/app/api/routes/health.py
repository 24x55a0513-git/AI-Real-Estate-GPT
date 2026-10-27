import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.api.deps import DbSession
from app.core.config import get_settings
from app.db.base import Base
from app.db.errors import classify

logger = logging.getLogger("realestate")
router = APIRouter(tags=["health"])


def check_database(db=None) -> dict:
    """Really talk to the database: connect, run SELECT 1, and confirm every application table exists.

    Returns a dict that never contains credentials. ``database`` is ok/unavailable, ``schema`` is ok/missing/unknown.
    """
    from app.db.session import SessionLocal  # local import: lets tests override the dependency instead

    own = db is None
    session = db or SessionLocal()
    result: dict = {"database": "unavailable", "schema": "unknown", "migration": None}
    try:
        session.execute(text("SELECT 1"))
        result["database"] = "ok"
        existing = set(inspect(session.get_bind()).get_table_names())
        missing = sorted(set(Base.metadata.tables) - existing)
        if missing:
            result["schema"] = "missing"
            result["missing_tables"] = missing
            result["detail"] = "Tables are missing. Run: alembic upgrade head (in the backend folder)."
        else:
            result["schema"] = "ok"
            if "alembic_version" in existing:
                result["migration"] = session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except SQLAlchemyError as exc:
        code, hint = classify(exc)
        logger.error("Health check: database problem (%s, %s)", code, exc.__class__.__name__)
        result.update(code=code, detail=hint)
    finally:
        if own:
            session.close()
    return result


@router.get("/health", summary="Liveness + REAL database connectivity and schema check")
def health(db: DbSession) -> JSONResponse:
    db_status = check_database(db)
    healthy = db_status["database"] == "ok" and db_status["schema"] == "ok"
    body = {"status": "ok" if healthy else "error", "environment": get_settings().environment, **db_status}
    return JSONResponse(status_code=200 if healthy else 503, content=body)
