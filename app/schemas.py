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


class RoleOut(BaseModel):
    slug: str
    name: str
    description: str | None = None
    is_system: bool | int = True


class PermissionOut(BaseModel):
    key: str
    name: str
    description: str | None = None
    category: str


class RolePermissionsOut(BaseModel):
    role: RoleOut
    permissions: list[PermissionOut]


class RolePermissionsUpdate(BaseModel):
    permission_keys: list[str] = Field(default_factory=list, max_length=100)


class RagDocumentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    source_label: str | None = Field(default=None, max_length=120)
    content: str = Field(min_length=20, max_length=50000)


class RagDocumentOut(BaseModel):
    id: int
    title: str
    source_label: str | None = None
    created_by: int
    created_at: datetime
    chunk_count: int = 0


class RagQueryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    limit: int = Field(default=5, ge=1, le=10)


class RagQueryMatch(BaseModel):
    document_id: int
    document_title: str
    source_label: str | None = None
    content: str
    score: float


class RagQueryResponse(BaseModel):
    matches: list[RagQueryMatch]


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


class TaskCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class TaskCommentOut(BaseModel):
    id: int
    task_id: int
    author_user_id: int
    author_name: str | None = None
    body: str
    created_at: datetime


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


class TaskDetailOut(TaskOut):
    assignee_name: str | None = None
    project_name: str | None = None
    sprint_name: str | None = None
    due_state: str
    comments: list[TaskCommentOut]
    activity_logs: list["AuditLogOut"]


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


class OpsFailedQueueItemOut(BaseModel):
    id: int
    user_id: int | None = None
    channel: str
    status: str
    attempts: int
    max_attempts: int
    last_error_summary: str | None = None
    next_retry_at: datetime | None = None
    created_at: datetime
    sent_at: datetime | None = None


class OpsQueueStatusOut(BaseModel):
    queued_count: int
    sent_count: int
    failed_count: int
    latest_failed_items: list[OpsFailedQueueItemOut]


class OpsOverdueProjectOut(BaseModel):
    project_id: int | None = None
    project_name: str
    overdue_count: int


class OpsOverdueSprintOut(BaseModel):
    sprint_id: int | None = None
    sprint_name: str
    project_id: int | None = None
    project_name: str
    overdue_count: int


class OpsOverdueSpikeOut(BaseModel):
    overdue_count: int
    threshold: int
    alert: bool
    top_projects: list[OpsOverdueProjectOut]
    top_sprints: list[OpsOverdueSprintOut]


class OpsDashboardOut(BaseModel):
    can_manage_queue: bool
    audit_logs: list[AuditLogOut]
    notification_queue: OpsQueueStatusOut
    overdue_spike: OpsOverdueSpikeOut


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


class TaskReminderRunOut(BaseModel):
    due_soon_created: int
    overdue_created: int
    skipped_duplicates: int


class QueueProcessOut(BaseModel):
    processed: int
    sent: int
    retried: int
    failed: int


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


class PlanCompletionOut(BaseModel):
    total_items: int
    completed_items: int
    completion_percent: float
    items: list[dict]


class TaskBreakdownRequest(BaseModel):
    text: str = Field(min_length=10, max_length=50000)
    project_context: str | None = Field(default=None, max_length=2000)
    max_tasks: int = Field(default=8, ge=1, le=30)
    use_rag: bool = True
    rag_query: str | None = Field(default=None, max_length=1000)


class TaskBreakdownItem(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1200)
    story_points: int = Field(default=3, ge=1, le=13)
    difficulty: str = Field(default="medium", description="easy|medium|hard")
    deadline_offset_days: int = Field(default=7, ge=1, le=90)
    rationale: str | None = Field(default=None, max_length=500)
    selected: bool = True


class TaskBreakdownResponse(BaseModel):
    ai_draft_id: int
    status: str = "draft"
    source: str
    items: list[TaskBreakdownItem]
    warnings: list[str] = []
    retrieved_context_count: int = 0
    retrieved_sources: list[str] = []


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


class TaskImportRequest(BaseModel):
    ai_draft_id: int
    assignee_id: int
    project_id: int | None = None
    sprint_id: int | None = None
    base_deadline: datetime | None = None


class TaskImportResponse(BaseModel):
    created_count: int
    tasks: list[TaskOut]
