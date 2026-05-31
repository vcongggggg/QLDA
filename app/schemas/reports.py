from datetime import datetime
from pydantic import BaseModel, Field

class DashboardSummary(BaseModel):
    month: str
    total_tasks: int
    todo_tasks: int
    doing_tasks: int
    done_tasks: int
    open_tasks: int
    overdue_tasks: int
    completion_rate: float
    avg_kpi_score: float

class AnalyticsScope(BaseModel):
    type: str
    user_id: int | None = None

class AnalyticsProductivity(BaseModel):
    total_tasks: int
    done_tasks: int
    open_tasks: int
    completion_rate: float
    total_story_points: int
    completed_story_points: int

class AnalyticsWorkloadRow(BaseModel):
    user_id: int | None = None
    assignee_name: str
    total_tasks: int
    done_tasks: int
    open_tasks: int
    overdue_open_tasks: int
    story_points: int
    completed_story_points: int

class AnalyticsBacklogHealth(BaseModel):
    overdue_open_tasks: int
    backlog_open_tasks: int
    unassigned_open_tasks: int

class AnalyticsCycleTime(BaseModel):
    done_tasks_with_cycle_time: int
    avg_cycle_time_days: float | None = None
    min_cycle_time_days: float | None = None
    max_cycle_time_days: float | None = None

class AnalyticsTaskStatus(BaseModel):
    todo_tasks: int
    doing_tasks: int
    done_tasks: int

class AnalyticsUtilization(BaseModel):
    assigned_tasks: int
    unassigned_tasks: int
    assigned_story_points: int
    unassigned_story_points: int
    utilization_rate: float

class AnalyticsVelocityRow(BaseModel):
    sprint_id: int | None = None
    sprint_name: str
    planned_story_points: int
    completed_story_points: int
    completion_rate: float

class AnalyticsProjectEffortRow(BaseModel):
    project_id: int | None = None
    project_name: str
    total_tasks: int
    done_tasks: int
    overdue_open_tasks: int
    story_points: int
    completed_story_points: int
    completion_rate: float

class AnalyticsDependencyMap(BaseModel):
    total_dependency_edges: int
    blocked_tasks: int
    dependency_source_tasks: int

class ReportAnalyticsSummary(BaseModel):
    month: str
    scope: AnalyticsScope
    generated_at: datetime
    productivity: AnalyticsProductivity
    workload_distribution: list[AnalyticsWorkloadRow]
    backlog_health: AnalyticsBacklogHealth
    cycle_time: AnalyticsCycleTime
    task_status: AnalyticsTaskStatus
    utilization: AnalyticsUtilization
    velocity: list[AnalyticsVelocityRow]
    project_effort: list[AnalyticsProjectEffortRow]
    dependency_map: AnalyticsDependencyMap


class ScheduledReportCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    report_type: str = Field(description="kpi|portfolio|progress|analytics")
    format: str = Field(description="csv|xlsx|pdf|json")
    frequency: str = Field(description="daily|weekly|monthly")
    recipients: list[str] = Field(default_factory=list, max_length=20)
    next_run_at: datetime
    active: bool = True


class ScheduledReportDeliveryOut(BaseModel):
    id: int
    schedule_id: int
    status: str
    delivery_channel: str
    message: str | None = None
    created_at: datetime


class ScheduledReportOut(BaseModel):
    id: int
    name: str
    report_type: str
    format: str
    frequency: str
    recipients: list[str]
    active: bool
    next_run_at: datetime
    last_run_at: datetime | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    last_delivery: ScheduledReportDeliveryOut | None = None
