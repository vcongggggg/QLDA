from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import get_connection, init_db
from app.main import app
from app.repository import create_task, create_user, get_notification_by_id, get_task_by_id, update_task_status
from app.settings import settings

client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _email(prefix: str) -> str:
    return f"{prefix}.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}@example.com"


def _bootstrap() -> tuple[dict, dict]:
    init_db()
    manager = create_user("Teams Sim Manager", _email("teams.sim.manager"), "manager", "PMO", aad_object_id=_email("aad.manager"))
    staff = create_user("Teams Sim Staff", _email("teams.sim.staff"), "staff", "Engineering", aad_object_id=_email("aad.staff"))
    return manager, staff


def test_simulator_task_list_returns_valid_adaptive_card() -> None:
    manager, staff = _bootstrap()
    task = create_task(
        "Simulation task list card",
        None,
        int(staff["id"]),
        None,
        None,
        2,
        "easy",
        (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
    )

    resp = client.post(
        "/integrations/teams/simulator/command",
        headers=_hdr(int(manager["id"])),
        json={"command": "/task-list"},
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["card"]["type"] == "AdaptiveCard"
    assert payload["card"]["version"] == "1.5"
    assert f"#{task['id']}" in payload["text"]
    assert "Complete" in {action["title"] for action in payload["card"]["actions"]}
    assert "tw-adaptive-card" in payload["preview_html"]


def test_simulator_kpi_me_returns_current_user_kpi_fields() -> None:
    manager, _staff = _bootstrap()
    task = create_task(
        "Simulation KPI task",
        None,
        int(manager["id"]),
        None,
        None,
        1,
        "easy",
        (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )
    update_task_status(int(task["id"]), "done")

    resp = client.post(
        "/integrations/teams/simulator/command",
        headers=_hdr(int(manager["id"])),
        json={"command": "/kpi-me", "month": datetime.now(timezone.utc).strftime("%Y-%m")},
    )

    assert resp.status_code == 200
    kpi = resp.json()["kpi"]
    assert {"score", "done_on_time", "done_late", "overdue_unfinished"}.issubset(kpi)
    assert resp.json()["card"]["type"] == "AdaptiveCard"


def test_simulation_queue_process_and_health_do_not_call_real_teams() -> None:
    manager, staff = _bootstrap()
    task = create_task(
        "Simulation deadline reminder",
        None,
        int(staff["id"]),
        None,
        None,
        3,
        "medium",
        (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
    )

    queue_resp = client.post(
        "/integrations/teams/notifications/queue",
        headers=_hdr(int(manager["id"])),
        json={"type": "deadline_reminder", "task_id": task["id"]},
    )
    assert queue_resp.status_code == 200
    queued = queue_resp.json()["notifications"][0]
    assert queued["notification_type"] == "deadline_reminder"
    assert queued["retry_count"] == 0
    assert queued["max_attempts"] == 3

    process_resp = client.post("/integrations/teams/notifications/process", headers=_hdr(int(manager["id"])))
    assert process_resp.status_code == 200
    assert process_resp.json()["mode"] == "simulation"
    assert process_resp.json()["sent"] >= 1
    assert get_notification_by_id(int(queued["id"]))["status"] == "sent"

    health = client.get("/integrations/teams/health", headers=_hdr(int(manager["id"])))
    assert health.status_code == 200
    assert health.json()["mode"] == "simulation"
    assert health.json()["real_graph_enabled"] is False


def test_simulation_retry_failed_notification_resets_attempts() -> None:
    manager, staff = _bootstrap()
    task = create_task(
        "Simulation failed reminder",
        None,
        int(staff["id"]),
        None,
        None,
        1,
        "easy",
        (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
    )
    queue_resp = client.post(
        "/integrations/teams/notifications/queue",
        headers=_hdr(int(manager["id"])),
        json={"type": "deadline_reminder", "task_id": task["id"], "simulate_failure": True},
    )
    notification_id = int(queue_resp.json()["notifications"][0]["id"])
    for _ in range(3):
        client.post("/integrations/teams/notifications/process", headers=_hdr(int(manager["id"])))
        with get_connection() as conn:
            conn.execute(
                "UPDATE notification_queue SET next_retry_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), notification_id),
            )

    failed = get_notification_by_id(notification_id)
    assert failed["status"] == "failed"
    assert failed["attempts"] == 3

    retry = client.post(f"/integrations/teams/notifications/retry/{notification_id}", headers=_hdr(int(manager["id"])))
    assert retry.status_code == 200
    assert retry.json()["status"] == "queued"
    assert retry.json()["retry_count"] == 0


def test_complete_card_action_updates_task_to_done() -> None:
    _manager, staff = _bootstrap()
    task = create_task(
        "Simulation complete action",
        None,
        int(staff["id"]),
        None,
        None,
        1,
        "easy",
        (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )

    resp = client.post(
        "/integrations/teams/card/actions",
        json={
            "type": "invoke",
            "from": {"aadObjectId": staff["aad_object_id"]},
            "value": {"action": "complete", "task_id": task["id"]},
        },
    )

    assert resp.status_code == 200
    assert "moved to done" in resp.json()["text"]
    assert get_task_by_id(int(task["id"]))["status"] == "done"
