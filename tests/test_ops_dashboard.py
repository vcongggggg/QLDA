from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.database import get_connection, init_db
from app.main import app
from app.repository import (
    create_audit_log,
    create_project,
    create_sprint,
    create_task,
    create_user,
    list_processable_notifications,
    mark_notification_result,
    queue_notification,
    replace_role_permissions,
)
from app.settings import settings


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _email(prefix: str) -> str:
    return f"{prefix}.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}@example.com"


def _bootstrap() -> tuple[dict, dict, dict, dict]:
    init_db()
    admin = create_user("Ops Admin", _email("ops.admin"), "admin", "IT")
    manager = create_user("Ops Manager", _email("ops.manager"), "manager", "PMO")
    hr = create_user("Ops HR", _email("ops.hr"), "hr", "People")
    staff = create_user("Ops Staff", _email("ops.staff"), "staff", "Engineering")
    return admin, manager, hr, staff


def _make_failed_notification(user_id: int) -> dict:
    item = queue_notification(
        user_id=user_id,
        channel="teams",
        payload={
            "type": "message",
            "text": "hello",
            "webhook_url": "https://example.invalid/secret-webhook",
            "Authorization": "Bearer should-not-leak",
        },
        max_attempts=1,
    )
    failed = mark_notification_result(
        int(item["id"]),
        success=False,
        error_message=(
            "Bearer token leaked at https://example.invalid/webhook "
            "Traceback (most recent call last): client_secret=super-secret"
        ),
    )
    assert failed is not None
    return failed


def test_privileged_roles_can_view_ops_dashboard_and_staff_is_blocked() -> None:
    admin, manager, hr, staff = _bootstrap()

    for user in (admin, hr):
        resp = client.get("/monitoring/ops", headers=_hdr(int(user["id"])))
        assert resp.status_code == 200
        payload = resp.json()
        assert "audit_logs" in payload
        assert "notification_queue" in payload
        assert "overdue_spike" in payload
        assert payload["can_manage_queue"] is True

    manager_resp = client.get("/monitoring/ops", headers=_hdr(int(manager["id"])))
    assert manager_resp.status_code == 403

    staff_resp = client.get("/monitoring/ops", headers=_hdr(int(staff["id"])))
    assert staff_resp.status_code == 403

    staff_queue = client.post("/integrations/teams/proactive/process", headers=_hdr(int(staff["id"])))
    assert staff_queue.status_code == 403


def test_ops_dashboard_view_is_controlled_by_permission_not_role_allowlist() -> None:
    admin, _manager, _hr, staff = _bootstrap()
    original_permissions = client.get(
        "/rbac/roles/staff/permissions",
        headers=_hdr(int(admin["id"])),
    ).json()["permissions"]
    original_keys = [item["key"] for item in original_permissions]
    try:
        replace_role_permissions("staff", [*original_keys, "OPS_VIEW"])

        resp = client.get("/monitoring/ops", headers=_hdr(int(staff["id"])))

        assert resp.status_code == 200
        assert resp.json()["can_manage_queue"] is False
    finally:
        replace_role_permissions("staff", original_keys)


def test_ops_dashboard_queue_management_flag_is_permission_based() -> None:
    admin, _manager, _hr, staff = _bootstrap()
    original_permissions = client.get(
        "/rbac/roles/staff/permissions",
        headers=_hdr(int(admin["id"])),
    ).json()["permissions"]
    original_keys = [item["key"] for item in original_permissions]
    try:
        replace_role_permissions("staff", [*original_keys, "OPS_VIEW", "teams.manage"])

        resp = client.get("/monitoring/ops", headers=_hdr(int(staff["id"])))

        assert resp.status_code == 200
        assert resp.json()["can_manage_queue"] is True
    finally:
        replace_role_permissions("staff", original_keys)


