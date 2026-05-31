from datetime import datetime

from pydantic import BaseModel, Field


class AdminSearchResultOut(BaseModel):
    type: str
    id: int | None = None
    title: str
    subtitle: str | None = None
    url: str | None = None


class AdminSearchOut(BaseModel):
    query: str
    results: list[AdminSearchResultOut]


class AdminConfigFlagOut(BaseModel):
    key: str
    value: str | bool | int | float | None
    source: str
    sensitive: bool = False


class SystemNotificationCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    message: str = Field(min_length=3, max_length=1000)
    audience: str = Field(default="all", pattern="^(all|admin|manager|hr)$")


class SystemNotificationBroadcastOut(BaseModel):
    created: int
    audience: str


class ComplianceRequestCreate(BaseModel):
    subject_user_id: int
    request_type: str = Field(pattern="^(export|delete)$")
    reason: str = Field(min_length=3, max_length=1000)


class ComplianceRequestUpdate(BaseModel):
    status: str = Field(pattern="^(open|in_review|approved|rejected|fulfilled)$")
    resolution_note: str | None = Field(default=None, max_length=1000)


class ComplianceRequestOut(BaseModel):
    id: int
    subject_user_id: int
    subject_email: str | None = None
    request_type: str
    status: str
    reason: str
    resolution_note: str | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime


class MaintenanceWindowCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    message: str = Field(min_length=3, max_length=1000)
    starts_at: datetime
    ends_at: datetime
    status: str = Field(default="scheduled", pattern="^(scheduled|active|completed|cancelled)$")


class MaintenanceWindowUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    message: str | None = Field(default=None, min_length=3, max_length=1000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str | None = Field(default=None, pattern="^(scheduled|active|completed|cancelled)$")


class MaintenanceWindowOut(BaseModel):
    id: int
    title: str
    message: str
    starts_at: datetime
    ends_at: datetime
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime

