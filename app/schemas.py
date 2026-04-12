from datetime import datetime

from pydantic import BaseModel, Field


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


class TaskCreate(BaseModel):
    title: str = Field(min_length=1)
    priority: str = "medium"
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: datetime | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    due_date: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


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


class SummaryOut(BaseModel):
    captures_today: int
    tasks_open: int
    reminders_pending: int
    reminders_sent_today: int


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
