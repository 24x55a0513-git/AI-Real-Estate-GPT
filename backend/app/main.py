import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import admin, auth, chat, favorites, health, inquiries, properties, users
from app.core.config import get_settings
from app.db.errors import classify

logger = logging.getLogger("realestate")
if not logger.handlers:  # uvicorn only configures its own loggers; give ours a visible INFO console handler
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s:     [realestate] %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)
    logger.propagate = False
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Log (never crash on) the real database state at startup, so a missing MySQL is obvious in the console."""
    if settings.secret_key.startswith("CHANGE_ME"):
        logger.warning("SECRET_KEY is still the placeholder from .env.example. Generate a random one before sharing this app.")
    try:
        status = health.check_database()
        if status["database"] == "ok" and status["schema"] == "ok":
            logger.info("Database OK (all tables present, migration %s).", status.get("migration") or "unknown")
        else:
            logger.error("Database NOT ready: %s", status.get("detail") or status)
    except Exception:  # noqa: BLE001 - startup must never fail because of a diagnostic
        logger.exception("Could not run the startup database check")
    yield


app = FastAPI(
    title="Real Estate GPT API",
    version="1.0.0",
    description=("API for the Real Estate GPT demo platform. All listings are **fictional demonstration data**. "
                 "The assistant uses rule-based language parsing, not a large language model."),
    docs_url="/docs", redoc_url="/redoc", lifespan=lifespan,
)


# --------------------------------------------------------------------------- error handling
# Why this matters for CORS: Starlette's outermost layer (ServerErrorMiddleware) answers any *unhandled* exception
# itself, OUTSIDE the CORS middleware, so such a 500 carries no Access-Control-Allow-Origin header and the browser
# reports "blocked by CORS policy" instead of the real problem (e.g. MySQL is down or the tables do not exist).
# Two defences: (1) a handler for database errors, which runs inside the CORS layer, and (2) a catch-all middleware
# that is registered FIRST (= innermost), so even unexpected errors are turned into a normal JSON response that the
# CORS middleware then decorates.
@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    code, hint = classify(exc)
    logger.error("Database error on %s %s: %s (%s)", request.method, request.url.path, code, exc.__class__.__name__)
    return JSONResponse(status_code=503, content={"detail": hint, "code": code})


@app.middleware("http")
async def catch_unhandled(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:  # noqa: BLE001
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)  # details stay in server logs
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,                  # explicit allow-list, never "*"
    allow_origin_regex=settings.effective_cors_origin_regex,  # dev: any localhost port. production: none unless configured
    allow_credentials=False,  # bearer tokens are sent in the Authorization header, not cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):  # registered last = outermost: applies to every response
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/api"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


for r in (health.router, auth.router, users.router, properties.router, favorites.router, inquiries.router,
          chat.router, admin.router):
    app.include_router(r, prefix="/api")


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"name": "Real Estate GPT API", "docs": "/docs", "health": "/api/health"}
