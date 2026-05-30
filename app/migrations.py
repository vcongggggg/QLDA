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
    "CREATE INDEX IF NOT EXISTS idx_rag_documents_project ON rag_documents(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_rag_document_permissions_project ON rag_document_permissions(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_rag_chunk_embeddings_chunk ON rag_chunk_embeddings(chunk_id)",
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


def _phase5_rag_schema(conn: Any, table_columns: TableColumns, ensure_column: EnsureColumn) -> None:
    from app.settings import settings

    use_pgvector = (
        conn.dialect == "postgresql"
        and settings.rag_embedding_enabled
        and settings.rag_vector_backend == "pgvector"
    )
    if use_pgvector:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

    ensure_column(conn, "rag_documents", "project_id", "project_id INTEGER")
    ensure_column(conn, "rag_documents", "storage_path", "storage_path TEXT")
    ensure_column(conn, "rag_chunks", "char_count", "char_count INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "rag_chunks", "token_estimate", "token_estimate INTEGER NOT NULL DEFAULT 0")

    if conn.dialect == "postgresql":
        embedding_column = "embedding vector(1536)" if use_pgvector else "embedding TEXT"
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS rag_chunk_embeddings (
                id SERIAL PRIMARY KEY,
                chunk_id INTEGER NOT NULL REFERENCES rag_chunks(id),
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                dim INTEGER NOT NULL,
                version TEXT NOT NULL,
                {embedding_column},
                created_at TEXT NOT NULL,
                UNIQUE (chunk_id, provider, model, version)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rag_document_permissions (
                id SERIAL PRIMARY KEY,
                document_id INTEGER NOT NULL REFERENCES rag_documents(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                user_id INTEGER REFERENCES users(id),
                role_slug TEXT,
                access_level TEXT NOT NULL DEFAULT 'query',
                created_at TEXT NOT NULL,
                UNIQUE (document_id, project_id, user_id, role_slug)
            )
            """
        )
    else:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rag_chunk_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                dim INTEGER NOT NULL,
                version TEXT NOT NULL,
                embedding_json TEXT,
                created_at TEXT NOT NULL,
                UNIQUE (chunk_id, provider, model, version),
                FOREIGN KEY (chunk_id) REFERENCES rag_chunks(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rag_document_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                user_id INTEGER,
                role_slug TEXT,
                access_level TEXT NOT NULL DEFAULT 'query',
                created_at TEXT NOT NULL,
                UNIQUE (document_id, project_id, user_id, role_slug),
                FOREIGN KEY (document_id) REFERENCES rag_documents(id),
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_documents_project ON rag_documents(project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_document_permissions_project ON rag_document_permissions(project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunk_embeddings_chunk ON rag_chunk_embeddings(chunk_id)")


def _auth_rbac_department_schema(conn: Any, table_columns: TableColumns, ensure_column: EnsureColumn) -> None:
    ensure_column(conn, "users", "password_hash", "password_hash TEXT")
    ensure_column(conn, "users", "role_id", "role_id TEXT")
    ensure_column(conn, "users", "department_id", "department_id INTEGER")
    ensure_column(conn, "users", "position", "position TEXT")
    ensure_column(conn, "users", "avatar_url", "avatar_url TEXT")
    ensure_column(conn, "users", "is_active", "is_active INTEGER NOT NULL DEFAULT 1")
    ensure_column(conn, "users", "created_at", "created_at TEXT")
    ensure_column(conn, "users", "updated_at", "updated_at TEXT")

    ensure_column(conn, "roles", "code", "code TEXT")
    ensure_column(conn, "roles", "is_system_role", "is_system_role INTEGER NOT NULL DEFAULT 1")
    ensure_column(conn, "permissions", "code", "code TEXT")
    ensure_column(conn, "permissions", "module", "module TEXT")
    ensure_column(conn, "departments", "description", "description TEXT")
    ensure_column(conn, "departments", "manager_user_id", "manager_user_id INTEGER")
    ensure_column(conn, "departments", "is_active", "is_active INTEGER NOT NULL DEFAULT 1")

    conn.execute("UPDATE roles SET code = COALESCE(code, slug)")
    conn.execute(
        """
        UPDATE roles
        SET is_system_role = CASE
            WHEN is_system_role IS NOT NULL THEN is_system_role
            WHEN is_system THEN 1
            ELSE 0
        END
        """
    )
    conn.execute("UPDATE permissions SET code = COALESCE(code, key)")
    conn.execute("UPDATE permissions SET module = COALESCE(module, category)")
    conn.execute("UPDATE users SET role_id = COALESCE(role_id, role)")
    conn.execute(
        """
        UPDATE users
        SET department_id = (
            SELECT d.id FROM departments d WHERE d.name = users.department OR d.code = users.department LIMIT 1
        )
        WHERE department_id IS NULL AND department IS NOT NULL
        """
    )
    conn.execute("UPDATE users SET created_at = COALESCE(created_at, CAST(CURRENT_TIMESTAMP AS TEXT))")
    conn.execute("UPDATE users SET updated_at = COALESCE(updated_at, created_at, CAST(CURRENT_TIMESTAMP AS TEXT))")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_department_id ON users(department_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_departments_active ON departments(is_active)")


def _task_ai_details_schema(conn: Any, _: TableColumns, __: EnsureColumn) -> None:
    if conn.dialect == "postgresql":
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_ai_details (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL UNIQUE REFERENCES tasks(id),
                source_ai_draft_id INTEGER NOT NULL REFERENCES ai_task_drafts(id),
                type TEXT,
                business_goal TEXT,
                subtasks TEXT NOT NULL DEFAULT '[]',
                acceptance_criteria TEXT NOT NULL DEFAULT '[]',
                data_requirements TEXT NOT NULL DEFAULT '[]',
                ui_components TEXT NOT NULL DEFAULT '[]',
                test_cases TEXT NOT NULL DEFAULT '[]',
                dependencies TEXT NOT NULL DEFAULT '[]',
                risks TEXT NOT NULL DEFAULT '[]',
                demo_value TEXT,
                suggested_role TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
    else:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_ai_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL UNIQUE,
                source_ai_draft_id INTEGER NOT NULL,
                type TEXT,
                business_goal TEXT,
                subtasks TEXT NOT NULL DEFAULT '[]',
                acceptance_criteria TEXT NOT NULL DEFAULT '[]',
                data_requirements TEXT NOT NULL DEFAULT '[]',
                ui_components TEXT NOT NULL DEFAULT '[]',
                test_cases TEXT NOT NULL DEFAULT '[]',
                dependencies TEXT NOT NULL DEFAULT '[]',
                risks TEXT NOT NULL DEFAULT '[]',
                demo_value TEXT,
                suggested_role TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                FOREIGN KEY (source_ai_draft_id) REFERENCES ai_task_drafts(id)
            )
            """
        )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_ai_details_draft ON task_ai_details(source_ai_draft_id)")


MIGRATIONS = (
    Migration(1, "legacy_compat_columns", _legacy_compat_columns),
    Migration(2, "operational_indexes", _operational_indexes),
    Migration(3, "normalize_reserved_user_email_domains", _normalize_reserved_user_email_domains),
    Migration(4, "create_ai_task_drafts", _create_ai_task_drafts),
    Migration(5, "phase5_rag_schema", _phase5_rag_schema),
    Migration(6, "auth_rbac_department_schema", _auth_rbac_department_schema),
    Migration(7, "task_ai_details_schema", _task_ai_details_schema),
)
