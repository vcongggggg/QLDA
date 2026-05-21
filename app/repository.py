from datetime import datetime, timedelta, timezone
import json
import re
from typing import Any

from app.database import get_connection


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_SECRET_PATTERNS = (
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"(client[_-]?secret|api[_-]?key|token|authorization)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"webhook[_-]?url\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\b\S*webhook[_-]?url\S*\b", re.IGNORECASE),
)


def _redact_operational_text(value: str | None, max_length: int = 180) -> str | None:
    if not value:
        return None
    cleaned = str(value).replace("\r", " ").replace("\n", " ")
    traceback_at = cleaned.lower().find("traceback")
    if traceback_at >= 0:
        cleaned = cleaned[:traceback_at] + "provider error"
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub("[redacted]", cleaned)
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > max_length:
        cleaned = cleaned[: max_length - 3].rstrip() + "..."
    return cleaned or "redacted"


def create_user(
    full_name: str,
    email: str,
    role: str,
    department: str | None,
    aad_object_id: str | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (full_name, email, aad_object_id, role, department) VALUES (?, ?, ?, ?, ?)",
            (full_name, email, aad_object_id, role, department),
        )
        user_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row)


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_user_by_aad_object_id(aad_object_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE aad_object_id = ?", (aad_object_id,)).fetchone()
    return dict(row) if row else None


def upsert_user_from_aad(aad_object_id: str, display_name: str | None, email: str | None) -> dict[str, Any]:
    existing = get_user_by_aad_object_id(aad_object_id)
    if existing:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE users
                SET full_name = COALESCE(?, full_name),
                    email = COALESCE(?, email)
                WHERE id = ?
                """,
                (display_name, email, existing["id"]),
            )
            row = conn.execute("SELECT * FROM users WHERE id = ?", (existing["id"],)).fetchone()
        return dict(row)

    safe_email = email or f"{aad_object_id}@aad.example.com"
    safe_name = display_name or "Teams User"
    return create_user(
        full_name=safe_name,
        email=safe_email,
        aad_object_id=aad_object_id,
        role="staff",
        department="Unassigned",
    )


def list_users() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def list_roles() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM roles ORDER BY slug").fetchall()
    return [dict(r) for r in rows]


def list_permissions() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM permissions ORDER BY category, key").fetchall()
    return [dict(r) for r in rows]


def role_exists(role_slug: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT slug FROM roles WHERE slug = ?", (role_slug,)).fetchone()
    return row is not None


def permission_keys_exist(permission_keys: list[str]) -> bool:
    if not permission_keys:
        return True
    placeholders = ",".join(["?"] * len(permission_keys))
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT key FROM permissions WHERE key IN ({placeholders})",
            tuple(permission_keys),
        ).fetchall()
    return {str(row["key"]) for row in rows} == set(permission_keys)


def list_permissions_for_role(role_slug: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.*
            FROM permissions p
            JOIN role_permissions rp ON rp.permission_key = p.key
            WHERE rp.role_slug = ?
            ORDER BY p.category, p.key
            """,
            (role_slug,),
        ).fetchall()
    return [dict(r) for r in rows]


def replace_role_permissions(role_slug: str, permission_keys: list[str]) -> list[dict[str, Any]]:
    unique_keys = sorted(set(permission_keys))
    with get_connection() as conn:
        conn.execute("DELETE FROM role_permissions WHERE role_slug = ?", (role_slug,))
        for permission_key in unique_keys:
            conn.execute(
                "/* no-returning-id */ INSERT INTO role_permissions (role_slug, permission_key) VALUES (?, ?)",
                (role_slug, permission_key),
            )
    return list_permissions_for_role(role_slug)


def role_has_permission(role_slug: str, permission_key: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM role_permissions
            WHERE role_slug = ? AND permission_key = ?
            LIMIT 1
            """,
            (role_slug, permission_key),
        ).fetchone()
    return row is not None


def count_users() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    return int(row[0] if row else 0)


def user_exists(user_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    return row is not None


def create_task(
    title: str,
    description: str | None,
    assignee_id: int,
    project_id: int | None,
    sprint_id: int | None,
    story_points: int,
    difficulty: str,
    deadline_iso: str,
) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (title, description, assignee_id, project_id, sprint_id, story_points, difficulty, status, deadline, completed_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'todo', ?, NULL, ?, ?)
            """,
            (title, description, assignee_id, project_id, sprint_id, story_points, difficulty, deadline_iso, now, now),
        )
        task_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row)


def list_tasks(
    assignee_id: int | None = None,
    status: str | None = None,
    project_id: int | None = None,
    sprint_id: int | None = None,
    overdue: bool | None = None,
    keyword: str | None = None,
    deadline_from: str | None = None,
    deadline_to: str | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM tasks WHERE 1=1"
    params: list[Any] = []
    if assignee_id is not None:
        query += " AND assignee_id = ?"
        params.append(assignee_id)
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if project_id is not None:
        query += " AND project_id = ?"
        params.append(project_id)
    if sprint_id is not None:
        query += " AND sprint_id = ?"
        params.append(sprint_id)
    if overdue is True:
        query += " AND status != 'done' AND deadline < ?"
        params.append(_now_iso())
    elif overdue is False:
        query += " AND (status = 'done' OR deadline >= ?)"
        params.append(_now_iso())
    if keyword:
        query += " AND (LOWER(title) LIKE ? OR LOWER(COALESCE(description, '')) LIKE ?)"
        term = f"%{keyword.lower()}%"
        params.extend([term, term])
    if deadline_from is not None:
        query += " AND deadline >= ?"
        params.append(deadline_from)
    if deadline_to is not None:
        query += " AND deadline <= ?"
        params.append(deadline_to)
    query += " ORDER BY deadline ASC"
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def update_task_status(task_id: int, status: str) -> dict[str, Any] | None:
    now = _now_iso()
    completed_at = now if status == "done" else None
    with get_connection() as conn:
        exists = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE tasks SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?",
            (status, completed_at, now, task_id),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row)


