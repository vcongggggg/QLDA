from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user, require_permission
from app.repository import (
    create_audit_log,
    implementation_plan_completion,
    list_audit_logs,
    notification_queue_status,
    overdue_spike_summary,
    system_metrics,
)
from app.schemas import AuditLogOut, OpsDashboardOut, PlanCompletionOut, SystemMetricsOut
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
    require_permission(current_user, "monitoring.view")
    return {
        "can_manage_queue": current_user["role"] in {"admin", "manager", "hr"},
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
    require_permission(current_user, "monitoring.admin")
    return list_audit_logs(
        limit=limit,
        actor_id=actor_id,
        action=action.strip() if action else None,
        entity_type=entity_type.strip() if entity_type else None,
        date_from=_query_datetime_to_iso(date_from),
        date_to=_query_datetime_to_iso(date_to),
        keyword=keyword.strip() if keyword else None,
    )


@router.post("/seed/init")
def init_seed_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "monitoring.admin")
    create_audit_log(current_user["id"], "seed", "system", None, "seed init")
    return seed_data()
