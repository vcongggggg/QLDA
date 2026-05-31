from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import create_project, create_user


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _unique(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"


def _template_payload(marker: str, project_id: int | None = None) -> dict:
    return {
        "name": f"{marker} Weekly template",
        "title": f"{marker} Weekly task",
        "description": "Generated from template",
        "project_id": project_id,
        "story_points": 3,
        "difficulty": "medium",
        "priority": "high",
        "labels": ["weekly"],
        "checklist": ["Review"],
        "subtasks": ["Prepare"],
    }


def test_task_template_crud_and_create_task_from_template() -> None:
    init_db()
    marker = _unique("template")
    manager = create_user(f"{marker} Manager", f"{marker}.manager@example.com", "manager", "PMO")
    staff = create_user(f"{marker} Staff", f"{marker}.staff@example.com", "staff", "Engineering")
    project = create_project(f"{marker} Project", None, None, int(manager["id"]), None, None, "active")

    created = client.post("/task-templates", headers=_hdr(int(manager["id"])), json=_template_payload(marker, int(project["id"])))
    assert created.status_code == 200
    template_id = created.json()["id"]

    listed = client.get(f"/task-templates?project_id={project['id']}", headers=_hdr(int(manager["id"])))
    assert listed.status_code == 200
    assert any(item["id"] == template_id for item in listed.json())

    task = client.post(
        f"/task-templates/{template_id}/tasks",
        headers=_hdr(int(manager["id"])),
        json={
            "assignee_id": int(staff["id"]),
            "project_id": int(project["id"]),
            "deadline": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        },
    )
    assert task.status_code == 200
    assert task.json()["title"] == f"{marker} Weekly task"
    assert task.json()["labels"] == ["weekly"]


def test_recurring_rule_run_due_creates_task_and_advances_next_run() -> None:
    init_db()
    marker = _unique("recurring")
    manager = create_user(f"{marker} Manager", f"{marker}.manager@example.com", "manager", "PMO")
    staff = create_user(f"{marker} Staff", f"{marker}.staff@example.com", "staff", "Engineering")

    template = client.post("/task-templates", headers=_hdr(int(manager["id"])), json=_template_payload(marker))
    assert template.status_code == 200
    template_id = template.json()["id"]
    next_run = datetime.now(timezone.utc) - timedelta(days=1)

    rule = client.post(
        "/recurring-task-rules",
        headers=_hdr(int(manager["id"])),
        json={
            "template_id": template_id,
            "assignee_id": int(staff["id"]),
            "frequency": "weekly",
            "next_run_at": next_run.isoformat(),
            "active": True,
        },
    )
    assert rule.status_code == 200

    run = client.post("/recurring-task-rules/run-due", headers=_hdr(int(manager["id"])))
    assert run.status_code == 200
    assert run.json()["created_count"] == 1
    assert run.json()["tasks"][0]["title"] == f"{marker} Weekly task"
