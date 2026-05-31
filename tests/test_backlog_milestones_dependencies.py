from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import create_project, create_task, create_user


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _unique(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"


def _seed_case() -> dict:
    init_db()
    marker = _unique("backlog")
    manager = create_user(f"{marker} Manager", f"{marker}.manager@example.com", "manager", "PMO")
    staff = create_user(f"{marker} Staff", f"{marker}.staff@example.com", "staff", "Engineering")
    project = create_project(f"{marker} Project", None, None, int(manager["id"]), None, None, "active")
    deadline = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    first = create_task(f"{marker} First", None, int(staff["id"]), int(project["id"]), None, 3, "medium", deadline)
    second = create_task(f"{marker} Second", None, int(staff["id"]), int(project["id"]), None, 2, "easy", deadline)
    return {"manager_id": int(manager["id"]), "project_id": int(project["id"]), "first_id": int(first["id"]), "second_id": int(second["id"])}


def test_backlog_grooming_and_milestone_assignment() -> None:
    data = _seed_case()

    grooming = client.patch(
        f"/tasks/{data['first_id']}/backlog-grooming",
        headers=_hdr(data["manager_id"]),
        json={"backlog_rank": 10, "readiness_status": "ready", "acceptance_notes": "Ready for sprint planning"},
    )
    assert grooming.status_code == 200
    assert grooming.json()["backlog_rank"] == 10
    assert grooming.json()["readiness_status"] == "ready"

    milestone = client.post(
        f"/projects/{data['project_id']}/milestones",
        headers=_hdr(data["manager_id"]),
        json={"name": "MVP", "description": "Release milestone", "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(), "status": "planned"},
    )
    assert milestone.status_code == 200

    assigned = client.patch(
        f"/tasks/{data['first_id']}/milestone",
        headers=_hdr(data["manager_id"]),
        json={"milestone_id": milestone.json()["id"]},
    )
    assert assigned.status_code == 200
    assert assigned.json()["milestone_id"] == milestone.json()["id"]


def test_task_dependencies_validate_project_and_block_cycles() -> None:
    data = _seed_case()

    dependency = client.patch(
        f"/tasks/{data['second_id']}/dependencies",
        headers=_hdr(data["manager_id"]),
        json={"dependency_ids": [data["first_id"]]},
    )
    assert dependency.status_code == 200
    assert dependency.json()["dependency_ids"] == [data["first_id"]]

    cycle = client.patch(
        f"/tasks/{data['first_id']}/dependencies",
        headers=_hdr(data["manager_id"]),
        json={"dependency_ids": [data["second_id"]]},
    )
    assert cycle.status_code == 400
    assert cycle.json()["detail"] == "circular dependency"
