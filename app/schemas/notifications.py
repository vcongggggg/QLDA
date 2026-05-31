from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class NotificationQueueOut(BaseModel):
    id: int
    user_id: int | None = None
    channel: str
    payload: dict
    status: str
    attempts: int
    max_attempts: int
    last_error: str | None = None
    next_retry_at: datetime | None = None
    created_at: datetime
    sent_at: datetime | None = None

class AppNotificationOut(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: str
    entity_type: str
    entity_id: int
    is_read: bool
    created_at: datetime
    read_at: datetime | None = None

class UnreadNotificationCountOut(BaseModel):
    unread_count: int

class MarkAllReadOut(BaseModel):
    updated: int

class QueueProcessOut(BaseModel):
    processed: int
    sent: int
    retried: int
    failed: int
