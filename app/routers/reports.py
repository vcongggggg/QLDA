from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from app.auth import get_current_user, has_permission, is_member_role, require_permission
from app.kpi import calculate_monthly_kpi_from_transactions, policy_from_row
from app.reporting import (
    build_kpi_csv,
    build_kpi_pdf,
    build_kpi_xlsx,
    build_portfolio_csv,
    build_portfolio_xlsx,
    build_project_progress_csv,
    build_project_progress_xlsx,
    build_report_analytics_csv,
    build_report_analytics_summary,
    build_report_analytics_xlsx,
    build_sprint_review_csv,
    build_sprint_review_xlsx,
    build_tasks_csv,
    build_tasks_xlsx,
)
from app.repository import (
    all_tasks_with_users,
    create_report_schedule,
    create_scheduled_report_delivery,
    get_kpi_policy,
    get_report_schedule,
    latest_scheduled_report_delivery,
    list_kpi_target_progress,
    list_kpi_transactions,
    list_due_report_schedules,
    list_projects,
    list_report_schedules,
    list_scheduled_report_deliveries,
    list_task_dependency_edges,
    list_tasks,
    portfolio_summary,
    project_progress,
    rebuild_kpi_transactions,
    sprint_exists,
    sprint_review_summary,
    update_report_schedule_next_run,
)
from app.schemas import ReportAnalyticsSummary, ScheduledReportCreate, ScheduledReportDeliveryOut, ScheduledReportOut
from fastapi import HTTPException

router = APIRouter(prefix="/reports", tags=["reports"])


def _kpi_rows(month: str, current_user: dict) -> list[dict]:
    rebuild_kpi_transactions(month, policy_from_row(get_kpi_policy()))
    user_id = int(current_user["id"]) if is_member_role(current_user) else None
    report = calculate_monthly_kpi_from_transactions(
        list_kpi_transactions(month, user_id=user_id, include_reversed=False),
        month,
    )
    progress = {int(row["user_id"]): row for row in list_kpi_target_progress(month)}
    for row in report.values():
        target = progress.get(int(row["user_id"]))
        if target:
            row["target_score"] = target["target_score"]
            row["progress_percent"] = target["progress_percent"]
            row["gap"] = target["gap"]
    return sorted(report.values(), key=lambda r: r["score"], reverse=True)


def _normalize_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _require_report_view(current_user: dict) -> None:
    allowed = (
        "REPORT_VIEW_ALL",
        "REPORT_VIEW_TEAM",
        "REPORT_EXPORT",
        "reports.export",
    )
    if not any(has_permission(current_user, permission) for permission in allowed):
        raise HTTPException(status_code=403, detail="forbidden")


def _schedule_response(row: dict) -> dict:
    item = dict(row)
    item["last_delivery"] = latest_scheduled_report_delivery(int(row["id"]))
    return item


def _validate_schedule_payload(payload: ScheduledReportCreate) -> None:
    allowed_types = {"kpi", "portfolio", "progress", "analytics"}
    allowed_formats = {"csv", "xlsx", "pdf", "json"}
    allowed_frequencies = {"daily", "weekly", "monthly"}
    if payload.report_type not in allowed_types:
        raise HTTPException(status_code=400, detail="report_type must be one of kpi|portfolio|progress|analytics")
    if payload.format not in allowed_formats:
        raise HTTPException(status_code=400, detail="format must be one of csv|xlsx|pdf|json")
    if payload.frequency not in allowed_frequencies:
        raise HTTPException(status_code=400, detail="frequency must be one of daily|weekly|monthly")
    if not payload.recipients:
        raise HTTPException(status_code=400, detail="at least one recipient is required")


def _next_schedule_run(current: str, frequency: str) -> str:
    value = datetime.fromisoformat(str(current).replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    if frequency == "daily":
        return (value + timedelta(days=1)).isoformat()
    if frequency == "weekly":
        return (value + timedelta(days=7)).isoformat()
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, 28)
    return value.replace(year=year, month=month, day=day).isoformat()


