from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, has_permission, require_permission, require_roles
from app.repository import (
    admin_config_flags,
    admin_department_ops_evidence,
    admin_global_search,
    admin_license_status,
    admin_release_panel_summary,
    admin_system_config_overview,
    compliance_release_evidence,
    create_compliance_request,
    create_maintenance_window,
    create_system_notification_broadcast,
    data_lineage_notes,
    list_audit_logs,
    list_compliance_requests,
    list_maintenance_windows,
    log_cleanup_dry_run,
    qa_release_evidence,
    retention_metadata,
    system_notification_evidence,
    test_data_inventory,
    update_compliance_request,
    update_maintenance_window,
    user_exists,
    compliance_user_export,
)
from app.schemas import (
    AdminConfigFlagOut,
    AdminSearchOut,
    AuditLogOut,
    ComplianceRequestCreate,
    ComplianceRequestOut,
    ComplianceRequestUpdate,
    MaintenanceWindowCreate,
    MaintenanceWindowOut,
    MaintenanceWindowUpdate,
    SystemNotificationBroadcastOut,
    SystemNotificationCreate,
)

router = APIRouter(tags=["phase6"])


def _require_compliance_view(current_user: dict) -> None:
    if not (
        has_permission(current_user, "AUDIT_VIEW")
        or has_permission(current_user, "OPS_VIEW")
        or has_permission(current_user, "USER_VIEW")
    ):
        raise HTTPException(status_code=403, detail="forbidden")


@router.get("/admin/search", response_model=AdminSearchOut)
def admin_search_endpoint(
    q: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=25, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "USER_VIEW")
    return admin_global_search(q, limit=limit)


