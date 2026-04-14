from __future__ import annotations

from sqlalchemy.orm import Session

from app import models
from app.config import settings


def task_marker(task_id: int) -> str:
    return f"[task:{task_id}]"


def _task_message(task: models.Task) -> str:
    title = (task.title or "Task reminder").strip()
    return f"{task_marker(task.id)} {title}"


def find_task_reminders(db: Session, task_id: int) -> list[models.Reminder]:
    marker = f"{task_marker(task_id)}%"
    return (
        db.query(models.Reminder)
        .filter(models.Reminder.message.like(marker))
        .filter(models.Reminder.channel == "telegram")
        .all()
    )


def delete_task_due_reminders(db: Session, task_id: int) -> int:
    reminders = find_task_reminders(db, task_id)
    for reminder in reminders:
        db.delete(reminder)
    return len(reminders)


def upsert_task_due_reminder(db: Session, task: models.Task) -> None:
    """Keep one pending reminder in sync with the task's due date.

    Rules:
    - no due date OR task is done -> delete existing task reminder(s)
    - no telegram target configured -> skip reminder creation
    - otherwise upsert a single pending reminder and remove duplicates
    """
    if not task.id:
        return

    if not task.due_date or task.status == "done":
        delete_task_due_reminders(db, task.id)
        return

    target = (settings.telegram_chat_id or "").strip()
    if not target:
        return

    existing = find_task_reminders(db, task.id)
    message = _task_message(task)

    if existing:
        primary = existing[0]
        primary.message = message
        primary.channel = "telegram"
        primary.target = target
        primary.remind_at = task.due_date
        primary.is_recurring = False
        primary.recurrence_minutes = None
        primary.status = "pending"
        primary.last_error = ""
        primary.sent_at = None
        db.add(primary)

        for duplicate in existing[1:]:
            db.delete(duplicate)
        return

    db.add(models.Reminder(
        message=message,
        channel="telegram",
        target=target,
        remind_at=task.due_date,
        is_recurring=False,
        recurrence_minutes=None,
        status="pending",
    ))
