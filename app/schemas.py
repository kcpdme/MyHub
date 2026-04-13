from __future__ import annotations

from datetime import datetime
from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ─────────────────────────────────────────────
# Paginated response wrapper
# ─────────────────────────────────────────────

class Page(BaseModel, Generic[T]):
    """Standard paginated list response used by all list endpoints."""
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int


# ─────────────────────────────────────────────
# Captures
# ─────────────────────────────────────────────

class CaptureCreate(BaseModel):
    content: str = Field(min_length=1)
    url: str = ""


class CaptureUpdate(BaseModel):
    content: str | None = None
    url: str | None = None


class CaptureOut(BaseModel):
    id: int
    content: str
    url: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Tasks
# ─────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    priority: str = "medium"
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: datetime | None = None
    clear_due_date: bool = False


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Reminders
# ─────────────────────────────────────────────

class ReminderCreate(BaseModel):
    message: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    target: str = Field(min_length=1)
    remind_at: datetime
    is_recurring: bool = False
    recurrence_minutes: int | None = Field(default=None, ge=1)


class ReminderOut(BaseModel):
    id: int
    message: str
    channel: str
    target: str
    remind_at: datetime
    is_recurring: bool
    recurrence_minutes: int | None
    status: str
    last_error: str
    created_at: datetime
    sent_at: datetime | None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────

class SummaryOut(BaseModel):
    captures_today: int
    tasks_open: int
    reminders_pending: int
    reminders_sent_today: int
    notes_total: int = 0
    tasks_done_today: int = 0


# ─────────────────────────────────────────────
# API Keys
# ─────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    name: str = "generated"


class ApiKeyCreateOut(BaseModel):
    id: int
    name: str
    api_key: str
    created_at: datetime


class ApiKeyOut(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Notes
# ─────────────────────────────────────────────

class NoteCreate(BaseModel):
    title: str = ""
    content: str = Field(min_length=1)


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────
# Tags
# ─────────────────────────────────────────────

class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = "#6366f1"


class TagOut(BaseModel):
    id: int
    name: str
    color: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Telegram
# ─────────────────────────────────────────────

class TelegramUserCreate(BaseModel):
    telegram_user_id: str = Field(min_length=1)
    display_name: str = ""


class TelegramUserOut(BaseModel):
    id: int
    telegram_user_id: str
    display_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class InboxItemOut(BaseModel):
    id: int
    source: str
    telegram_user_id: str
    chat_id: str
    message_id: int
    item_type: str
    text: str
    file_id: str
    file_unique_id: str
    media_group_id: str
    is_archived: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class InboxPromoteTaskCreate(BaseModel):
    priority: str = "medium"


# ─────────────────────────────────────────────
# Habits
# ─────────────────────────────────────────────

class HabitCreate(BaseModel):
    name: str = Field(min_length=1)
    icon: str = "check"
    color: str = "green"


class HabitOut(BaseModel):
    id: int
    name: str
    icon: str
    color: str
    is_active: bool
    created_at: datetime
    streak: int = 0
    completed_today: bool = False


class HabitLogOut(BaseModel):
    id: int
    habit_id: int
    log_date: str
    completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class HabitToggle(BaseModel):
    date: str | None = None


# ─────────────────────────────────────────────
# Audit log
# ─────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int | None
    action: str
    actor: str
    detail_json: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Outbound webhooks
# ─────────────────────────────────────────────

class WebhookSubscriptionCreate(BaseModel):
    url: str = Field(min_length=1)
    event_types: str = "*"
    secret: str = ""


class WebhookSubscriptionOut(BaseModel):
    id: int
    url: str
    event_types: str
    is_active: bool
    created_at: datetime
    last_fired_at: datetime | None

    model_config = {"from_attributes": True}


class WebhookDeliveryLogOut(BaseModel):
    id: int
    subscription_id: int
    event_type: str
    response_status: int | None
    success: bool
    error_message: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Search
# ─────────────────────────────────────────────

class SearchResult(BaseModel):
    entity_type: str   # "capture", "task", "note", "inbox"
    entity_id: int
    title: str
    snippet: str
    created_at: datetime
