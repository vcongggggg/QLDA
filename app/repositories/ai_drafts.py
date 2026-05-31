from app.repositories.shared import *

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


def _json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        try:
            decoded = json.loads(value or "[]")
        except json.JSONDecodeError:
            return [value] if value.strip() else []
        if isinstance(decoded, list):
            return [str(item) for item in decoded if str(item).strip()]
    return []


def _encode_ai_detail_lists(item: dict[str, Any]) -> dict[str, str]:
    return {
        field: json.dumps(_json_list(item.get(field)), ensure_ascii=True)
        for field in TASK_AI_DETAIL_LIST_FIELDS
    }


def _decode_task_ai_detail(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    for field in TASK_AI_DETAIL_LIST_FIELDS:
        item[field] = _json_list(item.get(field))
    return item
