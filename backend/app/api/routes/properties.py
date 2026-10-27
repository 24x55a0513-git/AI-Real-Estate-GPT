from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import DbSession, get_filters
from app.repositories.property_repository import PropertyRepository
from app.schemas.property import CompareResult, Facets, Page, PropertyFilters, PropertyOut
from app.services.compare_service import build_comparison

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=Page, summary="Search and filter properties (database-backed, paginated)")
def list_properties(filters: Annotated[PropertyFilters, Depends(get_filters)], db: DbSession):
    repo = PropertyRepository(db)
    items, total = repo.search(filters)
    return Page(items=[PropertyOut.model_validate(p) for p in items], total=total, page=filters.page,
                page_size=filters.page_size, total_pages=repo.total_pages(total, filters.page_size))


@router.get("/facets", response_model=Facets, summary="Cities, localities and amenities available for filtering")
def facets(db: DbSession):
    return PropertyRepository(db).facets()


@router.get("/compare", response_model=CompareResult, summary="Compare 2 to 4 properties")
def compare(db: DbSession, ids: str = Query(..., description="Comma-separated property ids, e.g. 1,2,3")):
    try:
        parsed = list(dict.fromkeys(int(x) for x in ids.split(",") if x.strip()))
    except ValueError:
        raise HTTPException(422, "ids must be a comma-separated list of integers")
    if not 2 <= len(parsed) <= 4:
        raise HTTPException(422, "Select between 2 and 4 distinct properties to compare")
    if any(i <= 0 for i in parsed):
        raise HTTPException(422, "Invalid property id")
    props = PropertyRepository(db).get_many(parsed)
    if len(props) != len(parsed):
        raise HTTPException(404, "One or more properties were not found or are no longer available")
    return build_comparison(props)


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(property_id: int, db: DbSession):
    prop = PropertyRepository(db).get(property_id)
    if prop is None:
        raise HTTPException(404, "Property not found")
    return prop
