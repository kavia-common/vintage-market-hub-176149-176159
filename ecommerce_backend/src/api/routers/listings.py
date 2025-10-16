from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.security import decode_token
from src.deps import db_session
from src.models import Category, Listing, Region
from src.schemas.listing import ListingCreate, ListingRead, ListingUpdate

router = APIRouter(prefix="/listings", tags=["listings"])


class _TokenUser(BaseModel):
    """Internal helper schema to represent token-authenticated user identity for listings endpoints."""
    sub: UUID


def _auth_user(authorization: str | None = Header(default=None)) -> _TokenUser:
    """Extract current user UUID from Bearer access token, raising 401 on problems."""
    from uuid import UUID as _UUID

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    sub = payload.get("sub")
    try:
        user_id = _UUID(str(sub))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    return _TokenUser(sub=user_id)


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[ListingRead],
    summary="List listings",
    description=(
        "List product listings with search, filters, sorting, and pagination.\n"
        "Query params:\n"
        "- search: case-insensitive search in title and description\n"
        "- region: region UUID filter\n"
        "- category: category UUID filter\n"
        "- price_min/price_max: decimal price range (inclusive)\n"
        "- sort: one of 'new', 'price_asc', 'price_desc'\n"
        "- page: 1-based page number\n"
        "- page_size: items per page (max 100)\n"
    ),
    responses={
        200: {"description": "List of listings"},
        400: {"description": "Invalid query parameters"},
    },
)
def list_listings(
    search: Optional[str] = Query(default=None, description="Search text in title and description"),
    region: Optional[UUID] = Query(default=None, description="Region id to filter"),
    category: Optional[UUID] = Query(default=None, description="Category id to filter"),
    price_min: Optional[Decimal] = Query(default=None, description="Minimum price"),
    price_max: Optional[Decimal] = Query(default=None, description="Maximum price"),
    sort: Optional[str] = Query(default="new", description="Sort by: new | price_asc | price_desc"),
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(db_session),
) -> List[ListingRead]:
    """Return a paginated list of listings applying provided filters and sorting."""
    stmt = select(Listing)

    filters = []
    # Search - use ILIKE for postgres; fallback to lower() contains for compatibility
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Listing.title.ilike(term), Listing.description.ilike(term)))

    if region:
        filters.append(Listing.region_id == region)
    if category:
        filters.append(Listing.category_id == category)
    if price_min is not None:
        filters.append(Listing.price >= price_min)
    if price_max is not None:
        filters.append(Listing.price <= price_max)

    if filters:
        stmt = stmt.where(and_(*filters))

    # Sorting
    if sort == "price_asc":
        stmt = stmt.order_by(Listing.price.asc(), Listing.created_at.desc())
    elif sort == "price_desc":
        stmt = stmt.order_by(Listing.price.desc(), Listing.created_at.desc())
    else:
        # default newest first
        stmt = stmt.order_by(desc(Listing.created_at))

    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    results = db.scalars(stmt).all()
    return [ListingRead.model_validate(r) for r in results]


# PUBLIC_INTERFACE
@router.get(
    "/{id}",
    response_model=ListingRead,
    summary="Get listing by id",
    description="Fetch a single listing by its UUID.",
    responses={
        200: {"description": "Listing found"},
        404: {"description": "Listing not found"},
    },
)
def get_listing(id: UUID, db: Session = Depends(db_session)) -> ListingRead:
    """Return a single listing by UUID."""
    listing = db.get(Listing, id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return ListingRead.model_validate(listing)


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=ListingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a listing",
    description="Create a new listing for the authenticated seller.",
    responses={
        201: {"description": "Listing created"},
        400: {"description": "Invalid input"},
        401: {"description": "Not authenticated"},
        404: {"description": "Region or Category not found"},
    },
)
def create_listing(
    payload: ListingCreate,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> ListingRead:
    """Create a new listing owned by the current user. Validates region and category existence."""
    # Validate foreign keys existence for better error messages
    if not db.get(Region, payload.region_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region not found")
    if not db.get(Category, payload.category_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    listing = Listing(
        title=payload.title,
        description=payload.description,
        price=payload.price,
        currency=payload.currency,
        seller_id=token_user.sub,
        region_id=payload.region_id,
        category_id=payload.category_id,
    )
    db.add(listing)
    db.flush()
    db.refresh(listing)
    return ListingRead.model_validate(listing)


# PUBLIC_INTERFACE
@router.patch(
    "/{id}",
    response_model=ListingRead,
    summary="Update a listing",
    description="Update fields of a listing. Only the owner (seller) can update.",
    responses={
        200: {"description": "Listing updated"},
        400: {"description": "Invalid input"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden - not the owner"},
        404: {"description": "Listing, Region, or Category not found"},
    },
)
def update_listing(
    id: UUID,
    payload: ListingUpdate,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> ListingRead:
    """Update an existing listing ensuring the current user is the owner."""
    listing = db.get(Listing, id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if listing.seller_id != token_user.sub:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the owner")

    # Validate related ids if being changed
    if payload.region_id and not db.get(Region, payload.region_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region not found")
    if payload.category_id and not db.get(Category, payload.category_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    # Patch fields
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(listing, field, value)

    db.add(listing)
    db.flush()
    db.refresh(listing)
    return ListingRead.model_validate(listing)


# PUBLIC_INTERFACE
@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a listing",
    description="Delete a listing by id. Only the owner (seller) can delete.",
    responses={
        204: {"description": "Listing deleted"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden - not the owner"},
        404: {"description": "Listing not found"},
    },
)
def delete_listing(
    id: UUID,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> None:
    """Delete a listing ensuring the current user is the owner."""
    listing = db.get(Listing, id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if listing.seller_id != token_user.sub:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the owner")
    db.delete(listing)
    db.flush()
    return None


# PUBLIC_INTERFACE
@router.post(
    "/{id}/images",
    summary="Upload listing image (stub)",
    description=(
        "Multipart image upload stub for a listing. Accepts a file and returns a placeholder URL or "
        "stores locally depending on FILE_STORAGE_PROVIDER setting. In a future implementation, "
        "this will upload to configured storage and persist image metadata."
    ),
    responses={
        200: {"description": "Image accepted (stub)"},
        400: {"description": "Invalid file"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden - not the owner"},
        404: {"description": "Listing not found"},
    },
)
def upload_listing_image_stub(
    id: UUID,
    file: UploadFile = File(...),
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> dict:
    """Accept an image file for a listing. Currently stores locally or returns a placeholder."""
    listing = db.get(Listing, id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if listing.seller_id != token_user.sub:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the owner")

    if not file or not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

    settings = get_settings()
    provider = settings.FILE_STORAGE_PROVIDER.lower()
    if provider == "local":
        # Store to local directory under FILE_STORAGE_DIR/listings/{listing_id}/
        from pathlib import Path
        storage_dir = Path(settings.FILE_STORAGE_DIR).joinpath("listings", str(id))
        storage_dir.mkdir(parents=True, exist_ok=True)
        # Caution: This is a stub; no validation on filename
        dest = storage_dir.joinpath(file.filename)
        content = file.file.read()
        with open(dest, "wb") as out:
            out.write(content)
        url = f"/static/listings/{id}/{file.filename}"  # Stub URL; not actually served unless static mounts added
        return {"status": "ok", "provider": "local", "url": url, "note": "Stored locally (stub)."}
    else:
        # Return placeholder URL for other providers
        return {
            "status": "ok",
            "provider": provider,
            "url": f"https://placeholder.invalid/listings/{id}/{file.filename}",
            "note": "Upload not implemented for this provider; returning placeholder.",
        }
