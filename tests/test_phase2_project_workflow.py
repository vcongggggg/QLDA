from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import get_connection, init_db
from app.main import app
from app.repository import create_task, create_user


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _unique(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"


def test_manager_project_creation_defaults_owner_and_exposes_backlog_sprint_flow() -> None:
    init_db()
    marker = _unique("phase2-project")
    manager = create_user(f"{marker} Manager", f"{marker}.manager@example.com", "manager", "PMO")
    staff = create_user(f"{marker} Staff", f"{marker}.staff@example.com", "staff", "Engineering")

    project_resp = client.post(
        "/projects",
        headers=_hdr(int(manager["id"])),
        json={"name": f"{marker} Project", "description": "Phase 2 project workflow", "status": "active"},
    )
    assert project_resp.status_code == 200
    project = project_resp.json()
    assert project["manager_id"] == manager["id"]

    member_resp = client.post(
        f"/projects/{project['id']}/members",
        headers=_hdr(int(manager["id"])),
        json={"user_id": staff["id"], "role": "member"},
    )
    assert member_resp.status_code == 200

    sprint_resp = client.post(
        f"/projects/{project['id']}/sprints",
        headers=_hdr(int(manager["id"])),
        json={
            "name": f"{marker} Sprint",
            "goal": "Ship Phase 2 workflow",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        },
    )
    assert sprint_resp.status_code == 200

    task = create_task(
        f"{marker} Backlog task",
        "Visible backlog task",
        int(staff["id"]),
        int(project["id"]),
        None,
        3,
        "medium",
        (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    )

    backlog = client.get(f"/projects/{project['id']}/backlog", headers=_hdr(int(manager["id"])))
    assert backlog.status_code == 200
    assert [item["id"] for item in backlog.json()] == [task["id"]]

    move = client.post(
        f"/projects/{project['id']}/backlog/move-to-sprint",
        headers=_hdr(int(manager["id"])),
        json={"task_ids": [task["id"]], "sprint_id": sprint_resp.json()["id"]},
    )
    assert move.status_code == 200
    assert move.json()["updated"] == 1

    with get_connection() as conn:
        logs = conn.execute(
            "SELECT action, entity FROM audit_logs WHERE actor_user_id = ? ORDER BY id DESC",
            (manager["id"],),
        ).fetchall()
    evidence = {(row["action"], row["entity"]) for row in logs}
    assert ("create", "project") in evidence
    assert ("create", "project_member") in evidence
    assert ("create", "sprint") in evidence
    assert ("move_to_sprint", "backlog") in evidence


def test_outside_manager_cannot_mutate_project_sprint_or_membership() -> None:
    init_db()
    marker = _unique("phase2-project-rbac")
    owner = create_user(f"{marker} Owner", f"{marker}.owner@example.com", "manager", "PMO")
    outside = create_user(f"{marker} Outside", f"{marker}.outside@example.com", "manager", "PMO")
    staff = create_user(f"{marker} Staff", f"{marker}.staff@example.com", "staff", "Engineering")

    project = client.post(
        "/projects",
        headers=_hdr(int(owner["id"])),
        json={"name": f"{marker} Project", "status": "active"},
    ).json()

    member_resp = client.post(
        f"/projects/{project['id']}/members",
        headers=_hdr(int(outside["id"])),
        json={"user_id": staff["id"], "role": "member"},
    )
    assert member_resp.status_code == 403

    sprint_resp = client.post(
        f"/projects/{project['id']}/sprints",
        headers=_hdr(int(outside["id"])),
        json={
            "name": f"{marker} Sprint",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        },
    )
    assert sprint_resp.status_code == 403
