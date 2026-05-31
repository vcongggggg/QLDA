from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import (
    count_notifications_by_status,
    create_task,
    create_user,
    get_task_by_id,
    list_teams_conversation_refs,
    queue_notification,
)
from app.settings import settings
from app.teams_bot import send_text_to_graph_channel
from scripts.package_teams_app import package_teams_app


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _email(prefix: str) -> str:
    return f"{prefix}.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}@example.com"


def _bootstrap() -> tuple[dict, dict, dict, dict]:
    init_db()
    admin = create_user("Teams Admin", _email("teams.admin"), "admin", "IT")
    manager = create_user("Teams Manager", _email("teams.manager"), "manager", "PMO")
    staff = create_user("Teams Staff", _email("teams.staff"), "staff", "Engineering")
    hr = create_user("Teams HR", _email("teams.hr"), "hr", "People")
    return admin, manager, staff, hr


def test_aad_sync_uses_bearer_identity_without_exposing_token_details() -> None:
    original_disable = settings.teams_disable_jwt_validation
    settings.teams_disable_jwt_validation = True
    try:
        me_resp = client.get("/integrations/teams/aad/me", headers={"Authorization": "Bearer local-dev-token"})
        assert me_resp.status_code == 200
        assert me_resp.json()["aad_object_id"] == "dev-user"

        sync_resp = client.post("/integrations/teams/aad/sync", headers={"Authorization": "Bearer local-dev-token"})
        assert sync_resp.status_code == 200
        payload = sync_resp.json()
        assert payload["aad_object_id"] == "dev-user"
        assert "token" not in sync_resp.text.lower()
    finally:
        settings.teams_disable_jwt_validation = original_disable