def get_task_by_id(task_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def get_task_detail_by_id(task_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                t.*,
                u.full_name AS assignee_name,
                p.name AS project_name,
                s.name AS sprint_name
            FROM tasks t
            JOIN users u ON u.id = t.assignee_id
            LEFT JOIN projects p ON p.id = t.project_id
            LEFT JOIN sprints s ON s.id = t.sprint_id
            WHERE t.id = ?
            """,
            (task_id,),
        ).fetchone()
    return dict(row) if row else None


def create_task_comment(task_id: int, author_user_id: int, body: str) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO task_comments (task_id, author_user_id, body, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, author_user_id, body, _now_iso()),
        )
        row = conn.execute(
            """
            SELECT tc.*, u.full_name AS author_name
            FROM task_comments tc
            JOIN users u ON u.id = tc.author_user_id
            WHERE tc.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row)


def list_task_comments(task_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT tc.*, u.full_name AS author_name
            FROM task_comments tc
            JOIN users u ON u.id = tc.author_user_id
            WHERE tc.task_id = ?
            ORDER BY tc.id ASC
            """,
            (task_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_task_activity_logs(task_id: int, limit: int = 100) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT al.*, u.full_name AS actor_name
            FROM audit_logs al
            LEFT JOIN users u ON u.id = al.actor_user_id
            WHERE al.entity = 'task' AND al.entity_id = ?
            ORDER BY al.id DESC
            LIMIT ?
            """,
            (task_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def create_app_notification(
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    entity_type: str,
    entity_id: int,
) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO app_notifications
            (user_id, type, title, message, entity_type, entity_id, is_read, created_at, read_at)
            VALUES (?, ?, ?, ?, ?, ?, FALSE, ?, NULL)
            """,
            (user_id, notification_type, title, message, entity_type, entity_id, _now_iso()),
        )
        row = conn.execute("SELECT * FROM app_notifications WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def list_app_notifications(user_id: int, unread_only: bool = False, limit: int = 50) -> list[dict[str, Any]]:
    query = "SELECT * FROM app_notifications WHERE user_id = ?"
    params: list[Any] = [user_id]
    if unread_only:
        query += " AND is_read = FALSE"
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def mark_app_notification_read(notification_id: int, user_id: int) -> dict[str, Any] | None:
    now = _now_iso()
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM app_notifications WHERE id = ? AND user_id = ?",
            (notification_id, user_id),
        ).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE app_notifications
            SET is_read = TRUE,
                read_at = COALESCE(read_at, ?)
            WHERE id = ? AND user_id = ?
            """,
            (now, notification_id, user_id),
        )
        row = conn.execute("SELECT * FROM app_notifications WHERE id = ?", (notification_id,)).fetchone()
    return dict(row) if row else None


def mark_all_app_notifications_read(user_id: int) -> int:
    now = _now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE app_notifications
            SET is_read = TRUE,
                read_at = COALESCE(read_at, ?)
            WHERE user_id = ? AND is_read = FALSE
            """,
            (now, user_id),
        )
    return int(cursor.rowcount)


def count_unread_app_notifications(user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM app_notifications WHERE user_id = ? AND is_read = FALSE",
            (user_id,),
        ).fetchone()
    return int(row["c"] if row else 0)


def notification_exists_for_event(
    user_id: int,
    notification_type: str,
    entity_type: str,
    entity_id: int,
    window_start_iso: str,
    window_end_iso: str,
) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id
            FROM app_notifications
            WHERE user_id = ?
              AND type = ?
              AND entity_type = ?
              AND entity_id = ?
              AND created_at >= ?
              AND created_at < ?
            LIMIT 1
            """,
            (user_id, notification_type, entity_type, entity_id, window_start_iso, window_end_iso),
        ).fetchone()
    return row is not None


def all_tasks_with_users() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT t.*, u.full_name AS assignee_name
            FROM tasks t
            JOIN users u ON u.id = t.assignee_id
            ORDER BY t.id
            """
        ).fetchall()
    return [dict(r) for r in rows]


def create_audit_log(
    actor_user_id: int | None,
    action: str,
    entity: str,
    entity_id: int | None,
    detail: str | None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs (actor_user_id, action, entity, entity_id, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (actor_user_id, action, entity, entity_id, detail, _now_iso()),
        )


def _decode_ai_task_draft(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    raw_tasks = item.pop("generated_tasks", "[]")
    try:
        item["items"] = json.loads(raw_tasks or "[]")
    except json.JSONDecodeError:
        item["items"] = []
    item["item_count"] = len(item["items"])
    return item


def create_ai_task_draft(
    source_type: str,
    source_summary: str | None,
    source_name: str | None,
    generated_tasks: list[dict[str, Any]],
    created_by: int,
) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO ai_task_drafts
            (source_type, source_summary, source_name, generated_tasks, status, reviewer_id, reviewed_at, imported_at, review_note, edit_reason, created_by, created_at)
            VALUES (?, ?, ?, ?, 'draft', NULL, NULL, NULL, NULL, NULL, ?, ?)
            """,
            (
                source_type,
                source_summary,
                source_name,
                json.dumps(generated_tasks, ensure_ascii=True),
                created_by,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM ai_task_drafts WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _decode_ai_task_draft(dict(row))


def list_ai_task_drafts(status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    query = "SELECT * FROM ai_task_drafts"
    params: list[Any] = []
    if status is not None:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [_decode_ai_task_draft(dict(row)) for row in rows]


def get_ai_task_draft(draft_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM ai_task_drafts WHERE id = ?", (draft_id,)).fetchone()
    return _decode_ai_task_draft(dict(row)) if row else None


def review_ai_task_draft(
    draft_id: int,
    generated_tasks: list[dict[str, Any]],
    reviewer_id: int,
    review_note: str | None,
    edit_reason: str | None,
) -> dict[str, Any] | None:
    now = _now_iso()
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM ai_task_drafts WHERE id = ?", (draft_id,)).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE ai_task_drafts
            SET generated_tasks = ?,
                status = 'reviewed',
                reviewer_id = ?,
                reviewed_at = ?,
                review_note = ?,
                edit_reason = ?
            WHERE id = ?
            """,
            (
                json.dumps(generated_tasks, ensure_ascii=True),
                reviewer_id,
                now,
                review_note,
                edit_reason,
                draft_id,
            ),
        )
        row = conn.execute("SELECT * FROM ai_task_drafts WHERE id = ?", (draft_id,)).fetchone()
    return _decode_ai_task_draft(dict(row)) if row else None


def mark_ai_task_draft_imported(draft_id: int) -> dict[str, Any] | None:
    now = _now_iso()
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM ai_task_drafts WHERE id = ?", (draft_id,)).fetchone()
        if not existing:
            return None
        conn.execute(
            "UPDATE ai_task_drafts SET status = 'imported', imported_at = ? WHERE id = ?",
            (now, draft_id),
        )
        row = conn.execute("SELECT * FROM ai_task_drafts WHERE id = ?", (draft_id,)).fetchone()
    return _decode_ai_task_draft(dict(row)) if row else None


def create_rag_document(
    title: str,
    source_label: str | None,
    project_id: int,
    content_chunks: list[Any],
    created_by: int,
    storage_path: str | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO rag_documents (title, source_label, project_id, storage_path, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, source_label, project_id, storage_path, created_by, _now_iso()),
        )
        document_id = int(cursor.lastrowid)
        for index, chunk in enumerate(content_chunks):
            content = str(getattr(chunk, "content", chunk))
            char_count = int(getattr(chunk, "char_count", len(content)))
            token_estimate = int(getattr(chunk, "token_estimate", max(1, -(-char_count // 4))))
            conn.execute(
                """
                INSERT INTO rag_chunks
                (document_id, content, source_label, chunk_index, char_count, token_estimate, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, content, source_label, index, char_count, token_estimate, _now_iso()),
            )
        conn.execute(
            """
            /* no-returning-id */ INSERT INTO rag_document_permissions
            (document_id, project_id, user_id, role_slug, access_level, created_at)
            VALUES (?, ?, NULL, NULL, 'query', ?)
            ON CONFLICT(document_id, project_id, user_id, role_slug) DO NOTHING
            """,
            (document_id, project_id, _now_iso()),
        )
        row = conn.execute("SELECT * FROM rag_documents WHERE id = ?", (document_id,)).fetchone()
    item = dict(row)
    item["chunk_count"] = len(content_chunks)
    return item


def _rag_acl_clause(current_user: dict[str, Any] | None) -> tuple[str, list[Any]]:
    if current_user is None:
        return "1=1", []
    user_id = int(current_user["id"])
    role = str(current_user.get("role") or "")
    if role in {"admin", "hr"}:
        return "d.project_id IS NOT NULL", []
    return (
        """
        d.project_id IS NOT NULL
        AND EXISTS (
            SELECT 1
            FROM rag_document_permissions rdp
            JOIN projects p ON p.id = rdp.project_id
            LEFT JOIN project_members pm ON pm.project_id = rdp.project_id AND pm.user_id = ?
            WHERE rdp.document_id = d.id
              AND rdp.access_level IN ('query', 'manage')
              AND (
                p.manager_id = ?
                OR pm.id IS NOT NULL
                OR rdp.user_id = ?
                OR rdp.role_slug = ?
              )
        )
        """,
        [user_id, user_id, user_id, role],
    )


def list_rag_documents(current_user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    acl_sql, params = _rag_acl_clause(current_user)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT d.*, COUNT(c.id) AS chunk_count
            FROM rag_documents d
            LEFT JOIN rag_chunks c ON c.document_id = d.id
            WHERE {acl_sql}
            GROUP BY d.id, d.title, d.source_label, d.project_id, d.storage_path, d.created_by, d.created_at
            ORDER BY d.id DESC
            """,
            tuple(params),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_rag_document(document_id: int, current_user: dict[str, Any] | None = None) -> bool:
    acl_sql, params = _rag_acl_clause(current_user)
    with get_connection() as conn:
        existing = conn.execute(
            f"SELECT d.id FROM rag_documents d WHERE d.id = ? AND {acl_sql}",
            (document_id, *params),
        ).fetchone()
        if not existing:
            return False
        chunk_rows = conn.execute("SELECT id FROM rag_chunks WHERE document_id = ?", (document_id,)).fetchall()
        for row in chunk_rows:
            conn.execute("DELETE FROM rag_chunk_embeddings WHERE chunk_id = ?", (row["id"],))
        conn.execute("DELETE FROM rag_document_permissions WHERE document_id = ?", (document_id,))
        conn.execute("DELETE FROM rag_chunks WHERE document_id = ?", (document_id,))
        conn.execute("DELETE FROM rag_documents WHERE id = ?", (document_id,))
    return True


def list_rag_chunks(limit: int = 500, current_user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    acl_sql, params = _rag_acl_clause(current_user)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT c.*, d.title AS document_title, d.project_id AS project_id
            FROM rag_chunks c
            JOIN rag_documents d ON d.id = c.document_id
            WHERE {acl_sql}
            ORDER BY c.id DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def list_rag_chunks_for_document(document_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.*
            FROM rag_chunks c
            WHERE c.document_id = ?
            ORDER BY c.chunk_index ASC
            """,
            (document_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def store_rag_chunk_embedding(
    chunk_id: int,
    provider: str,
    model: str,
    dim: int,
    version: str,
    embedding: list[float],
) -> None:
    import json

    with get_connection() as conn:
        if conn.dialect == "postgresql":
            vector_value = "[" + ",".join(str(float(value)) for value in embedding) + "]"
            conn.execute(
                """
                /* no-returning-id */ INSERT INTO rag_chunk_embeddings
                (chunk_id, provider, model, dim, version, embedding, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id, provider, model, version) DO UPDATE SET
                    dim = excluded.dim,
                    embedding = excluded.embedding,
                    created_at = excluded.created_at
                """,
                (chunk_id, provider, model, dim, version, vector_value, _now_iso()),
            )
            return
        conn.execute(
            """
            /* no-returning-id */ INSERT INTO rag_chunk_embeddings
            (chunk_id, provider, model, dim, version, embedding_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id, provider, model, version) DO UPDATE SET
                dim = excluded.dim,
                embedding_json = excluded.embedding_json,
                created_at = excluded.created_at
            """,
            (chunk_id, provider, model, dim, version, json.dumps(embedding, ensure_ascii=True), _now_iso()),
        )


def search_rag_chunks_by_embedding(
    embedding: list[float],
    provider: str,
    model: str,
    version: str,
    limit: int,
    current_user: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    vector_value = "[" + ",".join(str(float(value)) for value in embedding) + "]"
    acl_sql, params = _rag_acl_clause(current_user)
    with get_connection() as conn:
        if conn.dialect != "postgresql":
            return []
        rows = conn.execute(
            f"""
            SELECT
                c.*,
                d.title AS document_title,
                d.project_id AS project_id,
                (e.embedding <=> ?::vector) AS distance
            FROM rag_chunk_embeddings e
            JOIN rag_chunks c ON c.id = e.chunk_id
            JOIN rag_documents d ON d.id = c.document_id
            WHERE e.provider = ?
              AND e.model = ?
              AND e.version = ?
              AND {acl_sql}
            ORDER BY e.embedding <=> ?::vector ASC
            LIMIT ?
            """,
            (vector_value, provider, model, version, *params, vector_value, limit),
        ).fetchall()
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["semantic_score"] = max(0.0, 1.0 - float(item.pop("distance") or 1.0))
        output.append(item)
    return output


def list_audit_logs(
    limit: int = 100,
    actor_id: int | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    keyword: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT al.*, u.full_name AS actor_name
        FROM audit_logs al
        LEFT JOIN users u ON u.id = al.actor_user_id
        WHERE 1=1
    """
    params: list[Any] = []
    if actor_id is not None:
        query += " AND al.actor_user_id = ?"
        params.append(actor_id)
    if action:
        query += " AND al.action = ?"
        params.append(action)
    if entity_type:
        query += " AND al.entity = ?"
        params.append(entity_type)
    if date_from:
        query += " AND al.created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND al.created_at <= ?"
        params.append(date_to)
    if keyword:
        query += """
            AND (
                LOWER(COALESCE(al.detail, '')) LIKE ?
                OR LOWER(al.action) LIKE ?
                OR LOWER(al.entity) LIKE ?
                OR LOWER(COALESCE(u.full_name, '')) LIKE ?
            )
        """
        term = f"%{keyword.lower()}%"
        params.extend([term, term, term, term])
    query += " ORDER BY al.id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["detail"] = _redact_operational_text(item.get("detail"))
        output.append(item)
    return output


def create_kpi_adjustment(
    user_id: int,
    month: str,
    points: float,
    reason: str,
    created_by: int,
) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO kpi_adjustments (user_id, month, points, reason, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, month, points, reason, created_by, _now_iso()),
        )
        item_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM kpi_adjustments WHERE id = ?", (item_id,)).fetchone()
    return dict(row)


def list_kpi_adjustments_by_month(month: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT ka.*, u.full_name AS user_name
            FROM kpi_adjustments ka
            JOIN users u ON u.id = ka.user_id
            WHERE ka.month = ?
            ORDER BY ka.id ASC
            """,
            (month,),
        ).fetchall()
    return [dict(r) for r in rows]


def department_exists(department_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM departments WHERE id = ?", (department_id,)).fetchone()
    return row is not None


def create_department(name: str, code: str) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO departments (name, code, created_at) VALUES (?, ?, ?)",
            (name, code.upper(), _now_iso()),
        )
        dep_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM departments WHERE id = ?", (dep_id,)).fetchone()
    return dict(row)


def list_departments() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM departments ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def project_exists(project_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    return row is not None


def create_project(
    name: str,
    description: str | None,
    department_id: int | None,
    manager_id: int | None,
    start_date: str | None,
    end_date: str | None,
    status: str,
) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO projects (name, description, department_id, manager_id, start_date, end_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, description, department_id, manager_id, start_date, end_date, status, _now_iso()),
        )
        project_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return dict(row)


def list_projects(status: str | None = None, department_id: int | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM projects WHERE 1=1"
    params: list[Any] = []
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if department_id is not None:
        query += " AND department_id = ?"
        params.append(department_id)
    query += " ORDER BY id"
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def get_project_by_id(project_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return dict(row) if row else None


def is_project_member(project_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, user_id),
        ).fetchone()
    return row is not None


def add_project_member(project_id: int, user_id: int, role: str) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO project_members (project_id, user_id, role, joined_at)
            VALUES (?, ?, ?, ?)
            """,
            (project_id, user_id, role, _now_iso()),
        )
        item_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM project_members WHERE id = ?", (item_id,)).fetchone()
    return dict(row)


def list_project_members(project_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM project_members WHERE project_id = ? ORDER BY id",
            (project_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def create_sprint(
    project_id: int,
    name: str,
    goal: str | None,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO sprints (project_id, name, goal, start_date, end_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'planned', ?)
            """,
            (project_id, name, goal, start_date, end_date, _now_iso()),
        )
        sprint_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM sprints WHERE id = ?", (sprint_id,)).fetchone()
    return dict(row)


def sprint_exists(sprint_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM sprints WHERE id = ?", (sprint_id,)).fetchone()
    return row is not None


def get_sprint_by_id(sprint_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM sprints WHERE id = ?", (sprint_id,)).fetchone()
    return dict(row) if row else None


def update_sprint_status(sprint_id: int, status: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        exists = conn.execute("SELECT id FROM sprints WHERE id = ?", (sprint_id,)).fetchone()
        if not exists:
            return None
        conn.execute("UPDATE sprints SET status = ? WHERE id = ?", (status, sprint_id))
        row = conn.execute("SELECT * FROM sprints WHERE id = ?", (sprint_id,)).fetchone()
    return dict(row)


def list_sprints(project_id: int, status: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM sprints WHERE project_id = ?"
    params: list[Any] = [project_id]
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY id"
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def assign_tasks_to_sprint(project_id: int, sprint_id: int, task_ids: list[int]) -> int:
    if not task_ids:
        return 0
    placeholders = ",".join(["?"] * len(task_ids))
    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            UPDATE tasks
            SET sprint_id = ?, updated_at = ?
            WHERE id IN ({placeholders}) AND project_id = ?
            """,
            (sprint_id, _now_iso(), *task_ids, project_id),
        )
    return int(cursor.rowcount)


def project_progress(project_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS total_tasks,
                SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done_tasks,
                SUM(CASE WHEN status != 'done' AND deadline < ? THEN 1 ELSE 0 END) AS overdue_tasks,
                SUM(story_points) AS total_story_points,
                SUM(CASE WHEN status = 'done' THEN story_points ELSE 0 END) AS completed_story_points
            FROM tasks
            WHERE project_id = ?
            """,
            (_now_iso(), project_id),
        ).fetchone()
    total_tasks = int(totals["total_tasks"] or 0)
    done_tasks = int(totals["done_tasks"] or 0)
    overdue_tasks = int(totals["overdue_tasks"] or 0)
    total_story_points = int(totals["total_story_points"] or 0)
    completed_story_points = int(totals["completed_story_points"] or 0)
    completion_rate = round((done_tasks / total_tasks) * 100, 2) if total_tasks else 0.0
    return {
        "project_id": project_id,
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "overdue_tasks": overdue_tasks,
        "completion_rate": completion_rate,
        "total_story_points": total_story_points,
        "completed_story_points": completed_story_points,
    }


def sprint_burndown_points(sprint_id: int) -> list[dict[str, Any]]:
    sprint = get_sprint_by_id(sprint_id)
    if not sprint:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT story_points, completed_at
            FROM tasks
            WHERE sprint_id = ?
            """,
            (sprint_id,),
        ).fetchall()

    total_points = sum(int(r["story_points"] or 0) for r in rows)
    completed_points = 0
    points: list[dict[str, Any]] = []

    start = datetime.fromisoformat(sprint["start_date"]).date()
    end = datetime.fromisoformat(sprint["end_date"]).date()
    day = start
    while day <= end:
        for r in rows:
            completed_at = r["completed_at"]
            if completed_at:
                done_day = datetime.fromisoformat(completed_at).date()
                if done_day == day:
                    completed_points += int(r["story_points"] or 0)
        remaining = max(total_points - completed_points, 0)
        points.append({"date": day.isoformat(), "remaining_points": remaining})
        day = day.fromordinal(day.toordinal() + 1)

    return points


def upsert_sprint_capacity(
    sprint_id: int,
    user_id: int,
    capacity_hours: float,
    allocated_hours: float,
) -> dict[str, Any]:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM sprint_capacity_plans WHERE sprint_id = ? AND user_id = ?",
            (sprint_id, user_id),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE sprint_capacity_plans
                SET capacity_hours = ?, allocated_hours = ?
                WHERE id = ?
                """,
                (capacity_hours, allocated_hours, existing["id"]),
            )
            row = conn.execute(
                "SELECT * FROM sprint_capacity_plans WHERE id = ?",
                (existing["id"],),
            ).fetchone()
            return dict(row)

        cursor = conn.execute(
            """
            INSERT INTO sprint_capacity_plans (sprint_id, user_id, capacity_hours, allocated_hours, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sprint_id, user_id, capacity_hours, allocated_hours, _now_iso()),
        )
        row = conn.execute(
            "SELECT * FROM sprint_capacity_plans WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row)


def list_sprint_capacities(sprint_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM sprint_capacity_plans WHERE sprint_id = ? ORDER BY id",
            (sprint_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_sprint_workload_warnings(sprint_id: int, user_id: int | None = None) -> list[dict[str, Any]]:
    sprint = get_sprint_by_id(sprint_id)
    if not sprint:
        return []

    task_query = """
        SELECT
            t.assignee_id AS user_id,
            u.full_name AS user_name,
            SUM(t.story_points) AS workload_points,
            COUNT(*) AS open_task_count,
            SUM(CASE WHEN t.deadline < ? THEN 1 ELSE 0 END) AS overdue_task_count
        FROM tasks t
        JOIN users u ON u.id = t.assignee_id
        WHERE t.sprint_id = ?
          AND t.status != 'done'
    """
    task_params: list[Any] = [_now_iso(), sprint_id]
    if user_id is not None:
        task_query += " AND t.assignee_id = ?"
        task_params.append(user_id)
    task_query += " GROUP BY t.assignee_id, u.full_name"

    capacity_query = """
        SELECT
            scp.user_id,
            u.full_name AS user_name,
            scp.capacity_hours AS capacity_points
        FROM sprint_capacity_plans scp
        JOIN users u ON u.id = scp.user_id
        WHERE scp.sprint_id = ?
    """
    capacity_params: list[Any] = [sprint_id]
    if user_id is not None:
        capacity_query += " AND scp.user_id = ?"
        capacity_params.append(user_id)

    rows_by_user: dict[int, dict[str, Any]] = {}
    with get_connection() as conn:
        task_rows = conn.execute(task_query, tuple(task_params)).fetchall()
        capacity_rows = conn.execute(capacity_query, tuple(capacity_params)).fetchall()

    for row in capacity_rows:
        uid = int(row["user_id"])
        rows_by_user[uid] = {
            "user_id": uid,
            "user_name": row["user_name"],
            "sprint_id": int(sprint["id"]),
            "sprint_name": sprint["name"],
            "workload_points": 0,
            "capacity_points": float(row["capacity_points"]) if row["capacity_points"] is not None else None,
            "open_task_count": 0,
            "overdue_task_count": 0,
        }

    for row in task_rows:
        uid = int(row["user_id"])
        item = rows_by_user.setdefault(
            uid,
            {
                "user_id": uid,
                "user_name": row["user_name"],
                "sprint_id": int(sprint["id"]),
                "sprint_name": sprint["name"],
                "workload_points": 0,
                "capacity_points": None,
                "open_task_count": 0,
                "overdue_task_count": 0,
            },
        )
        item["workload_points"] = int(row["workload_points"] or 0)
        item["open_task_count"] = int(row["open_task_count"] or 0)
        item["overdue_task_count"] = int(row["overdue_task_count"] or 0)

    output: list[dict[str, Any]] = []
    for item in rows_by_user.values():
        capacity_points = item["capacity_points"]
        overloaded = capacity_points is not None and item["workload_points"] > capacity_points
        overdue_count = int(item["overdue_task_count"] or 0)
        reasons: list[str] = []
        if overloaded:
            reasons.append("workload exceeds capacity")
        if overdue_count == 1:
            reasons.append("1 overdue open task")
        elif overdue_count > 1:
            reasons.append(f"{overdue_count} overdue open tasks")
        risk_level = "high" if overloaded and overdue_count > 0 else "medium" if overloaded or overdue_count > 0 else "low"
        output.append(
            {
                **item,
                "overloaded": overloaded,
                "risk_level": risk_level,
                "reasons": reasons,
            }
        )

    risk_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(output, key=lambda item: (risk_order.get(str(item["risk_level"]), 3), item["user_name"]))


def sprint_velocity_history(project_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        sprints = conn.execute(
            "SELECT id, name, status FROM sprints WHERE project_id = ? ORDER BY id",
            (project_id,),
        ).fetchall()

    history: list[dict[str, Any]] = []
    with get_connection() as conn:
        for s in sprints:
            metrics = conn.execute(
                """
                SELECT
                    SUM(story_points) AS planned_story_points,
                    SUM(CASE WHEN status = 'done' THEN story_points ELSE 0 END) AS completed_story_points
                FROM tasks
                WHERE sprint_id = ?
                """,
                (s["id"],),
            ).fetchone()
            history.append(
                {
                    "sprint_id": int(s["id"]),
                    "sprint_name": s["name"],
                    "status": s["status"],
                    "planned_story_points": int(metrics["planned_story_points"] or 0),
                    "completed_story_points": int(metrics["completed_story_points"] or 0),
                }
            )
    return history


def create_project_risk(
    project_id: int,
    title: str,
    description: str | None,
    probability: str,
    impact: str,
    mitigation_plan: str | None,
    owner_user_id: int | None,
    status: str,
) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO project_risks
            (project_id, title, description, probability, impact, mitigation_plan, owner_user_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                title,
                description,
                probability,
                impact,
                mitigation_plan,
                owner_user_id,
                status,
                _now_iso(),
            ),
        )
        row = conn.execute("SELECT * FROM project_risks WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def list_project_risks(project_id: int, status: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM project_risks WHERE project_id = ?"
    params: list[Any] = [project_id]
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY id DESC"
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def create_weekly_status_update(
    project_id: int,
    sprint_id: int | None,
    week_label: str,
    progress_percent: float,
    rag_status: str,
    summary: str,
    next_steps: str | None,
    blocker: str | None,
    created_by: int,
) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO weekly_status_updates
            (project_id, sprint_id, week_label, progress_percent, rag_status, summary, next_steps, blocker, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                sprint_id,
                week_label,
                progress_percent,
                rag_status,
                summary,
                next_steps,
                blocker,
                created_by,
                _now_iso(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM weekly_status_updates WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row)


def list_weekly_status_updates(project_id: int, limit: int = 20) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM weekly_status_updates
            WHERE project_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (project_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_teams_conversation_ref(
    user_id: int | None,
    aad_object_id: str | None,
    conversation_id: str,
    service_url: str | None,
    tenant_id: str | None,
    channel_id: str | None,
) -> dict[str, Any]:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM teams_conversation_refs WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE teams_conversation_refs
                SET user_id = ?, aad_object_id = ?, service_url = ?, tenant_id = ?, channel_id = ?
                WHERE id = ?
                """,
                (user_id, aad_object_id, service_url, tenant_id, channel_id, existing["id"]),
            )
            row = conn.execute(
                "SELECT * FROM teams_conversation_refs WHERE id = ?",
                (existing["id"],),
            ).fetchone()
            return dict(row)

        cursor = conn.execute(
            """
            INSERT INTO teams_conversation_refs
            (user_id, aad_object_id, conversation_id, service_url, tenant_id, channel_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, aad_object_id, conversation_id, service_url, tenant_id, channel_id, _now_iso()),
        )
        row = conn.execute(
            "SELECT * FROM teams_conversation_refs WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row)


def list_teams_conversation_refs(user_id: int | None = None, limit: int = 20) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if user_id is None:
            rows = conn.execute(
                "SELECT * FROM teams_conversation_refs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM teams_conversation_refs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]


def queue_notification(
    user_id: int | None,
    channel: str,
    payload: dict,
    max_attempts: int = 3,
) -> dict[str, Any]:
    if max_attempts < 1:
        max_attempts = 1
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO notification_queue (user_id, channel, payload, status, attempts, max_attempts, last_error, next_retry_at, created_at)
            VALUES (?, ?, ?, 'queued', 0, ?, NULL, NULL, ?)
            """,
            (user_id, channel, json.dumps(payload, ensure_ascii=True), max_attempts, _now_iso()),
        )
        row = conn.execute("SELECT * FROM notification_queue WHERE id = ?", (cursor.lastrowid,)).fetchone()
    item = dict(row)
    item["payload"] = json.loads(item["payload"])
    return item


def list_notifications(status: str = "queued", limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if status == "all":
            rows = conn.execute(
                "SELECT * FROM notification_queue ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notification_queue WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit),
            ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        item["payload"] = json.loads(item["payload"])
        out.append(item)
    return out


def count_notifications_by_status() -> dict[str, int]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS c
            FROM notification_queue
            WHERE status IN ('queued', 'sent', 'failed')
            GROUP BY status
            """
        ).fetchall()
    counts = {"queued": 0, "sent": 0, "failed": 0}
    counts.update({str(row["status"]): int(row["c"] or 0) for row in rows})
    return counts


def latest_failed_notification_items(limit: int = 5) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, channel, status, attempts, max_attempts, last_error, next_retry_at, created_at, sent_at
            FROM notification_queue
            WHERE status = 'failed'
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["last_error_summary"] = _redact_operational_text(item.pop("last_error", None))
        output.append(item)
    return output


def notification_queue_status(limit_failed: int = 5) -> dict[str, Any]:
    counts = count_notifications_by_status()
    return {
        "queued_count": counts["queued"],
        "sent_count": counts["sent"],
        "failed_count": counts["failed"],
        "latest_failed_items": latest_failed_notification_items(limit=limit_failed),
    }


def list_processable_notifications(limit: int = 50) -> list[dict[str, Any]]:
    now = _now_iso()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM notification_queue
            WHERE status = 'queued'
              AND (next_retry_at IS NULL OR next_retry_at <= ?)
            ORDER BY CASE WHEN next_retry_at IS NULL THEN 0 ELSE 1 END,
                     next_retry_at ASC,
                     id ASC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        item["payload"] = json.loads(item["payload"])
        out.append(item)
    return out


def mark_notification_result(
    notification_id: int,
    success: bool,
    error_message: str | None = None,
    retry_base_minutes: int = 5,
) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, attempts, max_attempts FROM notification_queue WHERE id = ?",
            (notification_id,),
        ).fetchone()
        if not row:
            return None

        attempts = int(row["attempts"] or 0)
        max_attempts = int(row["max_attempts"] or 1)

        if success:
            conn.execute(
                """
                UPDATE notification_queue
                SET status = 'sent', attempts = ?, last_error = NULL, next_retry_at = NULL, sent_at = ?
                WHERE id = ?
                """,
                (attempts + 1, _now_iso(), notification_id),
            )
        else:
            new_attempts = attempts + 1
            if new_attempts >= max_attempts:
                conn.execute(
                    """
                    UPDATE notification_queue
                    SET status = 'failed', attempts = ?, last_error = ?, next_retry_at = NULL, sent_at = ?
                    WHERE id = ?
                    """,
                    (new_attempts, error_message, _now_iso(), notification_id),
                )
            else:
                retry_minutes = max(1, retry_base_minutes) * new_attempts
                next_retry_at = (datetime.now(timezone.utc) + timedelta(minutes=retry_minutes)).isoformat()
                conn.execute(
                    """
                    UPDATE notification_queue
                    SET status = 'queued', attempts = ?, last_error = ?, next_retry_at = ?, sent_at = NULL
                    WHERE id = ?
                    """,
                    (new_attempts, error_message, next_retry_at, notification_id),
                )

        updated = conn.execute("SELECT * FROM notification_queue WHERE id = ?", (notification_id,)).fetchone()
    if not updated:
        return None
    item = dict(updated)
    item["payload"] = json.loads(item["payload"])
    return item


def mark_notification_sent(notification_id: int, success: bool) -> None:
    # Backward-compatible wrapper used by older code paths.
    mark_notification_result(notification_id=notification_id, success=success)


def get_notification_by_id(notification_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM notification_queue WHERE id = ?", (notification_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["payload"] = json.loads(item["payload"])
    return item


def requeue_notification(notification_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE notification_queue
            SET status = 'queued', attempts = 0, last_error = NULL, next_retry_at = NULL, sent_at = NULL
            WHERE id = ?
            """,
            (notification_id,),
        )
        row = conn.execute("SELECT * FROM notification_queue WHERE id = ?", (notification_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["payload"] = json.loads(item["payload"])
    return item


def overdue_spike_summary(threshold: int = 10, limit: int = 5) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM tasks WHERE status != 'done' AND deadline < ?",
            (now,),
        ).fetchone()["c"]
        project_rows = conn.execute(
            """
            SELECT
                t.project_id AS project_id,
                COALESCE(p.name, 'Unassigned') AS project_name,
                COUNT(*) AS overdue_count
            FROM tasks t
            LEFT JOIN projects p ON p.id = t.project_id
            WHERE t.status != 'done' AND t.deadline < ?
            GROUP BY t.project_id, p.name
            ORDER BY overdue_count DESC, t.project_id DESC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
        sprint_rows = conn.execute(
            """
            SELECT
                t.sprint_id AS sprint_id,
                COALESCE(s.name, 'Unassigned') AS sprint_name,
                t.project_id AS project_id,
                COALESCE(p.name, 'Unassigned') AS project_name,
                COUNT(*) AS overdue_count
            FROM tasks t
            LEFT JOIN sprints s ON s.id = t.sprint_id
            LEFT JOIN projects p ON p.id = t.project_id
            WHERE t.status != 'done' AND t.deadline < ?
            GROUP BY t.sprint_id, s.name, t.project_id, p.name
            ORDER BY overdue_count DESC, t.sprint_id DESC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()

    overdue_count = int(total or 0)
    return {
        "overdue_count": overdue_count,
        "threshold": threshold,
        "alert": overdue_count > threshold,
        "top_projects": [
            {
                "project_id": row["project_id"],
                "project_name": row["project_name"],
                "overdue_count": int(row["overdue_count"] or 0),
            }
            for row in project_rows
        ],
        "top_sprints": [
            {
                "sprint_id": row["sprint_id"],
                "sprint_name": row["sprint_name"],
                "project_id": row["project_id"],
                "project_name": row["project_name"],
                "overdue_count": int(row["overdue_count"] or 0),
            }
            for row in sprint_rows
        ],
    }


def system_metrics() -> dict[str, Any]:
    with get_connection() as conn:
        users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        projects = conn.execute("SELECT COUNT(*) AS c FROM projects").fetchone()["c"]
        tasks = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"]
        overdue = conn.execute(
            "SELECT COUNT(*) AS c FROM tasks WHERE status != 'done' AND deadline < ?",
            (_now_iso(),),
        ).fetchone()["c"]
        open_risks = conn.execute(
            "SELECT COUNT(*) AS c FROM project_risks WHERE status = 'open'"
        ).fetchone()["c"]
        queued_notifications = conn.execute(
            "SELECT COUNT(*) AS c FROM notification_queue WHERE status = 'queued'"
        ).fetchone()["c"]
        failed_notifications = conn.execute(
            "SELECT COUNT(*) AS c FROM notification_queue WHERE status = 'failed'"
        ).fetchone()["c"]
    return {
        "users": int(users),
        "projects": int(projects),
        "tasks": int(tasks),
        "overdue_tasks": int(overdue),
        "open_risks": int(open_risks),
        "queued_notifications": int(queued_notifications),
        "failed_notifications": int(failed_notifications),
    }


def sprint_review_summary(sprint_id: int) -> dict[str, Any]:
    sprint = get_sprint_by_id(sprint_id)
    if not sprint:
        return {}

    with get_connection() as conn:
        metrics = conn.execute(
            """
            SELECT
                COUNT(*) AS total_tasks,
                SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done_tasks,
                SUM(CASE WHEN status != 'done' THEN 1 ELSE 0 END) AS unfinished_tasks,
                SUM(story_points) AS planned_story_points,
                SUM(CASE WHEN status = 'done' THEN story_points ELSE 0 END) AS completed_story_points
            FROM tasks
            WHERE sprint_id = ?
            """,
            (sprint_id,),
        ).fetchone()

    total_tasks = int(metrics["total_tasks"] or 0)
    done_tasks = int(metrics["done_tasks"] or 0)
    unfinished_tasks = int(metrics["unfinished_tasks"] or 0)
    planned_story_points = int(metrics["planned_story_points"] or 0)
    completed_story_points = int(metrics["completed_story_points"] or 0)
    completion_rate = round((done_tasks / total_tasks) * 100, 2) if total_tasks else 0.0

    return {
        "sprint_id": int(sprint["id"]),
        "project_id": int(sprint["project_id"]),
        "sprint_name": sprint["name"],
        "status": sprint["status"],
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "unfinished_tasks": unfinished_tasks,
        "planned_story_points": planned_story_points,
        "completed_story_points": completed_story_points,
        "completion_rate": completion_rate,
    }


def portfolio_summary() -> list[dict[str, Any]]:
    projects = list_projects()
    output: list[dict[str, Any]] = []
    for p in projects:
        progress = project_progress(int(p["id"]))
        output.append(
            {
                "project_id": int(p["id"]),
                "project_name": p["name"],
                "status": p["status"],
                "completion_rate": progress["completion_rate"],
                "total_tasks": progress["total_tasks"],
                "overdue_tasks": progress["overdue_tasks"],
                "completed_story_points": progress["completed_story_points"],
                "total_story_points": progress["total_story_points"],
            }
        )
    return output


def implementation_plan_completion() -> dict[str, Any]:
    items = [
        {"key": "phase1_core_mvp", "title": "Phase 1 MVP core APIs", "done": True},
        {"key": "phase2_rbac_audit", "title": "Phase 2 RBAC and audit", "done": True},
        {"key": "phase3_reports", "title": "Phase 3 report exports", "done": True},
        {"key": "phase3_teams_bot_scaffold", "title": "Teams bot scaffold and reminders", "done": True},
        {"key": "phase3_proactive_queue", "title": "Proactive queue processing", "done": True},
        {"key": "phase3_ops_monitoring", "title": "Readiness and metrics monitoring", "done": True},
        {"key": "phase3_ci_docker", "title": "CI and container setup", "done": True},
        {"key": "phase4_azure_ad_sso", "title": "Azure AD SSO production hardening", "done": False},
        {"key": "phase4_security_hardening", "title": "Security hardening baseline", "done": True},
        {"key": "phase4_qa_automation", "title": "QA automation baseline", "done": True},
        {"key": "full_backlog_coverage", "title": "Full product backlog coverage", "done": False},
    ]
    total = len(items)
    completed = sum(1 for item in items if item["done"])
    completion_percent = round((completed / total) * 100, 2) if total else 0.0
    return {
        "total_items": total,
        "completed_items": completed,
        "completion_percent": completion_percent,
        "items": items,
    }