def test_processable_notifications_prioritize_new_then_oldest_due_retry() -> None:
    _admin, _manager, _hr, staff = _bootstrap()
    with get_connection() as conn:
        conn.execute("UPDATE notification_queue SET status = 'sent' WHERE status = 'queued'")

    first_new = queue_notification(int(staff["id"]), "teams", {"type": "message", "text": "first-new"})
    due_later = queue_notification(int(staff["id"]), "teams", {"type": "message", "text": "due-later"})
    due_earlier = queue_notification(int(staff["id"]), "teams", {"type": "message", "text": "due-earlier"})
    second_new = queue_notification(int(staff["id"]), "teams", {"type": "message", "text": "second-new"})
    future_retry = queue_notification(int(staff["id"]), "teams", {"type": "message", "text": "future"})

    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        conn.execute(
            "UPDATE notification_queue SET attempts = 4, next_retry_at = ? WHERE id = ?",
            ((now - timedelta(minutes=5)).isoformat(), due_later["id"]),
        )
        conn.execute(
            "UPDATE notification_queue SET attempts = 1, next_retry_at = ? WHERE id = ?",
            ((now - timedelta(minutes=10)).isoformat(), due_earlier["id"]),
        )
        conn.execute(
            "UPDATE notification_queue SET attempts = 9, next_retry_at = ? WHERE id = ?",
            ((now + timedelta(hours=1)).isoformat(), future_retry["id"]),
        )

    rows = list_processable_notifications(limit=10)
    ids = [int(row["id"]) for row in rows if row["payload"]["text"] in {"first-new", "second-new", "due-later", "due-earlier", "future"}]

    assert ids == [int(first_new["id"]), int(second_new["id"]), int(due_earlier["id"]), int(due_later["id"])]


def test_audit_filters_work_on_ops_and_audit_endpoint() -> None:
    admin, manager, hr, _staff = _bootstrap()
    now = datetime.now(timezone.utc)
    create_audit_log(int(manager["id"]), "ops_filter_match", "task", 101, "needle detail for ops dashboard")
    create_audit_log(int(admin["id"]), "ops_filter_other", "project", 202, "other detail")

    params = {
        "actor_id": int(manager["id"]),
        "action": "ops_filter_match",
        "entity_type": "task",
        "keyword": "needle",
        "date_from": (now - timedelta(minutes=2)).isoformat(),
        "date_to": (now + timedelta(minutes=2)).isoformat(),
    }
    ops_resp = client.get("/monitoring/ops", params=params, headers=_hdr(int(hr["id"])))
    assert ops_resp.status_code == 200
    ops_logs = ops_resp.json()["audit_logs"]
    assert ops_logs
    assert {row["action"] for row in ops_logs} == {"ops_filter_match"}
    assert all(row["entity"] == "task" for row in ops_logs)

    audit_resp = client.get("/audit/logs", params=params, headers=_hdr(int(admin["id"])))
    assert audit_resp.status_code == 200
    audit_logs = audit_resp.json()
    assert audit_logs
    assert {row["action"] for row in audit_logs} == {"ops_filter_match"}


