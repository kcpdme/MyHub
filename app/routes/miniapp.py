"""Telegram Mini App routes.

Endpoints
---------
GET  /miniapp          Serve the Mini App HTML shell (includes telegram-web-app.js).
POST /miniapp/auth     Validate Telegram initData (HMAC-SHA256) and return an API key.
POST /miniapp/setmenu  Register the bot's menu button URL with Telegram (helper).

Auth flow
---------
1. Telegram injects `window.Telegram.WebApp.initData` into the Mini App JS context.
2. The Mini App JS POSTs that string to /miniapp/auth.
3. We validate the HMAC-SHA256 signature using the bot token (standard Telegram spec).
4. We check auth_date is within 24 hours (replay protection).
5. We check the telegram_user_id is in the AllowedTelegramUser allowlist.
6. On success we return the bootstrap API key — the Mini App uses this as X-API-Key
   for all subsequent /api/* calls (no new auth layer needed).
"""
from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import get_db

router = APIRouter(tags=["miniapp"])
templates = Jinja2Templates(directory="app/templates")

# initData must be no older than 24 hours.
_MAX_AGE_SECONDS = 86_400


# ─── Models ───────────────────────────────────────────────────────────────────

class InitDataPayload(BaseModel):
    init_data: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _validate_init_data(init_data: str, bot_token: str) -> dict:
    """Validate Telegram initData HMAC-SHA256 signature.

    Returns parsed fields dict on success; raises HTTPException on failure.
    Official spec: https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    # Parse query-string format.
    params = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))

    received_hash = params.pop("hash", "")
    if not received_hash:
        raise HTTPException(status_code=401, detail="initData missing hash")

    # Build the check string: sorted key=value pairs joined by \n.
    check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(params.items())
    )

    # Derive secret key: HMAC-SHA256("WebAppData", bot_token).
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()

    # Compute expected hash.
    expected_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(status_code=401, detail="initData signature invalid")

    # Replay-attack protection.
    auth_date = int(params.get("auth_date", 0))
    if auth_date == 0:
        raise HTTPException(status_code=401, detail="initData missing auth_date")
    age = time.time() - auth_date
    if age > _MAX_AGE_SECONDS:
        raise HTTPException(status_code=401, detail="initData expired")

    return params


def _extract_user_id(params: dict) -> str:
    """Extract telegram user id from the parsed initData params."""
    user_json = params.get("user", "{}")
    try:
        import json
        user = json.loads(user_json)
        uid = str(user.get("id", "")).strip()
        if uid:
            return uid
    except Exception:
        pass
    raise HTTPException(status_code=401, detail="initData missing user.id")


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/miniapp", response_class=HTMLResponse)
def miniapp_shell(request: Request):
    """Serve the Telegram Mini App HTML shell."""
    return templates.TemplateResponse(
        request=request,
        name="miniapp.html",
        context={
            "title": "AutoHub Mini App",
            "miniapp_url": settings.miniapp_url or str(request.base_url).rstrip("/"),
            "app_timezone": settings.app_timezone,
        },
    )


@router.post("/miniapp/auth")
def miniapp_auth(payload: InitDataPayload, db: Session = Depends(get_db)):
    """Validate Telegram initData and return an API key for subsequent requests."""
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=400, detail="Telegram bot is not configured")

    # Full initData from empty context (e.g. browser testing) fallback.
    if not payload.init_data.strip():
        raise HTTPException(status_code=401, detail="initData is empty")

    # Validate signature & freshness.
    params = _validate_init_data(payload.init_data, settings.telegram_bot_token)

    # Check allowlist.
    telegram_user_id = _extract_user_id(params)
    allowed = (
        db.query(models.AllowedTelegramUser)
        .filter(models.AllowedTelegramUser.telegram_user_id == telegram_user_id)
        .filter(models.AllowedTelegramUser.is_active.is_(True))
        .first()
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Ask admin to allow telegram_user_id: {telegram_user_id}",
        )

    # Return the bootstrap API key — Mini App uses this as X-API-Key.
    # In a multi-user setup you'd issue per-user short-lived tokens here instead.
    if not settings.app_api_key or settings.app_api_key == "change-me":
        raise HTTPException(status_code=500, detail="API key is not configured on server")

    import json
    user_info = {}
    try:
        user_info = json.loads(params.get("user", "{}"))
    except Exception:
        pass

    return {
        "ok": True,
        "api_key": settings.app_api_key,
        "user": {
            "id": telegram_user_id,
            "first_name": user_info.get("first_name", ""),
            "last_name": user_info.get("last_name", ""),
            "username": user_info.get("username", ""),
        },
    }


@router.post("/miniapp/setmenu")
def miniapp_set_menu_button(request: Request):
    """Register the bot's menu button URL with Telegram (call once after deploy)."""
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=400, detail="Telegram bot is not configured")

    miniapp_url = settings.miniapp_url or str(request.base_url).rstrip("/") + "/miniapp"

    import httpx
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/setChatMenuButton",
            json={
                "menu_button": {
                    "type": "web_app",
                    "text": "🚀 Open Dashboard",
                    "web_app": {"url": miniapp_url},
                }
            },
            timeout=15,
        )
        data = resp.json()
        if not data.get("ok"):
            raise HTTPException(status_code=502, detail=f"Telegram API error: {data}")
        return {"ok": True, "miniapp_url": miniapp_url, "telegram_response": data}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Request failed: {exc}")
