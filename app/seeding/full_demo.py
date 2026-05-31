from app.seeding.shared import *

def _upsert_full_demo_departments(conn: Any) -> dict[str, int]:
    columns = _table_columns(conn, "departments")
    for name, code, description in FULL_DEMO_DEPARTMENTS:
        if {"description", "is_active"}.issubset(columns):
            conn.execute(
                """
                /* no-returning-id */ INSERT INTO departments (name, code, description, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    is_active = 1
                """,
                (name, code, description, DEMO_NOW_ISO),
            )
        else:
            conn.execute(
                """
                /* no-returning-id */ INSERT INTO departments (name, code, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET name = excluded.name
                """,
                (name, code, DEMO_NOW_ISO),
            )
    rows = conn.execute("SELECT id, code FROM departments").fetchall()
    return {str(row["code"]): int(row["id"]) for row in rows}


def _upsert_full_demo_users(conn: Any, department_ids: dict[str, int]) -> dict[str, int]:
    for full_name, email, role, role_id, department_code, position, password in FULL_DEMO_USERS:
        department_id = department_ids[department_code]
        department_name = conn.execute("SELECT name FROM departments WHERE id = ?", (department_id,)).fetchone()["name"]
        existing = conn.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email.lower(),)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE users
                SET full_name = ?, role = ?, role_id = ?, department = ?, department_id = ?,
                    position = ?, password_hash = COALESCE(password_hash, ?), is_active = 1, updated_at = ?
                WHERE id = ?
                """,
                (
                    full_name,
                    role,
                    role_id,
                    department_name,
                    department_id,
                    position,
                    hash_password(password),
                    DEMO_NOW_ISO,
                    existing["id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO users
                (full_name, email, aad_object_id, role, department, password_hash, role_id, department_id, position, avatar_url, is_active, created_at, updated_at)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, NULL, 1, ?, ?)
                """,
                (
                    full_name,
                    email.lower(),
                    role,
                    department_name,
                    hash_password(password),
                    role_id,
                    department_id,
                    position,
                    DEMO_NOW_ISO,
                    DEMO_NOW_ISO,
                ),
            )
    _assign_demo_department_managers(conn)
    rows = conn.execute(
        f"SELECT id, email FROM users WHERE LOWER(email) IN ({_placeholders(FULL_DEMO_USER_EMAILS)})",
        tuple(email.lower() for email in FULL_DEMO_USER_EMAILS),
    ).fetchall()
    return {str(row["email"]).lower(): int(row["id"]) for row in rows}


def _assign_demo_department_managers(conn: Any) -> None:
    if "manager_user_id" not in _table_columns(conn, "departments"):
        return
    manager_by_department = {
        "ADM": "an.nguyen@teamswork.example.com",
        "PMO": "phuc.tran@teamswork.example.com",
        "PBA": "linh.vo@teamswork.example.com",
        "UXD": "mai.bui@teamswork.example.com",
        "WEB": "phuc.tran@teamswork.example.com",
        "MOB": "ha.le@teamswork.example.com",
        "QA": "yen.ho@teamswork.example.com",
        "OPS": "bao.pham@teamswork.example.com",
        "HR": "vy.mai@teamswork.example.com",
        "AUD": "auditor@teamswork.local",
    }
    for code, email in manager_by_department.items():
        row = conn.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email.lower(),)).fetchone()
        if row:
            conn.execute("UPDATE departments SET manager_user_id = ? WHERE code = ?", (int(row["id"]), code))


