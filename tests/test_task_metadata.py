from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import create_task, create_user


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _unique(prefix: str) -> str:
    return f"{prefix}.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"


def test_create_list_and_detail_include_task_metadata_defaults_and_values() -> None:
    init_db()
    manager = create_user("Metadata Manager", f"{_unique('metadata.manager')}@example.com", "manager", "PMO")
    staff = create_user("Metadata Staff", f"{_unique('metadata.staff')}@example.com", "staff", "Engineering")

    deadline = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    created = client.post(
        "/tasks",
        headers=_hdr(int(manager["id"])),
        json={
            "title": "Document task metadata",
            "description": "Add labels and checklist",
            "assignee_id": int(staff["id"]),
            "story_points": 3,
            "difficulty": "medium",
            "priority": "high",
            "labels": ["phase-2", "backend"],
            "checklist": ["Write tests", "Update API"],
            "subtasks": ["Schema", "Repository"],
            "dependencies": ["Phase 1A auth baseline"],
            "attachment_metadata": [{"name": "spec-link", "url": "https://example.com/spec"}],
            "deadline": deadline,
        },
    )

    assert created.status_code == 200
    payload = created.json()
    assert payload["priority"] == "high"
    assert payload["labels"] == ["phase-2", "backend"]
    assert payload["checklist"] == ["Write tests", "Update API"]
    assert payload["attachment_metadata"][0]["name"] == "spec-link"

    listed = client.get("/tasks", headers=_hdr(int(manager["id"])))
    assert listed.status_code == 200
    listed_task = next(item for item in listed.json() if item["id"] == payload["id"])
    assert listed_task["priority"] == "high"
    assert listed_task["subtasks"] == ["Schema", "Repository"]

    detail = client.get(f"/tasks/{payload['id']}", headers=_hdr(int(manager["id"])))
    assert detail.status_code == 200
    assert detail.json()["dependencies"] == ["Phase 1A auth baseline"]

    default_task = create_task(
        "Default metadata task",
        None,
        int(staff["id"]),
        None,
        None,
        1,
        "easy",
        deadline,
    )
    assert default_task["priority"] == "medium"
    assert default_task["labels"] == []


def test_task_metadata_update_validates_inputs_and_preserves_staff_scope() -> None:
    init_db()
    manager = create_user("Metadata Scope Manager", f"{_unique('scope.manager')}@example.com", "manager", "PMO")
    owner = create_user("Metadata Owner", f"{_unique('scope.owner')}@example.com", "staff", "Engineering")
    outsider = create_user("Metadata Outsider", f"{_unique('scope.outsider')}@example.com", "staff", "Engineering")
    task = create_task(
        "Scoped metadata task",
        None,
        int(owner["id"]),
        None,
        None,
        2,
        "medium",
        (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    )

    invalid = client.patch(
        f"/tasks/{task['id']}/metadata",
        headers=_hdr(int(manager["id"])),
        json={"priority": "critical"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "priority must be one of low|medium|high|urgent"

    own_update = client.patch(
        f"/tasks/{task['id']}/metadata",
        headers=_hdr(int(owner["id"])),
        json={"priority": "urgent", "labels": ["mine"]},
    )
    assert own_update.status_code == 200
    assert own_update.json()["priority"] == "urgent"
    assert own_update.json()["labels"] == ["mine"]

    forbidden = client.patch(
        f"/tasks/{task['id']}/metadata",
        headers=_hdr(int(outsider["id"])),
        json={"labels": ["not-mine"]},
    )
    assert forbidden.status_code == 403

    too_long = client.patch(
        f"/tasks/{task['id']}/metadata",
        headers=_hdr(int(owner["id"])),
        json={"labels": ["x" * 81]},
    )
    assert too_long.status_code == 400


def test_duplicate_task_copies_metadata_and_resets_status() -> None:
    init_db()
    manager = create_user("Duplicate Manager", f"{_unique('duplicate.manager')}@example.com", "manager", "PMO")
    staff = create_user("Duplicate Staff", f"{_unique('duplicate.staff')}@example.com", "staff", "Engineering")
    task_resp = client.post(
        "/tasks",
        headers=_hdr(int(manager["id"])),
        json={
            "title": "Original metadata task",
            "description": "Copy this",
            "assignee_id": int(staff["id"]),
            "story_points": 5,
            "difficulty": "hard",
            "priority": "high",
            "labels": ["copy-me"],
            "deadline": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
    )
    assert task_resp.status_code == 200
    original_id = task_resp.json()["id"]
    done = client.patch(f"/tasks/{original_id}/status", headers=_hdr(int(staff["id"])), json={"status": "done"})
    assert done.status_code == 200

    duplicated = client.post(
        f"/tasks/{original_id}/duplicate",
        headers=_hdr(int(manager["id"])),
        json={"title": "Copied metadata task"},
    )

    assert duplicated.status_code == 200
    payload = duplicated.json()
    assert payload["title"] == "Copied metadata task"
    assert payload["status"] == "todo"
    assert payload["completed_at"] is None
    assert payload["priority"] == "high"
    assert payload["labels"] == ["copy-me"]
