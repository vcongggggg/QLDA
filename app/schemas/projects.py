from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    department_id: int | None = None
    manager_id: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str = Field(default="active", description="active|on_hold|done|archived")

class ProjectOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    department_id: int | None = None
    manager_id: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str
    created_at: datetime

class ProjectMemberCreate(BaseModel):
    user_id: int
    role: str = Field(min_length=2, max_length=40)

class ProjectMemberOut(BaseModel):
    id: int
    project_id: int
    user_id: int
    role: str
    joined_at: datetime

class ProjectProgressOut(BaseModel):
    project_id: int
    total_tasks: int
    done_tasks: int
    overdue_tasks: int
    completion_rate: float
    total_story_points: int
    completed_story_points: int

class ProjectRiskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str | None = None
    probability: str = Field(description="low|medium|high")
    impact: str = Field(description="low|medium|high")
    mitigation_plan: str | None = None
    owner_user_id: int | None = None
    status: str = Field(default="open", description="open|mitigated|closed")

class ProjectRiskOut(BaseModel):
    id: int
    project_id: int
    title: str
    description: str | None = None
    probability: str
    impact: str
    mitigation_plan: str | None = None
    owner_user_id: int | None = None
    status: str
    created_at: datetime

class WeeklyStatusCreate(BaseModel):
    sprint_id: int | None = None
    week_label: str = Field(min_length=4, max_length=40)
    progress_percent: float = Field(ge=0, le=100)
    rag_status: str = Field(description="red|amber|green")
    summary: str = Field(min_length=3, max_length=1000)
    next_steps: str | None = None
    blocker: str | None = None

class WeeklyStatusOut(BaseModel):
    id: int
    project_id: int
    sprint_id: int | None = None
    week_label: str
    progress_percent: float
    rag_status: str
    summary: str
    next_steps: str | None = None
    blocker: str | None = None
    created_by: int
    created_at: datetime
