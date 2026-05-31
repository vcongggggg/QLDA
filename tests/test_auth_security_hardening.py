from fastapi.testclient import TestClient

from app.database import get_connection, init_db
from app.main import app
from app.repository import create_audit_log
from app.seed import seed_auth_demo_accounts
from app.settings import settings


client = TestClient(app)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(email: str, password: str):
    return client.post("/auth/login", json={"usernameOrEmail": email, "password": password})


def test_failed_login_records_safe_attempt_and_blocks_after_limit(monkeypatch) -> None:
    init_db()
    seed_auth_demo_accounts()
    monkeypatch.setattr(settings, "auth_failed_login_limit", 5, raising=False)
    monkeypatch.setattr(settings, "auth_failed_login_window_minutes", 30, raising=False)
    monkeypatch.setattr(settings, "auth_failed_login_block_minutes", 30, raising=False)

    for _ in range(5):
        response = _login("admin@teamswork.local", "wrong")
        assert response.status_code == 401
        assert "password" not in response.text.lower()

    blocked = _login("admin@teamswork.local", "Admin@123")
    assert blocked.status_code == 429
    assert "too many" in blocked.json()["detail"].lower()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT email, outcome, reason_code, ip_hash
            FROM auth_login_attempts
            WHERE email = ?
            ORDER BY id
            """,
            ("admin@teamswork.local",),
        ).fetchall()

    assert len(rows) == 6
    assert {row["outcome"] for row in rows} == {"failure", "blocked"}
    assert {row["reason_code"] for row in rows} == {"invalid_credentials", "rate_limited"}
    assert all(row["ip_hash"] for row in rows)
    assert all("wrong" not in str(dict(row)).lower() for row in rows)


def test_domain_whitelist_allows_configured_domain_and_rejects_other_domains(monkeypatch) -> None:
    init_db()
    seed_auth_demo_accounts()
    monkeypatch.setattr(settings, "auth_allowed_email_domains", ("teamswork.local",), raising=False)

    allowed = _login("admin@teamswork.local", "Admin@123")
    assert allowed.status_code == 200

    monkeypatch.setattr(settings, "auth_allowed_email_domains", ("example.com",), raising=False)
    rejected = _login("admin@teamswork.local", "Admin@123")
    assert rejected.status_code == 403
    assert rejected.json()["detail"] == "email domain is not allowed"


def test_aad_sync_rejects_disallowed_domain_when_whitelist_is_configured(monkeypatch) -> None:
    init_db()
    seed_auth_demo_accounts()
    monkeypatch.setattr(settings, "teams_disable_jwt_validation", True)
    monkeypatch.setattr(settings, "auth_allowed_email_domains", ("teamswork.local",), raising=False)

    response = client.post("/integrations/teams/aad/sync", headers={"Authorization": "Bearer dev-token"})

    assert response.status_code == 403
    assert response.json()["detail"] == "email domain is not allowed"


def test_security_headers_are_added_to_api_responses(monkeypatch) -> None:
    monkeypatch.setattr(settings, "security_hsts_enabled", True, raising=False)
    monkeypatch.setattr(settings, "app_env", "production")

    response = client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "SAMEORIGIN"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert "https://res.cdn.office.net" in response.headers["content-security-policy"]
    assert "'unsafe-eval'" not in response.headers["content-security-policy"]
    assert response.headers["strict-transport-security"].startswith("max-age=")


def test_audit_export_requires_permission_and_returns_csv_xlsx() -> None:
    init_db()
    seed_auth_demo_accounts()
    admin = _login("admin@teamswork.local", "Admin@123").json()
    member = _login("member@teamswork.local", "Member@123").json()
    create_audit_log(int(admin["user"]["id"]), "test_export", "audit", None, "safe audit detail")

    forbidden = client.get("/audit/logs.csv", headers=_bearer(member["accessToken"]))
    assert forbidden.status_code == 403

    csv_response = client.get("/audit/logs.csv", headers=_bearer(admin["accessToken"]))
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "test_export" in csv_response.text
    assert "safe audit detail" in csv_response.text

    xlsx_response = client.get("/audit/logs.xlsx", headers=_bearer(admin["accessToken"]))
    assert xlsx_response.status_code == 200
    assert xlsx_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert xlsx_response.content.startswith(b"PK")
