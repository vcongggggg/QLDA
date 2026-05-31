from app.repositories.shared import *

def _decode_task_template(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    for field in ("labels", "checklist", "subtasks"):
        item[field] = _json_array(item.get(field))
    return item


def create_task_template(
    *,
    name: str,
    title: str,
    description: str | None,
    project_id: int | None,
    story_points: int,
    difficulty: str,
    priority: str,
    labels: list[str],
    checklist: list[str],
    subtasks: list[str],
    created_by: int,
) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO task_templates
            (name, title, description, project_id, story_points, difficulty, priority, labels, checklist, subtasks, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                title,
                description,
                project_id,
                story_points,
                difficulty,
                priority,
                _encode_json_list(labels),
                _encode_json_list(checklist),
                _encode_json_list(subtasks),
                created_by,
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM task_templates WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _decode_task_template(dict(row))


def list_task_templates(project_id: int | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM task_templates WHERE 1=1"
    params: list[Any] = []
    if project_id is not None:
        query += " AND (project_id = ? OR project_id IS NULL)"
        params.append(project_id)
    query += " ORDER BY name ASC"
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [_decode_task_template(dict(row)) for row in rows]


def get_task_template(template_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM task_templates WHERE id = ?", (template_id,)).fetchone()
    return _decode_task_template(dict(row)) if row else None


def update_task_template(template_id: int, **values: Any) -> dict[str, Any] | None:
    fields: list[str] = []
    params: list[Any] = []
    for key, value in values.items():
        if value is None:
            continue
        if key in {"labels", "checklist", "subtasks"}:
            value = _encode_json_list(value)
        fields.append(f"{key} = ?")
        params.append(value)
    if not fields:
        return get_task_template(template_id)
    fields.append("updated_at = ?")
    params.append(_now_iso())
    params.append(template_id)
    with get_connection() as conn:
        exists = conn.execute("SELECT id FROM task_templates WHERE id = ?", (template_id,)).fetchone()
        if not exists:
            return None
        conn.execute(f"UPDATE task_templates SET {', '.join(fields)} WHERE id = ?", tuple(params))
        row = conn.execute("SELECT * FROM task_templates WHERE id = ?", (template_id,)).fetchone()
    return _decode_task_template(dict(row)) if row else None


def delete_task_template(template_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM task_templates WHERE id = ?", (template_id,))
    return int(cursor.rowcount) > 0


def create_recurring_task_rule(
    *,
    template_id: int,
    assignee_id: int,
    project_id: int | None,
    sprint_id: int | None,
    frequency: str,
    next_run_at: str,
    active: bool,
    created_by: int,
) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO recurring_task_rules
            (template_id, assignee_id, project_id, sprint_id, frequency, next_run_at, active, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (template_id, assignee_id, project_id, sprint_id, frequency, next_run_at, 1 if active else 0, created_by, now, now),
        )
        row = conn.execute("SELECT * FROM recurring_task_rules WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _decode_recurring_rule(dict(row))


def _decode_recurring_rule(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["active"] = bool(item.get("active"))
    return item


def list_recurring_task_rules(active: bool | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM recurring_task_rules WHERE 1=1"
    params: list[Any] = []
    if active is not None:
        query += " AND active = ?"
        params.append(1 if active else 0)
    query += " ORDER BY next_run_at ASC"
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [_decode_recurring_rule(dict(row)) for row in rows]


def _next_recurring_run(value: str, frequency: str) -> str:
    current = datetime.fromisoformat(value)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if frequency == "weekly":
        return (current + timedelta(days=7)).isoformat()
    month = current.month + 1
    year = current.year
    if month > 12:
        month = 1
        year += 1
    day = min(current.day, 28)
    return current.replace(year=year, month=month, day=day).isoformat()


def run_due_recurring_task_rules(as_of_iso: str, actor_user_id: int) -> list[dict[str, Any]]:
    due_rules = [rule for rule in list_recurring_task_rules(active=True) if str(rule["next_run_at"]) <= as_of_iso]
    created: list[dict[str, Any]] = []
    for rule in due_rules:
        template = get_task_template(int(rule["template_id"]))
        if not template:
            continue
        task = create_task(
            title=str(template["title"]),
            description=template.get("description"),
            assignee_id=int(rule["assignee_id"]),
            project_id=rule.get("project_id"),
            sprint_id=rule.get("sprint_id"),
            story_points=int(template["story_points"]),
            difficulty=str(template["difficulty"]),
            deadline_iso=str(rule["next_run_at"]),
            priority=str(template.get("priority") or "medium"),
            labels=list(template.get("labels") or []),
            checklist=list(template.get("checklist") or []),
            subtasks=list(template.get("subtasks") or []),
        )
        created.append(task)
        create_audit_log(actor_user_id, "create_recurring", "task", int(task["id"]), f"rule={rule['id']};template={template['id']}")
        with get_connection() as conn:
            conn.execute(
                "UPDATE recurring_task_rules SET next_run_at = ?, updated_at = ? WHERE id = ?",
                (_next_recurring_run(str(rule["next_run_at"]), str(rule["frequency"])), _now_iso(), int(rule["id"])),
            )
    return created
