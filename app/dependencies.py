"""FastAPI dependencies shared across routes."""
from fastapi import Header, HTTPException, Request, status

from app.database import SessionLocal
from app.services.api_keys import validate_api_key


def require_api_key(request: Request, x_api_key: str = Header(default="")) -> None:
    """Allow access if the request carries a valid session cookie OR a valid API key header."""
    if request.session.get("authenticated") is True:
        return

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


def require_csrf(request: Request) -> None:
    """Validate the CSRF double-submit token for browser session requests.

    API-key authenticated requests are exempt — browsers cannot set custom
    headers for cross-origin requests without a CORS pre-flight, making
    CSRF attacks impossible for header-authenticated callers.
    """
    if request.headers.get("X-API-Key"):
        return
    if not request.session.get("authenticated"):
        return  # Not a session request; require_api_key will handle auth.

    session_token = request.session.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")

    if not session_token or not header_token:
        raise HTTPException(status_code=403, detail="CSRF token missing")

    import secrets
    if not secrets.compare_digest(session_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF token mismatch")
