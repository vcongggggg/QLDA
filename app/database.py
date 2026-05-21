from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import psycopg2

from app.migrations import run_schema_migrations


_SQLITE_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        aad_object_id TEXT UNIQUE,
        role TEXT NOT NULL,
        department TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roles (
        slug TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        is_system INTEGER NOT NULL DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS permissions (
        key TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS role_permissions (
        role_slug TEXT NOT NULL,
        permission_key TEXT NOT NULL,
        PRIMARY KEY (role_slug, permission_key),
        FOREIGN KEY (role_slug) REFERENCES roles(slug),
        FOREIGN KEY (permission_key) REFERENCES permissions(key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        code TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        department_id INTEGER,
        manager_id INTEGER,
        start_date TEXT,
        end_date TEXT,
        status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','on_hold','done','archived')),
        created_at TEXT NOT NULL,
        FOREIGN KEY (department_id) REFERENCES departments(id),
        FOREIGN KEY (manager_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        joined_at TEXT NOT NULL,
        UNIQUE (project_id, user_id),
        FOREIGN KEY (project_id) REFERENCES projects(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sprints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        goal TEXT,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN ('planned','active','completed')),
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        assignee_id INTEGER NOT NULL,
        project_id INTEGER,
        sprint_id INTEGER,
        story_points INTEGER NOT NULL DEFAULT 1,
        difficulty TEXT NOT NULL CHECK (difficulty IN ('easy','medium','hard')),
        status TEXT NOT NULL CHECK (status IN ('todo','doing','done')),
        deadline TEXT NOT NULL,
        completed_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (assignee_id) REFERENCES users(id),
        FOREIGN KEY (project_id) REFERENCES projects(id),
        FOREIGN KEY (sprint_id) REFERENCES sprints(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS task_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        author_user_id INTEGER NOT NULL,
        body TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id),
        FOREIGN KEY (author_user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sprint_capacity_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sprint_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        capacity_hours REAL NOT NULL,
        allocated_hours REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        UNIQUE (sprint_id, user_id),
        FOREIGN KEY (sprint_id) REFERENCES sprints(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_risks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        probability TEXT NOT NULL CHECK(probability IN ('low','medium','high')),
        impact TEXT NOT NULL CHECK(impact IN ('low','medium','high')),
        mitigation_plan TEXT,
        owner_user_id INTEGER,
        status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','mitigated','closed')),
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id),
        FOREIGN KEY (owner_user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS weekly_status_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        sprint_id INTEGER,
        week_label TEXT NOT NULL,
        progress_percent REAL NOT NULL,
        rag_status TEXT NOT NULL CHECK(rag_status IN ('red','amber','green')),
        summary TEXT NOT NULL,
        next_steps TEXT,
        blocker TEXT,
        created_by INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id),
        FOREIGN KEY (sprint_id) REFERENCES sprints(id),
        FOREIGN KEY (created_by) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS teams_conversation_refs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        aad_object_id TEXT,
        conversation_id TEXT NOT NULL UNIQUE,
        service_url TEXT,
        tenant_id TEXT,
        channel_id TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notification_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        channel TEXT NOT NULL,
        payload TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','sent','failed')),
        attempts INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 3,
        last_error TEXT,
        next_retry_at TEXT,
        created_at TEXT NOT NULL,
        sent_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS app_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('task_due_soon','task_overdue','task_comment','task_status_changed')),
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id INTEGER NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        read_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_user_id INTEGER,
        action TEXT NOT NULL,
        entity TEXT NOT NULL,
        entity_id INTEGER,
        detail TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (actor_user_id) REFERENCES users(id)
    )
    """,
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
    """,
    """
    CREATE TABLE IF NOT EXISTS kpi_adjustments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        month TEXT NOT NULL,
        points REAL NOT NULL,
        reason TEXT NOT NULL,
        created_by INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (created_by) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rag_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        source_label TEXT,
        created_by INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (created_by) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rag_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        source_label TEXT,
        chunk_index INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES rag_documents(id)
    )
    """,
]

_POSTGRES_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        aad_object_id TEXT UNIQUE,
        role TEXT NOT NULL,
        department TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roles (
        slug TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        is_system BOOLEAN NOT NULL DEFAULT TRUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS permissions (
        key TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS role_permissions (
        role_slug TEXT NOT NULL REFERENCES roles(slug),
        permission_key TEXT NOT NULL REFERENCES permissions(key),
        PRIMARY KEY (role_slug, permission_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS departments (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        code TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS projects (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        department_id INTEGER REFERENCES departments(id),
        manager_id INTEGER REFERENCES users(id),
        start_date TEXT,
        end_date TEXT,
        status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','on_hold','done','archived')),
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_members (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id),
        user_id INTEGER NOT NULL REFERENCES users(id),
        role TEXT NOT NULL,
        joined_at TEXT NOT NULL,
        UNIQUE (project_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sprints (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id),
        name TEXT NOT NULL,
        goal TEXT,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN ('planned','active','completed')),
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        assignee_id INTEGER NOT NULL REFERENCES users(id),
        project_id INTEGER REFERENCES projects(id),
        sprint_id INTEGER REFERENCES sprints(id),
        story_points INTEGER NOT NULL DEFAULT 1,
        difficulty TEXT NOT NULL CHECK (difficulty IN ('easy','medium','hard')),
        status TEXT NOT NULL CHECK (status IN ('todo','doing','done')),
        deadline TEXT NOT NULL,
        completed_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS task_comments (
        id SERIAL PRIMARY KEY,
        task_id INTEGER NOT NULL REFERENCES tasks(id),
        author_user_id INTEGER NOT NULL REFERENCES users(id),
        body TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sprint_capacity_plans (
        id SERIAL PRIMARY KEY,
        sprint_id INTEGER NOT NULL REFERENCES sprints(id),
        user_id INTEGER NOT NULL REFERENCES users(id),
        capacity_hours DOUBLE PRECISION NOT NULL,
        allocated_hours DOUBLE PRECISION NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        UNIQUE (sprint_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_risks (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id),
        title TEXT NOT NULL,
        description TEXT,
        probability TEXT NOT NULL CHECK(probability IN ('low','medium','high')),
        impact TEXT NOT NULL CHECK(impact IN ('low','medium','high')),
        mitigation_plan TEXT,
        owner_user_id INTEGER REFERENCES users(id),
        status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','mitigated','closed')),
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS weekly_status_updates (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id),
        sprint_id INTEGER REFERENCES sprints(id),
        week_label TEXT NOT NULL,
        progress_percent DOUBLE PRECISION NOT NULL,
        rag_status TEXT NOT NULL CHECK(rag_status IN ('red','amber','green')),
        summary TEXT NOT NULL,
        next_steps TEXT,
        blocker TEXT,
        created_by INTEGER NOT NULL REFERENCES users(id),
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS teams_conversation_refs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        aad_object_id TEXT,
        conversation_id TEXT NOT NULL UNIQUE,
        service_url TEXT,
        tenant_id TEXT,
        channel_id TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notification_queue (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        channel TEXT NOT NULL,
        payload TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','sent','failed')),
        attempts INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 3,
        last_error TEXT,
        next_retry_at TEXT,
        created_at TEXT NOT NULL,
        sent_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS app_notifications (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        type TEXT NOT NULL CHECK(type IN ('task_due_soon','task_overdue','task_comment','task_status_changed')),
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id INTEGER NOT NULL,
        is_read BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TEXT NOT NULL,
        read_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        actor_user_id INTEGER REFERENCES users(id),
        action TEXT NOT NULL,
        entity TEXT NOT NULL,
        entity_id INTEGER,
        detail TEXT,
        created_at TEXT NOT NULL
    )
    """,
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
    """,
    """
    CREATE TABLE IF NOT EXISTS kpi_adjustments (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        month TEXT NOT NULL,
        points DOUBLE PRECISION NOT NULL,
        reason TEXT NOT NULL,
        created_by INTEGER NOT NULL REFERENCES users(id),
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rag_documents (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        source_label TEXT,
        created_by INTEGER NOT NULL REFERENCES users(id),
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rag_chunks (
        id SERIAL PRIMARY KEY,
        document_id INTEGER NOT NULL REFERENCES rag_documents(id),
        content TEXT NOT NULL,
        source_label TEXT,
        chunk_index INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
]

_NO_ROW = object()


class DBRow(Mapping[str, Any]):
    def __init__(self, columns: Sequence[str], values: Sequence[Any]):
        self._columns = tuple(columns)
        self._values = tuple(values)
        self._data = dict(zip(self._columns, self._values))

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._columns)

    def __len__(self) -> int:
        return len(self._columns)


class DBCursor:
    def __init__(
        self,
        cursor: Any,
        *,
        prefetched_row: Any = _NO_ROW,
        lastrowid: int | None = None,
    ):
        self._cursor = cursor
        self._prefetched_row = prefetched_row
        self.lastrowid = lastrowid
        self.rowcount = cursor.rowcount

    def _columns(self) -> list[str]:
        if not self._cursor.description:
            return []
        return [col[0] for col in self._cursor.description]

    def _wrap_row(self, row: Any) -> DBRow | None:
        if row is None:
            return None
        columns = self._columns()
        if isinstance(row, Mapping):
            values = [row.get(col) for col in columns]
        else:
            values = list(row)
        return DBRow(columns, values)

    def fetchone(self) -> DBRow | None:
        if self._prefetched_row is not _NO_ROW:
            row = self._prefetched_row
            self._prefetched_row = _NO_ROW
            return self._wrap_row(row)
        return self._wrap_row(self._cursor.fetchone())

    def fetchall(self) -> list[DBRow]:
        rows: list[DBRow] = []
        if self._prefetched_row is not _NO_ROW:
            wrapped = self._wrap_row(self._prefetched_row)
            self._prefetched_row = _NO_ROW
            if wrapped is not None:
                rows.append(wrapped)
        rows.extend(w for w in (self._wrap_row(row) for row in self._cursor.fetchall()) if w is not None)
        return rows


class DatabaseConnection:
    def __init__(self, raw_connection: Any, dialect: str):
        self._raw_connection = raw_connection
        self.dialect = dialect

    def __enter__(self) -> DatabaseConnection:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()

    def execute(self, query: str, params: Sequence[Any] | None = None) -> DBCursor:
        params_tuple = tuple(params or ())
        cursor = self._raw_connection.cursor()
        if self.dialect == "postgresql":
            wants_lastrowid = _should_append_returning_id(query)
            cursor.execute(_translate_postgres_sql(query, append_returning_id=wants_lastrowid), params_tuple)
            inserted_id = None
            if wants_lastrowid:
                returned = cursor.fetchone()
                inserted_id = int(returned[0]) if returned else None
            return DBCursor(cursor, lastrowid=inserted_id)

        cursor.execute(query, params_tuple)
        return DBCursor(cursor, lastrowid=getattr(cursor, "lastrowid", None))

    def executemany(self, query: str, params_seq: Sequence[Sequence[Any]]) -> DBCursor:
        cursor = self._raw_connection.cursor()
        normalized_params = [tuple(params) for params in params_seq]
        if self.dialect == "postgresql":
            cursor.executemany(_translate_postgres_sql(query, append_returning_id=False), normalized_params)
        else:
            cursor.executemany(query, normalized_params)
        return DBCursor(cursor, lastrowid=getattr(cursor, "lastrowid", None))

    def commit(self) -> None:
        self._raw_connection.commit()

    def rollback(self) -> None:
        self._raw_connection.rollback()

    def close(self) -> None:
        self._raw_connection.close()


def _database_url() -> str:
    from app.settings import settings

    return settings.database_url.strip() or "sqlite:///teamswork.db"


def database_dialect() -> str:
    url = _database_url().lower()
    if url.startswith("sqlite:///"):
        return "sqlite"
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return "postgresql"
    raise ValueError(f"Unsupported DATABASE_URL: {_database_url()}")


def _sqlite_path() -> Path:
    """Derive SQLite file path from DATABASE_URL env setting."""
    raw = _database_url()[len("sqlite:///") :]
    if raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
        return Path(raw)
    raw = raw.lstrip("./") or "teamswork.db"
    return Path(__file__).resolve().parent.parent / raw


def _postgres_dsn() -> str:
    url = _database_url()
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _translate_postgres_sql(query: str, *, append_returning_id: bool) -> str:
    sql = query.replace("?", "%s").strip().rstrip(";")
    if append_returning_id:
        sql = f"{sql} RETURNING id"
    return sql


def _should_append_returning_id(query: str) -> bool:
    normalized = query.lstrip().upper()
    return normalized.startswith("INSERT INTO ") and " RETURNING " not in normalized


def get_connection() -> DatabaseConnection:
    dialect = database_dialect()
    if dialect == "sqlite":
        conn = sqlite3.connect(str(_sqlite_path()))
        conn.execute("PRAGMA foreign_keys = ON")
        return DatabaseConnection(conn, dialect)
    return DatabaseConnection(psycopg2.connect(_postgres_dsn()), dialect)


def _schema_statements(dialect: str) -> list[str]:
    if dialect == "postgresql":
        return _POSTGRES_SCHEMA_STATEMENTS
    return _SQLITE_SCHEMA_STATEMENTS


def _table_columns(conn: DatabaseConnection, table: str) -> set[str]:
    if conn.dialect == "sqlite":
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    rows = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = ?
        ORDER BY ordinal_position
        """,
        (table,),
    ).fetchall()
    return {str(row["column_name"]) for row in rows}


def _ensure_column(conn: DatabaseConnection, table: str, column: str, definition: str) -> None:
    columns = _table_columns(conn, table)
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def _seed_rbac_defaults(conn: DatabaseConnection) -> None:
    from app.permissions import DEFAULT_PERMISSIONS, DEFAULT_ROLE_PERMISSION_KEYS, DEFAULT_ROLES

    for role in DEFAULT_ROLES:
        conn.execute(
            """
            /* no-returning-id */ INSERT INTO roles (slug, name, description, is_system)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                name = excluded.name,
                description = excluded.description
            """,
            (role["slug"], role["name"], role["description"], True),
        )

    for permission in DEFAULT_PERMISSIONS:
        conn.execute(
            """
            /* no-returning-id */ INSERT INTO permissions (key, name, description, category)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                category = excluded.category
            """,
            (permission["key"], permission["name"], permission.get("description"), permission["category"]),
        )

    for role_slug, permission_keys in DEFAULT_ROLE_PERMISSION_KEYS.items():
        for permission_key in permission_keys:
            conn.execute(
                """
                /* no-returning-id */ INSERT INTO role_permissions (role_slug, permission_key)
                VALUES (?, ?)
                ON CONFLICT(role_slug, permission_key) DO NOTHING
                """,
                (role_slug, permission_key),
            )


def init_db() -> None:
    with get_connection() as conn:
        for statement in _schema_statements(conn.dialect):
            conn.execute(statement)

        run_schema_migrations(conn, _table_columns, _ensure_column)
        _seed_rbac_defaults(conn)
