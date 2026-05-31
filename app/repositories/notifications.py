from app.repositories.shared import *

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
            SELECT
                t.*,
                u.full_name AS assignee_name,
                p.name AS project_name,
                s.name AS sprint_name
            FROM tasks t
            JOIN users u ON u.id = t.assignee_id
            LEFT JOIN projects p ON p.id = t.project_id
            LEFT JOIN sprints s ON s.id = t.sprint_id
            ORDER BY t.id
            """
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
    dedup_key = str((payload or {}).get("dedup_key") or "").strip()
    with get_connection() as conn:
        if dedup_key:
            rows = conn.execute(
                """
                SELECT *
                FROM notification_queue
                WHERE channel = ?
                  AND status IN ('queued', 'sent')
                ORDER BY id DESC
                LIMIT 200
                """,
                (channel,),
            ).fetchall()
            for existing in rows:
                item = dict(existing)
                try:
                    existing_payload = json.loads(item["payload"] or "{}")
                except (TypeError, ValueError):
                    existing_payload = {}
                if str(existing_payload.get("dedup_key") or "") == dedup_key:
                    item["payload"] = existing_payload
                    return item
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
