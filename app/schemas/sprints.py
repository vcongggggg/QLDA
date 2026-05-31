from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class SprintCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    goal: str | None = None
    start_date: datetime
    end_date: datetime

class SprintOut(BaseModel):
    id: int
    project_id: int
    name: str
    goal: str | None = None
    start_date: datetime
    end_date: datetime
    status: str
    created_at: datetime

class SprintStatusUpdate(BaseModel):
    status: str = Field(description="planned|active|completed")

class SprintTaskAssign(BaseModel):
    task_ids: list[int]

class BurndownPoint(BaseModel):
    date: str
    remaining_points: int

class SprintCapacityCreate(BaseModel):
    user_id: int
    capacity_hours: float = Field(gt=0)
    allocated_hours: float = Field(default=0, ge=0)

class SprintCapacityOut(BaseModel):
    id: int
    sprint_id: int
    user_id: int
    capacity_hours: float
    allocated_hours: float
    created_at: datetime

class WorkloadWarningOut(BaseModel):
    user_id: int
    user_name: str
    sprint_id: int
    sprint_name: str
    workload_points: int
    capacity_points: float | None = None
    open_task_count: int
    overdue_task_count: int
    overloaded: bool
    risk_level: str
    reasons: list[str]

class SprintVelocityOut(BaseModel):
    sprint_id: int
    sprint_name: str
    status: str
    planned_story_points: int
    completed_story_points: int
