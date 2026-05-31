from app.repositories.shared import *


def _decode_schedule(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    try:
        item["recipients"] = json.loads(item.get("recipients") or "[]")
    except (TypeError, ValueError):
        item["recipients"] = []
    item["active"] = bool(item.get("active", True))
    return item


def create_report_schedule(
    *,
    name: str,
    report_type: str,
    format: str,
    frequency: str,
    recipients: list[str],
    next_run_at: str,
    created_by: int,
    active: bool = True,
) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO scheduled_reports
            (name, report_type, format, frequency, recipients, active, next_run_at, last_run_at, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
            """,
            (
                name,
                report_type,
                format,
                frequency,
                json.dumps(recipients, ensure_ascii=True),
                bool(active),
                next_run_at,
                created_by,
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM scheduled_reports WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _decode_schedule(dict(row))


def get_report_schedule(schedule_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM scheduled_reports WHERE id = ?", (schedule_id,)).fetchone()
    return _decode_schedule(dict(row)) if row else None


def list_report_schedules(active_only: bool = False) -> list[dict[str, Any]]:
    query = "SELECT * FROM scheduled_reports"
    params: list[Any] = []
    if active_only:
        query += " WHERE active = TRUE"
    query += " ORDER BY id DESC"
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [_decode_schedule(dict(row)) for row in rows]


def list_due_report_schedules(as_of: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM scheduled_reports
            WHERE active = TRUE AND next_run_at <= ?
            ORDER BY next_run_at ASC, id ASC
            """,
            (as_of,),
        ).fetchall()
    return [_decode_schedule(dict(row)) for row in rows]


def update_report_schedule_next_run(schedule_id: int, next_run_at: str) -> None:
    now = _now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE scheduled_reports
            SET next_run_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (next_run_at, now, schedule_id),
        )


def list_task_dependency_edges() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT task_id, dependency_task_id
            FROM task_dependencies
            ORDER BY task_id, dependency_task_id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def create_scheduled_report_delivery(
    *,
    schedule_id: int,
    status: str,
    delivery_channel: str,
    message: str | None,
) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO scheduled_report_deliveries
            (schedule_id, status, delivery_channel, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (schedule_id, status, delivery_channel, message, now),
        )
        conn.execute(
            """
            UPDATE scheduled_reports
            SET last_run_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, now, schedule_id),
        )
        row = conn.execute("SELECT * FROM scheduled_report_deliveries WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def list_scheduled_report_deliveries(schedule_id: int, limit: int = 20) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM scheduled_report_deliveries
            WHERE schedule_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (schedule_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def latest_scheduled_report_delivery(schedule_id: int) -> dict[str, Any] | None:
    rows = list_scheduled_report_deliveries(schedule_id=schedule_id, limit=1)
    return rows[0] if rows else None
