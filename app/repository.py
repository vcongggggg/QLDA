from datetime import datetime, timedelta, timezone
import json
from typing import Any

from app.database import get_connection


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def list_audit_logs(limit: int = 100) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT al.*, u.full_name AS actor_name
            FROM audit_logs al
            LEFT JOIN users u ON u.id = al.actor_user_id
            ORDER BY al.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


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
                "SELECT * FROM notification_queue ORDER BY id ASC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notification_queue WHERE status = ? ORDER BY id ASC LIMIT ?",
                (status, limit),
            ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        item["payload"] = json.loads(item["payload"])
        out.append(item)
    return out


def list_processable_notifications(limit: int = 50) -> list[dict[str, Any]]:
    now = _now_iso()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM notification_queue
            WHERE status = 'queued'
              AND (next_retry_at IS NULL OR next_retry_at <= ?)
            ORDER BY id ASC
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
