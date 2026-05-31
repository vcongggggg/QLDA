from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import get_connection, init_db
from app.main import app
from app.repository import create_audit_log, create_project, create_task, create_user


client = TestClient(app)


def _hdr(user_id: int) -> dict[str, str]:
    return {"X-User-Id": str(user_id)}


def _email(prefix: str) -> str:
    return f"{prefix}.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}@example.com"


def _bootstrap() -> tuple[dict, dict, dict, dict]:
    init_db()
    admin = create_user("Phase6 Admin", _email("phase6.admin"), "admin", "IT")
    manager = create_user("Phase6 Manager", _email("phase6.manager"), "manager", "PMO")
    hr = create_user("Phase6 HR", _email("phase6.hr"), "hr", "People")
    staff = create_user("Phase6 Staff", _email("phase6.staff"), "staff", "Engineering")
    return admin, manager, hr, staff


def test_admin_search_activity_config_and_system_notification_are_privileged(monkeypatch) -> None:
    admin, manager, hr, staff = _bootstrap()
    project = create_project("Phase 6 Search Project", None, None, int(manager["id"]), None, None, "active")
    create_task(
        "Phase 6 Search Task",
        None,
        int(staff["id"]),
        int(project["id"]),
        None,
        2,
        "medium",
        (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    )
    create_audit_log(int(admin["id"]), "phase6_search", "system", None, "safe activity detail")
    monkeypatch.setenv("PHASE6_TEST_API_KEY", "secret-value")

    search = client.get("/admin/search", params={"q": "Phase"}, headers=_hdr(int(admin["id"])))
    assert search.status_code == 200
    types = {item["type"] for item in search.json()["results"]}
    assert {"user", "project", "task", "audit"}.issubset(types)

    activity = client.get("/admin/activity", headers=_hdr(int(admin["id"])))
    assert activity.status_code == 200
    assert any(item["action"] == "phase6_search" for item in activity.json())

    flags = client.get("/admin/config-flags", headers=_hdr(int(hr["id"])))
    assert flags.status_code == 200
    assert any(item["key"] == "PHASE6_TEST_API_KEY" and item["value"] == "[redacted]" for item in flags.json())
    assert "secret-value" not in flags.text

    broadcast = client.post(
        "/admin/system-notifications",
        headers=_hdr(int(manager["id"])),
        json={"title": "Phase 6 notice", "message": "Release gate rehearsal", "audience": "hr"},
    )
    assert broadcast.status_code == 200
    assert broadcast.json()["created"] >= 1

    assert client.get("/admin/search", params={"q": "Phase"}, headers=_hdr(int(staff["id"]))).status_code == 403
    assert client.get("/admin/config-flags", headers=_hdr(int(staff["id"]))).status_code == 403
    assert client.post(
        "/admin/system-notifications",
        headers=_hdr(int(staff["id"])),
        json={"title": "Nope", "message": "Nope", "audience": "all"},
    ).status_code == 403


def test_phase6_admin_config_license_department_and_notification_evidence_are_privileged(monkeypatch) -> None:
    admin, _manager, hr, staff = _bootstrap()
    monkeypatch.setenv("PHASE6_RELEASE_API_TOKEN", "super-secret-token")

    config = client.get("/admin/system-config/overview", headers=_hdr(int(hr["id"])))
    assert config.status_code == 200
    config_payload = config.json()
    assert config_payload["status"] == "ok"
    assert config_payload["redacted_sensitive_count"] >= 1
    assert "super-secret-token" not in config.text
    assert config_payload["auth"]["app_env"]
    assert config_payload["teams"]["graph_outbound_default"] == "disabled_unless_configured"

    license_status = client.get("/admin/license/status", headers=_hdr(int(admin["id"])))
    assert license_status.status_code == 200
    license_payload = license_status.json()
    assert license_payload["mode"] == "local_demo_unlicensed"
    assert license_payload["active_users"] >= 1
    assert license_payload["external_license_integration"] == "not_configured_for_local_demo"

    departments = client.get("/admin/departments/ops-evidence", headers=_hdr(int(hr["id"])))
    assert departments.status_code == 200
    assert departments.json()["total_departments"] >= 0
    assert "user_distribution" in departments.json()

    notice = client.post(
        "/admin/system-notifications",
        headers=_hdr(int(admin["id"])),
        json={"title": "Phase 6 broadcast", "message": "System notification evidence", "audience": "all"},
    )
    assert notice.status_code == 200
    evidence = client.get("/admin/system-notifications/evidence", headers=_hdr(int(admin["id"])))
    assert evidence.status_code == 200
    assert evidence.json()["total"] >= notice.json()["created"]

    panel = client.get("/admin/release-panel", headers=_hdr(int(admin["id"])))
    assert panel.status_code == 200
    assert panel.json()["qa"] == "/qa/release-evidence"
    assert panel.json()["license"] == "/admin/license/status"

    assert client.get("/admin/system-config/overview", headers=_hdr(int(staff["id"]))).status_code == 403
    assert client.get("/admin/license/status", headers=_hdr(int(staff["id"]))).status_code == 403
    assert client.get("/admin/departments/ops-evidence", headers=_hdr(int(staff["id"]))).status_code == 403
    assert client.get("/admin/system-notifications/evidence", headers=_hdr(int(staff["id"]))).status_code == 403


def test_compliance_request_export_lineage_and_staff_blocking() -> None:
    admin, _manager, hr, staff = _bootstrap()
    create_task(
        "Compliance export task",
        "Contains no secrets",
        int(staff["id"]),
        None,
        None,
        1,
        "easy",
        (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
    )

    created = client.post(
        "/compliance/requests",
        headers=_hdr(int(hr["id"])),
        json={"subject_user_id": int(staff["id"]), "request_type": "export", "reason": "PDPA export request"},
    )
    assert created.status_code == 200
    request_id = created.json()["id"]
    assert created.json()["status"] == "open"

    listed = client.get("/compliance/requests", headers=_hdr(int(admin["id"])))
    assert listed.status_code == 200
    assert any(item["id"] == request_id for item in listed.json())

    updated = client.patch(
        f"/compliance/requests/{request_id}",
        headers=_hdr(int(hr["id"])),
        json={"status": "in_review", "resolution_note": "Export prepared; no hard delete."},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_review"

    export = client.get(f"/compliance/users/{staff['id']}/export", headers=_hdr(int(hr["id"])))
    assert export.status_code == 200
    payload = export.json()
    assert payload["user"]["email"] == staff["email"]
    assert payload["delete_policy"] == "request_export_manual_review_no_hard_delete"
    assert payload["tasks"]
    assert "password_hash" not in export.text

    lineage = client.get("/compliance/data-lineage", headers=_hdr(int(hr["id"])))
    assert lineage.status_code == 200
    assert "Request + export" in lineage.json()["policy"]

    evidence = client.get("/compliance/evidence", headers=_hdr(int(admin["id"])))
    assert evidence.status_code == 200
    assert evidence.json()["delete_policy"] == "manual_review_no_hard_delete"
    assert evidence.json()["data_lineage_domains"] >= 1

    assert client.get("/compliance/requests", headers=_hdr(int(staff["id"]))).status_code == 403
    assert client.get(f"/compliance/users/{staff['id']}/export", headers=_hdr(int(staff["id"]))).status_code == 403
    assert client.get("/compliance/evidence", headers=_hdr(int(staff["id"]))).status_code == 403


def test_maintenance_windows_retention_cleanup_and_release_gate_extensions() -> None:
    admin, _manager, hr, staff = _bootstrap()
    starts_at = datetime.now(timezone.utc) + timedelta(hours=1)
    ends_at = starts_at + timedelta(hours=2)
    created = client.post(
        "/maintenance/windows",
        headers=_hdr(int(admin["id"])),
        json={
            "title": "Phase 6 maintenance",
            "message": "Release rehearsal window",
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "status": "scheduled",
        },
    )
    assert created.status_code == 200
    window_id = created.json()["id"]

    listed = client.get("/maintenance/windows", headers=_hdr(int(hr["id"])))
    assert listed.status_code == 200
    assert any(item["id"] == window_id for item in listed.json())

    updated = client.patch(
        f"/maintenance/windows/{window_id}",
        headers=_hdr(int(admin["id"])),
        json={"status": "active"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "active"

    retention = client.get("/maintenance/retention", headers=_hdr(int(hr["id"])))
    assert retention.status_code == 200
    assert "audit_logs" in retention.json()["retention_days"]

    old_created_at = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO audit_logs (actor_user_id, action, entity, entity_id, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (int(admin["id"]), "old_log", "system", None, "old", old_created_at),
        )
    dry_run = client.post(
        "/maintenance/log-cleanup/dry-run",
        params={"retention_days": 365},
        headers=_hdr(int(admin["id"])),
    )
    assert dry_run.status_code == 200
    assert dry_run.json()["mode"] == "dry_run"
    assert dry_run.json()["counts"]["audit_logs"] >= 1

    release_gate = client.get("/monitoring/release-gate", headers=_hdr(int(hr["id"])))
    assert release_gate.status_code == 200
    payload = release_gate.json()
    assert payload["maintenance"]["active_or_upcoming_count"] >= 1
    assert "compliance_backlog" in payload
    assert "retention" in payload
    assert payload["synthetic_journey"]["script"] == "scripts/benchmark_smoke.py"
    assert payload["qa_evidence"]["uat_template"] == "docs/PHASE6_UAT_EVIDENCE_TEMPLATE.md"

    assert client.get("/maintenance/windows", headers=_hdr(int(staff["id"]))).status_code == 403
    assert client.post(
        "/maintenance/log-cleanup/dry-run",
        params={"retention_days": 365},
        headers=_hdr(int(staff["id"])),
    ).status_code == 403


def test_phase6_qa_release_evidence_and_test_data_inventory_are_privileged() -> None:
    admin, _manager, hr, staff = _bootstrap()
    create_audit_log(int(admin["id"]), "qa_evidence_probe", "system", None, "qa release evidence")

    for user in (admin, hr):
        evidence = client.get("/qa/release-evidence", headers=_hdr(int(user["id"])))
        assert evidence.status_code == 200
        payload = evidence.json()
        assert payload["status"] == "ready_for_local_release_review"
        assert payload["performance"]["script"] == "scripts/benchmark_smoke.py"
        assert "security headers" in payload["security"]["checks"]
        assert payload["monitoring"]["release_gate"] == "/monitoring/release-gate"
        assert payload["test_data"]["counts"]["users"] >= 1
        assert payload["uat"]["template"] == "docs/PHASE6_UAT_EVIDENCE_TEMPLATE.md"

        test_data = client.get("/qa/test-data", headers=_hdr(int(user["id"])))
        assert test_data.status_code == 200
        assert test_data.json()["reset_policy"].startswith("tests call init_db")

    assert client.get("/qa/release-evidence", headers=_hdr(int(staff["id"]))).status_code == 403
    assert client.get("/qa/test-data", headers=_hdr(int(staff["id"]))).status_code == 403


def test_release_acceptance_matrix_promotes_phase_partial_scope_with_deferrals() -> None:
    admin, _manager, hr, staff = _bootstrap()

    response = client.get("/monitoring/release-acceptance", headers=_hdr(int(hr["id"])))
    assert response.status_code == 200
    payload = response.json()

    assert payload["total_stories"] >= 139
    assert payload["done_stories"] == payload["total_stories"]
    assert payload["partial_stories"] == 0
    assert payload["deferral_count"] > 0
    assert "approved deferral" in payload["policy"]

    stories = {item["story_id"]: item for item in payload["stories"]}
    assert stories["US001"]["status"] == "Done"
    assert stories["US001"]["approved_deferrals"]
    assert stories["US221"]["evidence_type"] == "local_testable_with_approved_deferral"
    assert stories["US412"]["approved_deferrals"]
    assert stories["US493"]["approved_deferrals"]
    assert stories["US431"]["status"] == "Done"
    assert stories["US424"]["feature"] == "License"
    assert stories["US510"]["feature"] == "Security Testing"

    assert "secret" not in response.text.lower()
    assert client.get("/monitoring/release-acceptance", headers=_hdr(int(staff["id"]))).status_code == 403
    assert client.get("/monitoring/release-acceptance", headers=_hdr(int(admin["id"]))).status_code == 200
