from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.schemas.audit import AuditLogOut

class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    assignee_id: int
    project_id: int | None = None
    sprint_id: int | None = None
    story_points: int = Field(default=1, ge=1, le=100)
    difficulty: str = Field(description="easy|medium|hard")
    priority: str = Field(default="medium", description="low|medium|high|urgent")
    labels: list[str] = Field(default_factory=list, max_length=20)
    checklist: list[str] = Field(default_factory=list, max_length=50)
    subtasks: list[str] = Field(default_factory=list, max_length=50)
    dependencies: list[str] = Field(default_factory=list, max_length=50)
    attachment_metadata: list[dict] = Field(default_factory=list, max_length=20)
    deadline: datetime

class TaskStatusUpdate(BaseModel):
    status: str = Field(description="todo|doing|done")

class TaskDeadlineExtension(BaseModel):
    deadline: datetime
    reason: str = Field(min_length=1, max_length=500)

class TaskMetadataUpdate(BaseModel):
    priority: str | None = Field(default=None, description="low|medium|high|urgent")
    labels: list[str] | None = Field(default=None, max_length=20)
    checklist: list[str] | None = Field(default=None, max_length=50)
    subtasks: list[str] | None = Field(default=None, max_length=50)
    dependencies: list[str] | None = Field(default=None, max_length=50)
    attachment_metadata: list[dict] | None = Field(default=None, max_length=20)

class TaskBulkAction(BaseModel):
    task_ids: list[int] = Field(default_factory=list, max_length=200)
    status: str | None = Field(default=None, description="todo|doing|done")
    assignee_id: int | None = None
    sprint_id: int | None = None
    move_to_backlog: bool = False

class TaskBulkActionResult(BaseModel):
    updated: int

class TaskDuplicateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    assignee_id: int | None = None
    sprint_id: int | None = None
    deadline: datetime | None = None

class BacklogMoveToSprint(BaseModel):
    task_ids: list[int] = Field(default_factory=list, max_length=200)
    sprint_id: int

class SprintCarryoverRequest(BaseModel):
    target_sprint_id: int

class KanbanSavedFilterCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    filters: dict = Field(default_factory=dict)
    is_default: bool = False

class KanbanSavedFilterOut(BaseModel):
    id: int
    user_id: int
    name: str
    filters: dict
    is_default: bool
    created_at: datetime
    updated_at: datetime

class KanbanWipPolicyUpdate(BaseModel):
    project_id: int | None = None
    sprint_id: int | None = None
    todo_limit: int | None = Field(default=None, ge=0, le=1000)
    doing_limit: int | None = Field(default=None, ge=0, le=1000)
    done_limit: int | None = Field(default=None, ge=0, le=1000)

class KanbanWipPolicyOut(BaseModel):
    id: int
    project_id: int | None = None
    sprint_id: int | None = None
    todo_limit: int | None = None
    doing_limit: int | None = None
    done_limit: int | None = None
    created_at: datetime
    updated_at: datetime

class KanbanColumnSummary(BaseModel):
    status: str
    task_count: int
    story_points: int
    overdue_count: int = 0
    wip_limit: int | None = None
    wip_exceeded: bool = False

class KanbanSummaryOut(BaseModel):
    columns: list[KanbanColumnSummary]
    total_tasks: int
    total_story_points: int
    overdue_open_tasks: int = 0
    wip_exceeded_columns: int = 0
    wip_policy: KanbanWipPolicyOut | None = None

class TaskImportResult(BaseModel):
    created_count: int
    tasks: list["TaskOut"]

class TaskTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    project_id: int | None = None
    story_points: int = Field(default=1, ge=1, le=100)
    difficulty: str = Field(default="medium")
    priority: str = Field(default="medium")
    labels: list[str] = Field(default_factory=list, max_length=20)
    checklist: list[str] = Field(default_factory=list, max_length=50)
    subtasks: list[str] = Field(default_factory=list, max_length=50)

class TaskTemplateOut(TaskTemplateCreate):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime

