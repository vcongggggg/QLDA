from fastapi.testclient import TestClient

from app.database import get_connection
from app.main import app
from app.seed import seed_full_demo_data
from tests.role_module_matrix import EXPECTED_ROLE_MODULES, MODULE_PRIMARY_ENDPOINTS, ROLE_ACCOUNTS, ROLE_ADMIN_ENDPOINTS


client = TestClient(app)


def _login(role: str) -> dict:
    email, password = ROLE_ACCOUNTS[role]
    response = client.post("/auth/login", json={"usernameOrEmail": email, "password": password})
    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["role"]["code"] == role
    return payload


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _request(method: str, path: str, token: str):
    return client.request(method, path, headers=_auth_headers(token))


def test_demo_role_logins_return_expected_module_permissions() -> None:
    seed_full_demo_data(mode="upsert")

    for role, modules in EXPECTED_ROLE_MODULES.items():
        payload = _login(role)
        permissions = set(payload["user"]["permissions"])
        me = client.get("/auth/me", headers=_auth_headers(payload["accessToken"]))

        assert me.status_code == 200
        assert me.json()["role"]["code"] == role
        assert permissions
        for module in modules:
            assert module in EXPECTED_ROLE_MODULES[role]


def test_visible_module_primary_endpoints_do_not_return_forbidden() -> None:
    seed_full_demo_data(mode="upsert")

    for role, modules in EXPECTED_ROLE_MODULES.items():
        token = _login(role)["accessToken"]
        for module in modules:
            for method, path in MODULE_PRIMARY_ENDPOINTS[module]:
                response = _request(method, path, token)
                assert response.status_code != 403, f"{role} can see {module}, but {method} {path} returned 403"
                assert response.status_code < 500, f"{role} {method} {path} returned {response.status_code}"
        for method, path in ROLE_ADMIN_ENDPOINTS.get(role, ()):
            response = _request(method, path, token)
            assert response.status_code != 403, f"{role} admin endpoint {method} {path} returned 403"
            assert response.status_code < 500


def test_manager_demo_account_can_see_seeded_projects() -> None:
    seed_full_demo_data(mode="upsert")
    token = _login("MANAGER")["accessToken"]

    response = client.get("/projects", headers=_auth_headers(token))

    assert response.status_code == 200
    assert len(response.json()) == 3


def test_seeded_member_with_tasks_is_scoped_to_own_work() -> None:
    seed_full_demo_data(mode="upsert")
    login = client.post(
        "/auth/login",
        json={"usernameOrEmail": "kiet.do@teamswork.example.com", "password": "Demo@123"},
    )
    assert login.status_code == 200
    token = login.json()["accessToken"]
    user_id = int(login.json()["user"]["id"])

    tasks = client.get("/tasks", headers=_auth_headers(token))
    kpi = client.get("/kpi/monthly?month=2026-08", headers=_auth_headers(token))

    assert tasks.status_code == 200
    assert tasks.json()
    assert {int(task["assignee_id"]) for task in tasks.json()} == {user_id}
    assert kpi.status_code == 200
    assert {int(row["user_id"]) for row in kpi.json()} <= {user_id}

    with get_connection() as conn:
        other_task = conn.execute(
            "SELECT id FROM tasks WHERE assignee_id != ? LIMIT 1",
            (user_id,),
        ).fetchone()
    assert other_task is not None
    detail = client.get(f"/tasks/{int(other_task['id'])}", headers=_auth_headers(token))
    assert detail.status_code == 403