def test_ops_dashboard_queue_counts_overdue_spike_and_redaction() -> None:
    _admin, manager, hr, staff = _bootstrap()
    project = create_project("Ops Spike Project", None, None, int(manager["id"]), None, None, "active")
    sprint = create_sprint(
        int(project["id"]),
        "Ops Spike Sprint",
        None,
        (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
        (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    )
    for idx in range(2):
        create_task(
            f"Overdue ops task {idx}",
            None,
            int(staff["id"]),
            int(project["id"]),
            int(sprint["id"]),
            1,
            "easy",
            (datetime.now(timezone.utc) - timedelta(days=idx + 1)).isoformat(),
        )

    failed = _make_failed_notification(int(staff["id"]))
    queue_notification(int(staff["id"]), "teams", {"type": "message", "text": "queued"}, max_attempts=2)

    resp = client.get(
        "/monitoring/ops",
        params={"overdue_threshold": 1, "failed_limit": 10},
        headers=_hdr(int(hr["id"])),
    )
    assert resp.status_code == 200
    payload = resp.json()

    queue = payload["notification_queue"]
    assert queue["failed_count"] >= 1
    assert queue["queued_count"] >= 1
    assert any(int(item["id"]) == int(failed["id"]) for item in queue["latest_failed_items"])

    spike = payload["overdue_spike"]
    assert spike["overdue_count"] >= 2
    assert spike["threshold"] == 1
    assert spike["alert"] is True
    assert any(item["project_id"] == project["id"] for item in spike["top_projects"])
    assert any(item["sprint_id"] == sprint["id"] for item in spike["top_sprints"])

    text = resp.text.lower()
    forbidden_fragments = [
        "secret-webhook",
        "bearer should-not-leak",
        "client_secret",
        "super-secret",
        "traceback",
        "webhook_url",
    ]
    assert all(fragment not in text for fragment in forbidden_fragments)
    latest_failed = queue["latest_failed_items"][0]
    assert "payload" not in latest_failed
    assert "last_error" not in latest_failed
    assert "last_error_summary" in latest_failed


def test_latest_failed_items_do_not_expose_direct_db_secrets() -> None:
    _admin, _manager, hr, staff = _bootstrap()
    failed = _make_failed_notification(int(staff["id"]))
    with get_connection() as conn:
        raw = conn.execute("SELECT payload, last_error FROM notification_queue WHERE id = ?", (failed["id"],)).fetchone()
    assert "secret-webhook" in raw["payload"]
    assert "Traceback" in raw["last_error"]

    resp = client.get("/monitoring/ops", headers=_hdr(int(hr["id"])))
    assert resp.status_code == 200
    assert "secret-webhook" not in resp.text
    assert "Traceback" not in resp.text


def test_release_gate_is_privileged_and_summarizes_ops_readiness() -> None:
    admin, _manager, hr, staff = _bootstrap()
    create_audit_log(int(admin["id"]), "release_gate_probe", "system", None, "release gate evidence")
    queue_notification(int(staff["id"]), "teams", {"type": "message", "text": "queued"}, max_attempts=2)
    failed = _make_failed_notification(int(staff["id"]))

    for user in (admin, hr):
        resp = client.get("/monitoring/release-gate", headers=_hdr(int(user["id"])))
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] in {"ok", "warn"}
        assert payload["health"]["status"] == "ok"
        assert payload["readiness"]["status"] == "ready"
        assert payload["metrics"]["queued_notifications"] >= 1
        assert payload["notification_queue"]["queued_count"] >= 1
        assert payload["notification_queue"]["failed_count"] >= 1
        assert any(int(item["id"]) == int(failed["id"]) for item in payload["notification_queue"]["latest_failed_items"])
        assert payload["audit"]["available"] is True
        assert {check["key"] for check in payload["checks"]} >= {
            "health",
            "readiness",
            "metrics",
            "notification_queue",
            "audit_logs",
            "production_auth",
        }

    blocked = client.get("/monitoring/release-gate", headers=_hdr(int(staff["id"])))
    assert blocked.status_code == 403


def test_release_gate_redacts_queue_errors_and_reports_auth_safety(monkeypatch) -> None:
    _admin, _manager, hr, staff = _bootstrap()
    _make_failed_notification(int(staff["id"]))
    monkeypatch.setattr(settings, "app_env", "production", raising=False)
    monkeypatch.setattr(settings, "auth_jwt_secret", "dev-secret-change-me", raising=False)
    monkeypatch.setattr(settings, "auth_disable_jwt_validation", True, raising=False)
    monkeypatch.setattr(settings, "auth_allow_header_fallback", True, raising=False)

    resp = client.get("/monitoring/release-gate", headers=_hdr(int(hr["id"])))

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "fail"
    assert payload["production_auth"]["status"] == "fail"
    assert "production" in payload["production_auth"]["summary"].lower()
    text = resp.text.lower()
    forbidden_fragments = [
        "secret-webhook",
        "bearer should-not-leak",
        "client_secret",
        "super-secret",
        "traceback",
        "webhook_url",
    ]
    assert all(fragment not in text for fragment in forbidden_fragments)


def test_static_ui_exposes_audit_ops_section() -> None:
    index = Path("app/static/index.html").read_text(encoding="utf-8")
    app_js = Path("app/static/app.js").read_text(encoding="utf-8")

    assert 'data-section="ops"' in index
    assert 'id="sec-ops"' in index
    assert "Audit & Ops" in index
    assert "/monitoring/ops" in app_js
    assert "can_manage_queue" in app_js
    assert "requeueOpsItem" in app_js


def test_static_ai_docx_preview_sends_rag_options() -> None:
    app_js = Path("app/static/app.js").read_text(encoding="utf-8")

    assert "function getRagOptions()" in app_js
    assert "form.append('use_rag', String(useRag));" in app_js
    assert "form.append('rag_query', ragQuery);" in app_js
