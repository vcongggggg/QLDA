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
        priority TEXT NOT NULL DEFAULT 'medium',
        labels TEXT NOT NULL DEFAULT '[]',
        checklist TEXT NOT NULL DEFAULT '[]',
        subtasks TEXT NOT NULL DEFAULT '[]',
        dependencies TEXT NOT NULL DEFAULT '[]',
        attachment_metadata TEXT NOT NULL DEFAULT '[]',
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
        type TEXT NOT NULL CHECK(type IN ('task_due_soon','task_overdue','task_comment','task_status_changed','kpi_target_warning')),
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
        project_id INTEGER NOT NULL,
        storage_path TEXT,
        created_by INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id),
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
        char_count INTEGER NOT NULL DEFAULT 0,
        token_estimate INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES rag_documents(id)
    )
    """,
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
    """,
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
    """,
]
