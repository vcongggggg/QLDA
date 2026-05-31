from app.seeding.shared import *

def _table_exists(conn: Any, table: str) -> bool:
    if conn.dialect == "sqlite":
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        return row is not None
    row = conn.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = current_schema()
          AND table_name = ?
        """,
        (table,),
    ).fetchone()
    return row is not None


def _table_columns(conn: Any, table: str) -> set[str]:
    if conn.dialect == "sqlite":
        return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    rows = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = ?
        """,
        (table,),
    ).fetchall()
    return {str(row["column_name"]) for row in rows}


def _reset_sequences(conn: Any) -> None:
    existing = [table for table in DEMO_TABLES if _table_exists(conn, table)]
    if conn.dialect == "sqlite":
        for table in existing:
            conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        return
    for table in existing:
        conn.execute(f"ALTER SEQUENCE IF EXISTS {table}_id_seq RESTART WITH 1")


def reset_demo_data(conn: Any) -> None:
    for table in DEMO_TABLES:
        if _table_exists(conn, table):
            conn.execute(f"DELETE FROM {table}")
    _reset_sequences(conn)


def _count(conn: Any, table: str) -> int:
    if not _table_exists(conn, table):
        return 0
    row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
    return int(row["c"] if row else 0)


def _summary_counts(conn: Any) -> dict[str, int]:
    tables = (
        "users",
        "departments",
        "projects",
        "sprints",
        "project_members",
        "tasks",
        "sprint_capacity_plans",
        "project_risks",
        "weekly_status_updates",
        "kpi_adjustments",
        "task_comments",
        "app_notifications",
        "notification_queue",
        "audit_logs",
        "ai_task_drafts",
        "rag_documents",
        "rag_chunks",
    )
    return {table: _count(conn, table) for table in tables}


def _placeholders(values: tuple[Any, ...] | list[Any]) -> str:
    return ", ".join("?" for _ in values)


def _validate_seed_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in {"upsert", "reset"}:
        raise ValueError("mode must be 'upsert' or 'reset'")
    return normalized


def _ensure_reset_allowed(force: bool) -> None:
    if force:
        return
    if settings.app_env not in RESET_ALLOWED_ENVS:
        raise RuntimeError(
            "Refusing demo seed reset outside local/dev/demo/test. "
            "Pass force=True only for an explicitly approved non-production reset."
        )


def _select_ids(conn: Any, table: str, where_sql: str, params: tuple[Any, ...]) -> list[int]:
    if not _table_exists(conn, table):
        return []
    rows = conn.execute(f"SELECT id FROM {table} WHERE {where_sql}", params).fetchall()
    return [int(row["id"]) for row in rows]


def _delete_by_ids(conn: Any, table: str, ids: list[int]) -> None:
    if not ids or not _table_exists(conn, table):
        return
    conn.execute(f"DELETE FROM {table} WHERE id IN ({_placeholders(ids)})", tuple(ids))


def _delete_full_demo_rag(conn: Any, project_ids: list[int] | None = None) -> None:
    if not _table_exists(conn, "rag_documents"):
        return
    source_params = tuple(FULL_DEMO_RAG_SOURCE_LABELS)
    clauses = [f"source_label IN ({_placeholders(source_params)})"]
    params: list[Any] = list(source_params)
    if project_ids:
        clauses.append(f"project_id IN ({_placeholders(project_ids)})")
        params.extend(project_ids)
        if _table_exists(conn, "rag_document_permissions"):
            conn.execute(
                f"DELETE FROM rag_document_permissions WHERE project_id IN ({_placeholders(project_ids)})",
                tuple(project_ids),
            )
    doc_ids = _select_ids(conn, "rag_documents", " OR ".join(clauses), tuple(params))
    if not doc_ids:
        return
    chunk_ids = _select_ids(conn, "rag_chunks", f"document_id IN ({_placeholders(doc_ids)})", tuple(doc_ids))
    if chunk_ids and _table_exists(conn, "rag_chunk_embeddings"):
        conn.execute(f"DELETE FROM rag_chunk_embeddings WHERE chunk_id IN ({_placeholders(chunk_ids)})", tuple(chunk_ids))
    if _table_exists(conn, "rag_document_permissions"):
        conn.execute(f"DELETE FROM rag_document_permissions WHERE document_id IN ({_placeholders(doc_ids)})", tuple(doc_ids))
    if chunk_ids:
        conn.execute(f"DELETE FROM rag_chunks WHERE id IN ({_placeholders(chunk_ids)})", tuple(chunk_ids))
    conn.execute(f"DELETE FROM rag_documents WHERE id IN ({_placeholders(doc_ids)})", tuple(doc_ids))


