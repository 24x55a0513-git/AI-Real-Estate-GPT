"""All SQL for properties lives here (no business rules, no HTTP)."""
from math import ceil

from sqlalchemy import String, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Property, PropertyAmenity, PropertyImage
from app.models.enums import PropertyStatus, PropertyType
from app.schemas.property import PropertyCreate, PropertyFilters

def _lower(col):
    return func.lower(col, type_=String)


_EAGER = (selectinload(Property.images), selectinload(Property.amenity_rows))


class PropertyRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ querying
    @staticmethod
    def _conditions(f: PropertyFilters, admin: bool) -> list:
        c = []
        if admin:
            if f.status:
                c.append(Property.status == f.status.value)
        else:
            c.append(Property.status == PropertyStatus.active.value)  # public never sees inactive/sold/rented
        if f.city:
            c.append(_lower(Property.city) == f.city.strip().lower())
        if f.locality:
            c.append(_lower(Property.locality).contains(f.locality.strip().lower(), autoescape=True))
        if f.q:
            term = f.q.strip().lower()
            c.append(
                _lower(Property.title).contains(term, autoescape=True)
                | _lower(Property.description).contains(term, autoescape=True)
                | _lower(Property.locality).contains(term, autoescape=True)
                | _lower(Property.city).contains(term, autoescape=True))
        if f.listing_type:
            c.append(Property.listing_type == f.listing_type.value)
        if f.property_types:
            c.append(Property.property_type.in_([t.value for t in f.property_types]))
        if f.min_price is not None:
            c.append(Property.price >= f.min_price)
        if f.max_price is not None:
            c.append(Property.price <= f.max_price)
        if f.min_bedrooms is not None:
            c.append(Property.bedrooms >= f.min_bedrooms)
        if f.max_bedrooms is not None:
            c.append(Property.bedrooms <= f.max_bedrooms)
        if f.min_bathrooms is not None:
            c.append(Property.bathrooms >= f.min_bathrooms)
        if f.min_area is not None:
            c.append(Property.area_sqft >= f.min_area)
        if f.max_area is not None:
            c.append(Property.area_sqft <= f.max_area)
        if f.has_parking:
            c.append(Property.has_parking.is_(True))
        if f.furnishing:
            c.append(Property.furnishing == f.furnishing.value)
        for name in f.amenities:
            c.append(Property.amenity_rows.any(_lower(PropertyAmenity.name) == name.strip().lower()))
        return c

    def search(self, f: PropertyFilters, admin: bool = False) -> tuple[list[Property], int]:
        conds = self._conditions(f, admin)
        total = self.db.scalar(select(func.count(Property.id)).where(*conds)) or 0
        order = {"price_asc": (Property.price.asc(), Property.id.asc()),
                 "price_desc": (Property.price.desc(), Property.id.asc()),
                 "newest": (Property.created_at.desc(), Property.id.desc())}[f.sort]
        stmt = (select(Property).where(*conds).options(*_EAGER).order_by(*order)
                .limit(f.page_size).offset((f.page - 1) * f.page_size))
        return list(self.db.scalars(stmt).all()), total

    def count(self, f: PropertyFilters) -> int:
        return self.db.scalar(select(func.count(Property.id)).where(*self._conditions(f, False))) or 0

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        return max(1, ceil(total / page_size))

    def get(self, property_id: int, include_inactive: bool = False) -> Property | None:
        stmt = select(Property).where(Property.id == property_id).options(*_EAGER)
        if not include_inactive:
            stmt = stmt.where(Property.status == PropertyStatus.active.value)
        return self.db.scalars(stmt).first()

    def get_many(self, ids: list[int]) -> list[Property]:
        if not ids:
            return []
        rows = self.db.scalars(select(Property).where(Property.id.in_(ids),
                               Property.status == PropertyStatus.active.value).options(*_EAGER)).all()
        by_id = {p.id: p for p in rows}
        return [by_id[i] for i in ids if i in by_id]  # keep requested order

    # ------------------------------------------------------------------ writes
    def create(self, data: PropertyCreate, created_by: int | None) -> Property:
        prop = Property(**data.model_dump(exclude={"amenities", "images"}, mode="python"), created_by=created_by)
        self._apply_children(prop, data)
        self.db.add(prop)
        self.db.commit()
        return self.get(prop.id, include_inactive=True)  # type: ignore[return-value]

    def update(self, prop: Property, data: PropertyCreate) -> Property:
        for key, value in data.model_dump(exclude={"amenities", "images"}, mode="python").items():
            setattr(prop, key, value)
        prop.amenity_rows.clear()
        prop.images.clear()
        self.db.flush()
        self._apply_children(prop, data)
        self.db.commit()
        return self.get(prop.id, include_inactive=True)  # type: ignore[return-value]

    @staticmethod
    def _apply_children(prop: Property, data: PropertyCreate) -> None:
        for name in data.amenities:
            prop.amenity_rows.append(PropertyAmenity(name=name))
        for pos, img in enumerate(data.images):
            prop.images.append(PropertyImage(url=str(img.url), alt=img.alt, position=pos))

    def set_status(self, prop: Property, status: PropertyStatus) -> Property:
        prop.status = status.value
        self.db.commit()
        return self.get(prop.id, include_inactive=True)  # type: ignore[return-value]

    def delete(self, prop: Property) -> None:
        self.db.delete(prop)
        self.db.commit()

    # ------------------------------------------------------------------ facets & stats
    def facets(self) -> dict:
        active = Property.status == PropertyStatus.active.value
        rows = self.db.execute(select(Property.city, Property.locality).where(active).distinct()
                               .order_by(Property.city, Property.locality)).all()
        localities: dict[str, list[str]] = {}
        for city, loc in rows:
            localities.setdefault(city, []).append(loc)
        amenities = self.db.scalars(select(PropertyAmenity.name).join(Property).where(active).distinct()
                                    .order_by(PropertyAmenity.name)).all()
        return {"cities": sorted(localities), "localities": localities, "amenities": list(amenities),
                "property_types": [t.value for t in PropertyType]}

    def locality_index(self) -> dict[str, tuple[str, str]]:
        rows = self.db.execute(select(Property.locality, Property.city).where(
            Property.status == PropertyStatus.active.value).distinct()).all()
        return {loc.lower(): (loc, city) for loc, city in rows}

    def stats(self) -> dict:
        def count(*cond) -> int:
            return self.db.scalar(select(func.count(Property.id)).where(*cond)) or 0

        active = Property.status == PropertyStatus.active.value
        by_city = dict(self.db.execute(select(Property.city, func.count()).group_by(Property.city)).all())
        by_type = dict(self.db.execute(select(Property.property_type, func.count()).group_by(Property.property_type)).all())
        return {
            "total_properties": count(), "active_properties": count(active),
            "sale_listings": count(active, Property.listing_type == "buy"),
            "rental_listings": count(active, Property.listing_type == "rent"),
            "inactive_properties": count(Property.status != PropertyStatus.active.value),
            "by_city": by_city, "by_type": by_type,
        }
