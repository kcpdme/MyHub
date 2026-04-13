from datetime import datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ─────────────────────────────────────────────
# Core entities
# ─────────────────────────────────────────────

class Capture(Base):
    __tablename__ = "captures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="todo", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(32), default="medium", nullable=False, index=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    # updated_at tracks the last time any field changed (set by application logic on every PATCH).
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    # completed_at is set once when status transitions to "done".
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    remind_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reminder_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_response: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DailyDigestLog(Base):
    __tablename__ = "daily_digest_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    digest_date: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


# ─────────────────────────────────────────────
# Auth / API Keys
# ─────────────────────────────────────────────

class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="default", nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OtpCode(Base):
    """DB-backed OTP for the web login flow. Replaces in-memory globals."""
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # SHA-256 hash of the 6-digit code so the plaintext is never stored.
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class LoginAttempt(Base):
    """Tracks failed OTP verification attemps per IP for brute-force protection."""
    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


# ─────────────────────────────────────────────
# Notes
# ─────────────────────────────────────────────

class EncryptedNote(Base):
    __tablename__ = "encrypted_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    cipher_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


# ─────────────────────────────────────────────
# Tags (shared across tasks and notes)
# ─────────────────────────────────────────────

class Tag(Base):
    """Global tag registry. Tags have a name and a display colour."""
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    color: Mapped[str] = mapped_column(String(32), default="#6366f1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class TaskTag(Base):
    """Join table: tasks ↔ tags (many-to-many)."""
    __tablename__ = "task_tags"
    __table_args__ = (UniqueConstraint("task_id", "tag_id", name="uq_task_tag"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tag_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)


class NoteTag(Base):
    """Join table: notes ↔ tags (many-to-many)."""
    __tablename__ = "note_tags"
    __table_args__ = (UniqueConstraint("note_id", "tag_id", name="uq_note_tag"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    note_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tag_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)


# ─────────────────────────────────────────────
# Audit log
# ─────────────────────────────────────────────

class AuditLog(Base):
    """Immutable record of every significant state change in the system."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # actor: "api", "telegram", "scheduler", "web"
    actor: Mapped[str] = mapped_column(String(64), default="api", nullable=False)
    detail_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


# ─────────────────────────────────────────────
# Outbound webhooks
# ─────────────────────────────────────────────

class WebhookSubscription(Base):
    """An outbound webhook endpoint that receives events from this hub."""
    __tablename__ = "webhook_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    # Comma-separated event types, or "*" for all.
    event_types: Mapped[str] = mapped_column(String(512), default="*", nullable=False)
    # Optional HMAC-SHA256 secret. If set, each request carries an X-Hub-Signature-256 header.
    secret: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WebhookDeliveryLog(Base):
    """Records every outbound webhook delivery attempt."""
    __tablename__ = "webhook_delivery_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subscription_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


# ─────────────────────────────────────────────
# Telegram
# ─────────────────────────────────────────────

class AllowedTelegramUser(Base):
    __tablename__ = "allowed_telegram_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_user_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class TelegramInboxItem(Base):
    __tablename__ = "telegram_inbox_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), default="telegram", nullable=False)
    telegram_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    file_id: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    file_unique_id: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    media_group_id: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


# ─────────────────────────────────────────────
# Habits
# ─────────────────────────────────────────────

class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str] = mapped_column(String(32), default="check", nullable=False)
    color: Mapped[str] = mapped_column(String(32), default="green", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    habit_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    log_date: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
