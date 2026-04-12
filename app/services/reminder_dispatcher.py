from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models
from app.services.channels.telegram_sender import send_telegram


def send_channel_message(channel: str, target: str, message: str) -> tuple[bool, str]:
    normalized = channel.lower().strip()

    if normalized == "telegram":
        return send_telegram(target, message)
    return False, f"Unsupported channel: {channel}"


def dispatch_reminder(db: Session, reminder: models.Reminder) -> tuple[bool, str]:
    ok, detail = send_channel_message(reminder.channel, reminder.target, reminder.message)

    log = models.DeliveryLog(
        reminder_id=reminder.id,
        channel=reminder.channel,
        target=reminder.target,
        status="sent" if ok else "failed",
        provider_response=detail,
    )
    db.add(log)

    if ok:
        if reminder.is_recurring and reminder.recurrence_minutes:
            reminder.status = "pending"
            reminder.remind_at = datetime.utcnow() + timedelta(minutes=reminder.recurrence_minutes)
        else:
            reminder.status = "sent"
        reminder.last_error = ""
        reminder.sent_at = datetime.utcnow()
    else:
        reminder.status = "failed"
        reminder.last_error = detail

    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return ok, detail
