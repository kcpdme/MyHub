"""Main API router.

All endpoints under /api require authentication via:
  - Session cookie (set by the web login flow), OR
  - X-API-Key header (database-validated key).

New in v2.0
-----------
• Paginated list responses (Page[T] wrapper with total / page / pages).
• Tags CRUD + task/note tag associations.
• Full-text search across captures, tasks, notes, and inbox.
• Audit log endpoint.
• Outbound webhook subscriptions CRUD + delivery logs.
• Reminder snooze endpoint.
• Capture → Note and Inbox → Note promotions.
• Email channel support in reminders (channel="email", target=<email address>).
• Expanded /health endpoint.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.dependencies import require_api_key
from app.services.api_keys import generate_api_key, hash_api_key
from app.services.crypto_service import decrypt_text, encrypt_text
from app.services.reminder_dispatcher import dispatch_reminder
from app.services.summary_service import get_today_summary
from app.services import webhook_dispatcher

router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(require_api_key)])

ALLOWED_TASK_PRIORITIES = {"low", "medium", "high"}
ALLOWED_TASK_STATUSES = {"todo", "in_progress", "done"}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _paginate(query, page: int, page_size: int):
    """Apply LIMIT/OFFSET to a SQLAlchemy query and return (items, total)."""
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def _make_page(items, total: int, page: int, page_size: int):
    pages = max(1, math.ceil(total / page_size))
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}


def _audit(db: Session, entity_type: str, entity_id: int | None, action: str, actor: str = "api", detail: dict | None = None) -> None:
    db.add(models.AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        detail_json=json.dumps(detail or {}, default=str),
    ))
    # Committed as part of the calling transaction.


# ─── Inbox ─────────────────────────────────────────────────────────────────────

@router.get("/inbox")
def list_inbox(
    include_archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(models.TelegramInboxItem)
    if not include_archived:
        q = q.filter(models.TelegramInboxItem.is_archived.is_(False))
    q = q.order_by(models.TelegramInboxItem.created_at.desc())
    items, total = _paginate(q, page, page_size)
    return _make_page([schemas.InboxItemOut.model_validate(i) for i in items], total, page, page_size)


@router.get("/inbox/{item_id}/media")
def inbox_media(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.TelegramInboxItem).filter(models.TelegramInboxItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    if not item.file_id:
        raise HTTPException(status_code=404, detail="Inbox item has no media")
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=400, detail="Telegram bot token is not configured")

    try:
        with httpx.Client(timeout=20) as client:
            file_meta = client.get(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/getFile",
                params={"file_id": item.file_id},
            )
            file_meta.raise_for_status()
            payload = file_meta.json()
            file_path = ((payload.get("result") or {}).get("file_path") or "").strip()
            if not file_path:
                raise HTTPException(status_code=502, detail="Unable to resolve Telegram media file path")

            media_response = client.get(
                f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}",
            )
            media_response.raise_for_status()
            media_type = media_response.headers.get("content-type", "application/octet-stream")
            if media_type == "application/octet-stream":
                if item.item_type in {"photo", "sticker"}:
                    media_type = "image/jpeg"
                elif item.item_type == "animation":
                    media_type = "image/gif"
            return Response(content=media_response.content, media_type=media_type)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Media fetch failed: {exc}")


@router.post("/inbox/{item_id}/archive")
def archive_inbox_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.TelegramInboxItem).filter(models.TelegramInboxItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    item.is_archived = True
    db.add(item)
    _audit(db, "inbox", item_id, "archived")
    db.commit()
    webhook_dispatcher.fire_event("inbox.archived", {"id": item_id})
    return {"ok": True}


@router.post("/inbox/archive-all")
def archive_all_inbox_items(db: Session = Depends(get_db)):
    count = (
        db.query(models.TelegramInboxItem)
        .filter(models.TelegramInboxItem.is_archived.is_(False))
        .update({"is_archived": True})
    )
    db.commit()
    return {"ok": True, "archived": count}


@router.post("/inbox/{item_id}/analyze")
def analyze_inbox_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.TelegramInboxItem).filter(models.TelegramInboxItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")

    text_content = str(item.text).lower() + " " + item.item_type
    tags = ["[AI]"]
    if "photo" in text_content or "video" in text_content:
        tags.append("#media")
    if "http" in text_content or "www" in text_content:
        tags.append("#link")
    if "todo" in text_content or "need" in text_content or "buy" in text_content:
        tags.append("#actionable")
    if "invoice" in text_content or "$" in text_content or "receipt" in text_content or "bill" in text_content:
        tags.append("#finance")
    if "pass" in text_content or "code" in text_content:
        tags.append("#auth")
    if len(tags) == 1:
        tags.append("#general")

    tag_str = " ".join(set(tags))
    if not item.text:
        item.text = tag_str
    elif "[AI]" not in item.text:
        item.text = f"{item.text}\n\n{tag_str}"

    db.add(item)
    db.commit()
    return {"ok": True, "tags": tag_str}


@router.post("/inbox/{item_id}/to-capture", response_model=schemas.CaptureOut)
def promote_inbox_to_capture(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.TelegramInboxItem).filter(models.TelegramInboxItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")

    content = item.text.strip()
    if not content:
        content = f"[{item.item_type}] Telegram media item #{item.message_id}"

    capture = models.Capture(content=content, url="")
    item.is_archived = True
    db.add(capture)
    db.add(item)
    _audit(db, "inbox", item_id, "promoted_to_capture")
    db.commit()
    db.refresh(capture)
    webhook_dispatcher.fire_event("capture.created", {"id": capture.id, "content": capture.content[:100]})
    return capture


@router.post("/inbox/{item_id}/to-task", response_model=schemas.TaskOut)
def promote_inbox_to_task(
    item_id: int,
    payload: schemas.InboxPromoteTaskCreate,
    db: Session = Depends(get_db),
):
    item = db.query(models.TelegramInboxItem).filter(models.TelegramInboxItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")

    priority = payload.priority.strip().lower()
    if priority not in ALLOWED_TASK_PRIORITIES:
        raise HTTPException(status_code=400, detail="priority must be low, medium, or high")

    title = item.text.strip() or f"Review Telegram {item.item_type} item #{item.message_id}"
    now = datetime.utcnow()
    task = models.Task(title=title[:255], description="", status="todo", priority=priority, updated_at=now)
    item.is_archived = True
    db.add(task)
    db.add(item)
    _audit(db, "inbox", item_id, "promoted_to_task")
    db.commit()
    db.refresh(task)
    webhook_dispatcher.fire_event("task.created", {"id": task.id, "title": task.title})
    return task


@router.post("/inbox/{item_id}/to-note", response_model=schemas.NoteOut)
def promote_inbox_to_note(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.TelegramInboxItem).filter(models.TelegramInboxItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")

    content = item.text.strip()
    if not content:
        content = f"[{item.item_type}] Telegram media #{item.message_id}"

    now = datetime.utcnow()
    note = models.EncryptedNote(title="", cipher_text=encrypt_text(content), created_at=now, updated_at=now)
    item.is_archived = True
    db.add(note)
    db.add(item)
    _audit(db, "inbox", item_id, "promoted_to_note")
    db.commit()
    db.refresh(note)
    return schemas.NoteOut(id=note.id, title=note.title, content=content, created_at=note.created_at, updated_at=note.updated_at)


# ─── Captures ─────────────────────────────────────────────────────────────────

@router.get("/captures")
def list_captures(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(models.Capture).order_by(models.Capture.created_at.desc())
    items, total = _paginate(q, page, page_size)
    return _make_page([schemas.CaptureOut.model_validate(i) for i in items], total, page, page_size)


@router.post("/captures", response_model=schemas.CaptureOut)
def create_capture(payload: schemas.CaptureCreate, db: Session = Depends(get_db)):
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="content cannot be empty")

    capture = models.Capture(content=content, url=payload.url.strip())
    db.add(capture)
    _audit(db, "capture", None, "created")
    db.commit()
    db.refresh(capture)
    webhook_dispatcher.fire_event("capture.created", {"id": capture.id, "content": capture.content[:100]})
    return capture


@router.delete("/captures/{capture_id}")
def delete_capture(capture_id: int, db: Session = Depends(get_db)):
    capture = db.query(models.Capture).filter(models.Capture.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail="Capture not found")
    _audit(db, "capture", capture_id, "deleted")
    db.delete(capture)
    db.commit()
    webhook_dispatcher.fire_event("capture.deleted", {"id": capture_id})
    return {"ok": True}


@router.patch("/captures/{capture_id}", response_model=schemas.CaptureOut)
def update_capture(capture_id: int, payload: schemas.CaptureUpdate, db: Session = Depends(get_db)):
    capture = db.query(models.Capture).filter(models.Capture.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail="Capture not found")
    if payload.content is not None:
        content = payload.content.strip()
        if not content:
            raise HTTPException(status_code=400, detail="content cannot be empty")
        capture.content = content
    if payload.url is not None:
        capture.url = payload.url.strip()
    db.add(capture)
    db.commit()
    db.refresh(capture)
    return capture


@router.post("/captures/{capture_id}/to-note", response_model=schemas.NoteOut)
def promote_capture_to_note(capture_id: int, db: Session = Depends(get_db)):
    capture = db.query(models.Capture).filter(models.Capture.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail="Capture not found")

    now = datetime.utcnow()
    note = models.EncryptedNote(
        title=capture.content[:80],
        cipher_text=encrypt_text(capture.content),
        created_at=now,
        updated_at=now,
    )
    db.add(note)
    _audit(db, "capture", capture_id, "promoted_to_note")
    db.delete(capture)
    db.commit()
    db.refresh(note)
    return schemas.NoteOut(id=note.id, title=note.title, content=capture.content, created_at=note.created_at, updated_at=note.updated_at)


# ─── Tasks ─────────────────────────────────────────────────────────────────────

@router.get("/tasks")
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Task).order_by(models.Task.created_at.desc())
    if status:
        q = q.filter(models.Task.status == status)
    if priority:
        q = q.filter(models.Task.priority == priority)
    items, total = _paginate(q, page, page_size)
    return _make_page([schemas.TaskOut.model_validate(i) for i in items], total, page, page_size)


@router.post("/tasks", response_model=schemas.TaskOut)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    title = payload.title.strip()
    priority = payload.priority.strip().lower()

    if not title:
        raise HTTPException(status_code=400, detail="title cannot be empty")
    if priority not in ALLOWED_TASK_PRIORITIES:
        raise HTTPException(status_code=400, detail="priority must be low, medium, or high")

    now = datetime.utcnow()
    task = models.Task(
        title=title,
        description=payload.description.strip() if payload.description else "",
        priority=priority,
        due_date=payload.due_date,
        updated_at=now,
    )
    db.add(task)
    _audit(db, "task", None, "created", detail={"title": title})
    db.commit()
    db.refresh(task)
    webhook_dispatcher.fire_event("task.created", {"id": task.id, "title": task.title, "priority": task.priority})
    return task


@router.patch("/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: int, payload: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    now = datetime.utcnow()
    prev_status = task.status

    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="title cannot be empty")
        task.title = title
    if payload.description is not None:
        task.description = payload.description.strip()
    if payload.status is not None:
        new_status = payload.status.strip().lower()
        if new_status not in ALLOWED_TASK_STATUSES:
            raise HTTPException(status_code=400, detail="status must be todo, in_progress, or done")
        task.status = new_status
        # Set completed_at when transitioning to done; clear it when reverting.
        if new_status == "done" and prev_status != "done":
            task.completed_at = now
        elif new_status != "done":
            task.completed_at = None
    if payload.priority is not None:
        priority = payload.priority.strip().lower()
        if priority not in ALLOWED_TASK_PRIORITIES:
            raise HTTPException(status_code=400, detail="priority must be low, medium, or high")
        task.priority = priority
    if payload.clear_due_date:
        task.due_date = None
    elif payload.due_date is not None:
        task.due_date = payload.due_date

    task.updated_at = now
    db.add(task)
    _audit(db, "task", task_id, "updated", detail={"status": task.status})
    db.commit()
    db.refresh(task)

    event = "task.done" if task.status == "done" and prev_status != "done" else "task.updated"
    webhook_dispatcher.fire_event(event, {"id": task.id, "title": task.title, "status": task.status})
    return task


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    _audit(db, "task", task_id, "deleted")
    db.delete(task)
    db.commit()
    return {"ok": True}


@router.post("/tasks/batch-action")
def batch_task_action(action: str, ids: list[int], db: Session = Depends(get_db)):
    if action not in {"mark_done", "mark_todo", "delete"}:
        raise HTTPException(status_code=400, detail="action must be mark_done, mark_todo, or delete")
    if not ids:
        raise HTTPException(status_code=400, detail="ids cannot be empty")

    tasks = db.query(models.Task).filter(models.Task.id.in_(ids)).all()
    now = datetime.utcnow()
    count = 0
    for t in tasks:
        if action == "mark_done":
            t.status = "done"
            t.completed_at = now
            t.updated_at = now
            db.add(t)
        elif action == "mark_todo":
            t.status = "todo"
            t.completed_at = None
            t.updated_at = now
            db.add(t)
        elif action == "delete":
            db.delete(t)
        count += 1
    db.commit()
    return {"ok": True, "affected": count}


# ─── Task Tags ─────────────────────────────────────────────────────────────────

@router.get("/tasks/{task_id}/tags", response_model=list[schemas.TagOut])
def get_task_tags(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    tag_ids = [tt.tag_id for tt in db.query(models.TaskTag).filter(models.TaskTag.task_id == task_id).all()]
    return db.query(models.Tag).filter(models.Tag.id.in_(tag_ids)).all()


@router.post("/tasks/{task_id}/tags/{tag_id}")
def add_task_tag(task_id: int, tag_id: int, db: Session = Depends(get_db)):
    if not db.query(models.Task).filter(models.Task.id == task_id).first():
        raise HTTPException(status_code=404, detail="Task not found")
    if not db.query(models.Tag).filter(models.Tag.id == tag_id).first():
        raise HTTPException(status_code=404, detail="Tag not found")
    existing = db.query(models.TaskTag).filter(models.TaskTag.task_id == task_id, models.TaskTag.tag_id == tag_id).first()
    if not existing:
        db.add(models.TaskTag(task_id=task_id, tag_id=tag_id))
        db.commit()
    return {"ok": True}


@router.delete("/tasks/{task_id}/tags/{tag_id}")
def remove_task_tag(task_id: int, tag_id: int, db: Session = Depends(get_db)):
    tt = db.query(models.TaskTag).filter(models.TaskTag.task_id == task_id, models.TaskTag.tag_id == tag_id).first()
    if tt:
        db.delete(tt)
        db.commit()
    return {"ok": True}


# ─── Reminders ─────────────────────────────────────────────────────────────────

@router.delete("/reminders/{reminder_id}")
def delete_reminder(reminder_id: int, db: Session = Depends(get_db)):
    reminder = db.query(models.Reminder).filter(models.Reminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    db.delete(reminder)
    db.commit()
    return {"ok": True}


@router.get("/reminders")
def list_reminders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(models.Reminder).order_by(models.Reminder.remind_at.asc())
    items, total = _paginate(q, page, page_size)
    return _make_page([schemas.ReminderOut.model_validate(i) for i in items], total, page, page_size)


@router.post("/reminders", response_model=schemas.ReminderOut)
def create_reminder(payload: schemas.ReminderCreate, db: Session = Depends(get_db)):
    channel = payload.channel.lower().strip()
    if channel not in {"telegram", "email"}:
        raise HTTPException(status_code=400, detail="channel must be telegram or email")

    if payload.is_recurring and payload.recurrence_minutes is None:
        raise HTTPException(status_code=400, detail="recurrence_minutes is required when is_recurring=true")

    recurrence_minutes = payload.recurrence_minutes if payload.is_recurring else None
    reminder = models.Reminder(
        message=payload.message.strip(),
        channel=channel,
        target=payload.target.strip(),
        remind_at=payload.remind_at,
        is_recurring=payload.is_recurring,
        recurrence_minutes=recurrence_minutes,
        status="pending",
    )
    db.add(reminder)
    _audit(db, "reminder", None, "created")
    db.commit()
    db.refresh(reminder)
    webhook_dispatcher.fire_event("reminder.created", {"id": reminder.id, "message": reminder.message[:100]})
    return reminder


@router.post("/reminders/{reminder_id}/send-now")
def send_reminder_now(reminder_id: int, db: Session = Depends(get_db)):
    reminder = db.query(models.Reminder).filter(models.Reminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    ok, detail = dispatch_reminder(db, reminder)
    return {"ok": ok, "detail": detail, "status": reminder.status}


@router.post("/reminders/{reminder_id}/snooze", response_model=schemas.ReminderOut)
def snooze_reminder(
    reminder_id: int,
    minutes: int = Query(default=15, ge=1, le=10080),
    db: Session = Depends(get_db),
):
    """Create a new pending reminder shifted forward by `minutes` from now."""
    reminder = db.query(models.Reminder).filter(models.Reminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    snoozed = models.Reminder(
        message=f"[Snoozed] {reminder.message}",
        channel=reminder.channel,
        target=reminder.target,
        remind_at=datetime.utcnow() + timedelta(minutes=minutes),
        is_recurring=False,
        recurrence_minutes=None,
        status="pending",
    )
    db.add(snoozed)
    _audit(db, "reminder", reminder_id, "snoozed", detail={"minutes": minutes})
    db.commit()
    db.refresh(snoozed)
    return snoozed


# ─── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary/today", response_model=schemas.SummaryOut)
def today_summary(db: Session = Depends(get_db)):
    return get_today_summary(db)


# ─── Notes ─────────────────────────────────────────────────────────────────────

@router.get("/notes")
def list_notes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(models.EncryptedNote).order_by(models.EncryptedNote.updated_at.desc())
    notes, total = _paginate(q, page, page_size)
    output = []
    for note in notes:
        try:
            content = decrypt_text(note.cipher_text)
        except Exception:
            content = "<decryption failed>"
        output.append(schemas.NoteOut(
            id=note.id, title=note.title, content=content,
            created_at=note.created_at, updated_at=note.updated_at,
        ))
    return _make_page(output, total, page, page_size)


@router.post("/notes", response_model=schemas.NoteOut)
def create_note(payload: schemas.NoteCreate, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    note = models.EncryptedNote(
        title=payload.title.strip(),
        cipher_text=encrypt_text(payload.content.strip()),
        created_at=now,
        updated_at=now,
    )
    db.add(note)
    _audit(db, "note", None, "created")
    db.commit()
    db.refresh(note)
    webhook_dispatcher.fire_event("note.created", {"id": note.id})
    return schemas.NoteOut(id=note.id, title=note.title, content=payload.content, created_at=note.created_at, updated_at=note.updated_at)


@router.delete("/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(models.EncryptedNote).filter(models.EncryptedNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    _audit(db, "note", note_id, "deleted")
    db.delete(note)
    db.commit()
    return {"ok": True}


@router.put("/notes/{note_id}", response_model=schemas.NoteOut)
def update_note(note_id: int, payload: schemas.NoteUpdate, db: Session = Depends(get_db)):
    note = db.query(models.EncryptedNote).filter(models.EncryptedNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    now = datetime.utcnow()
    title = note.title
    content = None

    if payload.title is not None:
        title = payload.title.strip()
    if payload.content is not None:
        content = payload.content.strip()
        if not content:
            raise HTTPException(status_code=400, detail="content cannot be empty")
        note.cipher_text = encrypt_text(content)
    else:
        try:
            content = decrypt_text(note.cipher_text)
        except Exception:
            content = "<decryption failed>"

    note.title = title
    note.updated_at = now
    db.add(note)
    _audit(db, "note", note_id, "updated")
    db.commit()
    db.refresh(note)
    return schemas.NoteOut(id=note.id, title=note.title, content=content, created_at=note.created_at, updated_at=note.updated_at)


# ─── Note Tags ─────────────────────────────────────────────────────────────────

@router.get("/notes/{note_id}/tags", response_model=list[schemas.TagOut])
def get_note_tags(note_id: int, db: Session = Depends(get_db)):
    if not db.query(models.EncryptedNote).filter(models.EncryptedNote.id == note_id).first():
        raise HTTPException(status_code=404, detail="Note not found")
    tag_ids = [nt.tag_id for nt in db.query(models.NoteTag).filter(models.NoteTag.note_id == note_id).all()]
    return db.query(models.Tag).filter(models.Tag.id.in_(tag_ids)).all()


@router.post("/notes/{note_id}/tags/{tag_id}")
def add_note_tag(note_id: int, tag_id: int, db: Session = Depends(get_db)):
    if not db.query(models.EncryptedNote).filter(models.EncryptedNote.id == note_id).first():
        raise HTTPException(status_code=404, detail="Note not found")
    if not db.query(models.Tag).filter(models.Tag.id == tag_id).first():
        raise HTTPException(status_code=404, detail="Tag not found")
    existing = db.query(models.NoteTag).filter(models.NoteTag.note_id == note_id, models.NoteTag.tag_id == tag_id).first()
    if not existing:
        db.add(models.NoteTag(note_id=note_id, tag_id=tag_id))
        db.commit()
    return {"ok": True}


@router.delete("/notes/{note_id}/tags/{tag_id}")
def remove_note_tag(note_id: int, tag_id: int, db: Session = Depends(get_db)):
    nt = db.query(models.NoteTag).filter(models.NoteTag.note_id == note_id, models.NoteTag.tag_id == tag_id).first()
    if nt:
        db.delete(nt)
        db.commit()
    return {"ok": True}


# ─── Global Tags ───────────────────────────────────────────────────────────────

@router.get("/tags", response_model=list[schemas.TagOut])
def list_tags(db: Session = Depends(get_db)):
    return db.query(models.Tag).order_by(models.Tag.name.asc()).all()


@router.post("/tags", response_model=schemas.TagOut)
def create_tag(payload: schemas.TagCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Tag).filter(models.Tag.name == payload.name.strip()).first()
    if existing:
        return existing
    tag = models.Tag(name=payload.name.strip(), color=payload.color.strip())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    # Clean up associations.
    db.query(models.TaskTag).filter(models.TaskTag.tag_id == tag_id).delete()
    db.query(models.NoteTag).filter(models.NoteTag.tag_id == tag_id).delete()
    db.delete(tag)
    db.commit()
    return {"ok": True}


# ─── Habits ────────────────────────────────────────────────────────────────────

@router.get("/habits")
def list_habits(db: Session = Depends(get_db)):
    habits = db.query(models.Habit).filter(models.Habit.is_active.is_(True)).order_by(models.Habit.created_at.asc()).all()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    result = []
    for h in habits:
        streak = 0
        logs = (
            db.query(models.HabitLog)
            .filter(models.HabitLog.habit_id == h.id)
            .filter(models.HabitLog.completed.is_(True))
            .order_by(models.HabitLog.log_date.desc())
            .limit(60)
            .all()
        )
        if logs:
            check_date = datetime.utcnow().date()
            for log in logs:
                if log.log_date == check_date.strftime("%Y-%m-%d"):
                    streak += 1
                    check_date -= timedelta(days=1)
                else:
                    break

        completed_today = any(l.log_date == today and l.completed for l in logs)
        result.append(schemas.HabitOut(
            id=h.id, name=h.name, icon=h.icon, color=h.color,
            is_active=h.is_active, created_at=h.created_at,
            streak=streak, completed_today=completed_today,
        ))
    return result


@router.post("/habits")
def create_habit(payload: schemas.HabitCreate, db: Session = Depends(get_db)):
    habit = models.Habit(
        name=payload.name.strip(),
        icon=payload.icon.strip() or "check",
        color=payload.color.strip() or "green",
        is_active=True,
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return schemas.HabitOut(id=habit.id, name=habit.name, icon=habit.icon, color=habit.color, is_active=habit.is_active, created_at=habit.created_at, streak=0, completed_today=False)


@router.post("/habits/{habit_id}/toggle")
def toggle_habit(habit_id: int, payload: schemas.HabitToggle = None, db: Session = Depends(get_db)):
    if payload is None:
        payload = schemas.HabitToggle()
    habit = db.query(models.Habit).filter(models.Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    log_date = payload.date or datetime.utcnow().strftime("%Y-%m-%d")
    existing = (
        db.query(models.HabitLog)
        .filter(models.HabitLog.habit_id == habit_id)
        .filter(models.HabitLog.log_date == log_date)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
        return {"ok": True, "completed": False, "date": log_date}
    else:
        log = models.HabitLog(habit_id=habit_id, log_date=log_date, completed=True)
        db.add(log)
        db.commit()
        return {"ok": True, "completed": True, "date": log_date}


@router.delete("/habits/{habit_id}")
def delete_habit(habit_id: int, db: Session = Depends(get_db)):
    habit = db.query(models.Habit).filter(models.Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    habit.is_active = False
    db.add(habit)
    db.commit()
    return {"ok": True}


@router.get("/habits/{habit_id}/logs")
def habit_logs(habit_id: int, db: Session = Depends(get_db)):
    logs = (
        db.query(models.HabitLog)
        .filter(models.HabitLog.habit_id == habit_id)
        .filter(models.HabitLog.completed.is_(True))
        .order_by(models.HabitLog.log_date.desc())
        .limit(90)
        .all()
    )
    return [{"date": l.log_date, "completed": l.completed} for l in logs]


# ─── Search ────────────────────────────────────────────────────────────────────

@router.get("/search", response_model=list[schemas.SearchResult])
def search(
    q: str = Query(min_length=1),
    types: str = Query(default="captures,tasks,notes,inbox"),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Full-text search across captures, tasks, notes, and inbox items."""
    enabled_types = {t.strip() for t in types.split(",")}
    results: list[schemas.SearchResult] = []
    term = f"%{q}%"

    if "captures" in enabled_types:
        for c in db.query(models.Capture).filter(
            or_(models.Capture.content.ilike(term), models.Capture.url.ilike(term))
        ).limit(limit).all():
            results.append(schemas.SearchResult(
                entity_type="capture", entity_id=c.id,
                title=c.content[:80], snippet=c.content[:200],
                created_at=c.created_at,
            ))

    if "tasks" in enabled_types:
        for t in db.query(models.Task).filter(
            or_(models.Task.title.ilike(term), models.Task.description.ilike(term))
        ).limit(limit).all():
            results.append(schemas.SearchResult(
                entity_type="task", entity_id=t.id,
                title=t.title, snippet=t.description[:200],
                created_at=t.created_at,
            ))

    if "notes" in enabled_types:
        for n in db.query(models.EncryptedNote).limit(200).all():
            try:
                content = decrypt_text(n.cipher_text)
            except Exception:
                continue
            if q.lower() in content.lower() or q.lower() in (n.title or "").lower():
                results.append(schemas.SearchResult(
                    entity_type="note", entity_id=n.id,
                    title=n.title or "Untitled Note",
                    snippet=content[:200],
                    created_at=n.created_at,
                ))

    if "inbox" in enabled_types:
        for i in db.query(models.TelegramInboxItem).filter(
            models.TelegramInboxItem.text.ilike(term),
            models.TelegramInboxItem.is_archived.is_(False),
        ).limit(limit).all():
            results.append(schemas.SearchResult(
                entity_type="inbox", entity_id=i.id,
                title=i.text[:80] or f"[{i.item_type}]",
                snippet=i.text[:200],
                created_at=i.created_at,
            ))

    results.sort(key=lambda r: r.created_at, reverse=True)
    return results[:limit]


