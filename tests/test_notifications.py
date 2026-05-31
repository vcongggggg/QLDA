from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import create_app_notification, create_task, create_user, list_app_notifications, list_notifications, queue_notification

client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _unique_email(prefix: str) -> str:
    return f"{prefix}.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}@example.com"


def _bootstrap() -> tuple[dict, dict, dict]:
    init_db()
    manager = create_user("Notification Manager", _unique_email("notif.manager"), "manager", "PMO")
    staff = create_user("Notification Staff", _unique_email("notif.staff"), "staff", "Engineering")
    other = create_user("Notification Other", _unique_email("notif.other"), "staff", "Engineering")
    return manager, staff, other


def test_user_lists_only_own_notifications_and_unread_count() -> None:
    _manager, staff, other = _bootstrap()
    own = create_app_notification(
        int(staff["id"]),
        "task_comment",
        "Own notification",
        "This belongs to staff",
        "task",
        101,
    )
    create_app_notification(
        int(other["id"]),
        "task_comment",
        "Other notification",
        "This belongs to other user",
        "task",
        202,
    )

    list_resp = client.get("/notifications", headers=_hdr(int(staff["id"])))
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert any(row["id"] == own["id"] for row in rows)
    assert all(row["user_id"] == staff["id"] for row in rows)

    count_resp = client.get("/notifications/unread-count", headers=_hdr(int(staff["id"])))
    assert count_resp.status_code == 200
    assert count_resp.json()["unread_count"] >= 1


def test_user_can_mark_own_notification_read_but_not_another_users() -> None:
    _manager, staff, other = _bootstrap()
    own = create_app_notification(int(staff["id"]), "task_comment", "Own", "Mine", "task", 1)
    other_item = create_app_notification(int(other["id"]), "task_comment", "Other", "Not mine", "task", 2)

    read_resp = client.patch(f"/notifications/{own['id']}/read", headers=_hdr(int(staff["id"])))
    assert read_resp.status_code == 200
    assert read_resp.json()["is_read"] is True

    denied_resp = client.patch(f"/notifications/{other_item['id']}/read", headers=_hdr(int(staff["id"])))
    assert denied_resp.status_code == 404


def test_comment_by_other_user_creates_notification_for_assignee() -> None:
    manager, staff, _other = _bootstrap()
    task = create_task(
        title="Comment notification task",
        description=None,
        assignee_id=int(staff["id"]),
        project_id=None,
        sprint_id=None,
        story_points=1,
        difficulty="easy",
        deadline_iso=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )

    resp = client.post(
        f"/tasks/{task['id']}/comments",
        headers=_hdr(int(manager["id"])),
        json={"body": "Please check this update."},
    )
    assert resp.status_code == 200

    notifications = list_app_notifications(int(staff["id"]), unread_only=True, limit=10)
    assert any(n["type"] == "task_comment" and n["entity_id"] == task["id"] for n in notifications)


def test_assignee_commenting_on_own_task_does_not_notify_self() -> None:
    _manager, staff, _other = _bootstrap()
    task = create_task(
        title="Self comment task",
        description=None,
        assignee_id=int(staff["id"]),
        project_id=None,
        sprint_id=None,
        story_points=1,
        difficulty="easy",
        deadline_iso=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )

    before = len(list_app_notifications(int(staff["id"]), unread_only=True, limit=100))
    resp = client.post(
        f"/tasks/{task['id']}/comments",
        headers=_hdr(int(staff["id"])),
        json={"body": "I am working on this."},
    )
    assert resp.status_code == 200
    after = len(list_app_notifications(int(staff["id"]), unread_only=True, limit=100))
    assert after == before


