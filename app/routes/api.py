from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies import require_api_key
from app.services.api_keys import generate_api_key, hash_api_key
from app.services.crypto_service import decrypt_text, encrypt_text
from app.services.reminder_dispatcher import dispatch_reminder
from app.services.summary_service import get_today_summary

router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(require_api_key)])


@router.get("/captures", response_model=list[schemas.CaptureOut])
def list_captures(db: Session = Depends(get_db)):
    return db.query(models.Capture).order_by(models.Capture.created_at.desc()).limit(200).all()


@router.post("/captures", response_model=schemas.CaptureOut)
def create_capture(payload: schemas.CaptureCreate, db: Session = Depends(get_db)):
    capture = models.Capture(content=payload.content, url=payload.url)
    db.add(capture)
    db.commit()
    db.refresh(capture)
    return capture


@router.get("/tasks", response_model=list[schemas.TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(models.Task).order_by(models.Task.created_at.desc()).limit(200).all()


@router.post("/tasks", response_model=schemas.TaskOut)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    task = models.Task(title=payload.title, priority=payload.priority, due_date=payload.due_date)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: int, payload: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.status is not None:
        task.status = payload.status
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.due_date is not None:
        task.due_date = payload.due_date

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/reminders", response_model=list[schemas.ReminderOut])
def list_reminders(db: Session = Depends(get_db)):
    return db.query(models.Reminder).order_by(models.Reminder.remind_at.asc()).limit(500).all()


@router.post("/reminders", response_model=schemas.ReminderOut)
def create_reminder(payload: schemas.ReminderCreate, db: Session = Depends(get_db)):
    channel = payload.channel.lower().strip()
    if channel != "telegram":
        raise HTTPException(status_code=400, detail="channel must be telegram")

    if payload.is_recurring and payload.recurrence_minutes is None:
        raise HTTPException(status_code=400, detail="recurrence_minutes is required when is_recurring=true")

    recurrence_minutes = payload.recurrence_minutes if payload.is_recurring else None
    reminder = models.Reminder(
        message=payload.message,
        channel=channel,
        target=payload.target,
        remind_at=payload.remind_at,
        is_recurring=payload.is_recurring,
        recurrence_minutes=recurrence_minutes,
        status="pending",
    )
    if reminder.remind_at < datetime.utcnow():
        reminder.status = "pending"

    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.post("/reminders/{reminder_id}/send-now")
def send_reminder_now(reminder_id: int, db: Session = Depends(get_db)):
    reminder = db.query(models.Reminder).filter(models.Reminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    ok, detail = dispatch_reminder(db, reminder)
    return {"ok": ok, "detail": detail, "status": reminder.status}


@router.get("/summary/today", response_model=schemas.SummaryOut)
def today_summary(db: Session = Depends(get_db)):
    return get_today_summary(db)


@router.get("/notes", response_model=list[schemas.NoteOut])
def list_notes(db: Session = Depends(get_db)):
    notes = db.query(models.EncryptedNote).order_by(models.EncryptedNote.updated_at.desc()).limit(300).all()
    output: list[schemas.NoteOut] = []
    for note in notes:
        try:
            content = decrypt_text(note.cipher_text)
        except Exception:
            content = "<decryption failed>"
        output.append(
            schemas.NoteOut(
                id=note.id,
                title=note.title,
                content=content,
                created_at=note.created_at,
                updated_at=note.updated_at,
            )
        )
    return output


@router.post("/notes", response_model=schemas.NoteOut)
def create_note(payload: schemas.NoteCreate, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    note = models.EncryptedNote(
        title=payload.title.strip(),
        cipher_text=encrypt_text(payload.content),
        created_at=now,
        updated_at=now,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return schemas.NoteOut(
        id=note.id,
        title=note.title,
        content=payload.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.delete("/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(models.EncryptedNote).filter(models.EncryptedNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()
    return {"ok": True}


@router.get("/telegram/allowlist", response_model=list[schemas.TelegramUserOut])
def list_allowed_telegram_users(db: Session = Depends(get_db)):
    return db.query(models.AllowedTelegramUser).order_by(models.AllowedTelegramUser.created_at.desc()).all()


@router.post("/telegram/allowlist", response_model=schemas.TelegramUserOut)
def add_allowed_telegram_user(payload: schemas.TelegramUserCreate, db: Session = Depends(get_db)):
    user_id = payload.telegram_user_id.strip()
    existing = db.query(models.AllowedTelegramUser).filter(models.AllowedTelegramUser.telegram_user_id == user_id).first()
    if existing:
        existing.display_name = payload.display_name.strip()
        existing.is_active = True
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    record = models.AllowedTelegramUser(
        telegram_user_id=user_id,
        display_name=payload.display_name.strip(),
        is_active=True,
    )
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


@router.get("/auth/keys", response_model=list[schemas.ApiKeyOut])
def list_api_keys(db: Session = Depends(get_db)):
    return db.query(models.ApiKey).order_by(models.ApiKey.created_at.desc()).all()


@router.post("/auth/keys", response_model=schemas.ApiKeyCreateOut)
def create_api_key(payload: schemas.ApiKeyCreate, db: Session = Depends(get_db)):
    plain = generate_api_key()
    record = models.ApiKey(
        name=payload.name.strip() or "generated",
        key_hash=hash_api_key(plain),
        is_active=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return schemas.ApiKeyCreateOut(
        id=record.id,
        name=record.name,
        api_key=plain,
        created_at=record.created_at,
    )


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
