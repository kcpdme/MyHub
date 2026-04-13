"""Application entry point.

Startup sequence
----------------
1. init_db() — create tables for fresh installs (Alembic owns schema evolution).
2. ensure_bootstrap_api_key() — seed the API key from .env on first run.
3. Register Telegram webhook (if TELEGRAM_WEBHOOK_URL is set) OR start the
   long-polling thread (if TELEGRAM_BOT_POLLING_ENABLED=true).
4. Start APScheduler with two recurring jobs:
   - process_due_reminders : every SCHEDULER_POLL_SECONDS seconds.
   - process_daily_digest  : every 60 seconds (fires at UTC minute configured).

Rate limiting
-------------
slowapi Limiter attached to the app.  Per-endpoint limits are declared with
@limiter.limit() decorators on sensitive routes.  The default limit (applied
globally via middleware) is configured via RATE_LIMIT_DEFAULT in settings.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app import models
from app.config import settings
from app.database import SessionLocal, engine, init_db
from app.routes.api import router as api_router
from app.routes.web import router as web_router
from app.services.api_keys import ensure_bootstrap_api_key
from app.services.daily_digest import maybe_send_daily_digest
from app.services.reminder_dispatcher import dispatch_reminder
from app.services.telegram_bot import TelegramBotWorker, delete_webhook, register_webhook

# ─── Startup timestamp ────────────────────────────────────────────────────────
_START_TIME = time.monotonic()

# ─── Rate limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default] if settings.rate_limit_enabled else [],
    enabled=settings.rate_limit_enabled,
)

# ─── Scheduler & Bot ─────────────────────────────────────────────────────────
scheduler = BackgroundScheduler(timezone="UTC")
telegram_bot_worker = TelegramBotWorker()


# ─── Background jobs ──────────────────────────────────────────────────────────

def process_due_reminders() -> None:
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        due = (
            db.query(models.Reminder)
            .filter(models.Reminder.status.in_(["pending", "failed"]))
            .filter(models.Reminder.remind_at <= now)
            .order_by(models.Reminder.remind_at.asc())
            .limit(20)
            .all()
        )
        for reminder in due:
            dispatch_reminder(db, reminder)
    finally:
        db.close()


def process_daily_digest() -> None:
    db: Session = SessionLocal()
    try:
        maybe_send_daily_digest(db)
    finally:
        db.close()


# ─── Lifespan context manager ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    init_db()
    db: Session = SessionLocal()
    try:
        ensure_bootstrap_api_key(db, settings.app_api_key)

        # Auto-register the owner's Telegram user ID in the bot allowlist
        # so they never get "Access denied" from their own bot.
        if settings.telegram_chat_id:
            owner_id = settings.telegram_chat_id.strip()
            existing = (
                db.query(models.AllowedTelegramUser)
                .filter(models.AllowedTelegramUser.telegram_user_id == owner_id)
                .first()
            )
            if not existing:
                db.add(models.AllowedTelegramUser(
                    telegram_user_id=owner_id,
                    display_name="owner (auto-registered)",
                    is_active=True,
                ))
                db.commit()
            elif not existing.is_active:
                existing.is_active = True
                db.add(existing)
                db.commit()
    finally:
        db.close()

    scheduler.add_job(
        process_due_reminders,
        "interval",
        seconds=max(settings.scheduler_poll_seconds, 10),
        id="process_due_reminders",
        replace_existing=True,
    )
    scheduler.add_job(
        process_daily_digest,
        "interval",
        seconds=60,
        id="process_daily_digest",
        replace_existing=True,
    )
    scheduler.start()

    if settings.telegram_webhook_url:
        register_webhook()
    elif settings.telegram_bot_polling_enabled and settings.telegram_bot_token:
        telegram_bot_worker.start()

    yield  # ── Application running ──

    # ── Shutdown ──
    telegram_bot_worker.stop()
    if settings.telegram_webhook_url:
        delete_webhook()
    if scheduler.running:
        scheduler.shutdown(wait=False)


# ─── Application factory ──────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# Rate limiting middleware (must be before route registration).
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.notes_encryption_key or settings.app_api_key,
    session_cookie="hub_session",
    same_site="lax",
    https_only=False,  # Set True when serving behind TLS terminator.
    max_age=86400,
)

app.include_router(web_router)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ─── Health endpoint ───────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Rich health check: DB ping, scheduler state, bot mode, uptime."""
    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
    except Exception as exc:
        db_status = f"error: {exc}"

    bot_mode = "disabled"
    if settings.telegram_webhook_url:
        bot_mode = "webhook"
    elif settings.telegram_bot_polling_enabled and settings.telegram_bot_token:
        bot_mode = "polling" if telegram_bot_worker.is_running else "polling-stopped"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": settings.app_version,
        "uptime_seconds": round(time.monotonic() - _START_TIME),
        "db": db_status,
        "scheduler": "running" if scheduler.running else "stopped",
        "telegram_bot": bot_mode,
        "rate_limiting": settings.rate_limit_enabled,
    }