class TaskFromTemplateRequest(BaseModel):
    assignee_id: int
    project_id: int | None = None
    sprint_id: int | None = None
    deadline: datetime
    title: str | None = Field(default=None, min_length=2, max_length=200)

class RecurringTaskRuleCreate(BaseModel):
    template_id: int
    assignee_id: int
    project_id: int | None = None
    sprint_id: int | None = None
    frequency: str = Field(description="weekly|monthly")
    next_run_at: datetime
    active: bool = True

class RecurringTaskRuleOut(RecurringTaskRuleCreate):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime

class RecurringTaskRunResult(BaseModel):
    created_count: int
    tasks: list["TaskOut"]

class BacklogGroomingUpdate(BaseModel):
    backlog_rank: int | None = Field(default=None, ge=0, le=1000000)
    readiness_status: str | None = Field(default=None, max_length=40)
    acceptance_notes: str | None = Field(default=None, max_length=2000)

class MilestoneCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    due_date: datetime | None = None
    status: str = Field(default="planned")

class MilestoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = None
    due_date: datetime | None = None
    status: str | None = None

class MilestoneOut(BaseModel):
    id: int
    project_id: int
    name: str
    description: str | None = None
    due_date: datetime | None = None
    status: str
    created_at: datetime
    updated_at: datetime

class TaskDependencyUpdate(BaseModel):
    dependency_ids: list[int] = Field(default_factory=list, max_length=50)

class TaskMilestoneUpdate(BaseModel):
    milestone_id: int | None = None

class TaskCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

class TaskCommentOut(BaseModel):
    id: int
    task_id: int
    author_user_id: int
    author_name: str | None = None
    body: str
    created_at: datetime

class TaskAiDetailOut(BaseModel):
    id: int
    task_id: int
    source_ai_draft_id: int
    type: str | None = None
    business_goal: str | None = None
    subtasks: list[str] = []
    acceptance_criteria: list[str] = []
    data_requirements: list[str] = []
    ui_components: list[str] = []
    test_cases: list[str] = []
    dependencies: list[str] = []
    risks: list[str] = []
    demo_value: str | None = None
    suggested_role: str | None = None
    created_at: datetime
    updated_at: datetime

class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None
    assignee_id: int
    project_id: int | None = None
    sprint_id: int | None = None
    story_points: int
    difficulty: str
    priority: str = "medium"
    labels: list[str] = []
    checklist: list[str] = []
    subtasks: list[str] = []
    dependencies: list[str] = []
    attachment_metadata: list[dict] = []
    backlog_rank: int | None = None
    readiness_status: str | None = None
    acceptance_notes: str | None = None
    milestone_id: int | None = None
    dependency_ids: list[int] = []
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
    ai_detail: TaskAiDetailOut | None = None
    comments: list[TaskCommentOut]
    activity_logs: list["AuditLogOut"]

class TaskReminderRunOut(BaseModel):
    due_soon_created: int
    overdue_created: int
    skipped_duplicates: int

class TaskBreakdownRequest(BaseModel):
    text: str = Field(min_length=10, max_length=50000)
    project_context: str | None = Field(default=None, max_length=2000)
    max_tasks: int = Field(default=8, ge=1, le=30)
    use_rag: bool = True
    rag_query: str | None = Field(default=None, max_length=1000)

class TaskBreakdownItem(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    type: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=1200)
    business_goal: str | None = Field(default=None, max_length=1200)
    subtasks: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    data_requirements: list[str] = Field(default_factory=list)
    ui_components: list[str] = Field(default_factory=list)
    test_cases: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    demo_value: str | None = Field(default=None, max_length=1200)
    suggested_role: str | None = Field(default=None, max_length=120)
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

class TaskImportRequest(BaseModel):
    ai_draft_id: int
    assignee_id: int
    project_id: int | None = None
    sprint_id: int | None = None
    base_deadline: datetime | None = None

class TaskImportResponse(BaseModel):
    created_count: int
    tasks: list[TaskOut]
