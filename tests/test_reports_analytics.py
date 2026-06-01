from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.database import get_connection, init_db
from app.main import app
from app.repository import create_task, create_user


client = TestClient(app)


def _hdr(user_id: int) -> dict[str, str]:
    return {"X-User-Id": str(user_id)}


def _email(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}.{stamp}@example.com"


def _set_task_dates(task_id: int, *, created_at: str, completed_at: str | None, status: str | None = None) -> None:
    fields = ["created_at = ?", "updated_at = ?"]
    params: list[object] = [created_at, completed_at or created_at]
    if completed_at is not None:
        fields.append("completed_at = ?")
        params.append(completed_at)
    if status is not None:
        fields.append("status = ?")
        params.append(status)
    params.append(task_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", tuple(params))


def test_analytics_summary_requires_report_view_permission_and_has_empty_shape() -> None:
    init_db()
    member = create_user("Analytics Member", _email("analytics.member"), "MEMBER", "Engineering")
    auditor = create_user("Analytics Auditor", _email("analytics.auditor"), "AUDITOR", "QA")

    forbidden = client.get("/reports/analytics/summary?month=2099-12", headers=_hdr(int(member["id"])))
    assert forbidden.status_code == 403

    ok = client.get("/reports/analytics/summary?month=2099-12", headers=_hdr(int(auditor["id"])))
    assert ok.status_code == 200
    payload = ok.json()
    assert payload["month"] == "2099-12"
    assert payload["scope"] == {"type": "all", "user_id": None}
    assert payload["generated_at"]
    assert payload["productivity"] == {
        "total_tasks": 0,
        "done_tasks": 0,
        "open_tasks": 0,
        "completion_rate": 0.0,
        "total_story_points": 0,
        "completed_story_points": 0,
    }
    assert payload["workload_distribution"] == []
    assert payload["cycle_time"]["avg_cycle_time_days"] is None


def test_analytics_summary_reports_productivity_workload_backlog_and_cycle_time() -> None:
    init_db()
    year = 2200 + (datetime.now(timezone.utc).microsecond % 7000)
    month = f"{year}-11"
    manager = create_user("Analytics Manager", _email("analytics.manager"), "MANAGER", "PMO")
    first = create_user("Analytics First", _email("analytics.first"), "MEMBER", "Engineering")
    second = create_user("Analytics Second", _email("analytics.second"), "MEMBER", "Engineering")

    done = create_task(
        "Analytics done task",
        None,
        int(first["id"]),
        None,
        None,
        5,
        "medium",
        f"{month}-10T09:00:00+00:00",
    )
    _set_task_dates(
        int(done["id"]),
        created_at=f"{month}-01T09:00:00+00:00",
        completed_at=f"{month}-04T09:00:00+00:00",
        status="done",
    )
    create_task(
        "Analytics overdue backlog task",
        None,
        int(first["id"]),
        None,
        None,
        3,
        "easy",
        f"{month}-05T09:00:00+00:00",
    )
    create_task(
        "Analytics open assigned task",
        None,
        int(second["id"]),
        None,
        None,
        8,
        "hard",
        f"{month}-25T09:00:00+00:00",
    )

    response = client.get(
        f"/reports/analytics/summary?month={month}&as_of={month}-20T00:00:00%2B00:00",
        headers=_hdr(int(manager["id"])),
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["productivity"]["total_tasks"] == 3
    assert payload["productivity"]["done_tasks"] == 1
    assert payload["productivity"]["open_tasks"] == 2
    assert payload["productivity"]["completion_rate"] == 33.33
    assert payload["productivity"]["total_story_points"] == 16
    assert payload["productivity"]["completed_story_points"] == 5
    assert payload["backlog_health"] == {
        "overdue_open_tasks": 1,
        "backlog_open_tasks": 2,
        "unassigned_open_tasks": 0,
    }
    assert payload["cycle_time"] == {
        "done_tasks_with_cycle_time": 1,
        "avg_cycle_time_days": 3.0,
        "min_cycle_time_days": 3.0,
        "max_cycle_time_days": 3.0,
    }

    by_user = {item["user_id"]: item for item in payload["workload_distribution"]}
    assert by_user[int(first["id"])]["total_tasks"] == 2
    assert by_user[int(first["id"])]["done_tasks"] == 1
    assert by_user[int(first["id"])]["overdue_open_tasks"] == 1
    assert by_user[int(second["id"])]["open_tasks"] == 1
    assert payload["task_status"] == {"todo_tasks": 2, "doing_tasks": 0, "done_tasks": 1}
    assert payload["utilization"]["assigned_tasks"] == 3
    assert payload["velocity"][0]["sprint_name"] == "Backlog"
    assert payload["project_effort"][0]["project_name"] == "No project"
    assert payload["dependency_map"] == {
        "total_dependency_edges": 0,
        "blocked_tasks": 0,
        "dependency_source_tasks": 0,
    }


def test_analytics_exports_require_export_permission_and_reuse_summary_shape() -> None:
    init_db()
    member = create_user("Analytics Export Member", _email("analytics.export.member"), "MEMBER", "Engineering")
    manager = create_user("Analytics Export Manager", _email("analytics.export.manager"), "MANAGER", "PMO")

    forbidden = client.get("/reports/analytics.csv?month=2099-12", headers=_hdr(int(member["id"])))
    assert forbidden.status_code == 403

    json_export = client.get("/reports/analytics.json?month=2099-12", headers=_hdr(int(manager["id"])))
    assert json_export.status_code == 200
    assert json_export.json()["month"] == "2099-12"
    assert "teamswork-analytics-2099-12.json" in json_export.headers["content-disposition"]

    csv_export = client.get("/reports/analytics.csv?month=2099-12", headers=_hdr(int(manager["id"])))
    assert csv_export.status_code == 200
    assert "section,metric,label,value" in csv_export.text

    xlsx_export = client.get("/reports/analytics.xlsx?month=2099-12", headers=_hdr(int(manager["id"])))
    assert xlsx_export.status_code == 200
    assert "teamswork-analytics-2099-12.xlsx" in xlsx_export.headers["content-disposition"]


def test_dashboard_insights_are_role_scoped_and_export_aware() -> None:
    init_db()
    year = 2300 + (datetime.now(timezone.utc).microsecond % 6000)
    month = f"{year}-04"
    manager = create_user("Dashboard Manager", _email("dashboard.manager"), "MANAGER", "PMO")
    staff = create_user("Dashboard Staff", _email("dashboard.staff"), "MEMBER", "Engineering")
    other = create_user("Dashboard Other", _email("dashboard.other"), "MEMBER", "Engineering")
    own = create_task(
        "Dashboard own task",
        None,
        int(staff["id"]),
        None,
        None,
        3,
        "easy",
        f"{month}-10T09:00:00+00:00",
    )
    _set_task_dates(
        int(own["id"]),
        created_at=f"{month}-01T09:00:00+00:00",
        completed_at=f"{month}-03T09:00:00+00:00",
        status="done",
    )
    create_task(
        "Dashboard other task",
        None,
        int(other["id"]),
        None,
        None,
        5,
        "medium",
        f"{month}-12T09:00:00+00:00",
    )

    staff_resp = client.get(f"/reports/dashboard/insights?month={month}", headers=_hdr(int(staff["id"])))
    assert staff_resp.status_code == 200
    staff_payload = staff_resp.json()
    assert staff_payload["scope"] == {"type": "personal", "user_id": staff["id"]}
    assert staff_payload["analytics"]["productivity"]["total_tasks"] == 1
    assert staff_payload["analytics"]["productivity"]["done_tasks"] == 1
    assert staff_payload["export_links"] == {}
    assert staff_payload["states"] == {"loading": False, "empty": False, "error": None}
    assert {item["key"] for item in staff_payload["chart_catalog"]} >= {"task_status", "workload", "velocity", "project_effort"}

    manager_resp = client.get(f"/reports/dashboard/insights?month={month}", headers=_hdr(int(manager["id"])))
    assert manager_resp.status_code == 200
    manager_payload = manager_resp.json()
    assert manager_payload["scope"]["type"] == "team"
    assert manager_payload["analytics"]["productivity"]["total_tasks"] == 2
    assert manager_payload["export_links"]["analytics_csv"] == f"/reports/analytics.csv?month={month}"


def test_dashboard_insights_empty_month_has_stable_empty_state() -> None:
    init_db()
    auditor = create_user("Dashboard Empty Auditor", _email("dashboard.empty.auditor"), "AUDITOR", "QA")

    resp = client.get("/reports/dashboard/insights?month=2099-11", headers=_hdr(int(auditor["id"])))
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["states"]["empty"] is True
    assert payload["analytics"]["productivity"]["total_tasks"] == 0
    assert any(alert["code"] == "empty_dashboard" for alert in payload["alerts"])
    assert payload["cards"][0]["state"] == "empty"


def test_scheduled_report_queue_is_permissioned_and_logs_default_skip_delivery() -> None:
    init_db()
    member = create_user("Schedule Member", _email("schedule.member"), "MEMBER", "Engineering")
    manager = create_user("Schedule Manager", _email("schedule.manager"), "MANAGER", "PMO")

    payload = {
        "name": "Weekly KPI package",
        "report_type": "kpi",
        "format": "csv",
        "frequency": "weekly",
        "recipients": ["ops@example.com"],
        "next_run_at": "2099-01-07T09:00:00+00:00",
    }
    forbidden = client.post("/reports/schedules", headers=_hdr(int(member["id"])), json=payload)
    assert forbidden.status_code == 403

    created = client.post("/reports/schedules", headers=_hdr(int(manager["id"])), json=payload)
    assert created.status_code == 200
    item = created.json()
    assert item["name"] == "Weekly KPI package"
    assert item["report_type"] == "kpi"
    assert item["format"] == "csv"
    assert item["active"] is True
    assert item["last_delivery"] is None

    listed = client.get("/reports/schedules", headers=_hdr(int(manager["id"])))
    assert listed.status_code == 200
    assert any(row["id"] == item["id"] for row in listed.json())

    run = client.post(f"/reports/schedules/{item['id']}/run", headers=_hdr(int(manager["id"])))
    assert run.status_code == 200
    delivery = run.json()
    assert delivery["schedule_id"] == item["id"]
    assert delivery["status"] == "skipped"
    assert delivery["delivery_channel"] == "email"
    assert "not configured" in delivery["message"].lower()

    logs = client.get(f"/reports/schedules/{item['id']}/deliveries", headers=_hdr(int(manager["id"])))
    assert logs.status_code == 200
    assert logs.json()[0]["id"] == delivery["id"]


def test_run_due_scheduled_reports_logs_delivery_and_advances_next_run() -> None:
    init_db()
    manager = create_user("Schedule Due Manager", _email("schedule.due.manager"), "MANAGER", "PMO")

    created = client.post(
        "/reports/schedules",
        headers=_hdr(int(manager["id"])),
        json={
            "name": "Due weekly analytics",
            "report_type": "analytics",
            "format": "json",
            "frequency": "weekly",
            "recipients": ["ops@example.com"],
            "next_run_at": "2099-01-07T09:00:00+00:00",
        },
    )
    assert created.status_code == 200
    schedule_id = created.json()["id"]

    run_due = client.post(
        "/reports/schedules/run-due?as_of=2099-01-07T10:00:00%2B00:00",
        headers=_hdr(int(manager["id"])),
    )
    assert run_due.status_code == 200
    payload = run_due.json()
    assert payload["processed"] == 1
    assert payload["deliveries"][0]["schedule_id"] == schedule_id
    assert payload["deliveries"][0]["next_run_at"].startswith("2099-01-14T09:00:00")

    listed = client.get("/reports/schedules", headers=_hdr(int(manager["id"]))).json()
    updated = next(row for row in listed if row["id"] == schedule_id)
    assert updated["next_run_at"].startswith("2099-01-14T09:00:00")
    assert updated["last_delivery"]["status"] == "skipped"


def test_reports_static_ui_exposes_analytics_schedule_and_accessibility_hooks() -> None:
    root = Path(__file__).resolve().parents[1]
    index = (root / "app" / "static" / "index.html").read_text(encoding="utf-8")
    static_js_dir = root / "app" / "static" / "js"
    js_candidates = list(static_js_dir.glob("*.js")) if static_js_dir.exists() else []
    app_js = root / "app" / "static" / "app.js"
    if app_js.exists():
        js_candidates.append(app_js)
    reports_js = "\n".join(path.read_text(encoding="utf-8") for path in js_candidates)
    css_text = "\n".join(path.read_text(encoding="utf-8") for path in (root / "app" / "static" / "css").rglob("*.css"))

    assert 'id="reportAnalyticsPanel"' in index
    assert 'data-requires-any-permission="REPORT_VIEW_TEAM,REPORT_VIEW_ALL,REPORT_EXPORT,reports.export"' in index
    assert 'id="analyticsWorkloadChart"' in index
    assert 'id="scheduledReportsPanel"' in index
    assert "loadReportAnalytics" in reports_js
    assert "loadKpiReportSummary" in reports_js
    assert "/reports/kpi/summary" in reports_js
    assert "renderAnalyticsWorkloadChart" in reports_js
    assert "renderAnalyticsStatusChart" in reports_js
    assert "renderAnalyticsVelocityChart" in reports_js
    assert "renderAnalyticsProjectEffortChart" in reports_js
    assert "loadReportSchedules" in reports_js
    assert "runDueReportSchedules" in reports_js
    assert "/reports/schedules" in reports_js
    assert "/reports/analytics." in reports_js
    assert "aria-live=\"polite\"" in index
    assert ".analytics-grid" in css_text
    assert "@media (max-width: 760px)" in css_text