def _upsert_full_demo_projects(conn: Any, department_ids: dict[str, int], user_ids: dict[str, int]) -> dict[str, int]:
    descriptions = {
        "TeamsWork Internal PM & KPI": (
            f"[{DEMO_NAMESPACE}] Internal QLDA/TeamsWork demo project for RBAC, KPI dashboard, "
            "project progress, sprint review, AI task draft, Teams notification and overdue task workflows."
        ),
        "ShopMate Mobile Commerce": (
            f"[{DEMO_NAMESPACE}] Mobile commerce delivery project for requirements, UAT, cart, order tracking, "
            "voucher, push notification and sprint review demo scenarios."
        ),
        "FieldOps Service Mobile": (
            f"[{DEMO_NAMESPACE}] Field service mobile project for offline sync, GPS check-in, photo evidence, "
            "SLA dashboard, risk mitigation and project progress tracking."
        ),
    }
    for project in PROJECTS:
        name = str(project["name"])
        existing = conn.execute("SELECT id FROM projects WHERE name = ?", (name,)).fetchone()
        params = (
            descriptions[name],
            department_ids[str(project["department_code"])],
            user_ids[str(project["manager_email"]).lower()],
            project["start"],
            project["end"],
            "active",
            DEMO_NOW_ISO,
        )
        if existing:
            conn.execute(
                """
                UPDATE projects
                SET description = ?, department_id = ?, manager_id = ?, start_date = ?, end_date = ?,
                    status = ?, created_at = ?
                WHERE id = ?
                """,
                (*params, int(existing["id"])),
            )
        else:
            conn.execute(
                """
                INSERT INTO projects
                (name, description, department_id, manager_id, start_date, end_date, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, *params),
            )
    return _full_demo_project_ids(conn)


def _seed_full_demo_kpi_adjustments(conn: Any, user_ids: dict[str, int]) -> None:
    rows = (
        ("kiet.do@teamswork.example.com", "2026-06", 5.0, "Supported urgent RBAC release"),
        ("quan.pham@teamswork.example.com", "2026-07", -3.0, "Missed project progress update"),
        ("long.nguyen@teamswork.example.com", "2026-07", 8.0, "Resolved production-style demo blocker"),
        ("giabao.nguyen@teamswork.example.com", "2026-08", -5.0, "Overdue task was not escalated"),
        ("yen.ho@teamswork.example.com", "2026-08", 4.0, "Extra QA regression support"),
    )
    admin_id = user_ids["an.nguyen@teamswork.example.com"]
    conn.executemany(
        """
        INSERT INTO kpi_adjustments (user_id, month, points, reason, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (user_ids[email], month, points, f"[{DEMO_NAMESPACE}] {reason}", admin_id, _iso_date(f"{month}-28", 17))
            for email, month, points, reason in rows
        ],
    )


