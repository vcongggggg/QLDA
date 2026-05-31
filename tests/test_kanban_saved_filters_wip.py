from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import create_project, create_sprint, create_task, create_user, update_task_status


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _unique(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"


def test_kanban_saved_filters_are_user_scoped_and_defaulted() -> None:
    init_db()
    marker = _unique("kanban-filter")
    manager = create_user(f"{marker} Manager", f"{marker}.manager@example.com", "manager", "PMO")
    other = create_user(f"{marker} Other", f"{marker}.other@example.com", "manager", "PMO")

    created = client.post(
        "/kanban/saved-filters",
        headers=_hdr(int(manager["id"])),
        json={"name": "My urgent work", "filters": {"status": "doing", "keyword": "urgent"}, "is_default": True},
    )
    assert created.status_code == 200
    filter_id = created.json()["id"]
    assert created.json()["is_default"] is True

    own = client.get("/kanban/saved-filters", headers=_hdr(int(manager["id"])))
    assert own.status_code == 200
    assert [item["id"] for item in own.json()] == [filter_id]

    forbidden = client.put(
        f"/kanban/saved-filters/{filter_id}",
        headers=_hdr(int(other["id"])),
        json={"name": "Steal", "filters": {"status": "todo"}, "is_default": False},
    )
    assert forbidden.status_code == 403


def test_kanban_summary_returns_story_points_and_wip_warnings() -> None:
    init_db()
    marker = _unique("kanban-wip")
    manager = create_user(f"{marker} Manager", f"{marker}.manager@example.com", "manager", "PMO")
    staff = create_user(f"{marker} Staff", f"{marker}.staff@example.com", "staff", "Engineering")
    project = create_project(f"{marker} Project", None, None, int(manager["id"]), None, None, "active")
    sprint = create_sprint(
        int(project["id"]),
        f"{marker} Sprint",
        None,
        datetime.now(timezone.utc).isoformat(),
        (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
    )
    deadline = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    create_task(f"{marker} Todo", None, int(staff["id"]), int(project["id"]), int(sprint["id"]), 3, "medium", deadline)
    doing = create_task(f"{marker} Doing", None, int(staff["id"]), int(project["id"]), int(sprint["id"]), 5, "hard", deadline)
    update_task_status(int(doing["id"]), "doing")

    policy = client.put(
        "/kanban/wip-policy",
        headers=_hdr(int(manager["id"])),
        json={"project_id": int(project["id"]), "sprint_id": int(sprint["id"]), "todo_limit": 0, "doing_limit": 3},
    )
    assert policy.status_code == 200

    summary = client.get(f"/kanban/summary?project_id={project['id']}&sprint_id={sprint['id']}", headers=_hdr(int(manager["id"])))
    assert summary.status_code == 200
    columns = {item["status"]: item for item in summary.json()["columns"]}
    assert columns["todo"]["task_count"] == 1
    assert columns["todo"]["story_points"] == 3
    assert columns["todo"]["overdue_count"] == 0
    assert columns["todo"]["wip_exceeded"] is True
    assert summary.json()["total_story_points"] == 8
    assert summary.json()["wip_exceeded_columns"] == 1


def test_kanban_summary_reports_overdue_and_staff_self_scope() -> None:
    init_db()
    marker = _unique("kanban-scope")
    manager = create_user(f"{marker} Manager", f"{marker}.manager@example.com", "manager", "PMO")
    staff = create_user(f"{marker} Staff", f"{marker}.staff@example.com", "staff", "Engineering")
    other = create_user(f"{marker} Other", f"{marker}.other@example.com", "staff", "Engineering")
    project = create_project(f"{marker} Project", None, None, int(manager["id"]), None, None, "active")
    overdue = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    create_task(f"{marker} Overdue", None, int(staff["id"]), int(project["id"]), None, 2, "medium", overdue)
    create_task(f"{marker} Other", None, int(other["id"]), int(project["id"]), None, 3, "medium", future)

    manager_summary = client.get(f"/kanban/summary?project_id={project['id']}", headers=_hdr(int(manager["id"])))
    assert manager_summary.status_code == 200
    assert manager_summary.json()["total_tasks"] == 2
    assert manager_summary.json()["overdue_open_tasks"] == 1

    staff_summary = client.get(f"/kanban/summary?project_id={project['id']}", headers=_hdr(int(staff["id"])))
    assert staff_summary.status_code == 200
    assert staff_summary.json()["total_tasks"] == 1
    assert staff_summary.json()["overdue_open_tasks"] == 1


def test_kanban_ui_contains_release_controls_and_evidence_hooks() -> None:
    index_html = Path("app/static/index.html").read_text(encoding="utf-8")
    kanban_js = Path("app/static/js/kanban.js").read_text(encoding="utf-8")
    rag_js = Path("app/static/js/rag-teams.js").read_text(encoding="utf-8")

    assert "kanbanSummaryPanel" in index_html
    assert "kanban-list" in index_html
    assert "kanbanDefaultFilterCheck" in index_html
    assert "setKanbanView('list')" in index_html
    assert "function renderKanbanSummary" in kanban_js
    assert "function renderKanbanList" in kanban_js
    assert "WIP limit warning" in kanban_js
    assert "teamswork.kanban.savedFilterId" in rag_js
