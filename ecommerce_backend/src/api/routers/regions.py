from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.deps import db_session
from src.models import Region
from src.schemas.region import RegionRead

router = APIRouter(prefix="/regions", tags=["regions"])


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[RegionRead],
    summary="List regions",
    description="Return all available regions. If database hasn't been seeded yet, returns an empty array.",
    responses={200: {"description": "List of regions (possibly empty)"}},
)
def list_regions(db: Session = Depends(db_session)) -> List[RegionRead]:
    """List all regions.

    Returns:
    - List[RegionRead]: All regions; empty list if none exist.
    """
    results = db.scalars(select(Region).order_by(Region.name.asc())).all()
    return [RegionRead.model_validate(r) for r in results]