def _delete_full_demo_project_children(conn: Any, project_ids: dict[str, int]) -> None:
    ids = list(project_ids.values())
    if not ids:
        return
    _delete_full_demo_rag(conn, ids)
    task_ids = _select_ids(conn, "tasks", f"project_id IN ({_placeholders(ids)})", tuple(ids))
    sprint_ids = _select_ids(conn, "sprints", f"project_id IN ({_placeholders(ids)})", tuple(ids))
    if task_ids and _table_exists(conn, "task_comments"):
        conn.execute(f"DELETE FROM task_comments WHERE task_id IN ({_placeholders(task_ids)})", tuple(task_ids))
    if task_ids and _table_exists(conn, "app_notifications"):
        conn.execute(
            f"DELETE FROM app_notifications WHERE entity_type = 'task' AND entity_id IN ({_placeholders(task_ids)})",
            tuple(task_ids),
        )
    if task_ids and _table_exists(conn, "task_ai_details"):
        conn.execute(f"DELETE FROM task_ai_details WHERE task_id IN ({_placeholders(task_ids)})", tuple(task_ids))
    _delete_by_ids(conn, "tasks", task_ids)
    if sprint_ids and _table_exists(conn, "sprint_capacity_plans"):
        conn.execute(f"DELETE FROM sprint_capacity_plans WHERE sprint_id IN ({_placeholders(sprint_ids)})", tuple(sprint_ids))
    if _table_exists(conn, "weekly_status_updates"):
        conn.execute(f"DELETE FROM weekly_status_updates WHERE project_id IN ({_placeholders(ids)})", tuple(ids))
    if _table_exists(conn, "project_risks"):
        conn.execute(f"DELETE FROM project_risks WHERE project_id IN ({_placeholders(ids)})", tuple(ids))
    if _table_exists(conn, "project_members"):
        conn.execute(f"DELETE FROM project_members WHERE project_id IN ({_placeholders(ids)})", tuple(ids))
    _delete_by_ids(conn, "sprints", sprint_ids)


def _delete_full_demo_global_children(conn: Any) -> None:
    if _table_exists(conn, "kpi_adjustments"):
        conn.execute("DELETE FROM kpi_adjustments WHERE reason LIKE ?", (f"%[{DEMO_NAMESPACE}]%",))
    if _table_exists(conn, "ai_task_drafts"):
        if _table_exists(conn, "task_ai_details"):
            conn.execute(
                f"""
                DELETE FROM task_ai_details
                WHERE source_ai_draft_id IN (
                    SELECT id FROM ai_task_drafts WHERE source_name IN ({_placeholders(FULL_DEMO_AI_SOURCE_NAMES)})
                )
                """,
                FULL_DEMO_AI_SOURCE_NAMES,
            )
        conn.execute(
            f"DELETE FROM ai_task_drafts WHERE source_name IN ({_placeholders(FULL_DEMO_AI_SOURCE_NAMES)})",
            FULL_DEMO_AI_SOURCE_NAMES,
        )
    if _table_exists(conn, "audit_logs"):
        conn.execute("DELETE FROM audit_logs WHERE detail LIKE ?", (f"%[{DEMO_NAMESPACE}]%",))
    if _table_exists(conn, "notification_queue"):
        conn.execute("DELETE FROM notification_queue WHERE payload LIKE ?", (f"%{DEMO_NAMESPACE}%",))


def _full_demo_project_ids(conn: Any) -> dict[str, int]:
    rows = conn.execute(
        f"SELECT id, name FROM projects WHERE name IN ({_placeholders(DEMO_PROJECT_NAMES)})",
        DEMO_PROJECT_NAMES,
    ).fetchall()
    return {str(row["name"]): int(row["id"]) for row in rows}