def test_teams_summary_filters_staff_data_and_hides_queue_stats() -> None:
    _admin, manager, staff, _hr = _bootstrap()
    staff_task = create_task(
        "Staff Teams task",
        None,
        int(staff["id"]),
        None,
        None,
        3,
        "medium",
        (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )
    manager_task = create_task(
        "Manager private task",
        None,
        int(manager["id"]),
        None,
        None,
        5,
        "hard",
        (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    )
    queue_notification(user_id=int(staff["id"]), channel="teams", payload={"type": "message", "text": "Ping"})

    staff_resp = client.get("/integrations/teams/summary?month=2026-05", headers=_hdr(int(staff["id"])))
    assert staff_resp.status_code == 200
    staff_payload = staff_resp.json()
    assert staff_payload["can_manage_queue"] is False
    assert staff_payload["queue_stats"] is None
    assert {row["id"] for row in staff_payload["tasks"]} == {staff_task["id"]}

    manager_resp = client.get("/integrations/teams/summary?month=2026-05", headers=_hdr(int(manager["id"])))
    assert manager_resp.status_code == 200
    manager_payload = manager_resp.json()
    assert manager_payload["can_manage_queue"] is True
    assert manager_payload["queue_stats"]["queued"] >= 1
    assert {manager_task["id"], staff_task["id"]}.issubset({row["id"] for row in manager_payload["tasks"]})


def test_staff_cannot_manage_teams_queue() -> None:
    _admin, _manager, staff, _hr = _bootstrap()
    queue_resp = client.post(
        "/integrations/teams/proactive/queue?message=Staff%20should%20not%20queue",
        headers=_hdr(int(staff["id"])),
    )
    assert queue_resp.status_code == 403

    list_resp = client.get("/integrations/teams/proactive/queue?status=all", headers=_hdr(int(staff["id"])))
    assert list_resp.status_code == 403


def test_bot_help_unknown_and_non_message_are_safe() -> None:
    help_resp = client.post("/integrations/teams/bot/messages", json={"type": "message", "text": "  /help  "})
    assert help_resp.status_code == 200
    help_text = help_resp.json()["text"]
    assert "/task-list" in help_text
    assert "/team-kpi" in help_text
    assert "/search <keyword>" in help_text

    unknown_resp = client.post("/integrations/teams/bot/messages", json={"type": "message", "text": "/token please"})
    assert unknown_resp.status_code == 200
    unknown_text = unknown_resp.json()["text"].lower()
    assert "unknown command" in unknown_text
    assert "token" not in unknown_text

    event_resp = client.post("/integrations/teams/bot/messages", json={"type": "conversationUpdate"})
    assert event_resp.status_code == 200
    assert event_resp.json()["text"] == "Event received"


def test_bot_requires_mapped_teamswork_user_for_data_commands() -> None:
    resp = client.post(
        "/integrations/teams/bot/messages",
        json={
            "type": "message",
            "text": "/task-list",
            "from": {"aadObjectId": "missing-aad-user"},
            "conversation": {"id": "conv-missing-user", "tenantId": "tenant-a"},
            "serviceUrl": "https://service.example.com",
            "channelId": "msteams",
        },
    )
    assert resp.status_code == 200
    assert "sign in" in resp.json()["text"].lower()

    refs = list_teams_conversation_refs(limit=5)
    assert any(ref["conversation_id"] == "conv-missing-user" and ref["user_id"] is None for ref in refs)


def test_bot_task_list_deadlines_search_are_scoped_to_staff_user() -> None:
    init_db()
    suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    staff = create_user(
        "Bot Staff",
        f"bot.staff.{suffix}@example.com",
        "staff",
        "Engineering",
        aad_object_id=f"aad-staff-{suffix}",
    )
    other = create_user("Bot Other", f"bot.other.{suffix}@example.com", "staff", "Engineering")
    own_task = create_task(
        "Scoped bot task alpha",
        None,
        int(staff["id"]),
        None,
        None,
        2,
        "easy",
        (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )
    create_task(
        "Other bot task alpha",
        None,
        int(other["id"]),
        None,
        None,
        3,
        "medium",
        (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )
    activity = {
        "type": "message",
        "from": {"aadObjectId": f"aad-staff-{suffix}"},
        "conversation": {"id": f"conv-staff-{suffix}", "tenantId": "tenant-a"},
        "serviceUrl": "https://service.example.com",
        "channelId": "msteams",
    }

    task_resp = client.post("/integrations/teams/bot/messages", json={**activity, "text": "/task-list"})
    assert task_resp.status_code == 200
    task_text = task_resp.json()["text"]
    assert f"#{own_task['id']}" in task_text
    assert "Other bot task alpha" not in task_text

    deadline_resp = client.post("/integrations/teams/bot/messages", json={**activity, "text": "/my-deadlines"})
    assert deadline_resp.status_code == 200
    assert f"#{own_task['id']}" in deadline_resp.json()["text"]

    search_resp = client.post("/integrations/teams/bot/messages", json={**activity, "text": "/search alpha"})
    assert search_resp.status_code == 200
    search_text = search_resp.json()["text"]
    assert "Scoped bot task alpha" in search_text
    assert "Other bot task alpha" not in search_text

    refs = list_teams_conversation_refs(user_id=int(staff["id"]), limit=5)
    assert any(ref["conversation_id"] == f"conv-staff-{suffix}" for ref in refs)


def test_bot_top_kpi_requires_privileged_mapped_user() -> None:
    init_db()
    suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    staff = create_user(
        "Bot KPI Staff",
        f"bot.kpi.staff.{suffix}@example.com",
        "staff",
        "Engineering",
        aad_object_id=f"aad-kpi-staff-{suffix}",
    )
    manager = create_user(
        "Bot KPI Manager",
        f"bot.kpi.manager.{suffix}@example.com",
        "manager",
        "PMO",
        aad_object_id=f"aad-kpi-manager-{suffix}",
    )

    staff_resp = client.post(
        "/integrations/teams/bot/messages",
        json={"type": "message", "text": "/top-kpi", "from": {"aadObjectId": staff["aad_object_id"]}},
    )
    assert staff_resp.status_code == 200
    assert "personal KPI" in staff_resp.json()["text"]

    manager_resp = client.post(
        "/integrations/teams/bot/messages",
        json={"type": "message", "text": "/top-kpi", "from": {"aadObjectId": manager["aad_object_id"]}},
    )
    assert manager_resp.status_code == 200
    assert "KPI" in manager_resp.json()["text"]


def test_bot_new_task_assign_status_and_report_commands_are_guarded() -> None:
    init_db()
    suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    manager = create_user(
        "Bot Command Manager",
        f"bot.command.manager.{suffix}@example.com",
        "manager",
        "PMO",
        aad_object_id=f"aad-command-manager-{suffix}",
    )
    staff = create_user(
        "Bot Command Staff",
        f"bot.command.staff.{suffix}@example.com",
        "staff",
        "Engineering",
        aad_object_id=f"aad-command-staff-{suffix}",
    )
    other = create_user("Bot Command Other", f"bot.command.other.{suffix}@example.com", "staff", "Engineering")
    manager_activity = {"type": "message", "from": {"aadObjectId": manager["aad_object_id"]}}
    staff_activity = {"type": "message", "from": {"aadObjectId": staff["aad_object_id"]}}

    create_resp = client.post(
        "/integrations/teams/bot/messages",
        json={
            **manager_activity,
            "text": f'/new-task title="Bot created command task" assignee={staff["id"]} due=2026-06-15 points=2 difficulty=easy',
        },
    )
    assert create_resp.status_code == 200
    assert "Created task #" in create_resp.json()["text"]
    task_id = int(create_resp.json()["text"].split("#", 1)[1].split(":", 1)[0])
    task = get_task_by_id(task_id)
    assert task is not None
    assert task["title"] == "Bot created command task"
    assert int(task["assignee_id"]) == int(staff["id"])

    assign_resp = client.post(
        "/integrations/teams/bot/messages",
        json={**manager_activity, "text": f"/assign {task_id} {other['id']}"},
    )
    assert assign_resp.status_code == 200
    assert "assigned to" in assign_resp.json()["text"]
    assert int(get_task_by_id(task_id)["assignee_id"]) == int(other["id"])

    denied_assign = client.post(
        "/integrations/teams/bot/messages",
        json={**staff_activity, "text": f"/assign {task_id} {staff['id']}"},
    )
    assert denied_assign.status_code == 200
    assert "do not have" in denied_assign.json()["text"]

    own_task = create_task(
        "Own bot status task",
        None,
        int(staff["id"]),
        None,
        None,
        1,
        "easy",
        (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    )
    status_resp = client.post(
        "/integrations/teams/bot/messages",
        json={**staff_activity, "text": f"/status {own_task['id']} doing"},
    )
    assert status_resp.status_code == 200
    assert "moved to doing" in status_resp.json()["text"]
    assert get_task_by_id(int(own_task["id"]))["status"] == "doing"

    malformed = client.post(
        "/integrations/teams/bot/messages",
        json={**manager_activity, "text": "/new-task assignee=missing"},
    )
    assert malformed.status_code == 200
    assert "Usage:" in malformed.json()["text"]

    report = client.post("/integrations/teams/bot/messages", json={**manager_activity, "text": "/report 2026-06"})
    assert report.status_code == 200
    assert "Report 2026-06" in report.json()["text"]


def test_adaptive_card_actions_validate_payload_and_scope_writes() -> None:
    init_db()
    suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    staff = create_user(
        "Card Staff",
        f"card.staff.{suffix}@example.com",
        "staff",
        "Engineering",
        aad_object_id=f"aad-card-staff-{suffix}",
    )
    other = create_user(
        "Card Other",
        f"card.other.{suffix}@example.com",
        "staff",
        "Engineering",
        aad_object_id=f"aad-card-other-{suffix}",
    )
    own_task = create_task("Card own task", None, int(staff["id"]), None, None, 1, "easy", (datetime.now(timezone.utc) + timedelta(days=1)).isoformat())
    other_task = create_task("Card other task", None, int(other["id"]), None, None, 1, "easy", (datetime.now(timezone.utc) + timedelta(days=1)).isoformat())
    base = {"type": "invoke", "from": {"aadObjectId": staff["aad_object_id"]}}

    missing = client.post("/integrations/teams/card/actions", json=base)
    assert missing.status_code == 400

    invalid_status = client.post(
        "/integrations/teams/card/actions",
        json={**base, "value": {"action": "task_status", "task_id": own_task["id"], "status": "blocked"}},
    )
    assert invalid_status.status_code == 400

    denied = client.post(
        "/integrations/teams/card/actions",
        json={**base, "value": {"action": "task_status", "task_id": other_task["id"], "status": "doing"}},
    )
    assert denied.status_code == 403

    ok = client.post(
        "/integrations/teams/card/actions",
        json={**base, "value": {"action": "task_status", "task_id": own_task["id"], "status": "done"}},
    )
    assert ok.status_code == 200
    assert "moved to done" in ok.json()["text"]
    assert get_task_by_id(int(own_task["id"]))["status"] == "done"

    view = client.post(
        "/integrations/teams/card/actions",
        json={**base, "value": {"action": "task_view", "task_id": own_task["id"]}},
    )
    assert view.status_code == 200
    assert view.json()["card"]["type"] == "AdaptiveCard"


def test_graph_channel_send_is_disabled_by_default_and_mockable(monkeypatch: pytest.MonkeyPatch) -> None:
    original_mode = settings.teams_proactive_mode
    original_team = settings.teams_graph_team_id
    original_channel = settings.teams_graph_channel_id
    original_client = settings.teams_client_id
    original_secret = settings.teams_client_secret
    original_tenant = settings.teams_tenant_id
    original_real_graph = settings.teams_real_graph_enabled
    try:
        settings.teams_proactive_mode = "webhook"
        assert send_text_to_graph_channel("hello")["sent"] is False

        calls = []

        class FakeResponse:
            def __init__(self, status_code: int, payload: dict | None = None) -> None:
                self.status_code = status_code
                self._payload = payload or {}

            def json(self) -> dict:
                return self._payload

        def fake_post(url: str, **kwargs):
            calls.append((url, kwargs))
            if "login.microsoftonline.com" in url:
                return FakeResponse(200, {"access_token": "fake-token"})
            return FakeResponse(201, {})

        settings.teams_proactive_mode = "graph"
        settings.teams_graph_team_id = "team-1"
        settings.teams_graph_channel_id = "channel-1"
        settings.teams_client_id = "client-1"
        settings.teams_client_secret = "secret-1"
        settings.teams_tenant_id = "tenant-1"
        settings.teams_real_graph_enabled = True
        monkeypatch.setattr("app.teams_bot.httpx.post", fake_post)

        result = send_text_to_graph_channel("hello graph")
        assert result["sent"] is True
        assert calls[-1][1]["json"]["body"]["content"] == "hello graph"
        assert "fake-token" not in str(result)
    finally:
        settings.teams_proactive_mode = original_mode
        settings.teams_graph_team_id = original_team
        settings.teams_graph_channel_id = original_channel
        settings.teams_client_id = original_client
        settings.teams_client_secret = original_secret
        settings.teams_tenant_id = original_tenant
        settings.teams_real_graph_enabled = original_real_graph


def test_teams_summary_queue_stats_count_beyond_list_page_limit() -> None:
    _admin, manager, staff, _hr = _bootstrap()
    before = count_notifications_by_status()["queued"]
    for index in range(205):
        queue_notification(
            user_id=int(staff["id"]),
            channel="teams",
            payload={"type": "message", "text": f"Bulk queue {index}"},
        )

    resp = client.get("/integrations/teams/summary?month=2026-05", headers=_hdr(int(manager["id"])))
    assert resp.status_code == 200
    assert resp.json()["queue_stats"]["queued"] >= before + 205


def test_production_tab_uses_teams_summary_endpoint() -> None:
    resp = client.get("/teams/tab/prod")
    assert resp.status_code == 200
    assert "/integrations/teams/summary" in resp.text
    assert "Authorization:'Bearer '+" in resp.text
    assert "/tasks/${taskId}" in resp.text
    assert "/tasks/${taskId}/status" in resp.text
    assert "/integrations/teams/proactive/queue?status=" in resp.text
    assert "/integrations/teams/proactive/process" in resp.text
    assert "/integrations/teams/proactive/requeue/${id}" in resp.text
    assert "can_manage_queue" in resp.text
    assert "data-state=\"loading\"" in resp.text
    assert "data-state=\"empty\"" in resp.text
    assert "data-state=\"error\"" in resp.text
    assert "taskDrawer" in resp.text
    assert "queuePanel" in resp.text


def test_package_teams_app_renders_manifest_from_explicit_values(tmp_path: Path) -> None:
    out_zip = tmp_path / "teams-app.zip"

    package_teams_app(
        Path("teams-app"),
        out_zip,
        host="teamswork.example.com",
        client_id="11111111-1111-1111-1111-111111111111",
        env_path=tmp_path / "missing.env",
    )

    assert out_zip.exists()
    import zipfile

    with zipfile.ZipFile(out_zip) as zf:
        manifest = zf.read("manifest.json").decode("utf-8")

    assert "REPLACE_WITH_PUBLIC_HOST" not in manifest
    assert "REPLACE_WITH_AAD_APP_CLIENT_ID" not in manifest
    assert "https://teamswork.example.com/teams/tab/prod" in manifest


def test_package_teams_app_rejects_missing_manifest_values(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Missing values for manifest placeholders"):
        package_teams_app(
            Path("teams-app"),
            tmp_path / "teams-app.zip",
            env_path=tmp_path / "missing.env",
        )
