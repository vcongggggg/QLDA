from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import add_project_member, create_project, create_sprint, create_task, create_user, update_task_status


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _unique(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"


def _seed_bulk_case() -> dict:
    init_db()
    marker = _unique("bulk")
    manager = create_user(f"{marker} Manager", f"{marker}.manager@example.com", "manager", "PMO")
    staff = create_user(f"{marker} Staff", f"{marker}.staff@example.com", "staff", "Engineering")
    other = create_user(f"{marker} Other", f"{marker}.other@example.com", "staff", "Engineering")
    outsider = create_user(f"{marker} Outsider", f"{marker}.outsider@example.com", "staff", "Engineering")
    project = create_project(f"{marker} Project", None, None, int(manager["id"]), None, None, "active")
    sprint = create_sprint(
        int(project["id"]),
        f"{marker} Sprint 1",
        None,
        datetime.now(timezone.utc).isoformat(),
        (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
    )
    target_sprint = create_sprint(
        int(project["id"]),
        f"{marker} Sprint 2",
        None,
        (datetime.now(timezone.utc) + timedelta(days=15)).isoformat(),
        (datetime.now(timezone.utc) + timedelta(days=28)).isoformat(),
    )
    add_project_member(int(project["id"]), int(staff["id"]), "member")
    add_project_member(int(project["id"]), int(other["id"]), "member")
    future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    backlog_a = create_task(f"{marker} Backlog A", None, int(staff["id"]), int(project["id"]), None, 2, "medium", future)
    backlog_b = create_task(f"{marker} Backlog B", None, int(staff["id"]), int(project["id"]), None, 3, "medium", future)
    sprint_task = create_task(
        f"{marker} Sprint task",
        None,
        int(staff["id"]),
        int(project["id"]),
        int(sprint["id"]),
        5,
        "hard",
        future,
    )
    done_task = create_task(
        f"{marker} Done sprint task",
        None,
        int(staff["id"]),
        int(project["id"]),
        int(sprint["id"]),
        1,
        "easy",
        future,
    )
    update_task_status(int(done_task["id"]), "done")
    return {
        "manager_id": int(manager["id"]),
        "staff_id": int(staff["id"]),
        "other_id": int(other["id"]),
        "outsider_id": int(outsider["id"]),
        "project_id": int(project["id"]),
        "sprint_id": int(sprint["id"]),
        "target_sprint_id": int(target_sprint["id"]),
        "backlog_a_id": int(backlog_a["id"]),
        "backlog_b_id": int(backlog_b["id"]),
        "sprint_task_id": int(sprint_task["id"]),
        "done_task_id": int(done_task["id"]),
    }


def test_bulk_task_actions_update_status_assignee_sprint_and_backlog() -> None:
    data = _seed_bulk_case()

    staff_forbidden = client.post(
        "/tasks/bulk",
        headers=_hdr(data["staff_id"]),
        json={"task_ids": [data["backlog_a_id"]], "status": "doing"},
    )
    assert staff_forbidden.status_code == 403

    empty = client.post("/tasks/bulk", headers=_hdr(data["manager_id"]), json={"task_ids": []})
    assert empty.status_code == 400

    status_update = client.post(
        "/tasks/bulk",
        headers=_hdr(data["manager_id"]),
        json={"task_ids": [data["backlog_a_id"], data["backlog_b_id"]], "status": "doing"},
    )
    assert status_update.status_code == 200
    assert status_update.json()["updated"] == 2

    assignee_update = client.post(
        "/tasks/bulk",
        headers=_hdr(data["manager_id"]),
        json={"task_ids": [data["backlog_a_id"]], "assignee_id": data["other_id"]},
    )
    assert assignee_update.status_code == 200
    detail = client.get(f"/tasks/{data['backlog_a_id']}", headers=_hdr(data["manager_id"]))
    assert detail.json()["assignee_id"] == data["other_id"]

    sprint_update = client.post(
        "/tasks/bulk",
        headers=_hdr(data["manager_id"]),
        json={"task_ids": [data["backlog_a_id"]], "sprint_id": data["sprint_id"]},
    )
    assert sprint_update.status_code == 200
    assert client.get(f"/tasks/{data['backlog_a_id']}", headers=_hdr(data["manager_id"])).json()["sprint_id"] == data["sprint_id"]

    backlog_update = client.post(
        "/tasks/bulk",
        headers=_hdr(data["manager_id"]),
        json={"task_ids": [data["backlog_a_id"]], "move_to_backlog": True},
    )
    assert backlog_update.status_code == 200
    assert client.get(f"/tasks/{data['backlog_a_id']}", headers=_hdr(data["manager_id"])).json()["sprint_id"] is None


def test_backlog_move_to_sprint_and_carryover_respect_project_and_status_rules() -> None:
    data = _seed_bulk_case()

    backlog = client.get(f"/projects/{data['project_id']}/backlog", headers=_hdr(data["manager_id"]))
    assert backlog.status_code == 200
    backlog_ids = {item["id"] for item in backlog.json()}
    assert {data["backlog_a_id"], data["backlog_b_id"]}.issubset(backlog_ids)
    assert data["sprint_task_id"] not in backlog_ids

    move = client.post(
        f"/projects/{data['project_id']}/backlog/move-to-sprint",
        headers=_hdr(data["manager_id"]),
        json={"task_ids": [data["backlog_a_id"], data["backlog_b_id"]], "sprint_id": data["sprint_id"]},
    )
    assert move.status_code == 200
    assert move.json()["updated"] == 2

    not_backlog = client.post(
        f"/projects/{data['project_id']}/backlog/move-to-sprint",
        headers=_hdr(data["manager_id"]),
        json={"task_ids": [data["sprint_task_id"]], "sprint_id": data["sprint_id"]},
    )
    assert not_backlog.status_code == 400

    carryover = client.post(
        f"/sprints/{data['sprint_id']}/carryover",
        headers=_hdr(data["manager_id"]),
        json={"target_sprint_id": data["target_sprint_id"]},
    )
    assert carryover.status_code == 200
    assert carryover.json()["updated"] == 3
    assert client.get(f"/tasks/{data['sprint_task_id']}", headers=_hdr(data["manager_id"])).json()["sprint_id"] == data["target_sprint_id"]
    assert client.get(f"/tasks/{data['done_task_id']}", headers=_hdr(data["manager_id"])).json()["sprint_id"] == data["sprint_id"]

    staff_carryover = client.post(
        f"/sprints/{data['sprint_id']}/carryover",
        headers=_hdr(data["staff_id"]),
        json={"target_sprint_id": data["target_sprint_id"]},
    )
    assert staff_carryover.status_code == 403