def _task_rows(
    current_user: dict,
    assignee_id: int | None,
    project_id: int | None,
    sprint_id: int | None,
    status: str | None,
    overdue: bool | None,
    keyword: str | None,
    deadline_from: datetime | None,
    deadline_to: datetime | None,
) -> list[dict]:
    if is_member_role(current_user):
        assignee_id = int(current_user["id"])
    if status is not None and status not in {"todo", "doing", "done"}:
        raise HTTPException(status_code=400, detail="status must be one of todo|doing|done")
    if deadline_from and deadline_to and deadline_to < deadline_from:
        raise HTTPException(status_code=400, detail="deadline_to must be greater than or equal to deadline_from")
    return list_tasks(
        assignee_id=assignee_id,
        project_id=project_id,
        sprint_id=sprint_id,
        status=status,
        overdue=overdue,
        keyword=keyword.strip() if keyword else None,
        deadline_from=_normalize_dt(deadline_from),
        deadline_to=_normalize_dt(deadline_to),
    )


def _analytics_payload(month: str, as_of: datetime | None = None) -> dict:
    normalized_as_of = None
    if as_of is not None:
        normalized_as_of = as_of.replace(tzinfo=timezone.utc) if as_of.tzinfo is None else as_of.astimezone(timezone.utc)
    return build_report_analytics_summary(
        all_tasks_with_users(),
        month=month,
        as_of=normalized_as_of,
        dependency_edges=list_task_dependency_edges(),
    )


def _analytics_payload_for_tasks(tasks: list[dict], month: str, as_of: datetime | None = None) -> dict:
    normalized_as_of = None
    if as_of is not None:
        normalized_as_of = as_of.replace(tzinfo=timezone.utc) if as_of.tzinfo is None else as_of.astimezone(timezone.utc)
    return build_report_analytics_summary(
        tasks,
        month=month,
        as_of=normalized_as_of,
        dependency_edges=list_task_dependency_edges(),
    )


def _role_dashboard_scope(current_user: dict, tasks: list[dict]) -> tuple[str, list[dict]]:
    if is_member_role(current_user):
        return "personal", [task for task in tasks if int(task.get("assignee_id") or 0) == int(current_user["id"])]
    if str(current_user.get("role_code") or "").upper() == "HR":
        return "hr", tasks
    if str(current_user.get("role_code") or "").upper() == "ADMIN":
        return "admin", tasks
    return "team", tasks


def _dashboard_insight_cards(summary: dict, kpi_rows: list[dict], schedule_count: int) -> list[dict]:
    productivity = summary["productivity"]
    backlog = summary["backlog_health"]
    cycle = summary["cycle_time"]
    utilization = summary["utilization"]
    avg_kpi = round(sum(float(row.get("score") or 0) for row in kpi_rows) / len(kpi_rows), 2) if kpi_rows else 0.0
    return [
        {"key": "total_tasks", "label": "Total tasks", "value": productivity["total_tasks"], "state": "empty" if productivity["total_tasks"] == 0 else "ready"},
        {"key": "completion_rate", "label": "Completion rate", "value": productivity["completion_rate"], "unit": "%", "state": "ready"},
        {"key": "overdue_open_tasks", "label": "Overdue open tasks", "value": backlog["overdue_open_tasks"], "state": "warning" if backlog["overdue_open_tasks"] else "ready"},
        {"key": "avg_kpi_score", "label": "Average KPI", "value": avg_kpi, "state": "ready" if kpi_rows else "empty"},
        {"key": "avg_cycle_time_days", "label": "Average cycle time", "value": cycle["avg_cycle_time_days"], "unit": "days", "state": "empty" if cycle["avg_cycle_time_days"] is None else "ready"},
        {"key": "utilization_rate", "label": "Utilization", "value": utilization["utilization_rate"], "unit": "%", "state": "ready"},
        {"key": "scheduled_reports", "label": "Scheduled reports", "value": schedule_count, "state": "empty" if schedule_count == 0 else "ready"},
    ]


