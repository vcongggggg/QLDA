import os
from pathlib import Path
from typing import Any


def _load_dotenv_if_present() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv_if_present()


def parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    return default


class Settings:
    def __init__(self, **overrides: Any) -> None:
        self.app_env = str(overrides.get("app_env", os.getenv("APP_ENV", "development"))).lower()
        self.app_base_url = overrides.get("app_base_url", os.getenv("APP_BASE_URL", "http://localhost:8000"))
        self.database_url = overrides.get("database_url", os.getenv("DATABASE_URL", "sqlite:///teamswork.db"))

        self.auth_jwt_secret = overrides.get("auth_jwt_secret", os.getenv("AUTH_JWT_SECRET", "dev-secret-change-me"))
        self.auth_jwt_algorithm = overrides.get("auth_jwt_algorithm", os.getenv("AUTH_JWT_ALGORITHM", "HS256"))
        self.auth_disable_jwt_validation = parse_bool(
            overrides.get(
                "auth_disable_jwt_validation",
                os.getenv("AUTH_DISABLE_JWT_VALIDATION"),
            ),
            default=True,
        )
        self.auth_allow_header_fallback = parse_bool(
            overrides.get(
                "auth_allow_header_fallback",
                os.getenv("AUTH_ALLOW_HEADER_FALLBACK"),
            ),
            default=True,
        )

        self.teams_client_id = overrides.get("teams_client_id", os.getenv("TEAMS_CLIENT_ID", ""))
        self.teams_tenant_id = overrides.get("teams_tenant_id", os.getenv("TEAMS_TENANT_ID", "common"))
        self.teams_client_secret = overrides.get("teams_client_secret", os.getenv("TEAMS_CLIENT_SECRET", ""))
        self.teams_incoming_webhook_url = overrides.get(
            "teams_incoming_webhook_url",
            os.getenv("TEAMS_INCOMING_WEBHOOK_URL", ""),
        )
        self.teams_channel_id = overrides.get("teams_channel_id", os.getenv("TEAMS_CHANNEL_ID", ""))
        self.teams_service_url = overrides.get("teams_service_url", os.getenv("TEAMS_SERVICE_URL", ""))
        self.teams_disable_jwt_validation = parse_bool(
            overrides.get(
                "teams_disable_jwt_validation",
                os.getenv("TEAMS_DISABLE_JWT_VALIDATION"),
            ),
            default=False,
        )
        self.teams_proactive_mode = overrides.get("teams_proactive_mode", os.getenv("TEAMS_PROACTIVE_MODE", "webhook"))
        self.teams_bot_app_id = overrides.get("teams_bot_app_id", os.getenv("TEAMS_BOT_APP_ID", ""))
        self.teams_bot_app_secret = overrides.get("teams_bot_app_secret", os.getenv("TEAMS_BOT_APP_SECRET", ""))

        self.ai_provider = overrides.get("ai_provider", os.getenv("AI_PROVIDER", "openai_compatible"))
        self.ai_api_key = overrides.get("ai_api_key", os.getenv("AI_API_KEY", "ollama"))
        self.ai_base_url = overrides.get("ai_base_url", os.getenv("AI_BASE_URL", "http://localhost:11434/v1"))
        self.ai_model = overrides.get("ai_model", os.getenv("AI_MODEL", "qwen3:8b"))
        self.ai_fallback_model = overrides.get("ai_fallback_model", os.getenv("AI_FALLBACK_MODEL", "qwen2.5:7b"))
        self.ai_task_breakdown_timeout_seconds = float(
            overrides.get(
                "ai_task_breakdown_timeout_seconds",
                os.getenv("AI_TASK_BREAKDOWN_TIMEOUT_SECONDS", "20"),
            )
        )

    def validate_production_safety(self) -> None:
        if self.app_env != "production":
            return

        problems: list[str] = []
        if self.auth_disable_jwt_validation:
            problems.append("AUTH_DISABLE_JWT_VALIDATION must be false")
        if self.auth_allow_header_fallback:
            problems.append("AUTH_ALLOW_HEADER_FALLBACK must be false")
        if self.auth_jwt_secret in {"", "dev-secret-change-me", "change-this-production-secret"}:
            problems.append("AUTH_JWT_SECRET must be a real production secret")
        if len(self.auth_jwt_secret) < 24:
            problems.append("AUTH_JWT_SECRET must be at least 24 characters")

        if problems:
            joined = "; ".join(problems)
            raise ValueError(f"Insecure production settings: {joined}")


settings = Settings()
