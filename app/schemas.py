from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: str = Field(description="admin|manager|staff|hr")
    department: str | None = None


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    aad_object_id: str | None = None
    role: str
    department: str | None = None


class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    assignee_id: int
    project_id: int | None = None
    sprint_id: int | None = None
    story_points: int = Field(default=1, ge=1, le=100)
    difficulty: str = Field(description="easy|medium|hard")
    deadline: datetime


class TaskStatusUpdate(BaseModel):
    status: str = Field(description="todo|doing|done")


class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None
    assignee_id: int
    project_id: int | None = None
    sprint_id: int | None = None
    story_points: int
    difficulty: str
    status: str
    deadline: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class KPIUserResult(BaseModel):
    user_id: int
    user_name: str
    month: str
    done_on_time: int
    done_late: int
    overdue_unfinished: int
    score: float


class DashboardSummary(BaseModel):
    month: str
    total_tasks: int
    todo_tasks: int
    doing_tasks: int
    done_tasks: int
    overdue_tasks: int
    avg_kpi_score: float


class KPIAdjustmentCreate(BaseModel):
    user_id: int
    month: str = Field(description="YYYY-MM")
    points: float
    reason: str = Field(min_length=3, max_length=500)


class KPIAdjustmentOut(BaseModel):
    id: int
    user_id: int
    month: str
    points: float
    reason: str
    created_by: int
    created_at: datetime


class AuditLogOut(BaseModel):
    id: int
    actor_user_id: int | None
    actor_name: str | None = None
    action: str
    entity: str
    entity_id: int | None = None
    detail: str | None = None
    created_at: datetime


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


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=20)


class DepartmentOut(BaseModel):
    id: int
    name: str
    code: str
    created_at: datetime


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


class ProjectProgressOut(BaseModel):
    project_id: int
    total_tasks: int
    done_tasks: int
    overdue_tasks: int
    completion_rate: float
    total_story_points: int
    completed_story_points: int


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


class SprintVelocityOut(BaseModel):
    sprint_id: int
    sprint_name: str
    status: str
    planned_story_points: int
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


class SystemMetricsOut(BaseModel):
    users: int
    projects: int
    tasks: int
    overdue_tasks: int
    open_risks: int
    queued_notifications: int
    failed_notifications: int


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


class QueueProcessOut(BaseModel):
    processed: int
    sent: int
    retried: int
    failed: int


class PlanCompletionOut(BaseModel):
    total_items: int
    completed_items: int
    completion_percent: float
    items: list[dict]
