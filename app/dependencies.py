from fastapi import Header, HTTPException, status

from app.database import SessionLocal
from app.services.api_keys import validate_api_key


def require_api_key(x_api_key: str = Header(default="")) -> None:
    db = SessionLocal()
    try:
        if validate_api_key(db, x_api_key):
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    finally:
        db.close()
