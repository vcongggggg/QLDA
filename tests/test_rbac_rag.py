from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import create_user
from app.settings import settings


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _bootstrap() -> tuple[int, int, int]:
    init_db()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    admin = create_user("RBAC Admin", f"rbac.admin.{stamp}@example.com", "admin", "PMO")
    manager = create_user("RBAC Manager", f"rbac.manager.{stamp}@example.com", "manager", "PMO")
    staff = create_user("RBAC Staff", f"rbac.staff.{stamp}@example.com", "staff", "Engineering")
    return int(admin["id"]), int(manager["id"]), int(staff["id"])


def test_admin_can_update_role_permissions_and_staff_cannot() -> None:
    admin_id, _manager_id, staff_id = _bootstrap()

    roles = client.get("/rbac/roles", headers=_hdr(admin_id))
    assert roles.status_code == 200
    assert {role["slug"] for role in roles.json()} >= {"admin", "manager", "hr", "staff"}

    permissions = client.get("/rbac/permissions", headers=_hdr(admin_id))
    assert permissions.status_code == 200
    keys = {item["key"] for item in permissions.json()}
    assert {"ai.preview", "ai.import", "rag.manage", "roles.manage"}.issubset(keys)

    current = client.get("/rbac/roles/manager/permissions", headers=_hdr(admin_id))
    assert current.status_code == 200
    original_keys = sorted(item["key"] for item in current.json()["permissions"])
    reduced = [key for key in original_keys if key != "ai.preview"]

    denied = client.put(
        "/rbac/roles/manager/permissions",
        headers=_hdr(staff_id),
        json={"permission_keys": reduced},
    )
    assert denied.status_code == 403

    updated = client.put(
        "/rbac/roles/manager/permissions",
        headers=_hdr(admin_id),
        json={"permission_keys": reduced},
    )
    assert updated.status_code == 200
    assert "ai.preview" not in {item["key"] for item in updated.json()["permissions"]}

    restored = client.put(
        "/rbac/roles/manager/permissions",
        headers=_hdr(admin_id),
        json={"permission_keys": original_keys},
    )
    assert restored.status_code == 200


def test_permission_not_role_string_controls_ai_preview(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ai_api_key", "")
    admin_id, manager_id, _staff_id = _bootstrap()

    current = client.get("/rbac/roles/manager/permissions", headers=_hdr(admin_id))
    assert current.status_code == 200
    original_keys = sorted(item["key"] for item in current.json()["permissions"])
    without_preview = [key for key in original_keys if key != "ai.preview"]
    try:
        update = client.put(
            "/rbac/roles/manager/permissions",
            headers=_hdr(admin_id),
            json={"permission_keys": without_preview},
        )
        assert update.status_code == 200

        preview = client.post(
            "/ai/task-breakdown",
            headers=_hdr(manager_id),
            json={"text": "Tao dashboard KPI va bao cao tien do du an", "max_tasks": 3},
        )
        assert preview.status_code == 403
    finally:
        client.put(
            "/rbac/roles/manager/permissions",
            headers=_hdr(admin_id),
            json={"permission_keys": original_keys},
        )


def test_rag_document_query_and_ai_breakdown_metadata(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ai_api_key", "")
    admin_id, manager_id, staff_id = _bootstrap()

    staff_create = client.post(
        "/rag/documents",
        headers=_hdr(staff_id),
        json={"title": "Should fail", "content": "staff cannot manage rag documents"},
    )
    assert staff_create.status_code == 403

    created = client.post(
        "/rag/documents",
        headers=_hdr(admin_id),
        json={
            "title": "KPI report requirements",
            "source_label": "demo-spec",
            "content": (
                "Manager can export KPI report to CSV and XLSX. "
                "The implementation must keep human approval before importing AI tasks."
            ),
        },
    )
    assert created.status_code == 200
    doc = created.json()
    assert doc["chunk_count"] >= 1

    query = client.post(
        "/rag/query",
        headers=_hdr(manager_id),
        json={"query": "export KPI report", "limit": 3},
    )
    assert query.status_code == 200
    matches = query.json()["matches"]
    assert matches
    assert matches[0]["source_label"] == "demo-spec"

    preview = client.post(
        "/ai/task-breakdown",
        headers=_hdr(manager_id),
        json={
            "text": "Can phan tich yeu cau xuat bao cao KPI thanh cong viec",
            "max_tasks": 3,
            "use_rag": True,
            "rag_query": "export KPI report",
        },
    )
    assert preview.status_code == 200
    payload = preview.json()
    assert payload["retrieved_context_count"] >= 1
    assert "demo-spec" in payload["retrieved_sources"]
    assert payload["items"]
