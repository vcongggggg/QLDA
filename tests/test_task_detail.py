from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import create_task, create_user


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _unique_email(prefix: str) -> str:
    return f"{prefix}.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}@example.com"


def test_task_detail_includes_comments_activity_and_due_state() -> None:
    init_db()
    manager = create_user("Task Detail Manager", _unique_email("detail.manager"), "manager", "PMO")
    staff = create_user("Task Detail Staff", _unique_email("detail.staff"), "staff", "Engineering")
    task = create_task(
        title="Prepare detail drawer",
        description="Expose all fields needed by the drawer",
        assignee_id=int(staff["id"]),
        project_id=None,
        sprint_id=None,
        story_points=3,
        difficulty="medium",
        deadline_iso=(datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    )

    comment_resp = client.post(
        f"/tasks/{task['id']}/comments",
        headers=_hdr(int(staff["id"])),
        json={"body": "I will add the UI drawer today."},
    )
    assert comment_resp.status_code == 200
    assert comment_resp.json()["author_name"] == "Task Detail Staff"

    detail_resp = client.get(f"/tasks/{task['id']}", headers=_hdr(int(manager["id"])))
    assert detail_resp.status_code == 200
    payload = detail_resp.json()
    assert payload["id"] == task["id"]
    assert payload["assignee_name"] == "Task Detail Staff"
    assert payload["project_name"] is None
    assert payload["sprint_name"] is None
    assert payload["due_state"] == "on_time"
    assert payload["comments"][0]["body"] == "I will add the UI drawer today."
    assert payload["activity_logs"][0]["action"] == "comment"


def test_staff_cannot_access_or_comment_on_unassigned_task_detail() -> None:
    init_db()
    owner = create_user("Assigned Staff", _unique_email("detail.owner"), "staff", "Engineering")
    outsider = create_user("Other Staff", _unique_email("detail.outsider"), "staff", "Engineering")
    task = create_task(
        title="Private assigned task",
        description=None,
        assignee_id=int(owner["id"]),
        project_id=None,
        sprint_id=None,
        story_points=1,
        difficulty="easy",
        deadline_iso=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )

    detail_resp = client.get(f"/tasks/{task['id']}", headers=_hdr(int(outsider["id"])))
    assert detail_resp.status_code == 403

    comment_resp = client.post(
        f"/tasks/{task['id']}/comments",
        headers=_hdr(int(outsider["id"])),
        json={"body": "Trying to comment on someone else's task."},
    )
    assert comment_resp.status_code == 403
