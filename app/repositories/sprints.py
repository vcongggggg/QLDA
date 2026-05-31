from app.repositories.shared import *

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
