from app.repositories.shared import *

def _json_array(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value or "[]")
        except json.JSONDecodeError:
            return []
        return decoded if isinstance(decoded, list) else []
    return []


def _encode_json_list(value: list[Any] | None) -> str:
    return json.dumps(value or [], ensure_ascii=True)


def _decode_task_row(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["priority"] = item.get("priority") or "medium"
    item["backlog_rank"] = item.get("backlog_rank")
    item["readiness_status"] = item.get("readiness_status")
    item["acceptance_notes"] = item.get("acceptance_notes")
    item["milestone_id"] = item.get("milestone_id")
    item["dependency_ids"] = item.get("dependency_ids") or []
    for field in TASK_METADATA_LIST_FIELDS:
        item[field] = _json_array(item.get(field))
    return item


def create_task(
    title: str,
    description: str | None,
    assignee_id: int,
    project_id: int | None,
    sprint_id: int | None,
    story_points: int,
    difficulty: str,
    deadline_iso: str,
    priority: str = "medium",
    labels: list[str] | None = None,
    checklist: list[str] | None = None,
    subtasks: list[str] | None = None,
    dependencies: list[str] | None = None,
    attachment_metadata: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (
                title, description, assignee_id, project_id, sprint_id, story_points, difficulty,
                priority, labels, checklist, subtasks, dependencies, attachment_metadata,
                status, deadline, completed_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'todo', ?, NULL, ?, ?)
            """,
            (
                title,
                description,
                assignee_id,
                project_id,
                sprint_id,
                story_points,
                difficulty,
                priority,
                _encode_json_list(labels),
                _encode_json_list(checklist),
                _encode_json_list(subtasks),
                _encode_json_list(dependencies),
                _encode_json_list(attachment_metadata),
                deadline_iso,
                now,
                now,
            ),
        )
        task_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _decode_task_row(dict(row))


def _task_dependency_ids(task_id: int) -> list[int]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT dependency_task_id FROM task_dependencies WHERE task_id = ? ORDER BY dependency_task_id",
            (task_id,),
        ).fetchall()
    return [int(row["dependency_task_id"]) for row in rows]


def _attach_task_dependency_ids(task: dict[str, Any] | None) -> dict[str, Any] | None:
    if task is None:
        return None
    task["dependency_ids"] = _task_dependency_ids(int(task["id"]))
    return task


def list_tasks(
    assignee_id: int | None = None,
    status: str | None = None,
    project_id: int | None = None,
    sprint_id: int | None = None,
    overdue: bool | None = None,
    keyword: str | None = None,
    deadline_from: str | None = None,
    deadline_to: str | None = None,
    as_of: str | None = None,
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
        if sprint_id == 0:
            query += " AND sprint_id IS NULL"
        else:
            query += " AND sprint_id = ?"
            params.append(sprint_id)
    if overdue is True:
        query += " AND status != 'done' AND deadline < ?"
        params.append(as_of or _now_iso())
    elif overdue is False:
        query += " AND (status = 'done' OR deadline >= ?)"
        params.append(as_of or _now_iso())
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
    return [_attach_task_dependency_ids(_decode_task_row(dict(r))) for r in rows]


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
    return _attach_task_dependency_ids(_decode_task_row(dict(row)))


def update_task_deadline(task_id: int, deadline_iso: str) -> dict[str, Any] | None:
    now = _now_iso()
    with get_connection() as conn:
        exists = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not exists:
            return None
        conn.execute(
            "UPDATE tasks SET deadline = ?, updated_at = ? WHERE id = ?",
            (deadline_iso, now, task_id),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _attach_task_dependency_ids(_decode_task_row(dict(row))) if row else None


def get_task_by_id(task_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _attach_task_dependency_ids(_decode_task_row(dict(row))) if row else None


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
    return _attach_task_dependency_ids(_decode_task_row(dict(row))) if row else None


def update_task_metadata(
    task_id: int,
    *,
    priority: str | None = None,
    labels: list[str] | None = None,
    checklist: list[str] | None = None,
    subtasks: list[str] | None = None,
    dependencies: list[str] | None = None,
    attachment_metadata: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    fields: list[str] = []
    params: list[Any] = []
    for column, value in (
        ("priority", priority),
        ("labels", _encode_json_list(labels) if labels is not None else None),
        ("checklist", _encode_json_list(checklist) if checklist is not None else None),
        ("subtasks", _encode_json_list(subtasks) if subtasks is not None else None),
        ("dependencies", _encode_json_list(dependencies) if dependencies is not None else None),
        (
            "attachment_metadata",
            _encode_json_list(attachment_metadata) if attachment_metadata is not None else None,
        ),
    ):
        if value is not None:
            fields.append(f"{column} = ?")
            params.append(value)
    if not fields:
        return get_task_by_id(task_id)
    fields.append("updated_at = ?")
    params.append(_now_iso())
    params.append(task_id)
    with get_connection() as conn:
        exists = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not exists:
            return None
        conn.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", tuple(params))
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _attach_task_dependency_ids(_decode_task_row(dict(row))) if row else None


def bulk_update_tasks(
    task_ids: list[int],
    *,
    status: str | None = None,
    assignee_id: int | None = None,
    sprint_id: int | None = None,
    move_to_backlog: bool = False,
) -> int:
    fields: list[str] = []
    params: list[Any] = []
    if status is not None:
        fields.append("status = ?")
        params.append(status)
        fields.append("completed_at = ?")
        params.append(_now_iso() if status == "done" else None)
    if assignee_id is not None:
        fields.append("assignee_id = ?")
        params.append(assignee_id)
    if sprint_id is not None or move_to_backlog:
        fields.append("sprint_id = ?")
        params.append(None if move_to_backlog else sprint_id)
    if not fields or not task_ids:
        return 0
    fields.append("updated_at = ?")
    params.append(_now_iso())
    placeholders = ",".join(["?"] * len(task_ids))
    with get_connection() as conn:
        cursor = conn.execute(
            f"UPDATE tasks SET {', '.join(fields)} WHERE id IN ({placeholders})",
            tuple(params + task_ids),
        )
    return int(cursor.rowcount)


def duplicate_task(
    task_id: int,
    *,
    title: str | None = None,
    assignee_id: int | None = None,
    sprint_id: int | None = None,
    deadline_iso: str | None = None,
) -> dict[str, Any] | None:
    task = get_task_by_id(task_id)
    if not task:
        return None
    return create_task(
        title=title or f"{task['title']} (copy)",
        description=task.get("description"),
        assignee_id=assignee_id or int(task["assignee_id"]),
        project_id=task.get("project_id"),
        sprint_id=sprint_id if sprint_id is not None else task.get("sprint_id"),
        story_points=int(task["story_points"]),
        difficulty=str(task["difficulty"]),
        deadline_iso=deadline_iso or str(task["deadline"]),
        priority=str(task.get("priority") or "medium"),
        labels=list(task.get("labels") or []),
        checklist=list(task.get("checklist") or []),
        subtasks=list(task.get("subtasks") or []),
        dependencies=list(task.get("dependencies") or []),
        attachment_metadata=list(task.get("attachment_metadata") or []),
    )


def list_project_backlog(project_id: int) -> list[dict[str, Any]]:
    return list_tasks(project_id=project_id, sprint_id=0)


def task_project_ids(task_ids: list[int]) -> set[int | None]:
    if not task_ids:
        return set()
    placeholders = ",".join(["?"] * len(task_ids))
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT DISTINCT project_id FROM tasks WHERE id IN ({placeholders})",
            tuple(task_ids),
        ).fetchall()
    return {int(row["project_id"]) if row["project_id"] is not None else None for row in rows}


def carryover_sprint_tasks(source_sprint_id: int, target_sprint_id: int) -> int:
    target = get_sprint_by_id(target_sprint_id)
    source = get_sprint_by_id(source_sprint_id)
    if not source or not target:
        return 0
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE tasks
            SET sprint_id = ?, updated_at = ?
            WHERE sprint_id = ? AND status != 'done'
            """,
            (target_sprint_id, _now_iso(), source_sprint_id),
        )
    return int(cursor.rowcount)


def update_task_backlog_grooming(
    task_id: int,
    backlog_rank: int | None,
    readiness_status: str | None,
    acceptance_notes: str | None,
) -> dict[str, Any] | None:
    with get_connection() as conn:
        exists = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not exists:
            return None
        conn.execute(
            """
            UPDATE tasks
            SET backlog_rank = ?, readiness_status = ?, acceptance_notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (backlog_rank, readiness_status, acceptance_notes, _now_iso(), task_id),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _attach_task_dependency_ids(_decode_task_row(dict(row))) if row else None


def update_task_milestone(task_id: int, milestone_id: int | None) -> dict[str, Any] | None:
    with get_connection() as conn:
        exists = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not exists:
            return None
        conn.execute("UPDATE tasks SET milestone_id = ?, updated_at = ? WHERE id = ?", (milestone_id, _now_iso(), task_id))
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _attach_task_dependency_ids(_decode_task_row(dict(row))) if row else None


def _dependency_reaches(start_task_id: int, target_task_id: int, seen: set[int] | None = None) -> bool:
    seen = seen or set()
    if start_task_id in seen:
        return False
    seen.add(start_task_id)
    if start_task_id == target_task_id:
        return True
    for next_id in _task_dependency_ids(start_task_id):
        if _dependency_reaches(next_id, target_task_id, seen):
            return True
    return False


def replace_task_dependencies(task_id: int, dependency_ids: list[int]) -> dict[str, Any] | None:
    task = get_task_by_id(task_id)
    if not task:
        return None
    unique_ids = sorted({int(item) for item in dependency_ids})
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT id, project_id FROM tasks WHERE id IN ({','.join(['?'] * len(unique_ids))})",
            tuple(unique_ids),
        ).fetchall() if unique_ids else []
    found = {int(row["id"]): row for row in rows}
    if set(unique_ids) != set(found):
        raise ValueError("dependency task not found")
    for dep_id, dep in found.items():
        if dep_id == task_id:
            raise ValueError("task cannot depend on itself")
        if task.get("project_id") != dep["project_id"]:
            raise ValueError("dependency project mismatch")
        if _dependency_reaches(dep_id, task_id):
            raise ValueError("circular dependency")
    with get_connection() as conn:
        conn.execute("DELETE FROM task_dependencies WHERE task_id = ?", (task_id,))
        for dep_id in unique_ids:
            conn.execute(
                "INSERT INTO task_dependencies (task_id, dependency_task_id, created_at) VALUES (?, ?, ?)",
                (task_id, dep_id, _now_iso()),
            )
    return get_task_by_id(task_id)


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


def create_task_ai_detail(task_id: int, source_ai_draft_id: int, item: dict[str, Any]) -> dict[str, Any]:
    now = _now_iso()
    lists = _encode_ai_detail_lists(item)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO task_ai_details
            (task_id, source_ai_draft_id, type, business_goal, subtasks, acceptance_criteria,
             data_requirements, ui_components, test_cases, dependencies, risks, demo_value,
             suggested_role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                source_ai_draft_id,
                item.get("type"),
                item.get("business_goal"),
                lists["subtasks"],
                lists["acceptance_criteria"],
                lists["data_requirements"],
                lists["ui_components"],
                lists["test_cases"],
                lists["dependencies"],
                lists["risks"],
                item.get("demo_value"),
                item.get("suggested_role"),
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM task_ai_details WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _decode_task_ai_detail(dict(row))


def get_task_ai_detail(task_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM task_ai_details WHERE task_id = ?", (task_id,)).fetchone()
    return _decode_task_ai_detail(dict(row)) if row else None
