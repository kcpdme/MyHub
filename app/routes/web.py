import secrets
import threading
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.config import settings
from app.services.channels.telegram_sender import send_telegram

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")

_LOGIN_STATE_LOCK = threading.Lock()
_LOGIN_CODE_VALUE = ""
_LOGIN_CODE_EXPIRES_AT: datetime | None = None
_LOGIN_CODE_LAST_SENT_AT: datetime | None = None


class TelegramCodeVerifyPayload(BaseModel):
    code: str = Field(min_length=4, max_length=12)


def _is_session_authenticated(request: Request) -> bool:
    return bool(request.session.get("authenticated") is True)


def _require_telegram_login_config() -> None:
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=400, detail="Telegram bot token is not configured")
    if not settings.telegram_chat_id:
        raise HTTPException(status_code=400, detail="Telegram chat id is not configured")


def _issue_login_code() -> str:
    global _LOGIN_CODE_VALUE, _LOGIN_CODE_EXPIRES_AT, _LOGIN_CODE_LAST_SENT_AT
    now = datetime.now(timezone.utc)
    with _LOGIN_STATE_LOCK:
        if _LOGIN_CODE_LAST_SENT_AT and (now - _LOGIN_CODE_LAST_SENT_AT).total_seconds() < 20:
            raise HTTPException(status_code=429, detail="Please wait before requesting another code")

        _LOGIN_CODE_VALUE = f"{secrets.randbelow(1_000_000):06d}"
        _LOGIN_CODE_EXPIRES_AT = now + timedelta(minutes=5)
        _LOGIN_CODE_LAST_SENT_AT = now
        return _LOGIN_CODE_VALUE


def _verify_login_code(code: str) -> bool:
    global _LOGIN_CODE_VALUE, _LOGIN_CODE_EXPIRES_AT
    now = datetime.now(timezone.utc)
    with _LOGIN_STATE_LOCK:
        if not _LOGIN_CODE_VALUE or not _LOGIN_CODE_EXPIRES_AT:
            return False
        if now > _LOGIN_CODE_EXPIRES_AT:
            _LOGIN_CODE_VALUE = ""
            _LOGIN_CODE_EXPIRES_AT = None
            return False
        if secrets.compare_digest(_LOGIN_CODE_VALUE, code.strip()):
            _LOGIN_CODE_VALUE = ""
            _LOGIN_CODE_EXPIRES_AT = None
            return True
        return False


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    if not _is_session_authenticated(request):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"title": "Login | Personal Automation Hub"},
        )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "title": "Personal Automation Hub",
            "default_telegram_target": settings.telegram_chat_id,
        },
    )


@router.get("/auth/session")
def auth_session(request: Request) -> dict[str, bool]:
    return {"authenticated": _is_session_authenticated(request)}


@router.post("/auth/telegram/request-code")
def auth_request_telegram_code() -> dict[str, bool]:
    _require_telegram_login_config()
    code = _issue_login_code()

    ok, detail = send_telegram(
        settings.telegram_chat_id,
        "Personal Automation Hub login code:\n"
        f"{code}\n\n"
        "This code expires in 5 minutes.",
    )
    if not ok:
        raise HTTPException(status_code=502, detail=detail)
    return {"ok": True}


@router.post("/auth/telegram/verify")
def auth_verify_telegram_code(payload: TelegramCodeVerifyPayload, request: Request) -> dict[str, bool]:
    if not _verify_login_code(payload.code):
        raise HTTPException(status_code=401, detail="Invalid or expired code")
    request.session["authenticated"] = True
    request.session["authenticated_at"] = datetime.now(timezone.utc).isoformat()
    return {"ok": True}


@router.post("/auth/logout")
def auth_logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}