def _dashboard_alerts(summary: dict) -> list[dict]:
    alerts: list[dict] = []
    backlog = summary["backlog_health"]
    productivity = summary["productivity"]
    if productivity["total_tasks"] == 0:
        alerts.append({"severity": "info", "code": "empty_dashboard", "message": "No reportable task data exists for this month."})
    if backlog["overdue_open_tasks"]:
        alerts.append({"severity": "warning", "code": "overdue_backlog", "message": f"{backlog['overdue_open_tasks']} open task(s) are overdue."})
    if backlog["unassigned_open_tasks"]:
        alerts.append({"severity": "warning", "code": "unassigned_backlog", "message": f"{backlog['unassigned_open_tasks']} open task(s) are unassigned."})
    return alerts


def _dashboard_chart_catalog(summary: dict) -> list[dict]:
    return [
        {"key": "task_status", "title": "Task status", "type": "doughnut", "data": summary["task_status"], "state": "ready"},
        {"key": "workload", "title": "Workload by assignee", "type": "bar", "data": summary["workload_distribution"], "state": "empty" if not summary["workload_distribution"] else "ready"},
        {"key": "velocity", "title": "Sprint velocity", "type": "bar", "data": summary["velocity"], "state": "empty" if not summary["velocity"] else "ready"},
        {"key": "project_effort", "title": "Project effort", "type": "bar", "data": summary["project_effort"], "state": "empty" if not summary["project_effort"] else "ready"},
        {"key": "dependency_map", "title": "Dependency map", "type": "summary", "data": summary["dependency_map"], "state": "ready"},
    ]


def _dashboard_export_links(month: str) -> dict:
    return {
        "analytics_json": f"/reports/analytics.json?month={month}",
        "analytics_csv": f"/reports/analytics.csv?month={month}",
        "analytics_xlsx": f"/reports/analytics.xlsx?month={month}",
        "kpi_csv": f"/reports/kpi.csv?month={month}",
        "portfolio_csv": "/reports/portfolio/summary.csv",
        "project_progress_csv": "/reports/projects/progress.csv",
    }


