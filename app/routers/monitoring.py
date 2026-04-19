from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user, require_roles
from app.repository import (
    create_audit_log,
    implementation_plan_completion,
    list_audit_logs,
    system_metrics,
)
from app.schemas import AuditLogOut, PlanCompletionOut, SystemMetricsOut
from app.seed import seed_data

router = APIRouter(tags=["monitoring"])


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
    require_roles(current_user, {"admin", "manager", "hr"})
    return system_metrics()


@router.get("/plan/completion", response_model=PlanCompletionOut)
def plan_completion_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    require_roles(current_user, {"admin", "manager", "hr", "staff"})
    return implementation_plan_completion()


@router.get("/audit/logs", response_model=list[AuditLogOut])
def audit_logs_endpoint(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    require_roles(current_user, {"admin"})
    return list_audit_logs(limit)


@router.post("/seed/init")
def init_seed_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    require_roles(current_user, {"admin"})
    create_audit_log(current_user["id"], "seed", "system", None, "seed init")
    return seed_data()
