from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, is_member_role, require_permission
from app.kpi import calculate_monthly_kpi, compute_dashboard_metrics
from app.repository import (
    all_tasks_with_users,
    create_audit_log,
    create_kpi_adjustment,
    list_kpi_adjustments_by_month,
    user_exists,
)
from app.schemas import (
    DashboardSummary,
    KPIAdjustmentCreate,
    KPIAdjustmentOut,
    KPIUserResult,
)

router = APIRouter(tags=["kpi"])


@router.get("/kpi/monthly", response_model=list[KPIUserResult])
def monthly_kpi_endpoint(
    month: str = Query(description="YYYY-MM"),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    tasks = all_tasks_with_users()
    adjustments = list_kpi_adjustments_by_month(month)
    report = calculate_monthly_kpi(tasks, month, adjustments=adjustments)
    rows = sorted(report.values(), key=lambda item: item["score"], reverse=True)
    if is_member_role(current_user):
        rows = [r for r in rows if int(r["user_id"]) == int(current_user["id"])]
    return rows


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary_endpoint(
    month: str = Query(description="YYYY-MM"),
    as_of: datetime | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    tasks = all_tasks_with_users()
    if is_member_role(current_user):
        tasks = [t for t in tasks if int(t["assignee_id"]) == int(current_user["id"])]
    monthly_kpi = calculate_monthly_kpi(tasks, month, adjustments=list_kpi_adjustments_by_month(month))
    normalized_as_of = None
    if as_of is not None:
        normalized_as_of = as_of.replace(tzinfo=timezone.utc) if as_of.tzinfo is None else as_of.astimezone(timezone.utc)
    return compute_dashboard_metrics(tasks, monthly_kpi, month, as_of=normalized_as_of)


@router.post("/kpi/adjustments", response_model=KPIAdjustmentOut)
def create_kpi_adjustment_endpoint(
    payload: KPIAdjustmentCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "kpi.adjust")
    if not user_exists(payload.user_id):
        raise HTTPException(status_code=404, detail="target user not found")
    item = create_kpi_adjustment(
        user_id=payload.user_id,
        month=payload.month,
        points=payload.points,
        reason=payload.reason,
        created_by=current_user["id"],
    )
    create_audit_log(current_user["id"], "create", "kpi_adjustment", item["id"], payload.reason)
    return item