@router.get("/analytics/summary", response_model=ReportAnalyticsSummary)
def analytics_summary(
    month: str = Query(description="YYYY-MM"),
    as_of: datetime | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    _require_report_view(current_user)
    return _analytics_payload(month, as_of)


@router.get("/dashboard/insights")
def dashboard_insights(
    month: str = Query(description="YYYY-MM"),
    as_of: datetime | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    all_tasks = all_tasks_with_users()
    scope_type, scoped_tasks = _role_dashboard_scope(current_user, all_tasks)
    summary = _analytics_payload_for_tasks(scoped_tasks, month, as_of)
    summary["scope"] = {
        "type": scope_type,
        "user_id": int(current_user["id"]) if scope_type == "personal" else None,
    }
    kpi_rows = _kpi_rows(month, current_user)
    schedule_count = 0 if is_member_role(current_user) else len(list_report_schedules(active_only=True))
    return {
        "month": month,
        "role": str(current_user.get("role") or "").lower(),
        "role_code": str(current_user.get("role_code") or "").upper(),
        "scope": summary["scope"],
        "generated_at": summary["generated_at"],
        "cards": _dashboard_insight_cards(summary, kpi_rows, schedule_count),
        "alerts": _dashboard_alerts(summary),
        "analytics": summary,
        "kpi": kpi_rows,
        "chart_catalog": _dashboard_chart_catalog(summary),
        "export_links": _dashboard_export_links(month) if has_permission(current_user, "reports.export") else {},
        "states": {
            "loading": False,
            "empty": summary["productivity"]["total_tasks"] == 0,
            "error": None,
        },
    }


@router.get("/analytics.json")
def analytics_report_json(
    month: str = Query(description="YYYY-MM"),
    as_of: datetime | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    require_permission(current_user, "reports.export")
    return JSONResponse(
        content=_analytics_payload(month, as_of),
        headers={"Content-Disposition": f"attachment; filename=teamswork-analytics-{month}.json"},
    )


@router.get("/analytics.csv")
def analytics_report_csv(
    month: str = Query(description="YYYY-MM"),
    as_of: datetime | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> Response:
    require_permission(current_user, "reports.export")
    content = build_report_analytics_csv(_analytics_payload(month, as_of))
    return Response(content=content, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=teamswork-analytics-{month}.csv"})


@router.get("/analytics.xlsx")
def analytics_report_xlsx(
    month: str = Query(description="YYYY-MM"),
    as_of: datetime | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> Response:
    require_permission(current_user, "reports.export")
    content = build_report_analytics_xlsx(_analytics_payload(month, as_of))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=teamswork-analytics-{month}.xlsx"},
    )


@router.post("/schedules", response_model=ScheduledReportOut)
def create_report_schedule_endpoint(
    payload: ScheduledReportCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    _require_report_view(current_user)
    _validate_schedule_payload(payload)
    row = create_report_schedule(
        name=payload.name.strip(),
        report_type=payload.report_type,
        format=payload.format,
        frequency=payload.frequency,
        recipients=[str(item).strip() for item in payload.recipients if str(item).strip()],
        next_run_at=_normalize_dt(payload.next_run_at) or payload.next_run_at.isoformat(),
        created_by=int(current_user["id"]),
        active=payload.active,
    )
    return _schedule_response(row)


@router.get("/schedules", response_model=list[ScheduledReportOut])
def list_report_schedules_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    _require_report_view(current_user)
    return [_schedule_response(row) for row in list_report_schedules()]


@router.post("/schedules/run-due")
def run_due_report_schedules_endpoint(
    as_of: datetime | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    _require_report_view(current_user)
    cutoff = as_of or datetime.now(timezone.utc)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    cutoff_iso = cutoff.astimezone(timezone.utc).isoformat()
    deliveries = []
    for schedule in list_due_report_schedules(cutoff_iso):
        delivery = create_scheduled_report_delivery(
            schedule_id=int(schedule["id"]),
            status="skipped",
            delivery_channel="email",
            message="Email delivery is not configured; due scheduled report was logged without sending.",
        )
        next_run_at = _next_schedule_run(str(schedule["next_run_at"]), str(schedule["frequency"]))
        update_report_schedule_next_run(int(schedule["id"]), next_run_at)
        deliveries.append({"schedule_id": int(schedule["id"]), "next_run_at": next_run_at, "delivery": delivery})
    return {"as_of": cutoff_iso, "processed": len(deliveries), "deliveries": deliveries}


@router.post("/schedules/{schedule_id}/run", response_model=ScheduledReportDeliveryOut)
def run_report_schedule_endpoint(
    schedule_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    _require_report_view(current_user)
    schedule = get_report_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="schedule not found")
    return create_scheduled_report_delivery(
        schedule_id=schedule_id,
        status="skipped",
        delivery_channel="email",
        message="Email delivery is not configured; scheduled report was logged without sending.",
    )


@router.get("/schedules/{schedule_id}/deliveries", response_model=list[ScheduledReportDeliveryOut])
def list_report_schedule_deliveries_endpoint(
    schedule_id: int,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    _require_report_view(current_user)
    if not get_report_schedule(schedule_id):
        raise HTTPException(status_code=404, detail="schedule not found")
    return list_scheduled_report_deliveries(schedule_id=schedule_id)


@router.get("/kpi.csv")
def kpi_report_csv(month: str = Query(description="YYYY-MM"), current_user: dict = Depends(get_current_user)) -> Response:
    require_permission(current_user, "reports.export")
    content = build_kpi_csv(_kpi_rows(month, current_user))
    return Response(content=content, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=teamswork-kpi-{month}.csv"})


@router.get("/kpi.xlsx")
def kpi_report_xlsx(month: str = Query(description="YYYY-MM"), current_user: dict = Depends(get_current_user)) -> Response:
    require_permission(current_user, "reports.export")
    content = build_kpi_xlsx(_kpi_rows(month, current_user))
    return Response(content=content,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=teamswork-kpi-{month}.xlsx"})


@router.get("/kpi.pdf")
def kpi_report_pdf(month: str = Query(description="YYYY-MM"), current_user: dict = Depends(get_current_user)) -> Response:
    require_permission(current_user, "reports.export")
    content = build_kpi_pdf(_kpi_rows(month, current_user), month)
    return Response(content=content, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=teamswork-kpi-{month}.pdf"})


@router.get("/tasks.csv")
def tasks_report_csv(
    assignee_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    sprint_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    keyword: str | None = Query(default=None),
    deadline_from: datetime | None = Query(default=None),
    deadline_to: datetime | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> Response:
    require_permission(current_user, "reports.export")
    content = build_tasks_csv(_task_rows(current_user, assignee_id, project_id, sprint_id, status, overdue, keyword, deadline_from, deadline_to))
    return Response(content=content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=teamswork-tasks.csv"})


@router.get("/tasks.xlsx")
def tasks_report_xlsx(
    assignee_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    sprint_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    keyword: str | None = Query(default=None),
    deadline_from: datetime | None = Query(default=None),
    deadline_to: datetime | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> Response:
    require_permission(current_user, "reports.export")
    content = build_tasks_xlsx(_task_rows(current_user, assignee_id, project_id, sprint_id, status, overdue, keyword, deadline_from, deadline_to))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=teamswork-tasks.xlsx"},
    )


@router.get("/portfolio/summary.csv")
def portfolio_csv(current_user: dict = Depends(get_current_user)) -> Response:
    require_permission(current_user, "reports.export")
    content = build_portfolio_csv(portfolio_summary())
    return Response(content=content, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=teamswork-portfolio-summary.csv"})


@router.get("/portfolio/summary.xlsx")
def portfolio_xlsx(current_user: dict = Depends(get_current_user)) -> Response:
    require_permission(current_user, "reports.export")
    content = build_portfolio_xlsx(portfolio_summary())
    return Response(content=content,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=teamswork-portfolio-summary.xlsx"})


@router.get("/projects/progress.csv")
def project_progress_csv(current_user: dict = Depends(get_current_user)) -> Response:
    require_permission(current_user, "reports.export")
    rows = [project_progress(p["id"]) for p in list_projects()]
    content = build_project_progress_csv(rows)
    return Response(content=content, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=teamswork-project-progress.csv"})


@router.get("/projects/progress.xlsx")
def project_progress_xlsx(current_user: dict = Depends(get_current_user)) -> Response:
    require_permission(current_user, "reports.export")
    rows = [project_progress(p["id"]) for p in list_projects()]
    content = build_project_progress_xlsx(rows)
    return Response(content=content,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=teamswork-project-progress.xlsx"})


@router.get("/sprints/{sprint_id}/review.csv")
def sprint_review_csv(sprint_id: int, current_user: dict = Depends(get_current_user)) -> Response:
    require_permission(current_user, "reports.export")
    if not sprint_exists(sprint_id):
        raise HTTPException(status_code=404, detail="sprint not found")
    content = build_sprint_review_csv(sprint_review_summary(sprint_id))
    return Response(content=content, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=teamswork-sprint-{sprint_id}-review.csv"})


@router.get("/sprints/{sprint_id}/review.xlsx")
def sprint_review_xlsx(sprint_id: int, current_user: dict = Depends(get_current_user)) -> Response:
    require_permission(current_user, "reports.export")
    if not sprint_exists(sprint_id):
        raise HTTPException(status_code=404, detail="sprint not found")
    content = build_sprint_review_xlsx(sprint_review_summary(sprint_id))
    return Response(content=content,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=teamswork-sprint-{sprint_id}-review.xlsx"})
