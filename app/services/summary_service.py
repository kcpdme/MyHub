from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.schemas import SummaryOut


def get_today_summary(db: Session) -> SummaryOut:
    now = datetime.utcnow()
    day_start = datetime(now.year, now.month, now.day)
    day_end = day_start + timedelta(days=1)

    captures_today = db.query(func.count(models.Capture.id)).filter(models.Capture.created_at >= day_start).scalar() or 0
    tasks_open = db.query(func.count(models.Task.id)).filter(models.Task.status != "done").scalar() or 0
    reminders_pending = (
        db.query(func.count(models.Reminder.id)).filter(models.Reminder.status.in_(["pending", "failed"])).scalar() or 0
    )
    reminders_sent_today = (
        db.query(func.count(models.Reminder.id))
        .filter(models.Reminder.sent_at.isnot(None))
        .filter(models.Reminder.sent_at >= day_start)
        .filter(models.Reminder.sent_at < day_end)
        .scalar()
        or 0
    )

    return SummaryOut(
        captures_today=captures_today,
        tasks_open=tasks_open,
        reminders_pending=reminders_pending,
        reminders_sent_today=reminders_sent_today,
    )
