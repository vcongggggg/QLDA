from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.schemas.tasks import TaskBreakdownItem

class AiTaskDraftSummary(BaseModel):
    id: int
    source_type: str
    source_summary: str | None = None
    source_name: str | None = None
    status: str
    reviewer_id: int | None = None
    reviewed_at: datetime | None = None
    imported_at: datetime | None = None
    review_note: str | None = None
    edit_reason: str | None = None
    created_by: int
    created_at: datetime
    item_count: int = 0

class AiTaskDraftDetail(AiTaskDraftSummary):
    items: list[TaskBreakdownItem]

class AiTaskDraftReviewRequest(BaseModel):
    items: list[TaskBreakdownItem] = Field(min_length=1, max_length=30)
    review_note: str | None = Field(default=None, max_length=1000)
    edit_reason: str | None = Field(default=None, max_length=1000)
