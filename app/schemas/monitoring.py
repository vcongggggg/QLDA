from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.schemas.audit import AuditLogOut

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

class ReleaseGateCheckOut(BaseModel):
    key: str
    status: str
    summary: str

class ReleaseGateAuditOut(BaseModel):
    available: bool
    total_count: int
    latest_created_at: datetime | None = None

class ReleaseGateProductionAuthOut(BaseModel):
    status: str
    checked: bool
    summary: str

class ReleaseGateMaintenanceOut(BaseModel):
    active_or_upcoming_count: int

class ReleaseGateComplianceOut(BaseModel):
    open_count: int
    in_review_count: int
    by_status: dict

class ReleaseGateRetentionOut(BaseModel):
    backup_script: str
    backup_script_exists: bool
    retention_days: dict
    external_backup_integration: str

class ReleaseGateSyntheticJourneyOut(BaseModel):
    mode: str
    script: str
    journeys: list[str]
    external_integrations: str

class ReleaseGateQaEvidenceOut(BaseModel):
    focused_phase6_command: str
    compile_command: str
    full_suite_command: str
    uat_template: str

class ReleaseGateOut(BaseModel):
    status: str
    generated_at: datetime
    checks: list[ReleaseGateCheckOut]
    health: dict
    readiness: dict
    metrics: SystemMetricsOut
    notification_queue: OpsQueueStatusOut
    audit: ReleaseGateAuditOut
    production_auth: ReleaseGateProductionAuthOut
    maintenance: ReleaseGateMaintenanceOut | None = None
    compliance_backlog: ReleaseGateComplianceOut | None = None
    retention: ReleaseGateRetentionOut | None = None
    synthetic_journey: ReleaseGateSyntheticJourneyOut | None = None
    qa_evidence: ReleaseGateQaEvidenceOut | None = None

class PlanCompletionOut(BaseModel):
    total_items: int
    completed_items: int
    completion_percent: float
    items: list[dict]

class ReleaseAcceptanceStoryOut(BaseModel):
    story_id: str
    epic: str
    feature: str
    status: str
    evidence_type: str
    implementation_evidence: list[str]
    test_evidence: list[str]
    approved_deferrals: list[str] = []

class ReleaseAcceptanceOut(BaseModel):
    policy: str
    scope: str
    total_stories: int
    done_stories: int
    partial_stories: int
    deferral_count: int
    stories: list[ReleaseAcceptanceStoryOut]
