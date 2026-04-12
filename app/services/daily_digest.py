from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.services.reminder_dispatcher import send_channel_message
from app.services.summary_service import get_today_summary


def _parse_hhmm(value: str) -> tuple[int, int]:
    try:
        hh, mm = value.split(":", maxsplit=1)
        return int(hh), int(mm)
    except Exception:
        return 19, 0


def maybe_send_daily_digest(db: Session) -> None:
    if not settings.daily_summary_enabled:
        return
    if not settings.daily_summary_target:
        return

    now = datetime.utcnow()
    hour, minute = _parse_hhmm(settings.daily_summary_time_utc)

    # Job runs every minute; only fire at configured UTC minute.
    if now.hour != hour or now.minute != minute:
        return

    digest_date = now.strftime("%Y-%m-%d")
    already_sent = (
        db.query(models.DailyDigestLog)
        .filter(models.DailyDigestLog.digest_date == digest_date)
        .filter(models.DailyDigestLog.status == "sent")
        .first()
    )
    if already_sent:
        return

    summary = get_today_summary(db)
    body = (
        f"Daily Summary ({digest_date} UTC)\n"
        f"Captures today: {summary.captures_today}\n"
        f"Open tasks: {summary.tasks_open}\n"
        f"Pending reminders: {summary.reminders_pending}\n"
        f"Reminders sent today: {summary.reminders_sent_today}"
    )

    ok, detail = send_channel_message(settings.daily_summary_channel, settings.daily_summary_target, body)

    log = models.DailyDigestLog(
        digest_date=digest_date,
        channel=settings.daily_summary_channel,
        target=settings.daily_summary_target,
        status="sent" if ok else "failed",
        detail=detail,
    )
    db.add(log)
    db.commit()
