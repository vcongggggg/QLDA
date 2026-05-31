from app.repositories.shared import *

def _decode_kanban_saved_filter(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    try:
        item["filters"] = json.loads(item.get("filters") or "{}")
    except json.JSONDecodeError:
        item["filters"] = {}
    item["is_default"] = bool(item.get("is_default"))
    return item


def list_kanban_saved_filters(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM kanban_saved_filters WHERE user_id = ? ORDER BY is_default DESC, name ASC",
            (user_id,),
        ).fetchall()
    return [_decode_kanban_saved_filter(dict(row)) for row in rows]


def create_kanban_saved_filter(user_id: int, name: str, filters: dict, is_default: bool = False) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        if is_default:
            conn.execute("UPDATE kanban_saved_filters SET is_default = 0 WHERE user_id = ?", (user_id,))
        cursor = conn.execute(
            """
            INSERT INTO kanban_saved_filters (user_id, name, filters, is_default, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, name, json.dumps(filters, ensure_ascii=True), 1 if is_default else 0, now, now),
        )
        row = conn.execute("SELECT * FROM kanban_saved_filters WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _decode_kanban_saved_filter(dict(row))


def get_kanban_saved_filter(filter_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM kanban_saved_filters WHERE id = ?", (filter_id,)).fetchone()
    return _decode_kanban_saved_filter(dict(row)) if row else None


def update_kanban_saved_filter(filter_id: int, name: str, filters: dict, is_default: bool) -> dict[str, Any] | None:
    existing = get_kanban_saved_filter(filter_id)
    if not existing:
        return None
    now = _now_iso()
    with get_connection() as conn:
        if is_default:
            conn.execute("UPDATE kanban_saved_filters SET is_default = 0 WHERE user_id = ?", (int(existing["user_id"]),))
        conn.execute(
            """
            UPDATE kanban_saved_filters
            SET name = ?, filters = ?, is_default = ?, updated_at = ?
            WHERE id = ?
            """,
            (name, json.dumps(filters, ensure_ascii=True), 1 if is_default else 0, now, filter_id),
        )
        row = conn.execute("SELECT * FROM kanban_saved_filters WHERE id = ?", (filter_id,)).fetchone()
    return _decode_kanban_saved_filter(dict(row)) if row else None


def delete_kanban_saved_filter(filter_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM kanban_saved_filters WHERE id = ?", (filter_id,))
    return int(cursor.rowcount) > 0


def upsert_kanban_wip_policy(
    project_id: int | None,
    sprint_id: int | None,
    todo_limit: int | None,
    doing_limit: int | None,
    done_limit: int | None,
) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM kanban_wip_policies
            WHERE COALESCE(project_id, 0) = COALESCE(?, 0)
              AND COALESCE(sprint_id, 0) = COALESCE(?, 0)
            LIMIT 1
            """,
            (project_id, sprint_id),
        ).fetchone()
        if row:
            conn.execute(
                """
                UPDATE kanban_wip_policies
                SET todo_limit = ?, doing_limit = ?, done_limit = ?, updated_at = ?
                WHERE id = ?
                """,
                (todo_limit, doing_limit, done_limit, now, int(row["id"])),
            )
            policy_id = int(row["id"])
        else:
            cursor = conn.execute(
                """
                INSERT INTO kanban_wip_policies
                (project_id, sprint_id, todo_limit, doing_limit, done_limit, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, sprint_id, todo_limit, doing_limit, done_limit, now, now),
            )
            policy_id = int(cursor.lastrowid)
        result = conn.execute("SELECT * FROM kanban_wip_policies WHERE id = ?", (policy_id,)).fetchone()
    return _decode_wip_policy(dict(result))


def get_kanban_wip_policy(project_id: int | None = None, sprint_id: int | None = None) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM kanban_wip_policies
            WHERE (? IS NOT NULL AND sprint_id = ?)
               OR (? IS NOT NULL AND sprint_id IS NULL AND project_id = ?)
               OR (? IS NULL AND ? IS NULL AND sprint_id IS NULL AND project_id IS NULL)
            ORDER BY CASE WHEN sprint_id IS NOT NULL THEN 0 WHEN project_id IS NOT NULL THEN 1 ELSE 2 END
            LIMIT 1
            """,
            (sprint_id, sprint_id, project_id, project_id, sprint_id, project_id),
        ).fetchone()
    return _decode_wip_policy(dict(row)) if row else None


def build_kanban_summary(tasks: list[dict[str, Any]], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    columns = []
    for status in ("todo", "doing", "done"):
        items = [task for task in tasks if task.get("status") == status]
        limit = policy.get(f"{status}_limit") if policy else None
        story_points = sum(int(task.get("story_points") or 0) for task in items)
        overdue_count = sum(1 for task in items if _is_kanban_task_overdue(task, now))
        columns.append(
            {
                "status": status,
                "task_count": len(items),
                "story_points": story_points,
                "overdue_count": overdue_count,
                "wip_limit": limit,
                "wip_exceeded": limit is not None and len(items) > int(limit),
            }
        )
    return {
        "columns": columns,
        "total_tasks": len(tasks),
        "total_story_points": sum(int(task.get("story_points") or 0) for task in tasks),
        "overdue_open_tasks": sum(1 for task in tasks if _is_kanban_task_overdue(task, now)),
        "wip_exceeded_columns": sum(1 for column in columns if column["wip_exceeded"]),
        "wip_policy": policy,
    }


def _is_kanban_task_overdue(task: dict[str, Any], now: datetime) -> bool:
    if task.get("status") == "done" or not task.get("deadline"):
        return False
    deadline = task["deadline"]
    if isinstance(deadline, str):
        try:
            deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except ValueError:
            return False
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return deadline < now
