from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app import models
from app.config import settings
from app.database import SessionLocal, init_db
from app.routes.api import router as api_router
from app.services.daily_digest import maybe_send_daily_digest
from app.routes.web import router as web_router
from app.services.api_keys import ensure_bootstrap_api_key
from app.services.reminder_dispatcher import dispatch_reminder
from app.services.telegram_bot import TelegramBotWorker

app = FastAPI(title=settings.app_name)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.notes_encryption_key or settings.app_api_key,
    session_cookie="hub_session",
    same_site="lax",
)
app.include_router(web_router)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

scheduler = BackgroundScheduler(timezone="UTC")
telegram_bot_worker = TelegramBotWorker()


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


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    db: Session = SessionLocal()
    try:
        ensure_bootstrap_api_key(db, settings.app_api_key)
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

    if settings.telegram_bot_polling_enabled and settings.telegram_bot_token:
        telegram_bot_worker.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    telegram_bot_worker.stop()
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
