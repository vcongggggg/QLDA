from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class KPIUserResult(BaseModel):
    user_id: int
    user_name: str
    month: str
    done_on_time: int
    done_late: int
    overdue_unfinished: int
    score: float
    target_score: float | None = None
    progress_percent: float | None = None
    gap: float | None = None

class KPIConfigOut(BaseModel):
    id: int | None = None
    difficulty_multiplier: dict[str, float]
    on_time_points: float
    late_points: float
    overdue_unfinished_points: float
    fallback_difficulty: str = "easy"
    change_reason: str | None = None
    updated_by: int | None = None
    updated_at: datetime | None = None

class KPIConfigUpdate(BaseModel):
    difficulty_multiplier: dict[str, float] = Field(default_factory=dict)
    on_time_points: float
    late_points: float
    overdue_unfinished_points: float
    fallback_difficulty: str = "easy"
    change_reason: str = Field(min_length=3, max_length=500)

class KPITransactionOut(BaseModel):
    id: int
    event_key: str
    source_type: str
    source_id: int | None = None
    user_id: int
    month: str
    points: float
    reason: str
    status: str
    created_at: datetime
    reversed_at: datetime | None = None

class KPITransactionRebuildOut(BaseModel):
    month: str
    active_count: int
    reversed_count: int

class KPIAdjustmentCreate(BaseModel):
    user_id: int
    month: str = Field(description="YYYY-MM")
    points: float
    reason: str = Field(min_length=3, max_length=500)

class KPIAdjustmentReview(BaseModel):
    review_reason: str = Field(min_length=3, max_length=500)

class KPIAdjustmentOut(BaseModel):
    id: int
    user_id: int
    month: str
    points: float
    reason: str
    created_by: int
    created_at: datetime
    status: str = "approved"
    reviewer_id: int | None = None
    reviewed_at: datetime | None = None
    review_reason: str | None = None

class KPITargetCreate(BaseModel):
    user_id: int
    month: str = Field(description="YYYY-MM")
    target_score: float = Field(ge=0)
    department_id: int | None = None
    team: str | None = Field(default=None, max_length=120)

class KPITargetUpdate(BaseModel):
    target_score: float | None = Field(default=None, ge=0)
    department_id: int | None = None
    team: str | None = Field(default=None, max_length=120)

class KPITargetOut(BaseModel):
    id: int
    user_id: int
    user_name: str | None = None
    month: str
    target_score: float
    department_id: int | None = None
    team: str | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime

class KPITargetProgressOut(BaseModel):
    user_id: int
    user_name: str
    month: str
    score: float
    target_score: float
    progress_percent: float
    gap: float
    department_id: int | None = None
    department_name: str | None = None

class KPITargetImportOut(BaseModel):
    upserted_count: int
    targets: list[KPITargetOut]

class KPIHistoryRow(BaseModel):
    user_id: int
    user_name: str
    month: str
    score: float
    target_score: float | None = None
    progress_percent: float | None = None
    gap: float | None = None

class KPITeamSummaryOut(BaseModel):
    month: str
    user_count: int
    avg_score: float
    avg_target: float | None = None
    below_target_count: int

class KPIDepartmentBreakdownOut(BaseModel):
    department_id: int | None = None
    department_name: str
    month: str
    user_count: int
    avg_score: float
    avg_target: float | None = None
    below_target_count: int
