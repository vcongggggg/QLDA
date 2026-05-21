from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import (
    add_project_member,
    create_project,
    create_sprint,
    create_task,
    create_user,
    replace_role_permissions,
    update_task_status,
    upsert_sprint_capacity,
)


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _unique(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"


def _seed_workload_case() -> dict:
    init_db()
    marker = _unique("workload")
    admin = create_user(f"{marker} Admin", f"{marker}.admin@example.com", "admin", "IT")
    manager = create_user(f"{marker} Manager", f"{marker}.manager@example.com", "manager", "PMO")
    staff_under = create_user(f"{marker} Under", f"{marker}.under@example.com", "staff", "Engineering")
    staff_over = create_user(f"{marker} Over", f"{marker}.over@example.com", "staff", "Engineering")
    staff_missing_capacity = create_user(
        f"{marker} Missing Capacity",
        f"{marker}.missing@example.com",
        "staff",
        "Engineering",
    )
    outsider = create_user(f"{marker} Outsider", f"{marker}.outsider@example.com", "staff", "Engineering")
    project = create_project(f"{marker} Project", None, None, int(manager["id"]), None, None, "active")
    sprint = create_sprint(
        int(project["id"]),
        f"{marker} Sprint",
        None,
        datetime.now(timezone.utc).isoformat(),
        (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
    )
    other_sprint = create_sprint(
        int(project["id"]),
        f"{marker} Other Sprint",
        None,
        datetime.now(timezone.utc).isoformat(),
        (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
    )

    for user in (manager, staff_under, staff_over, staff_missing_capacity):
        add_project_member(int(project["id"]), int(user["id"]), "member")

    future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    overdue = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

    create_task(
        f"{marker} Under capacity task",
        None,
        int(staff_under["id"]),
        int(project["id"]),
        int(sprint["id"]),
        3,
        "medium",
        future,
    )
    create_task(
        f"{marker} Over capacity future task",
        None,
        int(staff_over["id"]),
        int(project["id"]),
        int(sprint["id"]),
        4,
        "medium",
        future,
    )
    create_task(
        f"{marker} Over capacity overdue task",
        None,
        int(staff_over["id"]),
        int(project["id"]),
        int(sprint["id"]),
        4,
        "hard",
        overdue,
    )
    done_overdue = create_task(
        f"{marker} Done overdue task",
        None,
        int(staff_over["id"]),
        int(project["id"]),
        int(sprint["id"]),
        100,
        "hard",
        overdue,
    )
    update_task_status(int(done_overdue["id"]), "done")
    create_task(
        f"{marker} Other sprint overdue task",
        None,
        int(staff_over["id"]),
        int(project["id"]),
        int(other_sprint["id"]),
        50,
        "hard",
        overdue,
    )
    create_task(
        f"{marker} Missing capacity task",
        None,
        int(staff_missing_capacity["id"]),
        int(project["id"]),
        int(sprint["id"]),
        9,
        "medium",
        future,
    )

    upsert_sprint_capacity(int(sprint["id"]), int(staff_under["id"]), 10.0, 0.0)
    upsert_sprint_capacity(int(sprint["id"]), int(staff_over["id"]), 6.0, 0.0)

    return {
        "admin_id": int(admin["id"]),
        "manager_id": int(manager["id"]),
        "staff_under_id": int(staff_under["id"]),
        "staff_over_id": int(staff_over["id"]),
        "staff_missing_capacity_id": int(staff_missing_capacity["id"]),
        "outsider_id": int(outsider["id"]),
        "sprint_id": int(sprint["id"]),
    }


def _rows_by_user(payload: list[dict]) -> dict[int, dict]:
    return {int(row["user_id"]): row for row in payload}


def test_sprint_workload_warnings_detect_capacity_and_overdue_rules() -> None:
    data = _seed_workload_case()

    resp = client.get(f"/sprints/{data['sprint_id']}/workload-warnings", headers=_hdr(data["manager_id"]))

    assert resp.status_code == 200
    rows = _rows_by_user(resp.json())

    under = rows[data["staff_under_id"]]
    assert under["workload_points"] == 3
    assert under["capacity_points"] == 10.0
    assert under["overloaded"] is False
    assert under["risk_level"] == "low"
    assert under["overdue_task_count"] == 0

    over = rows[data["staff_over_id"]]
    assert over["workload_points"] == 8
    assert over["capacity_points"] == 6.0
    assert over["open_task_count"] == 2
    assert over["overdue_task_count"] == 1
    assert over["overloaded"] is True
    assert over["risk_level"] == "high"
    assert "workload exceeds capacity" in over["reasons"]
    assert "1 overdue open task" in over["reasons"]

    missing_capacity = rows[data["staff_missing_capacity_id"]]
    assert missing_capacity["workload_points"] == 9
    assert missing_capacity["capacity_points"] is None
    assert missing_capacity["overloaded"] is False
    assert missing_capacity["risk_level"] == "low"


def test_staff_sees_only_own_sprint_workload_warning() -> None:
    data = _seed_workload_case()

    resp = client.get(f"/sprints/{data['sprint_id']}/workload-warnings", headers=_hdr(data["staff_over_id"]))

    assert resp.status_code == 200
    payload = resp.json()
    assert [int(row["user_id"]) for row in payload] == [data["staff_over_id"]]


def test_staff_cannot_view_workload_for_inaccessible_project() -> None:
    data = _seed_workload_case()

    resp = client.get(f"/sprints/{data['sprint_id']}/workload-warnings", headers=_hdr(data["outsider_id"]))

    assert resp.status_code == 403


def test_sprint_workload_warnings_require_sprints_view_permission() -> None:
    data = _seed_workload_case()
    original = client.get(
        "/rbac/roles/staff/permissions",
        headers=_hdr(data["admin_id"]),
    ).json()["permissions"]
    original_keys = [item["key"] for item in original]
    try:
        replace_role_permissions("staff", [key for key in original_keys if key != "sprints.view"])

        resp = client.get(f"/sprints/{data['sprint_id']}/workload-warnings", headers=_hdr(data["staff_over_id"]))

        assert resp.status_code == 403
    finally:
        replace_role_permissions("staff", original_keys)
