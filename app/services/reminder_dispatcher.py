from datetime import datetime, timedelta
import re

from sqlalchemy.orm import Session

from app import models
from app.services.datetime_service import utc_now_naive
from app.services.channels.telegram_sender import send_telegram
from app.services.channels.email_sender import send_email
from app.services import webhook_dispatcher


TASK_MARKER_RE = re.compile(r"^\[task:\d+\]\s*")


def send_channel_message(channel: str, target: str, message: str) -> tuple[bool, str]:
    """Route a message to the appropriate delivery channel."""
    normalized = channel.lower().strip()

    if normalized == "telegram":
        return send_telegram(target, message)

    if normalized == "email":
        return send_email(target, message)

    return False, f"Unsupported channel: {channel!r}. Valid channels: telegram, email"


def dispatch_reminder(db: Session, reminder: models.Reminder) -> tuple[bool, str]:
    outbound_message = TASK_MARKER_RE.sub("", reminder.message or "").strip() or "Task reminder"
    ok, detail = send_channel_message(reminder.channel, reminder.target, outbound_message)

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
            reminder.remind_at = utc_now_naive() + timedelta(minutes=reminder.recurrence_minutes)
            reminder.last_error = ""
            reminder.sent_at = utc_now_naive()
            db.add(reminder)
        else:
            # One-shot reminders are ephemeral; keep audit in DeliveryLog only.
            db.delete(reminder)

        # Fire outbound webhook so external systems know a reminder was sent.
        webhook_dispatcher.fire_event("reminder.sent", {
            "id": reminder.id,
            "message": outbound_message,
            "channel": reminder.channel,
            "target": reminder.target,
            "sent_at": utc_now_naive().isoformat(),
        })
    else:
        reminder.status = "failed"
        reminder.last_error = detail
        db.add(reminder)

    db.commit()
    if ok and not reminder.is_recurring:
        return ok, detail
    db.refresh(reminder)
    return ok, detail