def test_status_update_notifies_only_when_status_changes() -> None:
    manager, staff, _other = _bootstrap()
    task = create_task(
        title="Status notification task",
        description=None,
        assignee_id=int(staff["id"]),
        project_id=None,
        sprint_id=None,
        story_points=2,
        difficulty="medium",
        deadline_iso=(datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    )

    changed = client.patch(f"/tasks/{task['id']}/status", headers=_hdr(int(manager["id"])), json={"status": "doing"})
    assert changed.status_code == 200
    after_change = [
        n
        for n in list_app_notifications(int(staff["id"]), unread_only=True, limit=50)
        if n["type"] == "task_status_changed" and n["entity_id"] == task["id"]
    ]
    assert len(after_change) == 1

    unchanged = client.patch(f"/tasks/{task['id']}/status", headers=_hdr(int(manager["id"])), json={"status": "doing"})
    assert unchanged.status_code == 200
    after_same = [
        n
        for n in list_app_notifications(int(staff["id"]), unread_only=True, limit=50)
        if n["type"] == "task_status_changed" and n["entity_id"] == task["id"]
    ]
    assert len(after_same) == 1


def test_reminder_runner_creates_due_soon_and_overdue_and_skips_duplicates() -> None:
    manager, staff, _other = _bootstrap()
    now = datetime.now(timezone.utc)
    create_task("Due soon task", None, int(staff["id"]), None, None, 1, "easy", (now + timedelta(hours=3)).isoformat())
    create_task("Overdue task", None, int(staff["id"]), None, None, 1, "easy", (now - timedelta(hours=3)).isoformat())
    create_task("Future task", None, int(staff["id"]), None, None, 1, "easy", (now + timedelta(days=3)).isoformat())

    first = client.post("/notifications/task-reminders/run", headers=_hdr(int(manager["id"])))
    assert first.status_code == 200
    assert first.json()["due_soon_created"] >= 1
    assert first.json()["overdue_created"] >= 1

    second = client.post("/notifications/task-reminders/run", headers=_hdr(int(manager["id"])))
    assert second.status_code == 200
    assert second.json()["due_soon_created"] == 0
    assert second.json()["overdue_created"] == 0
    assert second.json()["skipped_duplicates"] >= 2


def test_staff_cannot_run_reminder_scan_but_manager_can() -> None:
    manager, staff, _other = _bootstrap()
    staff_resp = client.post("/notifications/task-reminders/run", headers=_hdr(int(staff["id"])))
    assert staff_resp.status_code == 403

    manager_resp = client.post("/notifications/task-reminders/run", headers=_hdr(int(manager["id"])))
    assert manager_resp.status_code == 200


def test_teams_queue_deduplicates_payload_dedup_key_and_preserves_target_shape() -> None:
    _manager, staff, _other = _bootstrap()
    payload = {
        "type": "message",
        "text": "Dedup me",
        "dedup_key": "phase4-dedup-key",
        "target": {"type": "channel", "team_id": "team-a", "channel_id": "channel-a"},
    }
    first = queue_notification(int(staff["id"]), "teams", payload)
    second = queue_notification(int(staff["id"]), "teams", dict(payload))

    assert second["id"] == first["id"]
    rows = [row for row in list_notifications(status="all", limit=20) if row["payload"].get("dedup_key") == "phase4-dedup-key"]
    assert len(rows) == 1
    assert rows[0]["payload"]["target"]["type"] == "channel"


def test_teams_queue_endpoint_accepts_target_and_dedup_but_staff_cannot_manage_it() -> None:
    manager, staff, _other = _bootstrap()
    staff_resp = client.post(
        "/integrations/teams/proactive/queue?message=Nope&target_type=channel&dedup_key=staff-denied",
        headers=_hdr(int(staff["id"])),
    )
    assert staff_resp.status_code == 403

    first = client.post(
        "/integrations/teams/proactive/queue?message=Channel%20notice&target_type=channel&team_id=team-a&channel_id=channel-a&dedup_key=endpoint-dedup",
        headers=_hdr(int(manager["id"])),
    )
    second = client.post(
        "/integrations/teams/proactive/queue?message=Channel%20notice&target_type=channel&team_id=team-a&channel_id=channel-a&dedup_key=endpoint-dedup",
        headers=_hdr(int(manager["id"])),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert first.json()["payload"]["target"]["channel_id"] == "channel-a"
