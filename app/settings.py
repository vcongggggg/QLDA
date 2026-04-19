import os


class Settings:
    app_base_url: str = os.getenv("APP_BASE_URL", "http://localhost:8000")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///teamswork.db")

    auth_jwt_secret: str = os.getenv("AUTH_JWT_SECRET", "dev-secret-change-me")
    auth_jwt_algorithm: str = os.getenv("AUTH_JWT_ALGORITHM", "HS256")
    auth_disable_jwt_validation: bool = os.getenv("AUTH_DISABLE_JWT_VALIDATION", "true").lower() == "true"
    auth_allow_header_fallback: bool = os.getenv("AUTH_ALLOW_HEADER_FALLBACK", "true").lower() == "true"

    teams_client_id: str = os.getenv("TEAMS_CLIENT_ID", "")
    teams_tenant_id: str = os.getenv("TEAMS_TENANT_ID", "common")
    teams_client_secret: str = os.getenv("TEAMS_CLIENT_SECRET", "")
    teams_incoming_webhook_url: str = os.getenv("TEAMS_INCOMING_WEBHOOK_URL", "")
    teams_channel_id: str = os.getenv("TEAMS_CHANNEL_ID", "")
    teams_service_url: str = os.getenv("TEAMS_SERVICE_URL", "")
    teams_disable_jwt_validation: bool = os.getenv("TEAMS_DISABLE_JWT_VALIDATION", "false").lower() == "true"
    teams_proactive_mode: str = os.getenv("TEAMS_PROACTIVE_MODE", "webhook")
    teams_bot_app_id: str = os.getenv("TEAMS_BOT_APP_ID", "")
    teams_bot_app_secret: str = os.getenv("TEAMS_BOT_APP_SECRET", "")


settings = Settings()
