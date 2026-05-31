from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import (
    add_project_member,
    create_project,
    create_task,
    create_user,
    list_app_notifications,
    update_task_status,
)


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _unique(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"


def _seed_deadline_case() -> dict:
    init_db()
    marker = _unique("deadline")
    manager = create_user(f"{marker} Manager", f"{marker}.manager@example.com", "manager", "PMO")
    outside_manager = create_user(f"{marker} Outside Manager", f"{marker}.outside.manager@example.com", "manager", "PMO")
    staff = create_user(f"{marker} Staff", f"{marker}.staff@example.com", "staff", "Engineering")
    project = create_project(f"{marker} Project", None, None, int(manager["id"]), None, None, "active")
    add_project_member(int(project["id"]), int(staff["id"]), "member")
    deadline = datetime.now(timezone.utc) + timedelta(days=2)
    task = create_task(
        f"{marker} Extendable task",
        "Needs a manager-approved deadline extension",
        int(staff["id"]),
        int(project["id"]),
        None,
        3,
        "medium",
        deadline.isoformat(),
    )
    return {
        "manager_id": int(manager["id"]),
        "outside_manager_id": int(outside_manager["id"]),
        "staff_id": int(staff["id"]),
        "project_id": int(project["id"]),
        "task_id": int(task["id"]),
        "old_deadline": deadline,
    }


def test_manager_extends_task_deadline_with_audit_and_notification() -> None:
    data = _seed_deadline_case()
    new_deadline = data["old_deadline"] + timedelta(days=3)

    response = client.patch(
        f"/tasks/{data['task_id']}/deadline-extension",
        headers=_hdr(data["manager_id"]),
        json={"deadline": new_deadline.isoformat(), "reason": "Vendor dependency moved the review date"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert datetime.fromisoformat(payload["deadline"]) == new_deadline

    detail = client.get(f"/tasks/{data['task_id']}", headers=_hdr(data["manager_id"]))
    assert detail.status_code == 200
    logs = detail.json()["activity_logs"]
    assert logs[0]["action"] == "extend_deadline"
    assert "old_deadline=" in logs[0]["detail"]
    assert "new_deadline=" in logs[0]["detail"]
    assert "Vendor dependency moved the review date" in logs[0]["detail"]

    notifications = list_app_notifications(data["staff_id"])
    assert notifications[0]["type"] == "task_status_changed"
    assert notifications[0]["title"] == "Task deadline extended"
    assert notifications[0]["entity_id"] == data["task_id"]


def test_staff_cannot_extend_even_assigned_own_task() -> None:
    data = _seed_deadline_case()

    response = client.patch(
        f"/tasks/{data['task_id']}/deadline-extension",
        headers=_hdr(data["staff_id"]),
        json={"deadline": (data["old_deadline"] + timedelta(days=1)).isoformat(), "reason": "Need more time"},
    )

    assert response.status_code == 403


def test_deadline_extension_requires_trimmed_reason_and_later_deadline() -> None:
    data = _seed_deadline_case()

    blank_reason = client.patch(
        f"/tasks/{data['task_id']}/deadline-extension",
        headers=_hdr(data["manager_id"]),
        json={"deadline": (data["old_deadline"] + timedelta(days=1)).isoformat(), "reason": "   "},
    )
    assert blank_reason.status_code == 400
    assert blank_reason.json()["detail"] == "extension reason is required"

    same_deadline = client.patch(
        f"/tasks/{data['task_id']}/deadline-extension",
        headers=_hdr(data["manager_id"]),
        json={"deadline": data["old_deadline"].isoformat(), "reason": "Same date is not an extension"},
    )
    assert same_deadline.status_code == 400
    assert same_deadline.json()["detail"] == "deadline must be later than current deadline"

    earlier_deadline = client.patch(
        f"/tasks/{data['task_id']}/deadline-extension",
        headers=_hdr(data["manager_id"]),
        json={"deadline": (data["old_deadline"] - timedelta(days=1)).isoformat(), "reason": "Earlier is invalid"},
    )
    assert earlier_deadline.status_code == 400
    assert earlier_deadline.json()["detail"] == "deadline must be later than current deadline"


def test_completed_task_deadline_cannot_be_extended() -> None:
    data = _seed_deadline_case()
    update_task_status(data["task_id"], "done")

    response = client.patch(
        f"/tasks/{data['task_id']}/deadline-extension",
        headers=_hdr(data["manager_id"]),
        json={"deadline": (data["old_deadline"] + timedelta(days=2)).isoformat(), "reason": "Already completed"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "completed tasks cannot be extended"


def test_manager_outside_project_scope_cannot_extend_project_task() -> None:
    data = _seed_deadline_case()

    response = client.patch(
        f"/tasks/{data['task_id']}/deadline-extension",
        headers=_hdr(data["outside_manager_id"]),
        json={"deadline": (data["old_deadline"] + timedelta(days=2)).isoformat(), "reason": "No project access"},
    )

    assert response.status_code == 403
