from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import create_project, create_sprint, create_task, create_user, update_task_status


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _unique(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"


def _seed_filter_tasks() -> dict:
    init_db()
    marker = _unique("filter")
    manager = create_user(f"{marker} Manager", f"{marker}.manager@example.com", "manager", "PMO")
    staff = create_user(f"{marker} Staff", f"{marker}.staff@example.com", "staff", "Engineering")
    other = create_user(f"{marker} Other", f"{marker}.other@example.com", "staff", "Engineering")
    project = create_project(f"{marker} Project", None, None, int(manager["id"]), None, None, "active")
    other_project = create_project(f"{marker} Other Project", None, None, int(manager["id"]), None, None, "active")
    sprint = create_sprint(
        int(project["id"]),
        f"{marker} Sprint",
        None,
        datetime.now(timezone.utc).isoformat(),
        (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
    )
    future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    overdue = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

    todo = create_task(
        f"{marker} Project todo needle",
        "Searchable description alpha",
        int(staff["id"]),
        int(project["id"]),
        int(sprint["id"]),
        3,
        "medium",
        future,
    )
    doing = create_task(
        f"{marker} Doing task",
        "needle appears in description",
        int(staff["id"]),
        int(project["id"]),
        int(sprint["id"]),
        5,
        "hard",
        future,
    )
    update_task_status(int(doing["id"]), "doing")
    late = create_task(
        f"{marker} Overdue task",
        "Past deadline",
        int(staff["id"]),
        int(project["id"]),
        None,
        1,
        "easy",
        overdue,
    )
    done_late = create_task(
        f"{marker} Done old task",
        "Done tasks are not overdue",
        int(staff["id"]),
        int(project["id"]),
        None,
        1,
        "easy",
        overdue,
    )
    update_task_status(int(done_late["id"]), "done")
    other_assignee = create_task(
        f"{marker} Other assignee",
        "Private to another staff member",
        int(other["id"]),
        int(project["id"]),
        None,
        2,
        "easy",
        future,
    )
    other_project_task = create_task(
        f"{marker} Other project",
        "Different project",
        int(staff["id"]),
        int(other_project["id"]),
        None,
        2,
        "easy",
        future,
    )

    return {
        "marker": marker,
        "manager_id": int(manager["id"]),
        "staff_id": int(staff["id"]),
        "other_id": int(other["id"]),
        "project_id": int(project["id"]),
        "sprint_id": int(sprint["id"]),
        "todo_id": int(todo["id"]),
        "doing_id": int(doing["id"]),
        "late_id": int(late["id"]),
        "done_late_id": int(done_late["id"]),
        "other_assignee_id": int(other_assignee["id"]),
        "other_project_task_id": int(other_project_task["id"]),
        "future_deadline": future,
    }


def _ids(response) -> set[int]:
    assert response.status_code == 200
    return {int(item["id"]) for item in response.json()}


def test_get_tasks_filters_by_project_assignee_status_and_overdue() -> None:
    data = _seed_filter_tasks()

    by_project = client.get(f"/tasks?project_id={data['project_id']}", headers=_hdr(data["manager_id"]))
    assert data["todo_id"] in _ids(by_project)
    assert data["other_project_task_id"] not in _ids(by_project)

    by_assignee = client.get(f"/tasks?assignee_id={data['staff_id']}", headers=_hdr(data["manager_id"]))
    assert data["todo_id"] in _ids(by_assignee)
    assert data["other_assignee_id"] not in _ids(by_assignee)

    by_status = client.get("/tasks?status=doing", headers=_hdr(data["manager_id"]))
    assert data["doing_id"] in _ids(by_status)
    assert data["todo_id"] not in _ids(by_status)

    overdue = client.get("/tasks?overdue=true", headers=_hdr(data["manager_id"]))
    overdue_ids = _ids(overdue)
    assert data["late_id"] in overdue_ids
    assert data["done_late_id"] not in overdue_ids


def test_get_tasks_combines_keyword_sprint_status_and_deadline_filters() -> None:
    data = _seed_filter_tasks()
    deadline_to = (datetime.fromisoformat(data["future_deadline"]) + timedelta(days=1)).isoformat()

    response = client.get(
        "/tasks",
        params={
            "project_id": data["project_id"],
            "sprint_id": data["sprint_id"],
            "assignee_id": data["staff_id"],
            "status": "doing",
            "keyword": "needle",
            "deadline_to": deadline_to,
        },
        headers=_hdr(data["manager_id"]),
    )

    assert _ids(response) == {data["doing_id"]}


def test_staff_task_filters_remain_scoped_to_own_assignments() -> None:
    data = _seed_filter_tasks()

    response = client.get(f"/tasks?assignee_id={data['other_id']}", headers=_hdr(data["staff_id"]))

    ids = _ids(response)
    assert data["todo_id"] in ids
    assert data["other_assignee_id"] not in ids


def test_project_backlog_lists_only_unsprinted_tasks_and_preserves_staff_scope() -> None:
    data = _seed_filter_tasks()

    manager_resp = client.get(f"/projects/{data['project_id']}/backlog", headers=_hdr(data["manager_id"]))
    manager_ids = _ids(manager_resp)
    assert data["late_id"] in manager_ids
    assert data["done_late_id"] in manager_ids
    assert data["other_assignee_id"] in manager_ids
    assert data["todo_id"] not in manager_ids
    assert data["other_project_task_id"] not in manager_ids

    staff_resp = client.get(f"/projects/{data['project_id']}/backlog", headers=_hdr(data["staff_id"]))
    staff_ids = _ids(staff_resp)
    assert data["late_id"] in staff_ids
    assert data["done_late_id"] in staff_ids
    assert data["other_assignee_id"] not in staff_ids


def test_get_tasks_rejects_invalid_filters() -> None:
    data = _seed_filter_tasks()

    invalid_status = client.get("/tasks?status=blocked", headers=_hdr(data["manager_id"]))
    assert invalid_status.status_code == 400
    assert invalid_status.json()["detail"] == "status must be one of todo|doing|done"

    invalid_range = client.get(
        "/tasks?deadline_from=2026-05-20T00:00:00Z&deadline_to=2026-05-19T00:00:00Z",
        headers=_hdr(data["manager_id"]),
    )
    assert invalid_range.status_code == 400
    assert invalid_range.json()["detail"] == "deadline_to must be greater than or equal to deadline_from"
