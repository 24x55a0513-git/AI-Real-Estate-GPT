"""Boundary for FUTURE, legitimate property-data integrations (a licensed listings API, a partner CSV export, ...).

Nothing here talks to any external service and nothing in the running API imports this module. The design rule:
real listings enter the system through an *adapter* that yields already-validated ``PropertyCreate`` records, and
``import_feed`` stores them in MySQL. The website and the assistant keep reading only from MySQL, so a provider
outage, key limit or price plan can never break core search, and demo data (``is_demo=True``) stays separable from
real data (``is_demo=False``).

To integrate a provider later: implement ``PropertyFeed`` (``name`` + ``fetch()``), map the provider's fields to
``PropertyCreate``, make sure you are licensed to display the data and photos, then call ``import_feed``.
"""
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Property
from app.repositories.property_repository import PropertyRepository
from app.schemas.property import PropertyCreate


class PropertyFeed(Protocol):
    name: str

    def fetch(self) -> Iterable[PropertyCreate]: ...


@dataclass
class ImportReport:
    created: int = 0
    skipped_existing: int = 0
    rejected: list[str] = field(default_factory=list)


def import_feed(db: Session, feed: PropertyFeed, created_by: int | None = None) -> ImportReport:
    """Store every new record of ``feed``. Repeatable: a record whose (title, city, locality) already exists among
    real (non-demo) listings is skipped. Records flagged ``is_demo`` are rejected: demo data comes from the seed script."""
    report = ImportReport()
    repo = PropertyRepository(db)
    for record in feed.fetch():
        label = f"{record.title} ({record.locality}, {record.city})"
        if record.is_demo:
            report.rejected.append(f"{label}: feeds must not supply demo listings")
            continue
        exists = db.scalar(select(func.count(Property.id)).where(
            Property.is_demo.is_(False), Property.title == record.title, Property.city == record.city,
            Property.locality == record.locality))
        if exists:
            report.skipped_existing += 1
            continue
        repo.create(record, created_by=created_by)
        report.created += 1
    return report
