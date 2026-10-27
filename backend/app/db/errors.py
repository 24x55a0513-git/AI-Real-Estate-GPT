"""Translate low-level database failures into short, safe, actionable messages (no credentials, no SQL)."""
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError

# MySQL / MariaDB server and client error numbers
_SCHEMA_MISSING = {1146, 1054}            # table / column does not exist -> migrations not applied
_ACCESS_DENIED = {1044, 1045}             # wrong user / password / privileges
_UNKNOWN_DB = {1049}                      # database does not exist
_UNREACHABLE = {2002, 2003, 2005, 2006, 2013, 2026}  # server down, wrong host/port, connection lost


def _mysql_code(exc: BaseException) -> int | None:
    orig = getattr(exc, "orig", None)
    args = getattr(orig, "args", ())
    return args[0] if args and isinstance(args[0], int) else None


def classify(exc: SQLAlchemyError) -> tuple[str, str]:
    """Return (machine_code, human_hint) for a database exception."""
    code = _mysql_code(exc)
    if code in _SCHEMA_MISSING or "no such table" in str(exc).lower():  # second clause: SQLite (tests only)
        return "schema_missing", "The database schema is missing or out of date. Run: alembic upgrade head (in the backend folder)."
    if code in _ACCESS_DENIED:
        return "access_denied", "MySQL rejected the username/password in DATABASE_URL (check backend/.env)."
    if code in _UNKNOWN_DB:
        return "database_missing", "The database named in DATABASE_URL does not exist. Create it first (see the README, step 'Create the database')."
    if code in _UNREACHABLE or isinstance(exc, OperationalError):
        return "unreachable", "Cannot connect to MySQL. Check that the MySQL service is running and that host/port in DATABASE_URL are correct."
    if isinstance(exc, DBAPIError):
        return "database_error", "A database error occurred. See the backend log for details."
    return "database_error", "A database error occurred. See the backend log for details."
