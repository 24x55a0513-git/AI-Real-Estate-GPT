"""Create (or promote) the first administrator.   Run from the backend folder:  python -m scripts.create_admin

The e-mail/password come from ADMIN_EMAIL / ADMIN_PASSWORD environment variables, or are prompted for
interactively. Nothing is hard-coded. Use --promote to turn an existing user into an admin.
"""
import argparse
import os
from getpass import getpass

from pydantic import ValidationError

from app.db.session import SessionLocal
from app.models.enums import Role
from app.schemas.user import RegisterRequest
from app.services.auth_service import get_user_by_email, register_user

ap = argparse.ArgumentParser()
ap.add_argument("--promote", action="store_true", help="promote an existing user instead of creating one")
args = ap.parse_args()

email = os.getenv("ADMIN_EMAIL") or input("Admin e-mail: ").strip()
with SessionLocal() as db:
    existing = get_user_by_email(db, email)
    if args.promote:
        if not existing:
            raise SystemExit(f"No user with e-mail {email}.")
        existing.role = Role.admin.value
        db.commit()
        print(f"{email} is now an administrator.")
    else:
        if existing:
            raise SystemExit("That e-mail already exists. Re-run with --promote to make it an admin.")
        password = os.getenv("ADMIN_PASSWORD") or getpass("Admin password (min 8 chars, letters + digits): ")
        name = os.getenv("ADMIN_NAME", "Administrator")
        try:
            register_user(db, RegisterRequest(email=email, password=password, full_name=name), role=Role.admin)
        except ValidationError as exc:
            raise SystemExit("Invalid input: " + "; ".join(e["msg"] for e in exc.errors()))
        print(f"Administrator {email} created.")
