from pathlib import Path

import pytest

from app.database import get_connection, init_db
from app.settings import Settings


def test_teams_production_tab_has_single_response_path() -> None:
    source = Path("app/routers/teams.py").read_text(encoding="utf-8")
    function_source = source.split("def teams_tab_prod_page() -> Response:", 1)[1]

    assert function_source.count("return Response(content=html") == 1
    assert function_source.count("<title>TeamsWork Production Tab</title>") == 1


def test_init_db_records_versioned_migrations() -> None:
    init_db()

    with get_connection() as conn:
        rows = conn.execute("SELECT version, name FROM schema_migrations ORDER BY version").fetchall()

    assert [int(row["version"]) for row in rows] == sorted(int(row["version"]) for row in rows)
    assert {row["name"] for row in rows} >= {
        "legacy_compat_columns",
        "operational_indexes",
    }


def test_production_settings_reject_insecure_auth_defaults() -> None:
    settings = Settings(
        app_env="production",
        auth_jwt_secret="dev-secret-change-me",
        auth_disable_jwt_validation=True,
        auth_allow_header_fallback=True,
    )

    with pytest.raises(ValueError, match="production"):
        settings.validate_production_safety()


def test_production_settings_accept_secure_auth_config() -> None:
    settings = Settings(
        app_env="production",
        auth_jwt_secret="unit-test-secret-that-is-long-enough",
        auth_disable_jwt_validation=False,
        auth_allow_header_fallback=False,
    )

    settings.validate_production_safety()


def test_smoke_check_script_exists() -> None:
    script = Path("scripts/smoke_check.py")

    assert script.exists()
    assert "monitoring/metrics" in script.read_text(encoding="utf-8")