def _seed_full_demo_notifications_comments_audit(conn: Any, user_ids: dict[str, int], project_ids: dict[str, int]) -> None:
    tasks = conn.execute(
        f"""
        SELECT t.id, t.title, t.assignee_id, t.status, t.deadline, p.name AS project_name, s.name AS sprint_name
        FROM tasks t
        JOIN projects p ON p.id = t.project_id
        LEFT JOIN sprints s ON s.id = t.sprint_id
        WHERE p.name IN ({_placeholders(DEMO_PROJECT_NAMES)})
        ORDER BY t.id
        """,
        DEMO_PROJECT_NAMES,
    ).fetchall()
    if not tasks:
        return
    comment_authors = (
        user_ids["phuc.tran@teamswork.example.com"],
        user_ids["linh.vo@teamswork.example.com"],
        user_ids["kiet.do@teamswork.example.com"],
        user_ids["mai.bui@teamswork.example.com"],
        user_ids["yen.ho@teamswork.example.com"],
        user_ids["ngoc.phan@teamswork.example.com"],
    )
    comments = []
    for idx, task in enumerate(tasks):
        task_id = int(task["id"])
        title = str(task["title"])
        project_name = str(task["project_name"])
        sprint_name = str(task["sprint_name"] or "unplanned sprint")
        comments.append(
            (
                task_id,
                comment_authors[idx % len(comment_authors)],
                f"[{DEMO_NAMESPACE}] {project_name} / {sprint_name}: PM reviewed task '{title}' for sprint review and project progress.",
                _iso_date(f"2026-08-{1 + (idx % 9):02d}", 9 + (idx % 4)),
            )
        )
        comments.append(
            (
                task_id,
                comment_authors[(idx + 1) % len(comment_authors)],
                f"[{DEMO_NAMESPACE}] QA and BA notes for '{title}': confirm UAT evidence, overdue task risk and acceptance criteria.",
                _iso_date(f"2026-08-{1 + (idx % 9):02d}", 13 + (idx % 4)),
            )
        )
        if idx % 2 == 0:
            comments.append(
                (
                    task_id,
                    comment_authors[(idx + 2) % len(comment_authors)],
                    f"[{DEMO_NAMESPACE}] Teams notification follow-up for '{title}' is ready for manager and member visibility demo.",
                    _iso_date(f"2026-08-{2 + (idx % 8):02d}", 16),
                )
            )
    conn.executemany(
        "INSERT INTO task_comments (task_id, author_user_id, body, created_at) VALUES (?, ?, ?, ?)",
        comments,
    )
    notifications = []
    notification_types = ("task_status_changed", "task_comment", "task_due_soon", "task_overdue")
    for idx, task in enumerate(tasks[:12]):
        notifications.append(
            (
                int(task["assignee_id"]),
                notification_types[idx % len(notification_types)],
                "TeamsWork demo task update",
                f"[{DEMO_NAMESPACE}] Task '{task['title']}' needs attention for project progress, sprint review or overdue task handling.",
                "task",
                int(task["id"]),
                idx % 5 == 0,
                _iso_date(f"2026-08-{1 + (idx % 9):02d}", 10),
                _iso_date(f"2026-08-{1 + (idx % 9):02d}", 11) if idx % 5 == 0 else None,
            )
        )
    conn.executemany(
        """
        INSERT INTO app_notifications
        (user_id, type, title, message, entity_type, entity_id, is_read, created_at, read_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        notifications,
    )
    queue_rows = (
        ("phuc.tran@teamswork.example.com", "queued", 0, None, None),
        ("ha.le@teamswork.example.com", "sent", 1, None, _iso_date("2026-08-08", 8)),
        ("bao.pham@teamswork.example.com", "failed", 3, "Demo Teams webhook is intentionally not configured", _iso_date("2026-08-07", 8)),
        ("yen.ho@teamswork.example.com", "queued", 0, None, None),
        ("vy.mai@teamswork.example.com", "queued", 0, None, None),
    )
    conn.executemany(
        """
        INSERT INTO notification_queue
        (user_id, channel, payload, status, attempts, max_attempts, last_error, next_retry_at, created_at, sent_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                user_ids[email],
                "teams",
                json.dumps(
                    {
                        "demo_namespace": DEMO_NAMESPACE,
                        "message": "Demo Teams notification for KPI dashboard, overdue task and sprint review.",
                    },
                    ensure_ascii=True,
                ),
                status,
                attempts,
                3,
                last_error,
                None,
                _iso_date("2026-08-09", 8),
                sent_at,
            )
            for email, status, attempts, last_error, sent_at in queue_rows
        ],
    )
    audit_rows = [
        (user_ids["an.nguyen@teamswork.example.com"], "seed_full_demo", "system", None, f"[{DEMO_NAMESPACE}] Upserted demo seed data", DEMO_NOW_ISO),
        (user_ids["phuc.tran@teamswork.example.com"], "review_project_progress", "project", project_ids["TeamsWork Internal PM & KPI"], f"[{DEMO_NAMESPACE}] Reviewed KPI dashboard project progress", _iso_date("2026-08-08", 15)),
        (user_ids["ha.le@teamswork.example.com"], "review_uat", "project", project_ids["ShopMate Mobile Commerce"], f"[{DEMO_NAMESPACE}] Reviewed UAT notes and sprint review", _iso_date("2026-08-08", 16)),
        (user_ids["bao.pham@teamswork.example.com"], "mitigate_risk", "project", project_ids["FieldOps Service Mobile"], f"[{DEMO_NAMESPACE}] Updated risk mitigation plan", _iso_date("2026-08-08", 17)),
    ]
    conn.executemany(
        "INSERT INTO audit_logs (actor_user_id, action, entity, entity_id, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        audit_rows,
    )