# ─── Audit log ─────────────────────────────────────────────────────────────────

@router.get("/audit-log")
def list_audit_log(
    entity_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc())
    if entity_type:
        q = q.filter(models.AuditLog.entity_type == entity_type)
    items, total = _paginate(q, page, page_size)
    return _make_page([schemas.AuditLogOut.model_validate(i) for i in items], total, page, page_size)


# ─── Outbound Webhooks ─────────────────────────────────────────────────────────

@router.get("/webhooks", response_model=list[schemas.WebhookSubscriptionOut])
def list_webhooks(db: Session = Depends(get_db)):
    return db.query(models.WebhookSubscription).order_by(models.WebhookSubscription.created_at.desc()).all()


@router.post("/webhooks", response_model=schemas.WebhookSubscriptionOut)
def create_webhook(payload: schemas.WebhookSubscriptionCreate, db: Session = Depends(get_db)):
    sub = models.WebhookSubscription(
        url=payload.url.strip(),
        event_types=payload.event_types.strip() or "*",
        secret=payload.secret.strip(),
        is_active=True,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    sub = db.query(models.WebhookSubscription).filter(models.WebhookSubscription.id == webhook_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")
    db.delete(sub)
    db.commit()
    return {"ok": True}


@router.post("/webhooks/{webhook_id}/deactivate", response_model=schemas.WebhookSubscriptionOut)
def deactivate_webhook(webhook_id: int, db: Session = Depends(get_db)):
    sub = db.query(models.WebhookSubscription).filter(models.WebhookSubscription.id == webhook_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")
    sub.is_active = False
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/webhooks/{webhook_id}/logs", response_model=list[schemas.WebhookDeliveryLogOut])
def webhook_delivery_logs(webhook_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.WebhookDeliveryLog)
        .filter(models.WebhookDeliveryLog.subscription_id == webhook_id)
        .order_by(models.WebhookDeliveryLog.created_at.desc())
        .limit(100)
        .all()
    )


# ─── Export ────────────────────────────────────────────────────────────────────

@router.get("/export")
def export_all_data(db: Session = Depends(get_db)):
    captures = db.query(models.Capture).order_by(models.Capture.created_at.desc()).all()
    tasks = db.query(models.Task).order_by(models.Task.created_at.desc()).all()
    reminders = db.query(models.Reminder).order_by(models.Reminder.remind_at.desc()).all()
    notes_raw = db.query(models.EncryptedNote).order_by(models.EncryptedNote.updated_at.desc()).all()

    notes = []
    for n in notes_raw:
        try:
            content = decrypt_text(n.cipher_text)
        except Exception:
            content = "<decryption failed>"
        notes.append({
            "id": n.id, "title": n.title, "content": content,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "updated_at": n.updated_at.isoformat() if n.updated_at else None,
        })

    data = {
        "exported_at": datetime.utcnow().isoformat(),
        "app_version": settings.app_version,
        "captures": [
            {"id": c.id, "content": c.content, "url": c.url,
             "created_at": c.created_at.isoformat() if c.created_at else None}
            for c in captures
        ],
        "tasks": [
            {"id": t.id, "title": t.title, "description": t.description,
             "status": t.status, "priority": t.priority,
             "due_date": t.due_date.isoformat() if t.due_date else None,
             "completed_at": t.completed_at.isoformat() if t.completed_at else None,
             "created_at": t.created_at.isoformat() if t.created_at else None}
            for t in tasks
        ],
        "reminders": [
            {"id": r.id, "message": r.message, "channel": r.channel,
             "target": r.target, "remind_at": r.remind_at.isoformat() if r.remind_at else None,
             "is_recurring": r.is_recurring, "recurrence_minutes": r.recurrence_minutes,
             "status": r.status, "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in reminders
        ],
        "notes": notes,
    }
    return JSONResponse(content=data, headers={
        "Content-Disposition": "attachment; filename=automation_hub_export.json"
    })


# ─── Telegram allowlist ────────────────────────────────────────────────────────

@router.get("/telegram/allowlist", response_model=list[schemas.TelegramUserOut])
def list_allowed_telegram_users(db: Session = Depends(get_db)):
    return db.query(models.AllowedTelegramUser).order_by(models.AllowedTelegramUser.created_at.desc()).all()


@router.post("/telegram/allowlist", response_model=schemas.TelegramUserOut)
def add_allowed_telegram_user(payload: schemas.TelegramUserCreate, db: Session = Depends(get_db)):
    user_id = payload.telegram_user_id.strip()
    display_name = payload.display_name.strip()
    existing = db.query(models.AllowedTelegramUser).filter(models.AllowedTelegramUser.telegram_user_id == user_id).first()
    if existing:
        existing.display_name = display_name
        existing.is_active = True
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    record = models.AllowedTelegramUser(telegram_user_id=user_id, display_name=display_name, is_active=True)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/telegram/allowlist/{record_id}/deactivate", response_model=schemas.TelegramUserOut)
def deactivate_allowed_telegram_user(record_id: int, db: Session = Depends(get_db)):
    record = db.query(models.AllowedTelegramUser).filter(models.AllowedTelegramUser.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Allowed user not found")
    record.is_active = False
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ─── Telegram webhook receiver ─────────────────────────────────────────────────

@router.post("/telegram/webhook")
async def telegram_webhook_receiver(request: Request):
    """Receive incoming Telegram updates when webhook mode is active."""
    if settings.telegram_webhook_secret:
        incoming_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if incoming_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

    try:
        update = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    from app.services.telegram_bot import handle_telegram_update
    import threading
    t = threading.Thread(target=handle_telegram_update, args=(update,), daemon=True)
    t.start()

    return {"ok": True}


# ─── Auth / API Keys ───────────────────────────────────────────────────────────

@router.get("/auth/keys", response_model=list[schemas.ApiKeyOut])
def list_api_keys(db: Session = Depends(get_db)):
    return db.query(models.ApiKey).order_by(models.ApiKey.created_at.desc()).all()


@router.post("/auth/keys", response_model=schemas.ApiKeyCreateOut)
def create_api_key(payload: schemas.ApiKeyCreate, db: Session = Depends(get_db)):
    plain = generate_api_key()
    record = models.ApiKey(
        name=payload.name.strip()[:120] or "generated",
        key_hash=hash_api_key(plain),
        is_active=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return schemas.ApiKeyCreateOut(id=record.id, name=record.name, api_key=plain, created_at=record.created_at)


@router.post("/auth/keys/{key_id}/deactivate", response_model=schemas.ApiKeyOut)
def deactivate_api_key(key_id: int, db: Session = Depends(get_db)):
    key = db.query(models.ApiKey).filter(models.ApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    key.is_active = False
    db.add(key)
    db.commit()
    db.refresh(key)
    return key
