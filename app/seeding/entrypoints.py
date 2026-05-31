from app.seeding.shared import *

def seed_data() -> dict:
    """Legacy destructive demo reset used by /seed/init and existing tests."""
    with get_connection() as conn:
        reset_demo_data(conn)
        department_ids = seed_departments(conn)
        user_ids = seed_users(conn)
        project_ids = seed_projects(conn, department_ids, user_ids)
        sprint_ids = seed_sprints(conn, project_ids)
        seed_members(conn, project_ids, user_ids)
        seed_tasks(conn, project_ids, sprint_ids, user_ids)
        seed_capacity(conn, project_ids, sprint_ids)
        seed_risks(conn, project_ids, user_ids)
        seed_weekly_updates(conn, project_ids, sprint_ids, user_ids)
        seed_kpi_adjustments(conn, user_ids)
        seed_notifications_comments_audit(conn, user_ids)
        seed_ai_and_rag(conn, project_ids, user_ids)
        counts = _summary_counts(conn)
    return {
        "message": "Demo data reset and seeded",
        "demo_now": DEMO_NOW_ISO,
        "counts": counts,
    }
