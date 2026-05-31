from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.auth import get_current_user, has_permission, require_permission
from app.reporting import build_audit_csv, build_audit_xlsx
from app.repository import (
    create_audit_log,
    implementation_plan_completion,
    list_audit_logs,
    notification_queue_status,
    overdue_spike_summary,
    release_acceptance_matrix,
    release_gate_summary,
    system_metrics,
)
from app.schemas import AuditLogOut, OpsDashboardOut, PlanCompletionOut, ReleaseAcceptanceOut, ReleaseGateOut, SystemMetricsOut
from app.seed import seed_data

router = APIRouter(tags=["monitoring"])


def _query_datetime_to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.astimezone(timezone.utc).isoformat()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/meta/now")
def now_endpoint() -> dict:
    return {"utc_now": datetime.now(timezone.utc).isoformat()}


@router.get("/monitoring/readiness")
def readiness_probe() -> dict:
    return {"status": "ready", "utc_now": datetime.now(timezone.utc).isoformat()}


@router.get("/monitoring/metrics", response_model=SystemMetricsOut)
def monitoring_metrics_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "monitoring.view")
    return system_metrics()


@router.get("/monitoring/ops", response_model=OpsDashboardOut)
def monitoring_ops_endpoint(
    actor_id: int | None = Query(default=None),
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=120),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    failed_limit: int = Query(default=5, ge=0, le=50),
    overdue_threshold: int = Query(default=10, ge=0, le=10000),
    current_user: dict = Depends(get_current_user),
) -> dict:
    if not (has_permission(current_user, "OPS_VIEW") or has_permission(current_user, "AUDIT_VIEW")):
        raise HTTPException(status_code=403, detail="forbidden")
    return {
        "can_manage_queue": has_permission(current_user, "teams.manage"),
        "audit_logs": list_audit_logs(
            limit=limit,
            actor_id=actor_id,
            action=action.strip() if action else None,
            entity_type=entity_type.strip() if entity_type else None,
            date_from=_query_datetime_to_iso(date_from),
            date_to=_query_datetime_to_iso(date_to),
            keyword=keyword.strip() if keyword else None,
        ),
        "notification_queue": notification_queue_status(limit_failed=failed_limit),
        "overdue_spike": overdue_spike_summary(threshold=overdue_threshold),
    }


@router.get("/monitoring/release-gate", response_model=ReleaseGateOut)
def monitoring_release_gate_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    if not (
        has_permission(current_user, "OPS_VIEW")
        or has_permission(current_user, "AUDIT_VIEW")
        or has_permission(current_user, "monitoring.admin")
    ):
        raise HTTPException(status_code=403, detail="forbidden")
    return release_gate_summary()


@router.get("/monitoring/release-acceptance", response_model=ReleaseAcceptanceOut)
def monitoring_release_acceptance_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    if not (
        has_permission(current_user, "OPS_VIEW")
        or has_permission(current_user, "AUDIT_VIEW")
        or has_permission(current_user, "monitoring.admin")
    ):
        raise HTTPException(status_code=403, detail="forbidden")
    return release_acceptance_matrix()


@router.get("/plan/completion", response_model=PlanCompletionOut)
def plan_completion_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "projects.view")
    return implementation_plan_completion()


@router.get("/audit/logs", response_model=list[AuditLogOut])
def audit_logs_endpoint(
    actor_id: int | None = Query(default=None),
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=120),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    require_permission(current_user, "AUDIT_VIEW")
    return list_audit_logs(
        limit=limit,
        actor_id=actor_id,
        action=action.strip() if action else None,
        entity_type=entity_type.strip() if entity_type else None,
        date_from=_query_datetime_to_iso(date_from),
        date_to=_query_datetime_to_iso(date_to),
        keyword=keyword.strip() if keyword else None,
    )


def _audit_rows(
    actor_id: int | None,
    action: str | None,
    entity_type: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    keyword: str | None,
    limit: int,
) -> list[dict]:
    return list_audit_logs(
        limit=limit,
        actor_id=actor_id,
        action=action.strip() if action else None,
        entity_type=entity_type.strip() if entity_type else None,
        date_from=_query_datetime_to_iso(date_from),
        date_to=_query_datetime_to_iso(date_to),
        keyword=keyword.strip() if keyword else None,
    )


@router.get("/audit/logs.csv")
def audit_logs_csv_endpoint(
    actor_id: int | None = Query(default=None),
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=120),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
) -> Response:
    require_permission(current_user, "AUDIT_VIEW")
    content = build_audit_csv(_audit_rows(actor_id, action, entity_type, date_from, date_to, keyword, limit))
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=teamswork-audit-logs.csv"},
    )


@router.get("/audit/logs.xlsx")
def audit_logs_xlsx_endpoint(
    actor_id: int | None = Query(default=None),
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=120),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
) -> Response:
    require_permission(current_user, "AUDIT_VIEW")
    content = build_audit_xlsx(_audit_rows(actor_id, action, entity_type, date_from, date_to, keyword, limit))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=teamswork-audit-logs.xlsx"},
    )


@router.post("/seed/init")
def init_seed_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "monitoring.admin")
    create_audit_log(current_user["id"], "seed", "system", None, "seed init")
    return seed_data()