@router.get("/admin/activity", response_model=list[AuditLogOut])
def admin_activity_endpoint(
    limit: int = Query(default=25, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    require_permission(current_user, "AUDIT_VIEW")
    return list_audit_logs(limit=limit)


@router.get("/admin/config-flags", response_model=list[AdminConfigFlagOut])
def admin_config_flags_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    if not (has_permission(current_user, "OPS_VIEW") or has_permission(current_user, "monitoring.admin")):
        raise HTTPException(status_code=403, detail="forbidden")
    return admin_config_flags()


@router.get("/admin/system-config/overview")
def admin_system_config_overview_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    if not (has_permission(current_user, "OPS_VIEW") or has_permission(current_user, "monitoring.admin")):
        raise HTTPException(status_code=403, detail="forbidden")
    return admin_system_config_overview()


@router.get("/admin/license/status")
def admin_license_status_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    if not (has_permission(current_user, "USER_VIEW") or has_permission(current_user, "OPS_VIEW")):
        raise HTTPException(status_code=403, detail="forbidden")
    return admin_license_status()


@router.get("/admin/departments/ops-evidence")
def admin_department_ops_evidence_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    if not (has_permission(current_user, "DEPARTMENT_VIEW") or has_permission(current_user, "USER_VIEW")):
        raise HTTPException(status_code=403, detail="forbidden")
    return admin_department_ops_evidence()


@router.get("/admin/release-panel")
def admin_release_panel_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    if not (has_permission(current_user, "USER_VIEW") or has_permission(current_user, "OPS_VIEW")):
        raise HTTPException(status_code=403, detail="forbidden")
    return admin_release_panel_summary()


@router.post("/admin/system-notifications", response_model=SystemNotificationBroadcastOut)
def admin_system_notification_endpoint(
    payload: SystemNotificationCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager", "hr"})
    return create_system_notification_broadcast(payload.title, payload.message, payload.audience, int(current_user["id"]))


@router.get("/admin/system-notifications/evidence")
def admin_system_notification_evidence_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    if not (has_permission(current_user, "OPS_VIEW") or has_permission(current_user, "USER_VIEW")):
        raise HTTPException(status_code=403, detail="forbidden")
    return system_notification_evidence()


@router.get("/compliance/requests", response_model=list[ComplianceRequestOut])
def list_compliance_requests_endpoint(
    status: str | None = Query(default=None, pattern="^(open|in_review|approved|rejected|fulfilled)$"),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    _require_compliance_view(current_user)
    return list_compliance_requests(status=status, limit=limit)


@router.post("/compliance/requests", response_model=ComplianceRequestOut)
def create_compliance_request_endpoint(
    payload: ComplianceRequestCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    _require_compliance_view(current_user)
    if not user_exists(payload.subject_user_id):
        raise HTTPException(status_code=404, detail="subject user not found")
    return create_compliance_request(payload.subject_user_id, payload.request_type, payload.reason, int(current_user["id"]))


@router.patch("/compliance/requests/{request_id}", response_model=ComplianceRequestOut)
def update_compliance_request_endpoint(
    request_id: int,
    payload: ComplianceRequestUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    _require_compliance_view(current_user)
    updated = update_compliance_request(request_id, payload.status, payload.resolution_note, int(current_user["id"]))
    if not updated:
        raise HTTPException(status_code=404, detail="compliance request not found")
    return updated


@router.get("/compliance/users/{user_id}/export")
def compliance_user_export_endpoint(user_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    _require_compliance_view(current_user)
    export = compliance_user_export(user_id)
    if not export:
        raise HTTPException(status_code=404, detail="user not found")
    return export


@router.get("/compliance/data-lineage")
def compliance_data_lineage_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    _require_compliance_view(current_user)
    return data_lineage_notes()


@router.get("/compliance/evidence")
def compliance_release_evidence_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    _require_compliance_view(current_user)
    return compliance_release_evidence()


@router.get("/maintenance/windows", response_model=list[MaintenanceWindowOut])
def list_maintenance_windows_endpoint(
    status: str | None = Query(default=None, pattern="^(scheduled|active|completed|cancelled)$"),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    if not (has_permission(current_user, "OPS_VIEW") or has_permission(current_user, "monitoring.admin")):
        raise HTTPException(status_code=403, detail="forbidden")
    return list_maintenance_windows(status=status, limit=limit)


@router.post("/maintenance/windows", response_model=MaintenanceWindowOut)
def create_maintenance_window_endpoint(
    payload: MaintenanceWindowCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "monitoring.admin")
    starts_at = payload.starts_at.astimezone(timezone.utc)
    ends_at = payload.ends_at.astimezone(timezone.utc)
    if ends_at <= starts_at:
        raise HTTPException(status_code=400, detail="ends_at must be after starts_at")
    return create_maintenance_window(
        payload.title,
        payload.message,
        starts_at.isoformat(),
        ends_at.isoformat(),
        payload.status,
        int(current_user["id"]),
    )


@router.patch("/maintenance/windows/{window_id}", response_model=MaintenanceWindowOut)
def update_maintenance_window_endpoint(
    window_id: int,
    payload: MaintenanceWindowUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "monitoring.admin")
    if hasattr(payload, "model_dump"):
        fields = payload.model_dump(exclude_unset=True)
    else:
        fields = payload.dict(exclude_unset=True)
    if fields.get("starts_at") is not None:
        fields["starts_at"] = fields["starts_at"].astimezone(timezone.utc).isoformat()
    if fields.get("ends_at") is not None:
        fields["ends_at"] = fields["ends_at"].astimezone(timezone.utc).isoformat()
    updated = update_maintenance_window(window_id, fields, int(current_user["id"]))
    if not updated:
        raise HTTPException(status_code=404, detail="maintenance window not found")
    return updated


@router.get("/maintenance/retention")
def maintenance_retention_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    if not (has_permission(current_user, "OPS_VIEW") or has_permission(current_user, "monitoring.admin")):
        raise HTTPException(status_code=403, detail="forbidden")
    return retention_metadata()


@router.post("/maintenance/log-cleanup/dry-run")
def maintenance_log_cleanup_dry_run_endpoint(
    retention_days: int = Query(default=90, ge=1, le=3650),
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "monitoring.admin")
    return log_cleanup_dry_run(retention_days=retention_days)


@router.get("/qa/release-evidence")
def qa_release_evidence_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    if not (
        has_permission(current_user, "OPS_VIEW")
        or has_permission(current_user, "AUDIT_VIEW")
        or has_permission(current_user, "monitoring.admin")
    ):
        raise HTTPException(status_code=403, detail="forbidden")
    return qa_release_evidence()


@router.get("/qa/test-data")
def qa_test_data_inventory_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    if not (
        has_permission(current_user, "OPS_VIEW")
        or has_permission(current_user, "AUDIT_VIEW")
        or has_permission(current_user, "monitoring.admin")
    ):
        raise HTTPException(status_code=403, detail="forbidden")
    return test_data_inventory()
