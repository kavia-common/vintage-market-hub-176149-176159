from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import Region, Category


# PUBLIC_INTERFACE
def seed_regions(db: Session, regions: Iterable[tuple[str, str]] | None = None) -> int:
    """Seed default regions if they do not exist.

    Parameters:
    - db: SQLAlchemy Session
    - regions: Optional iterable of (code, name). If None, uses a sensible default set.

    Returns:
    - Number of regions inserted.
    """
    default_regions = regions or [
        ("NA", "North America"),
        ("EU", "Europe"),
        ("AS", "Asia"),
        ("SA", "South America"),
        ("AF", "Africa"),
        ("OC", "Oceania"),
    ]
    inserted = 0
    for code, name in default_regions:
        exists = db.scalar(select(Region).where(Region.code == code))
        if not exists:
            db.add(Region(code=code, name=name))
            inserted += 1
    if inserted:
        db.flush()
    return inserted


# PUBLIC_INTERFACE
def seed_categories(db: Session, categories: Iterable[tuple[str, str | None]] | None = None) -> int:
    """Seed base categories if they do not exist.

    Parameters:
    - db: SQLAlchemy Session
    - categories: Optional iterable of (name, description). If None, uses defaults.

    Returns:
    - Number of categories inserted.
    """
    default_categories = categories or [
        ("Clothing", "All vintage clothing items"),
        ("Footwear", "Shoes, boots, sneakers"),
        ("Accessories", "Bags, belts, hats, jewelry"),
        ("Furniture", "Chairs, tables, storage, home furnishings"),
        ("Electronics", "Vintage electronics and media"),
        ("Collectibles", "Collectible items and curios"),
    ]
    inserted = 0
    for name, desc in default_categories:
        exists = db.scalar(select(Category).where(Category.name == name))
        if not exists:
            db.add(Category(name=name, description=desc))
            inserted += 1
    if inserted:
        db.flush()
    return inserted
