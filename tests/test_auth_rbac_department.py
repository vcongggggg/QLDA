from fastapi.testclient import TestClient
from pathlib import Path
import re

from app.database import get_connection, init_db
from app.main import app
from app.repository import create_task, create_user, update_user_active
from app.seed import seed_auth_demo_accounts


client = TestClient(app)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _header_user(user_id: int) -> dict[str, str]:
    return {"X-User-Id": str(user_id)}


def _login(email: str, password: str) -> dict:
    response = client.post(
        "/auth/login",
        json={"usernameOrEmail": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def test_demo_accounts_login_and_me_returns_rbac_profile() -> None:
    init_db()
    seed_auth_demo_accounts()

    credentials = (
        ("admin@teamswork.local", "Admin@123", "ADMIN"),
        ("manager@teamswork.local", "Manager@123", "MANAGER"),
        ("leader@teamswork.local", "Leader@123", "LEADER"),
        ("member@teamswork.local", "Member@123", "MEMBER"),
        ("hr@teamswork.local", "Hr@123", "HR"),
        ("auditor@teamswork.local", "Auditor@123", "AUDITOR"),
    )

    for email, password, role_code in credentials:
        payload = _login(email, password)
        assert payload["accessToken"]
        assert payload["user"]["email"] == email
        assert payload["user"]["role"]["code"] == role_code
        assert payload["user"]["department"]
        assert payload["user"]["permissions"]
        assert "password_hash" not in payload["user"]

        me = client.get("/auth/me", headers=_bearer(payload["accessToken"]))
        assert me.status_code == 200
        assert me.json()["email"] == email
        assert me.json()["role"]["code"] == role_code
        assert "password_hash" not in me.json()


def test_login_rejects_wrong_password_and_inactive_user() -> None:
    init_db()
    seed_auth_demo_accounts()

    bad_password = client.post(
        "/auth/login",
        json={"usernameOrEmail": "admin@teamswork.local", "password": "wrong"},
    )
    assert bad_password.status_code == 401

    member = _login("member@teamswork.local", "Member@123")
    update_user_active(int(member["user"]["id"]), False)
    inactive = client.post(
        "/auth/login",
        json={"usernameOrEmail": "member@teamswork.local", "password": "Member@123"},
    )
    assert inactive.status_code == 403


def test_permissions_gate_admin_surfaces_and_do_not_duplicate_seed() -> None:
    init_db()
    seed_auth_demo_accounts()
    seed_auth_demo_accounts()

    admin = _login("admin@teamswork.local", "Admin@123")
    member = _login("member@teamswork.local", "Member@123")
    auditor = _login("auditor@teamswork.local", "Auditor@123")

    assert client.get("/users", headers=_bearer(admin["accessToken"])).status_code == 200
    assert client.get("/users", headers=_bearer(member["accessToken"])).status_code == 403
    assert client.get("/departments", headers=_bearer(admin["accessToken"])).status_code == 200
    assert client.post(
        "/departments",
        headers=_bearer(auditor["accessToken"]),
        json={"name": "Audit Owned", "code": "AUDX"},
    ).status_code == 403
    assert client.get("/audit/logs", headers=_bearer(auditor["accessToken"])).status_code == 200

    with get_connection() as conn:
        role_count = conn.execute("SELECT COUNT(*) AS c FROM roles WHERE slug = 'ADMIN'").fetchone()["c"]
        account_count = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE email = 'admin@teamswork.local'"
        ).fetchone()["c"]
    assert int(role_count) == 1
    assert int(account_count) == 1


def test_role_permission_seed_matches_sidebar_rbac_policy() -> None:
    init_db()
    seed_auth_demo_accounts()

    member = _login("member@teamswork.local", "Member@123")
    auditor = _login("auditor@teamswork.local", "Auditor@123")
    hr = _login("hr@teamswork.local", "Hr@123")
    manager = _login("manager@teamswork.local", "Manager@123")
    leader = _login("leader@teamswork.local", "Leader@123")

    member_permissions = set(member["user"]["permissions"])
    assert {
        "USER_VIEW",
        "ROLE_VIEW",
        "DEPARTMENT_VIEW",
        "AUDIT_VIEW",
        "OPS_VIEW",
    }.isdisjoint(member_permissions)

    auditor_permissions = set(auditor["user"]["permissions"])
    assert {"AUDIT_VIEW", "OPS_VIEW", "REPORT_VIEW_ALL"}.issubset(auditor_permissions)
    assert {
        "USER_CREATE",
        "USER_UPDATE",
        "USER_DEACTIVATE",
        "USER_RESET_PASSWORD",
        "PROJECT_CREATE",
        "PROJECT_UPDATE",
        "PROJECT_DELETE",
        "KANBAN_MANAGE_ALL",
        "KANBAN_MANAGE_TEAM",
        "tasks.create",
        "tasks.update_any",
        "projects.manage",
        "ai.import",
        "roles.manage",
        "ROLE_MANAGE",
    }.isdisjoint(auditor_permissions)

    hr_permissions = set(hr["user"]["permissions"])
    assert {
        "USER_VIEW",
        "USER_CREATE",
        "USER_UPDATE",
        "USER_RESET_PASSWORD",
        "DEPARTMENT_VIEW",
    }.issubset(hr_permissions)
    assert "ROLE_MANAGE" not in hr_permissions

    for user in (manager, leader):
        permissions = set(user["user"]["permissions"])
        assert {"KANBAN_VIEW", "PROJECT_VIEW", "KPI_VIEW_TEAM", "REPORT_VIEW_TEAM"}.issubset(permissions)
        assert {"USER_VIEW", "ROLE_VIEW", "DEPARTMENT_VIEW", "AUDIT_VIEW", "OPS_VIEW"}.isdisjoint(permissions)


def test_sidebar_visibility_uses_permissions_from_auth_me() -> None:
    init_db()
    seed_auth_demo_accounts()

    index = (Path(__file__).resolve().parents[1] / "app" / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (Path(__file__).resolve().parents[1] / "app" / "static" / "app.js").read_text(encoding="utf-8")
    nav_items = _sidebar_nav_items(index)

    member = _login("member@teamswork.local", "Member@123")
    auditor = _login("auditor@teamswork.local", "Auditor@123")
    admin = _login("admin@teamswork.local", "Admin@123")

    assert "ROLE_NAV_POLICY" in app_js
    assert "MEMBER:  ['dashboard', 'kanban', 'kpi']" in app_js
    assert "ROLE_NAV_LABELS" in app_js
    assert "My Tasks" in app_js
    assert "My KPI" in app_js
    assert {"dashboard", "kanban", "kpi"}.issubset(_visible_sections(member["user"]["permissions"], nav_items))
    assert {"admin", "ops"}.isdisjoint(_visible_sections(member["user"]["permissions"], nav_items))

    auditor_sections = _visible_sections(auditor["user"]["permissions"], nav_items)
    assert "ops" in auditor_sections
    assert "admin" not in auditor_sections

    assert {section for section, _requirements in nav_items}.issubset(
        _visible_sections(admin["user"]["permissions"], nav_items)
    )


def test_forbidden_direct_access_is_blocked_by_backend_and_static_guard_exists() -> None:
    init_db()
    seed_auth_demo_accounts()
    member = _login("member@teamswork.local", "Member@123")
    auditor = _login("auditor@teamswork.local", "Auditor@123")

    assert client.get("/users", headers=_bearer(member["accessToken"])).status_code == 403
    assert client.get("/monitoring/ops", headers=_bearer(member["accessToken"])).status_code == 403
    assert client.get("/monitoring/ops", headers=_bearer(auditor["accessToken"])).status_code == 200
    assert client.put(
        "/rbac/roles/MEMBER/permissions",
        headers=_bearer(auditor["accessToken"]),
        json={"permission_keys": []},
    ).status_code == 403

    app_js = (Path(__file__).resolve().parents[1] / "app" / "static" / "app.js").read_text(encoding="utf-8")
    index = (Path(__file__).resolve().parents[1] / "app" / "static" / "index.html").read_text(encoding="utf-8")
    assert "function canViewModule(module)" in app_js
    assert "showAccessDenied" in app_js
    assert "Phiên đăng nhập đã hết hạn" in app_js
    assert "Signing in..." in app_js
    assert "backToDashboard" in app_js
    assert "sec-access-denied" in index
    assert "Back to dashboard" in index


def test_canonical_member_role_scopes_tasks_dashboard_and_kpi_to_own_data() -> None:
    init_db()
    member = create_user("Scoped Member", "scoped.member@example.com", "MEMBER", "Engineering")
    other = create_user("Other Member", "other.member@example.com", "MEMBER", "Engineering")

    own_task = create_task(
        "Scoped own task",
        None,
        int(member["id"]),
        None,
        None,
        3,
        "medium",
        "2026-05-10T09:00:00+00:00",
    )
    other_task = create_task(
        "Scoped other task",
        None,
        int(other["id"]),
        None,
        None,
        5,
        "hard",
        "2026-05-11T09:00:00+00:00",
    )

    tasks = client.get(f"/tasks?assignee_id={other['id']}", headers=_header_user(int(member["id"])))
    assert tasks.status_code == 200
    task_ids = {item["id"] for item in tasks.json()}
    assert int(own_task["id"]) in task_ids
    assert int(other_task["id"]) not in task_ids

    dashboard = client.get("/dashboard/summary?month=2026-05", headers=_header_user(int(member["id"])))
    assert dashboard.status_code == 200
    assert dashboard.json()["total_tasks"] == 1

    kpi = client.get("/kpi/monthly?month=2026-05", headers=_header_user(int(member["id"])))
    assert kpi.status_code == 200
    assert {row["user_id"] for row in kpi.json()} == {int(member["id"])}


def test_create_user_sets_password_role_department_without_exposing_hash() -> None:
    init_db()
    seed_auth_demo_accounts()
    admin = _login("admin@teamswork.local", "Admin@123")

    created = client.post(
        "/users",
        headers=_bearer(admin["accessToken"]),
        json={
            "full_name": "Demo Created User",
            "email": "created.user@teamswork.local",
            "password": "Created@123",
            "role": "MEMBER",
            "department_id": admin["user"]["department"]["id"],
            "position": "Engineer",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["email"] == "created.user@teamswork.local"
    assert body["role_detail"]["code"] == "MEMBER"
    assert "password_hash" not in body

    assert _login("created.user@teamswork.local", "Created@123")["user"]["email"] == body["email"]


def _sidebar_nav_items(index_html: str) -> list[tuple[str, set[str]]]:
    items: list[tuple[str, set[str]]] = []
    for match in re.finditer(r'<a class="[^"]*\bnav-item\b[^"]*"(?P<attrs>[^>]+)>', index_html):
        attrs = match.group("attrs")
        section = re.search(r'data-section="([^"]+)"', attrs)
        if not section:
            continue
        one = re.search(r'data-permission="([^"]+)"', attrs)
        any_permission = re.search(r'data-any-permission="([^"]+)"', attrs)
        requirements: set[str] = set()
        if one:
            requirements.add(one.group(1))
        if any_permission:
            requirements.update(item.strip() for item in any_permission.group(1).split(",") if item.strip())
        items.append((section.group(1), requirements))
    return items


def _visible_sections(permissions: list[str], nav_items: list[tuple[str, set[str]]]) -> set[str]:
    granted = set(permissions)
    return {section for section, requirements in nav_items if not requirements or not granted.isdisjoint(requirements)}
