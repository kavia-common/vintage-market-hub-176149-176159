from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.deps import db_session
from src.models import Category
from src.schemas.category import CategoryRead

router = APIRouter(prefix="/categories", tags=["categories"])


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[CategoryRead],
    summary="List categories",
    description="Return all base categories. If database hasn't been seeded yet, returns an empty array.",
    responses={200: {"description": "List of categories (possibly empty)"}},
)
def list_categories(db: Session = Depends(db_session)) -> List[CategoryRead]:
    """List all categories.

    Returns:
    - List[CategoryRead]: All categories; empty list if none exist.
    """
    results = db.scalars(select(Category).order_by(Category.name.asc())).all()
    return [CategoryRead.model_validate(c) for c in results]
