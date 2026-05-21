from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


TableColumns = Callable[[Any, str], set[str]]
EnsureColumn = Callable[[Any, str, str, str], None]


INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_tasks_assignee_status_deadline ON tasks(assignee_id, status, deadline)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_project_status_deadline ON tasks(project_id, status, deadline)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_sprint_status ON tasks(sprint_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_notification_queue_status_retry ON notification_queue(status, next_retry_at)",
    "CREATE INDEX IF NOT EXISTS idx_app_notifications_user_read_created ON app_notifications(user_id, is_read, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_created ON audit_logs(entity, entity_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_kpi_adjustments_month_user ON kpi_adjustments(month, user_id)",
    "CREATE INDEX IF NOT EXISTS idx_role_permissions_permission ON role_permissions(permission_key)",
    "CREATE INDEX IF NOT EXISTS idx_rag_chunks_document ON rag_chunks(document_id, chunk_index)",
    "CREATE INDEX IF NOT EXISTS idx_ai_task_drafts_status_created ON ai_task_drafts(status, created_at)",
)


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[Any, TableColumns, EnsureColumn], None]


def run_schema_migrations(conn: Any, table_columns: TableColumns, ensure_column: EnsureColumn) -> None:
    _ensure_schema_migrations_table(conn)
    applied = {
        int(row["version"])
        for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }
    for migration in MIGRATIONS:
        if migration.version in applied:
            continue
        migration.apply(conn, table_columns, ensure_column)
        conn.execute(
            """
            /* no-returning-id */ INSERT INTO schema_migrations (version, name, applied_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (migration.version, migration.name),
        )


def _ensure_schema_migrations_table(conn: Any) -> None:
    if conn.dialect == "postgresql":
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _legacy_compat_columns(conn: Any, table_columns: TableColumns, ensure_column: EnsureColumn) -> None:
    user_cols = table_columns(conn, "users")
    if "aad_object_id" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN aad_object_id TEXT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_aad_object_id ON users(aad_object_id)")

    ensure_column(conn, "tasks", "project_id", "project_id INTEGER")
    ensure_column(conn, "tasks", "sprint_id", "sprint_id INTEGER")
    ensure_column(conn, "tasks", "story_points", "story_points INTEGER NOT NULL DEFAULT 1")

    ensure_column(conn, "notification_queue", "attempts", "attempts INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "notification_queue", "max_attempts", "max_attempts INTEGER NOT NULL DEFAULT 3")
    ensure_column(conn, "notification_queue", "last_error", "last_error TEXT")
    ensure_column(conn, "notification_queue", "next_retry_at", "next_retry_at TEXT")


def _operational_indexes(conn: Any, _: TableColumns, __: EnsureColumn) -> None:
    for statement in INDEX_STATEMENTS:
        conn.execute(statement)


def _normalize_reserved_user_email_domains(conn: Any, _: TableColumns, __: EnsureColumn) -> None:
    replacements = (
        ("@local.test", "@example.com"),
        ("@teamswork.local", "@teamswork.example.com"),
        ("@aad.local", "@aad.example.com"),
    )
    for old_domain, new_domain in replacements:
        conn.execute(
            """
            UPDATE users
            SET email = REPLACE(email, ?, ?)
            WHERE email LIKE ?
            """,
            (old_domain, new_domain, f"%{old_domain}"),
        )


def _create_ai_task_drafts(conn: Any, _: TableColumns, __: EnsureColumn) -> None:
    if conn.dialect == "postgresql":
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_task_drafts (
                id SERIAL PRIMARY KEY,
                source_type TEXT NOT NULL CHECK(source_type IN ('text','docx')),
                source_summary TEXT,
                source_name TEXT,
                generated_tasks TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','reviewed','imported')),
                reviewer_id INTEGER REFERENCES users(id),
                reviewed_at TEXT,
                imported_at TEXT,
                review_note TEXT,
                edit_reason TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL
            )
            """
        )
    else:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_task_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL CHECK(source_type IN ('text','docx')),
                source_summary TEXT,
                source_name TEXT,
                generated_tasks TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','reviewed','imported')),
                reviewer_id INTEGER,
                reviewed_at TEXT,
                imported_at TEXT,
                review_note TEXT,
                edit_reason TEXT,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (reviewer_id) REFERENCES users(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
            """
        )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_task_drafts_status_created ON ai_task_drafts(status, created_at)")


MIGRATIONS = (
    Migration(1, "legacy_compat_columns", _legacy_compat_columns),
    Migration(2, "operational_indexes", _operational_indexes),
    Migration(3, "normalize_reserved_user_email_domains", _normalize_reserved_user_email_domains),
    Migration(4, "create_ai_task_drafts", _create_ai_task_drafts),
)
