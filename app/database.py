import sqlite3
from pathlib import Path


def _sqlite_path() -> Path:
    """Derive SQLite file path from DATABASE_URL env setting.

    Supports:
      sqlite:///teamswork.db            → relative to project root
      sqlite:///./data/teamswork.db     → relative to project root
      sqlite:////absolute/path/db.db   → absolute path (Unix)
      sqlite:///C:/absolute/path/db.db → absolute path (Windows)
    Falls back to <project_root>/teamswork.db for any non-sqlite URL
    (e.g. postgresql://) so the app still starts in dev without changes.
    """
    from app.settings import settings

    url = settings.database_url
    if url.startswith("sqlite:///"):
        raw = url[len("sqlite:///"):]
        # Absolute paths: unix /abs or Windows C:/abs
        if raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
            return Path(raw)
        raw = raw.lstrip("./") or "teamswork.db"
        return Path(__file__).resolve().parent.parent / raw
    # PostgreSQL / other – SQLAlchemy migration needed; fall back to SQLite for now
    return Path(__file__).resolve().parent.parent / "teamswork.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_sqlite_path()))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                aad_object_id TEXT UNIQUE,
                role TEXT NOT NULL,
                department TEXT
            )
            """
        )

        # Lightweight migration for existing local DBs created before aad_object_id existed.
        cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "aad_object_id" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN aad_object_id TEXT")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_aad_object_id ON users(aad_object_id)")
        conn.execute(
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
            """
        )
        task_cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        if "project_id" not in task_cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN project_id INTEGER")
        if "sprint_id" not in task_cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN sprint_id INTEGER")
        if "story_points" not in task_cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN story_points INTEGER NOT NULL DEFAULT 1")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                code TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
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
            """
        )

        conn.execute(
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
            """
        )

        conn.execute(
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
            """
        )

        conn.execute(
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
            """
        )

        conn.execute(
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
            """
        )

        conn.execute(
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
            """
        )

        conn.execute(
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
            """
        )
        nq_cols = {row[1] for row in conn.execute("PRAGMA table_info(notification_queue)").fetchall()}
        if "attempts" not in nq_cols:
            conn.execute("ALTER TABLE notification_queue ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0")
        if "max_attempts" not in nq_cols:
            conn.execute("ALTER TABLE notification_queue ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 3")
        if "last_error" not in nq_cols:
            conn.execute("ALTER TABLE notification_queue ADD COLUMN last_error TEXT")
        if "next_retry_at" not in nq_cols:
            conn.execute("ALTER TABLE notification_queue ADD COLUMN next_retry_at TEXT")

        conn.execute(
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
            """
        )
        conn.execute(
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
            """
        )
        conn.execute(
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
            """
        )
