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


def test_local_card_preview_catalog_is_permission_scoped() -> None:
    manager, staff = _bootstrap()
    other = create_user("Teams Sim Card Other", _email("teams.sim.card.other"), "staff", "Engineering")
    own_task = create_task(
        "Local card own task",
        None,
        int(staff["id"]),
        None,
        None,
        1,
        "easy",
        (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )
    other_task = create_task(
        "Local card hidden task",
        None,
        int(other["id"]),
        None,
        None,
        1,
        "easy",
        (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )

    deadline = client.get(
        f"/integrations/teams/cards/preview?kind=deadline&task_id={own_task['id']}",
        headers=_hdr(int(staff["id"])),
    )
    assert deadline.status_code == 200
    assert deadline.json()["card"]["type"] == "AdaptiveCard"
    assert "Simulation only" in str(deadline.json()["card"])

    hidden = client.get(
        f"/integrations/teams/cards/preview?kind=task-action&task_id={other_task['id']}",
        headers=_hdr(int(staff["id"])),
    )
    assert hidden.status_code == 404

    action = client.get(
        f"/integrations/teams/cards/preview?kind=task-action&task_id={own_task['id']}",
        headers=_hdr(int(staff["id"])),
    )
    assert action.status_code == 200
    assert "Done" in {item["title"] for item in action.json()["card"]["actions"]}

    kpi_summary = client.get(
        "/integrations/teams/cards/preview?kind=kpi-summary&month=2026-05",
        headers=_hdr(int(manager["id"])),
    )
    assert kpi_summary.status_code == 200
    assert kpi_summary.json()["card"]["type"] == "AdaptiveCard"

    denied_summary = client.get(
        "/integrations/teams/cards/preview?kind=kpi-summary&month=2026-05",
        headers=_hdr(int(staff["id"])),
    )
    assert denied_summary.status_code == 403


def test_local_simulator_supports_bot_command_catalog_without_teams_tenant() -> None:
    manager, staff = _bootstrap()
    own_task = create_task(
        "Local simulator alpha task",
        None,
        int(staff["id"]),
        None,
        None,
        2,
        "easy",
        (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )
    create_task(
        "Manager-only alpha task",
        None,
        int(manager["id"]),
        None,
        None,
        3,
        "medium",
        (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )

    health = client.get("/integrations/teams/health", headers=_hdr(int(manager["id"])))
    assert health.status_code == 200
    assert "/new-task" in health.json()["supported_commands"]
    assert health.json()["real_outbound_enabled"] is False

    search = client.post(
        "/integrations/teams/simulator/command",
        headers=_hdr(int(staff["id"])),
        json={"command": "/search alpha"},
    )
    assert search.status_code == 200
    assert "Local simulator alpha task" in search.json()["text"]
    assert "Manager-only alpha task" not in search.json()["text"]
    assert search.json()["card"]["type"] == "AdaptiveCard"

    deadlines = client.post(
        "/integrations/teams/simulator/command",
        headers=_hdr(int(staff["id"])),
        json={"command": "/my-deadlines"},
    )
    assert deadlines.status_code == 200
    assert f"#{own_task['id']}" in deadlines.json()["text"]

    team_kpi = client.post(
        "/integrations/teams/simulator/command",
        headers=_hdr(int(manager["id"])),
        json={"command": "/team-kpi"},
    )
    assert team_kpi.status_code == 200
    assert team_kpi.json()["card"]["type"] == "AdaptiveCard"

    report = client.post(
        "/integrations/teams/simulator/command",
        headers=_hdr(int(manager["id"])),
        json={"command": "/report 2026-05"},
    )
    assert report.status_code == 200
    assert "Report 2026-05" in report.json()["text"]


def test_local_simulator_mutating_commands_use_existing_permissions() -> None:
    manager, staff = _bootstrap()
    other = create_user("Teams Sim Other", _email("teams.sim.other"), "staff", "Engineering")

    create_resp = client.post(
        "/integrations/teams/simulator/command",
        headers=_hdr(int(manager["id"])),
        json={
            "command": f'/new-task title="Local simulator created task" assignee={staff["id"]} due=2026-06-15 points=2 difficulty=easy'
        },
    )
    assert create_resp.status_code == 200
    assert "Created task #" in create_resp.json()["text"]
    task_id = int(create_resp.json()["text"].split("#", 1)[1].split(":", 1)[0])
    assert int(get_task_by_id(task_id)["assignee_id"]) == int(staff["id"])

    status_resp = client.post(
        "/integrations/teams/simulator/command",
        headers=_hdr(int(staff["id"])),
        json={"command": f"/status {task_id} doing"},
    )
    assert status_resp.status_code == 200
    assert "moved to doing" in status_resp.json()["text"]
    assert get_task_by_id(task_id)["status"] == "doing"

    denied_assign = client.post(
        "/integrations/teams/simulator/command",
        headers=_hdr(int(staff["id"])),
        json={"command": f"/assign {task_id} {other['id']}"},
    )
    assert denied_assign.status_code == 200
    assert "do not have permission" in denied_assign.json()["text"]

    assign_resp = client.post(
        "/integrations/teams/simulator/command",
        headers=_hdr(int(manager["id"])),
        json={"command": f"/assign {task_id} {other['id']}"},
    )
    assert assign_resp.status_code == 200
    assert "assigned to" in assign_resp.json()["text"]
    assert int(get_task_by_id(task_id)["assignee_id"]) == int(other["id"])
