from app.repositories.shared import *

def create_project_milestone(project_id: int, name: str, description: str | None, due_date: str | None, status: str) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO project_milestones (project_id, name, description, due_date, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, name, description, due_date, status, now, now),
        )
        row = conn.execute("SELECT * FROM project_milestones WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def list_project_milestones(project_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM project_milestones WHERE project_id = ? ORDER BY due_date ASC, id ASC",
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_project_milestone(milestone_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM project_milestones WHERE id = ?", (milestone_id,)).fetchone()
    return dict(row) if row else None


def update_project_milestone(milestone_id: int, **values: Any) -> dict[str, Any] | None:
    fields: list[str] = []
    params: list[Any] = []
    for key, value in values.items():
        if value is None:
            continue
        fields.append(f"{key} = ?")
        params.append(value)
    if not fields:
        return get_project_milestone(milestone_id)
    fields.append("updated_at = ?")
    params.append(_now_iso())
    params.append(milestone_id)
    with get_connection() as conn:
        exists = conn.execute("SELECT id FROM project_milestones WHERE id = ?", (milestone_id,)).fetchone()
        if not exists:
            return None
        conn.execute(f"UPDATE project_milestones SET {', '.join(fields)} WHERE id = ?", tuple(params))
        row = conn.execute("SELECT * FROM project_milestones WHERE id = ?", (milestone_id,)).fetchone()
    return dict(row) if row else None


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
