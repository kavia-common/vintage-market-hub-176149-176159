from typing import Generator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import decode_token


# PUBLIC_INTERFACE
def db_session() -> Generator[Session, None, None]:
    """Dependency that yields a SQLAlchemy session."""
    yield from get_db()


# PUBLIC_INTERFACE
def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(db_session)) -> dict:
    """Extract and validate current user from Bearer token.

    This is a minimal placeholder implementation returning the token payload.
    Replace with real user model lookup using the database session.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    # TODO: Use payload["sub"] to fetch user from DB once models are in place
    return {"sub": payload.get("sub"), "claims": payload}
