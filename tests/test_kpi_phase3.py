from datetime import datetime, timedelta, timezone
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.database import get_connection, init_db
from app.main import app
from app.repository import create_task, create_user, list_app_notifications

client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _email(prefix: str) -> str:
    return f"{prefix}.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}@example.com"


def _bootstrap() -> dict:
    init_db()
    admin = create_user("KPI Admin", _email("kpi.admin"), "ADMIN", "Administration")
    manager = create_user("KPI Manager", _email("kpi.manager"), "MANAGER", "PMO")
    hr = create_user("KPI HR", _email("kpi.hr"), "HR", "HR")
    staff = create_user("KPI Staff", _email("kpi.staff"), "MEMBER", "Engineering")
    other = create_user("KPI Other", _email("kpi.other"), "MEMBER", "Engineering")
    return {
        "admin": int(admin["id"]),
        "manager": int(manager["id"]),
        "hr": int(hr["id"]),
        "staff": int(staff["id"]),
        "other": int(other["id"]),
    }


def _done_task(user_id: int, *, month: str = "2026-04") -> dict:
    deadline = datetime.fromisoformat(f"{month}-10T10:00:00+00:00")
    return create_task(
        title="KPI ledger task",
        description=None,
        assignee_id=user_id,
        project_id=None,
        sprint_id=None,
        story_points=1,
        difficulty="easy",
        deadline_iso=deadline.isoformat(),
    )


