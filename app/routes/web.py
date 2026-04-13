"""Web routes: login, session management, and CSRF protection.

Authentication flow
-------------------
1. GET /             → serve login page (if not authenticated) or the main app.
2. POST /auth/telegram/request-code → generate a 6-digit OTP, store hashed in DB,
   send to the configured Telegram chat ID.
3. POST /auth/telegram/verify       → validate OTP from DB; set session on success.
   Failed attempts are tracked per-IP; 5 failures within 15 minutes → HTTP 429.
4. POST /auth/logout                → clear session.

CSRF protection (double-submit cookie)
---------------------------------------
On every authenticated page load a random token is placed in:
  - The session (server-side)
  - A readable JavaScript cookie: `csrf_token`

All state-mutating POST/PUT/PATCH/DELETE requests from the browser JS must echo
this token in the `X-CSRF-Token` request header.  The `require_csrf` dependency
validates it.  API-key authenticated requests bypass CSRF (they cannot originate
from cross-site form submissions).
"""
from __future__ import annotations

import hashlib
import secrets
import threading
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app import models
from app.services.channels.telegram_sender import send_telegram

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")

# ─── Constants ────────────────────────────────────────────────────────────────
_OTP_VALID_MINUTES = 5
_OTP_COOLDOWN_SECONDS = 20
_BRUTE_FORCE_MAX_ATTEMPTS = 5
_BRUTE_FORCE_WINDOW_MINUTES = 15
_CSRF_COOKIE_NAME = "csrf_token"

# Thread lock guards the last-sent timestamp check (cheap, in-memory only).
_code_request_lock = threading.Lock()
_last_code_sent_at: datetime | None = None


class TelegramCodeVerifyPayload(BaseModel):
    code: str = Field(min_length=4, max_length=12)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_session_authenticated(request: Request) -> bool:
    return bool(request.session.get("authenticated") is True)


def _require_telegram_login_config() -> None:
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=400, detail="Telegram bot token is not configured")
    if not settings.telegram_chat_id:
        raise HTTPException(status_code=400, detail="Telegram chat id is not configured")


def _is_ip_locked_out(db: Session, ip: str) -> bool:
    """Return True if the IP has exceeded the failed-attempt threshold."""
    window_start = datetime.utcnow() - timedelta(minutes=_BRUTE_FORCE_WINDOW_MINUTES)
    failed = (
        db.query(models.LoginAttempt)
        .filter(models.LoginAttempt.ip_address == ip)
        .filter(models.LoginAttempt.success.is_(False))
        .filter(models.LoginAttempt.attempted_at >= window_start)
        .count()
    )
    return failed >= _BRUTE_FORCE_MAX_ATTEMPTS


def _record_attempt(db: Session, ip: str, success: bool) -> None:
    db.add(models.LoginAttempt(ip_address=ip, success=success))
    db.commit()


def _set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        _CSRF_COOKIE_NAME,
        token,
        httponly=False,   # Must be readable by JS for double-submit pattern.
        samesite="lax",
        secure=False,     # Set to True when served over HTTPS.
        max_age=86400,
    )


# ─── CSRF dependency ──────────────────────────────────────────────────────────

def require_csrf(request: Request) -> None:
    """Dependency: validates the CSRF double-submit token on state-mutating requests.

    API-key authenticated requests are exempt (they cannot originate from
    cross-site requests because browsers cannot set arbitrary request headers
    for cross-origin requests without a CORS pre-flight).
    """
    # Skip CSRF for API-key authenticated requests.
    if request.headers.get("X-API-Key"):
        return

    session_token = request.session.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")

    if not session_token or not header_token:
        raise HTTPException(status_code=403, detail="CSRF token missing")

    if not secrets.compare_digest(session_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF token mismatch")


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def home(request: Request, response: Response):
    if not _is_session_authenticated(request):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"title": "Login | Personal Automation Hub"},
        )

    # Issue/refresh CSRF token on every page load.
    csrf_token = request.session.get("csrf_token") or secrets.token_hex(32)
    request.session["csrf_token"] = csrf_token

    resp = templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "title": "Personal Automation Hub",
            "default_telegram_target": settings.telegram_chat_id,
        },
    )
    _set_csrf_cookie(resp, csrf_token)
    return resp


@router.get("/auth/session")
def auth_session(request: Request) -> dict[str, bool]:
    return {"authenticated": _is_session_authenticated(request)}


@router.post("/auth/telegram/request-code")
def auth_request_telegram_code(request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
    global _last_code_sent_at

    _require_telegram_login_config()

    now = datetime.now(timezone.utc)
    with _code_request_lock:
        if _last_code_sent_at and (now - _last_code_sent_at).total_seconds() < _OTP_COOLDOWN_SECONDS:
            raise HTTPException(status_code=429, detail="Please wait before requesting another code")
        _last_code_sent_at = now

    # Invalidate any existing unused OTP codes.
    db.query(models.OtpCode).filter(models.OtpCode.used.is_(False)).update({"used": True})
    db.commit()

    plain_code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.utcnow() + timedelta(minutes=_OTP_VALID_MINUTES)
    ip = _get_client_ip(request)

    db.add(models.OtpCode(
        code_hash=_hash_code(plain_code),
        ip_address=ip,
        expires_at=expires_at,
    ))
    db.commit()

    ok, detail = send_telegram(
        settings.telegram_chat_id,
        f"Personal Automation Hub login code:\n{plain_code}\n\nThis code expires in {_OTP_VALID_MINUTES} minutes.",
    )
    if not ok:
        raise HTTPException(status_code=502, detail=detail)

    return {"ok": True}


@router.post("/auth/telegram/verify")
def auth_verify_telegram_code(
    payload: TelegramCodeVerifyPayload,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    ip = _get_client_ip(request)

    if _is_ip_locked_out(db, ip):
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in {_BRUTE_FORCE_WINDOW_MINUTES} minutes.",
            headers={"Retry-After": str(_BRUTE_FORCE_WINDOW_MINUTES * 60)},
        )

    now = datetime.utcnow()
    code_hash = _hash_code(payload.code.strip())

    otp = (
        db.query(models.OtpCode)
        .filter(models.OtpCode.code_hash == code_hash)
        .filter(models.OtpCode.used.is_(False))
        .filter(models.OtpCode.expires_at > now)
        .first()
    )

    if not otp:
        _record_attempt(db, ip, success=False)
        raise HTTPException(status_code=401, detail="Invalid or expired code")

    # Mark as used immediately to prevent replay attacks.
    otp.used = True
    db.add(otp)
    _record_attempt(db, ip, success=True)
    db.commit()

    # Establish session.
    csrf_token = secrets.token_hex(32)
    request.session["authenticated"] = True
    request.session["authenticated_at"] = datetime.now(timezone.utc).isoformat()
    request.session["csrf_token"] = csrf_token

    _set_csrf_cookie(response, csrf_token)
    return {"ok": True}


@router.post("/auth/logout")
def auth_logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}
