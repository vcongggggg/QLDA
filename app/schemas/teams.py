from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.schemas.kpi import KPIUserResult
from app.schemas.reports import DashboardSummary
from app.schemas.tasks import TaskOut

class TeamsBotActivity(BaseModel):
    type: str
    id: str | None = None
    serviceUrl: str | None = None
    channelId: str | None = None
    from_property: dict | None = Field(default=None, alias="from")
    conversation: dict | None = None
    recipient: dict | None = None
    text: str | None = None
    value: dict | None = None

class TeamsQueueStatsOut(BaseModel):
    queued: int
    sent: int
    failed: int

class TeamsSummaryOut(BaseModel):
    month: str
    dashboard: DashboardSummary
    kpi: list[KPIUserResult]
    tasks: list[TaskOut]
    can_manage_queue: bool
    queue_stats: TeamsQueueStatsOut | None = None