def test_kpi_config_update_requires_reason_and_preserves_policy_shape() -> None:
    ids = _bootstrap()

    current = client.get("/kpi/config", headers=_hdr(ids["admin"]))
    assert current.status_code == 200
    assert current.json()["difficulty_multiplier"]["easy"] == 1.0

    missing_reason = client.put(
        "/kpi/config",
        headers=_hdr(ids["admin"]),
        json={"on_time_points": 11.0, "late_points": 5.0, "overdue_unfinished_points": -5.0},
    )
    assert missing_reason.status_code == 422

    updated = client.put(
        "/kpi/config",
        headers=_hdr(ids["admin"]),
        json={
            "difficulty_multiplier": {"easy": 1.0, "medium": 1.5, "hard": 2.0},
            "on_time_points": 10.0,
            "late_points": 5.0,
            "overdue_unfinished_points": -5.0,
            "change_reason": "Lock default policy for Phase 3",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["on_time_points"] == 10.0

    denied = client.put(
        "/kpi/config",
        headers=_hdr(ids["staff"]),
        json={
            "difficulty_multiplier": {"easy": 1.0, "medium": 1.5, "hard": 2.0},
            "on_time_points": 10.0,
            "late_points": 5.0,
            "overdue_unfinished_points": -5.0,
            "change_reason": "Staff cannot manage KPI",
        },
    )
    assert denied.status_code == 403


def test_kpi_transaction_rebuild_is_idempotent_and_reverses_stale_task_events() -> None:
    ids = _bootstrap()
    task = _done_task(ids["staff"])
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET status = 'done', completed_at = ? WHERE id = ?",
            ("2026-04-09T10:00:00+00:00", task["id"]),
        )

    first = client.post("/kpi/transactions/rebuild?month=2026-04", headers=_hdr(ids["admin"]))
    assert first.status_code == 200
    assert first.json()["active_count"] >= 1

    second = client.post("/kpi/transactions/rebuild?month=2026-04", headers=_hdr(ids["admin"]))
    assert second.status_code == 200
    transactions = client.get("/kpi/transactions?month=2026-04", headers=_hdr(ids["admin"]))
    assert transactions.status_code == 200
    active_task_events = [
        row for row in transactions.json()
        if row["source_type"] == "task" and row["source_id"] == task["id"] and row["status"] == "active"
    ]
    assert len(active_task_events) == 1

    with get_connection() as conn:
        conn.execute("UPDATE tasks SET status = 'todo', completed_at = NULL WHERE id = ?", (task["id"],))
    rebuilt = client.post("/kpi/transactions/rebuild?month=2026-04", headers=_hdr(ids["admin"]))
    assert rebuilt.status_code == 200
    rows = client.get("/kpi/transactions?month=2026-04", headers=_hdr(ids["admin"])).json()
    assert any(row["source_type"] == "task" and row["source_id"] == task["id"] and row["status"] == "reversed" for row in rows)


def test_manual_adjustments_require_approval_before_affecting_kpi() -> None:
    ids = _bootstrap()

    pending = client.post(
        "/kpi/adjustments",
        headers=_hdr(ids["manager"]),
        json={"user_id": ids["staff"], "month": "2026-04", "points": 4, "reason": "Manager nomination"},
    )
    assert pending.status_code == 200
    assert pending.json()["status"] == "pending"

    monthly_before = client.get("/kpi/monthly?month=2026-04", headers=_hdr(ids["admin"]))
    assert all(row["score"] != 4 for row in monthly_before.json())

    approved = client.post(
        f"/kpi/adjustments/{pending.json()['id']}/approve",
        headers=_hdr(ids["hr"]),
        json={"review_reason": "Approved by HR"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    monthly_after = client.get("/kpi/monthly?month=2026-04", headers=_hdr(ids["admin"]))
    staff_row = next(row for row in monthly_after.json() if row["user_id"] == ids["staff"])
    assert staff_row["score"] == 4

    hr_adjustment = client.post(
        "/kpi/adjustments",
        headers=_hdr(ids["hr"]),
        json={"user_id": ids["staff"], "month": "2026-04", "points": -1, "reason": "HR correction"},
    )
    assert hr_adjustment.status_code == 200
    assert hr_adjustment.json()["status"] == "approved"


def test_kpi_targets_progress_import_and_warning_notifications() -> None:
    ids = _bootstrap()
    _done_task(ids["staff"])
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET status = 'done', completed_at = ? WHERE assignee_id = ?",
            ("2026-04-09T10:00:00+00:00", ids["staff"]),
        )

    created = client.post(
        "/kpi/targets",
        headers=_hdr(ids["hr"]),
        json={"user_id": ids["staff"], "month": "2026-04", "target_score": 15.0},
    )
    assert created.status_code == 200
    assert created.json()["target_score"] == 15.0

    progress = client.get("/kpi/targets/progress?month=2026-04", headers=_hdr(ids["hr"]))
    assert progress.status_code == 200
    staff_progress = next(row for row in progress.json() if row["user_id"] == ids["staff"])
    assert staff_progress["score"] == 10.0
    assert staff_progress["target_score"] == 15.0
    assert staff_progress["gap"] == 5.0

    first_warning = client.post("/notifications/kpi-target-warnings/run?month=2026-04", headers=_hdr(ids["hr"]))
    assert first_warning.status_code == 200
    assert first_warning.json()["created"] >= 1
    second_warning = client.post("/notifications/kpi-target-warnings/run?month=2026-04", headers=_hdr(ids["hr"]))
    assert second_warning.status_code == 200
    assert second_warning.json()["created"] == 0
    assert second_warning.json()["skipped_duplicates"] >= 1
    assert any(n["type"] == "kpi_target_warning" for n in list_app_notifications(ids["staff"], limit=20))

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["user_id", "month", "target_score"])
    sheet.append([ids["other"], "2026-04", 12])
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    imported = client.post(
        "/kpi/targets/import",
        headers=_hdr(ids["hr"]),
        files={"file": ("targets.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert imported.status_code == 200
    assert imported.json()["upserted_count"] == 1


def test_kpi_history_breakdowns_and_reports_include_target_progress() -> None:
    ids = _bootstrap()
    _done_task(ids["staff"])
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET status = 'done', completed_at = ? WHERE assignee_id = ?",
            ("2026-04-09T10:00:00+00:00", ids["staff"]),
        )
    client.post(
        "/kpi/targets",
        headers=_hdr(ids["hr"]),
        json={"user_id": ids["staff"], "month": "2026-04", "target_score": 15.0},
    )

    history = client.get(f"/kpi/history?user_id={ids['staff']}&months=6&end_month=2026-04", headers=_hdr(ids["hr"]))
    assert history.status_code == 200
    assert history.json()[-1]["month"] == "2026-04"

    team = client.get("/kpi/team-summary?month=2026-04", headers=_hdr(ids["hr"]))
    assert team.status_code == 200
    assert team.json()["month"] == "2026-04"

    departments = client.get("/kpi/department-breakdown?month=2026-04", headers=_hdr(ids["hr"]))
    assert departments.status_code == 200
    assert departments.json()

    csv_report = client.get("/reports/kpi.csv?month=2026-04", headers=_hdr(ids["hr"]))
    assert csv_report.status_code == 200
    assert "target_score" in csv_report.text
    assert "progress_percent" in csv_report.text

    xlsx_report = client.get("/reports/kpi.xlsx?month=2026-04", headers=_hdr(ids["hr"]))
    assert xlsx_report.status_code == 200
    assert "teamswork-kpi-2026-04.xlsx" in xlsx_report.headers["content-disposition"]

    staff_export = client.get("/reports/kpi.csv?month=2026-04", headers=_hdr(ids["staff"]))
    assert staff_export.status_code == 403
