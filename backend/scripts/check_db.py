"""Diagnose the MySQL connection.   Run from the backend folder:  python -m scripts.check_db

Prints which database the app is configured to use (password hidden), whether it can connect, whether every table
exists and which Alembic revision is applied. Exit code 0 = healthy, 1 = problem (with a hint on how to fix it).
"""
from sqlalchemy.engine import make_url

from app.api.routes.health import check_database
from app.core.config import get_settings


def main() -> int:
    settings = get_settings()
    url = make_url(settings.database_url)
    print(f"Environment : {settings.environment}")
    print(f"Database    : {url.render_as_string(hide_password=True)}")
    status = check_database()
    print(f"Connection  : {status['database']}")
    print(f"Schema      : {status['schema']}" + (f"  (missing: {', '.join(status['missing_tables'])})" if status.get("missing_tables") else ""))
    print(f"Migration   : {status.get('migration') or 'n/a'}")
    if status["database"] == "ok" and status["schema"] == "ok":
        print("\nOK - the database is reachable and the schema is in place.")
        return 0
    print(f"\nPROBLEM: {status.get('detail', 'unknown')}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