def _seed_full_demo_ai_drafts(conn: Any, user_ids: dict[str, int]) -> None:
    generated = [
        {"title": "Prepare KPI dashboard drilldown", "description": "Show monthly KPI, overdue task and adjustment detail.", "story_points": 5, "difficulty": "hard", "deadline_offset_days": 7, "selected": True},
        {"title": "Run UAT sprint review checklist", "description": "Collect UAT evidence and sprint review notes.", "story_points": 3, "difficulty": "medium", "deadline_offset_days": 5, "selected": True},
    ]
    rows = (
        ("text", "KPI dashboard needs project progress, overdue task and member drilldown.", FULL_DEMO_AI_SOURCE_NAMES[0], "draft", None, None, None, None, None, "phuc.tran@teamswork.example.com"),
        ("text", "UAT notes mention sprint review, RBAC role permission and Teams notification acceptance.", FULL_DEMO_AI_SOURCE_NAMES[1], "reviewed", "phuc.tran@teamswork.example.com", _iso_date("2026-08-07", 14), None, "Reviewed for Sprint 5.", None, "mai.bui@teamswork.example.com"),
        ("text", "ShopMate requirements include voucher, cart, order tracking and push notification.", FULL_DEMO_AI_SOURCE_NAMES[2], "imported", "ha.le@teamswork.example.com", _iso_date("2026-08-04", 13), _iso_date("2026-08-05", 10), "Imported core stories.", None, "ha.le@teamswork.example.com"),
        ("text", "FieldOps offline sync requires retry, conflict handling and SLA dashboard tasks.", FULL_DEMO_AI_SOURCE_NAMES[3], "reviewed", "bao.pham@teamswork.example.com", _iso_date("2026-08-05", 13), None, "Split offline sync work.", "Separated risk task.", "linh.vo@teamswork.example.com"),
        ("text", "RBAC permission matrix covers admin, manager, member, HR and auditor read-only scenarios.", FULL_DEMO_AI_SOURCE_NAMES[4], "draft", None, None, None, None, None, "an.nguyen@teamswork.example.com"),
        ("text", "Risk log requires mitigation tasks for overdue work and UAT blocker escalation.", FULL_DEMO_AI_SOURCE_NAMES[5], "imported", "bao.pham@teamswork.example.com", _iso_date("2026-08-06", 13), _iso_date("2026-08-06", 16), "Imported mitigation tasks.", None, "bao.pham@teamswork.example.com"),
    )
    conn.executemany(
        """
        INSERT INTO ai_task_drafts
        (source_type, source_summary, source_name, generated_tasks, status, reviewer_id, reviewed_at, imported_at, review_note, edit_reason, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                source_type,
                summary,
                source_name,
                json.dumps(generated, ensure_ascii=True),
                status,
                user_ids[reviewer] if reviewer else None,
                reviewed_at,
                imported_at,
                review_note,
                edit_reason,
                user_ids[created_by],
                _iso_date("2026-08-03", 9),
            )
            for source_type, summary, source_name, status, reviewer, reviewed_at, imported_at, review_note, edit_reason, created_by in rows
        ],
    )


def seed_full_demo_data(mode: str = "upsert", force: bool = False) -> dict:
    normalized_mode = _validate_seed_mode(mode)
    if normalized_mode == "reset":
        _ensure_reset_allowed(force)
    with get_connection() as conn:
        department_ids = _upsert_full_demo_departments(conn)
        user_ids = _upsert_full_demo_users(conn, department_ids)
        project_ids = _upsert_full_demo_projects(conn, department_ids, user_ids)
        _delete_full_demo_project_children(conn, project_ids)
        _delete_full_demo_global_children(conn)
        if normalized_mode == "reset":
            conn.execute(
                f"DELETE FROM projects WHERE name IN ({_placeholders(DEMO_PROJECT_NAMES)})",
                DEMO_PROJECT_NAMES,
            )
            project_ids = _upsert_full_demo_projects(conn, department_ids, user_ids)
        sprint_ids = seed_sprints(conn, project_ids)
        seed_members(conn, project_ids, user_ids)
        seed_tasks(conn, project_ids, sprint_ids, user_ids)
        seed_capacity(conn, project_ids, sprint_ids)
        seed_risks(conn, project_ids, user_ids)
        seed_weekly_updates(conn, project_ids, sprint_ids, user_ids)
        _seed_full_demo_kpi_adjustments(conn, user_ids)
        _seed_full_demo_notifications_comments_audit(conn, user_ids, project_ids)
        _seed_full_demo_ai_drafts(conn, user_ids)
        chunk_ids = _seed_rag_documents_with_conn(conn, project_ids, user_ids)
        counts = _summary_counts(conn)
    warnings = _try_store_seed_embeddings(chunk_ids)
    with get_connection() as conn:
        counts = _summary_counts(conn)
    return {
        "message": "Full demo data seeded",
        "mode": normalized_mode,
        "demo_namespace": DEMO_NAMESPACE,
        "demo_now": DEMO_NOW_ISO,
        "warnings": warnings,
        "counts": counts,
    }
