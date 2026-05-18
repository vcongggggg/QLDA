from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import count_notifications_by_status, create_task, create_user, queue_notification
from app.settings import settings
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
