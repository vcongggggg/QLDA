from datetime import datetime, timedelta, timezone

from app.database import get_connection


def seed_data() -> dict:
    with get_connection() as conn:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count == 0:
            users = [
                ("Nguyen Van A", "a@teamswork.local", None, "manager", "PMO"),
                ("Tran Thi B", "b@teamswork.local", None, "staff", "Engineering"),
                ("Le Van C", "c@teamswork.local", None, "staff", "Engineering"),
                ("Pham Thi D", "d@teamswork.local", None, "hr", "HR"),
            ]
            conn.executemany(
                "INSERT INTO users (full_name, email, aad_object_id, role, department) VALUES (?, ?, ?, ?, ?)",
                users,
            )

        department_count = conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
        if department_count == 0:
            deps = [
                ("Engineering", "ENG", datetime.now(timezone.utc).isoformat()),
                ("HR", "HR", datetime.now(timezone.utc).isoformat()),
                ("PMO", "PMO", datetime.now(timezone.utc).isoformat()),
            ]
            conn.executemany(
                "INSERT INTO departments (name, code, created_at) VALUES (?, ?, ?)",
                deps,
            )

        project_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        if project_count == 0:
            eng_id = conn.execute("SELECT id FROM departments WHERE code = 'ENG'").fetchone()[0]
            pmo_id = conn.execute("SELECT id FROM departments WHERE code = 'PMO'").fetchone()[0]
            manager_id = conn.execute("SELECT id FROM users WHERE role = 'manager' ORDER BY id LIMIT 1").fetchone()[0]
            now_iso = datetime.now(timezone.utc).isoformat()
            projects = [
                ("TeamsWork Core MVP", "Core sprint implementation", eng_id, manager_id, now_iso, None, "active", now_iso),
                ("PM Governance", "Project documentation and governance", pmo_id, manager_id, now_iso, None, "active", now_iso),
            ]
            conn.executemany(
                """
                INSERT INTO projects (name, description, department_id, manager_id, start_date, end_date, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                projects,
            )

        member_count = conn.execute("SELECT COUNT(*) FROM project_members").fetchone()[0]
        if member_count == 0:
            project_ids = [r[0] for r in conn.execute("SELECT id FROM projects ORDER BY id").fetchall()]
            staff_ids = [r[0] for r in conn.execute("SELECT id FROM users WHERE role IN ('manager','staff') ORDER BY id").fetchall()]
            joined_at = datetime.now(timezone.utc).isoformat()
            rows = []
            for p in project_ids:
                for u in staff_ids:
                    role = "manager" if u == staff_ids[0] else "member"
                    rows.append((p, u, role, joined_at))
            conn.executemany(
                "INSERT OR IGNORE INTO project_members (project_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)",
                rows,
            )

        sprint_count = conn.execute("SELECT COUNT(*) FROM sprints").fetchone()[0]
        if sprint_count == 0:
            project_id = conn.execute("SELECT id FROM projects ORDER BY id LIMIT 1").fetchone()[0]
            start = datetime.now(timezone.utc)
            end = start + timedelta(days=14)
            conn.execute(
                """
                INSERT INTO sprints (project_id, name, goal, start_date, end_date, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?)
                """,
                (
                    project_id,
                    "Seed Sprint 1",
                    "Deliver baseline modules",
                    start.isoformat(),
                    end.isoformat(),
                    start.isoformat(),
                ),
            )

        task_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if task_count == 0:
            now = datetime.now(timezone.utc)
            project_ids = [r[0] for r in conn.execute("SELECT id FROM projects ORDER BY id").fetchall()]
            rows = []
            for i in range(1, 51):
                assignee_id = 2 if i % 2 == 0 else 3
                project_id = project_ids[i % len(project_ids)] if project_ids else None
                sprint_id = None
                story_points = (i % 8) + 1
                difficulty = "easy" if i % 3 == 0 else "medium" if i % 3 == 1 else "hard"
                deadline = (now + timedelta(days=(i % 20) - 10)).isoformat()
                created_at = (now - timedelta(days=15)).isoformat()
                updated_at = now.isoformat()

                if i % 5 == 0:
                    status = "done"
                    completed_at = (now - timedelta(days=i % 4)).isoformat()
                elif i % 5 == 1:
                    status = "doing"
                    completed_at = None
                else:
                    status = "todo"
                    completed_at = None

                rows.append(
                    (
                        f"Task {i}",
                        f"Auto-generated task {i}",
                        assignee_id,
                        project_id,
                        sprint_id,
                        story_points,
                        difficulty,
                        status,
                        deadline,
                        completed_at,
                        created_at,
                        updated_at,
                    )
                )

            conn.executemany(
                """
                INSERT INTO tasks (title, description, assignee_id, project_id, sprint_id, story_points, difficulty, status, deadline, completed_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

        cap_count = conn.execute("SELECT COUNT(*) FROM sprint_capacity_plans").fetchone()[0]
        if cap_count == 0:
            sprint_id = conn.execute("SELECT id FROM sprints ORDER BY id LIMIT 1").fetchone()[0]
            members = conn.execute("SELECT user_id FROM project_members ORDER BY id").fetchall()
            now_iso = datetime.now(timezone.utc).isoformat()
            cap_rows = [(sprint_id, int(m[0]), 40.0, 24.0, now_iso) for m in members[:3]]
            conn.executemany(
                """
                INSERT INTO sprint_capacity_plans (sprint_id, user_id, capacity_hours, allocated_hours, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                cap_rows,
            )

        risk_count = conn.execute("SELECT COUNT(*) FROM project_risks").fetchone()[0]
        if risk_count == 0:
            project_id = conn.execute("SELECT id FROM projects ORDER BY id LIMIT 1").fetchone()[0]
            manager_id = conn.execute("SELECT id FROM users WHERE role = 'manager' ORDER BY id LIMIT 1").fetchone()[0]
            conn.execute(
                """
                INSERT INTO project_risks (project_id, title, description, probability, impact, mitigation_plan, owner_user_id, status, created_at)
                VALUES (?, ?, ?, 'medium', 'high', ?, ?, 'open', ?)
                """,
                (
                    project_id,
                    "Scope creep on sprint backlog",
                    "Potential uncontrolled feature additions",
                    "Freeze scope and enforce change control",
                    manager_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

        weekly_count = conn.execute("SELECT COUNT(*) FROM weekly_status_updates").fetchone()[0]
        if weekly_count == 0:
            project_id = conn.execute("SELECT id FROM projects ORDER BY id LIMIT 1").fetchone()[0]
            sprint_id = conn.execute("SELECT id FROM sprints ORDER BY id LIMIT 1").fetchone()[0]
            manager_id = conn.execute("SELECT id FROM users WHERE role = 'manager' ORDER BY id LIMIT 1").fetchone()[0]
            conn.execute(
                """
                INSERT INTO weekly_status_updates (project_id, sprint_id, week_label, progress_percent, rag_status, summary, next_steps, blocker, created_by, created_at)
                VALUES (?, ?, ?, ?, 'green', ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    sprint_id,
                    "2026-W16",
                    35.0,
                    "Sprint is on track with stable velocity",
                    "Complete KPI report integration",
                    "None",
                    manager_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    return {"message": "Seed data initialized"}
