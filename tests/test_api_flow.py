from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt

from app.database import init_db
from app.main import app
from app.repository import create_user
from app.settings import settings


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _bootstrap_users() -> tuple[int, int, int]:
    init_db()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    admin = create_user("Admin Test", f"admin.{ts}@local.test", "admin", "IT")
    manager = create_user("Manager Test", f"manager.{ts}@local.test", "manager", "PMO")
    staff = create_user("Staff Test", f"staff.{ts}@local.test", "staff", "Engineering")
    return int(admin["id"]), int(manager["id"]), int(staff["id"])


def test_end_to_end_rbac_kpi_and_reports() -> None:
    admin_id, manager_id, staff_id = _bootstrap_users()

    # health check is public
    h = client.get("/health")
    assert h.status_code == 200

    # seed requires auth and admin role
    unauth_seed = client.post("/seed/init")
    assert unauth_seed.status_code == 401

    # create bootstrap admin directly through DB-less flow by creating via endpoint is now admin-only,
    # so we rely on seeded users: user id=1 is manager in seed, not admin.
    # First create an admin by temporarily trying as manager should fail.
    create_admin_fail = client.post(
        "/users",
        headers=_hdr(manager_id),
        json={"full_name": "Admin User", "email": "admin@example.com", "role": "admin", "department": "IT"},
    )
    assert create_admin_fail.status_code == 403

    seed_ok = client.post("/seed/init", headers=_hdr(admin_id))
    assert seed_ok.status_code == 200

    dep_resp = client.post(
        "/departments",
        headers=_hdr(manager_id),
        json={
            "name": f"Integration QA {datetime.now(timezone.utc).strftime('%H%M%S%f')}",
            "code": f"QA{datetime.now(timezone.utc).strftime('%H%M%S')}",
        },
    )
    assert dep_resp.status_code == 200
    department_id = dep_resp.json()["id"]

    project_resp = client.post(
        "/projects",
        headers=_hdr(manager_id),
        json={
            "name": "Cross-Team Pilot",
            "description": "Pilot project",
            "department_id": department_id,
            "manager_id": manager_id,
            "status": "active",
        },
    )
    assert project_resp.status_code == 200
    project_id = project_resp.json()["id"]

    add_member_resp = client.post(
        f"/projects/{project_id}/members",
        headers=_hdr(manager_id),
        json={"user_id": staff_id, "role": "member"},
    )
    assert add_member_resp.status_code == 200

    sprint_resp = client.post(
        f"/projects/{project_id}/sprints",
        headers=_hdr(manager_id),
        json={
            "name": "Sprint 1",
            "goal": "Ship project core",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        },
    )
    assert sprint_resp.status_code == 200
    sprint_id = sprint_resp.json()["id"]

    # Create task as manager
    deadline = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    task_resp = client.post(
        "/tasks",
        headers=_hdr(manager_id),
        json={
            "title": "Prepare KPI review",
            "description": "Collect sprint outcomes",
            "assignee_id": staff_id,
            "project_id": project_id,
            "story_points": 5,
            "difficulty": "medium",
            "deadline": deadline,
        },
    )
    assert task_resp.status_code == 200
    task_id = task_resp.json()["id"]

    # Staff can only update own task
    update_ok = client.patch(f"/tasks/{task_id}/status", headers=_hdr(staff_id), json={"status": "doing"})
    assert update_ok.status_code == 200

    update_forbidden = client.patch(f"/tasks/{task_id}/status", headers=_hdr(admin_id), json={"status": "done"})
    assert update_forbidden.status_code == 200

    other_staff = create_user("Other Staff", f"other.{datetime.now(timezone.utc).timestamp()}@local.test", "staff", "Engineering")
    update_forbidden = client.patch(
        f"/tasks/{task_id}/status",
        headers=_hdr(int(other_staff["id"])),
        json={"status": "done"},
    )
    assert update_forbidden.status_code == 403

    # KPI report endpoints require privileged role
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    rpt_forbidden = client.get(f"/reports/kpi.csv?month={month}", headers=_hdr(staff_id))
    assert rpt_forbidden.status_code == 403

    rpt_ok = client.get(f"/reports/kpi.csv?month={month}", headers=_hdr(manager_id))
    assert rpt_ok.status_code == 200
    assert "user_id,user_name,month" in rpt_ok.text

    project_tasks = client.get(
        f"/tasks?project_id={project_id}",
        headers=_hdr(manager_id),
    )
    assert project_tasks.status_code == 200
    assert any(int(t.get("id")) == int(task_id) for t in project_tasks.json())

    assign_resp = client.post(
        f"/projects/{project_id}/sprints/{sprint_id}/tasks",
        headers=_hdr(manager_id),
        json={"task_ids": [task_id]},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["updated"] >= 1

    sprint_status_resp = client.patch(
        f"/sprints/{sprint_id}/status",
        headers=_hdr(manager_id),
        json={"status": "active"},
    )
    assert sprint_status_resp.status_code == 200

    progress_resp = client.get(f"/projects/{project_id}/progress", headers=_hdr(manager_id))
    assert progress_resp.status_code == 200
    assert progress_resp.json()["project_id"] == project_id

    burndown_resp = client.get(f"/sprints/{sprint_id}/burndown", headers=_hdr(manager_id))
    assert burndown_resp.status_code == 200
    assert len(burndown_resp.json()) >= 1

    capacity_resp = client.post(
        f"/sprints/{sprint_id}/capacity",
        headers=_hdr(manager_id),
        json={"user_id": staff_id, "capacity_hours": 40, "allocated_hours": 28},
    )
    assert capacity_resp.status_code == 200

    list_capacity_resp = client.get(f"/sprints/{sprint_id}/capacity", headers=_hdr(manager_id))
    assert list_capacity_resp.status_code == 200
    assert len(list_capacity_resp.json()) >= 1

    velocity_resp = client.get(f"/projects/{project_id}/velocity", headers=_hdr(manager_id))
    assert velocity_resp.status_code == 200
    assert len(velocity_resp.json()) >= 1

    risk_resp = client.post(
        f"/projects/{project_id}/risks",
        headers=_hdr(manager_id),
        json={
            "title": "API performance degradation",
            "description": "Heavy dashboard load can increase response time",
            "probability": "medium",
            "impact": "high",
            "mitigation_plan": "Add caching and index tuning",
            "owner_user_id": manager_id,
            "status": "open",
        },
    )
    assert risk_resp.status_code == 200

    list_risk_resp = client.get(f"/projects/{project_id}/risks", headers=_hdr(manager_id))
    assert list_risk_resp.status_code == 200
    assert len(list_risk_resp.json()) >= 1

    weekly_resp = client.post(
        f"/projects/{project_id}/weekly-status",
        headers=_hdr(manager_id),
        json={
            "sprint_id": sprint_id,
            "week_label": "2026-W17",
            "progress_percent": 52,
            "rag_status": "green",
            "summary": "Progress aligned with sprint baseline",
            "next_steps": "Finalize reporting module",
            "blocker": "None",
        },
    )
    assert weekly_resp.status_code == 200

    list_weekly_resp = client.get(f"/projects/{project_id}/weekly-status", headers=_hdr(manager_id))
    assert list_weekly_resp.status_code == 200
    assert len(list_weekly_resp.json()) >= 1

    proj_csv = client.get("/reports/projects/progress.csv", headers=_hdr(manager_id))
    assert proj_csv.status_code == 200
    assert "project_id,total_tasks" in proj_csv.text

    proj_xlsx = client.get("/reports/projects/progress.xlsx", headers=_hdr(manager_id))
    assert proj_xlsx.status_code == 200

    outsider = create_user(
        "Outsider Staff",
        f"outsider.{datetime.now(timezone.utc).timestamp()}@local.test",
        "staff",
        "Engineering",
    )
    outsider_projects = client.get("/projects", headers=_hdr(int(outsider["id"])))
    assert outsider_projects.status_code == 200
    assert all(int(p["id"]) != int(project_id) for p in outsider_projects.json())

    sprint_review = client.get(f"/sprints/{sprint_id}/review-summary", headers=_hdr(manager_id))
    assert sprint_review.status_code == 200
    assert sprint_review.json()["sprint_id"] == sprint_id

    sprint_review_csv = client.get(f"/reports/sprints/{sprint_id}/review.csv", headers=_hdr(manager_id))
    assert sprint_review_csv.status_code == 200
    assert "sprint_id,project_id" in sprint_review_csv.text

    sprint_review_xlsx = client.get(f"/reports/sprints/{sprint_id}/review.xlsx", headers=_hdr(manager_id))
    assert sprint_review_xlsx.status_code == 200

    portfolio = client.get("/portfolio/summary", headers=_hdr(manager_id))
    assert portfolio.status_code == 200
    assert len(portfolio.json()) >= 1

    portfolio_csv = client.get("/reports/portfolio/summary.csv", headers=_hdr(manager_id))
    assert portfolio_csv.status_code == 200
    assert "project_id,project_name" in portfolio_csv.text

    portfolio_xlsx = client.get("/reports/portfolio/summary.xlsx", headers=_hdr(manager_id))
    assert portfolio_xlsx.status_code == 200

    queue_resp = client.post(
        "/integrations/teams/proactive/queue?message=Weekly%20summary%20is%20ready&max_attempts=2",
        headers=_hdr(manager_id),
    )
    assert queue_resp.status_code == 200
    queue_item = queue_resp.json()
    notif_id = int(queue_item["id"])
    assert int(queue_item["max_attempts"]) == 2

    queue_list_resp = client.get("/integrations/teams/proactive/queue", headers=_hdr(manager_id))
    assert queue_list_resp.status_code == 200
    assert len(queue_list_resp.json()) >= 1

    process_queue_resp = client.post("/integrations/teams/proactive/process", headers=_hdr(manager_id))
    assert process_queue_resp.status_code == 200
    assert "processed" in process_queue_resp.json()

    # With webhook likely not configured in test env, first run should schedule retry.
    queued_after_first = client.get("/integrations/teams/proactive/queue?status=queued&limit=200", headers=_hdr(manager_id))
    assert queued_after_first.status_code == 200
    assert any(int(x["id"]) == notif_id for x in queued_after_first.json())

    # Force immediate retry by resetting next_retry_at in DB for this item.
    from app.database import get_connection

    with get_connection() as conn:
        conn.execute("UPDATE notification_queue SET next_retry_at = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), notif_id))

    process_queue_resp_2 = client.post("/integrations/teams/proactive/process", headers=_hdr(manager_id))
    assert process_queue_resp_2.status_code == 200

    failed_list_resp = client.get("/integrations/teams/proactive/queue?status=failed&limit=200", headers=_hdr(manager_id))
    assert failed_list_resp.status_code == 200
    assert any(int(x["id"]) == notif_id for x in failed_list_resp.json())

    requeue_resp = client.post(f"/integrations/teams/proactive/requeue/{notif_id}", headers=_hdr(manager_id))
    assert requeue_resp.status_code == 200
    assert requeue_resp.json()["status"] == "queued"

    completion_resp = client.get("/plan/completion", headers=_hdr(manager_id))
    assert completion_resp.status_code == 200
    completion_payload = completion_resp.json()
    assert "completion_percent" in completion_payload
    assert 0 <= completion_payload["completion_percent"] <= 100

    readiness_resp = client.get("/monitoring/readiness")
    assert readiness_resp.status_code == 200

    prod_tab_resp = client.get("/teams/tab/prod")
    assert prod_tab_resp.status_code == 200
    assert "TeamsWork Production Tab" in prod_tab_resp.text

    metrics_resp = client.get("/monitoring/metrics", headers=_hdr(manager_id))
    assert metrics_resp.status_code == 200
    assert "users" in metrics_resp.json()

    tab_resp = client.get("/teams/tab")
    assert tab_resp.status_code == 200
    assert "TeamsWork Integration Tab" in tab_resp.text

    reminder_resp = client.post("/integrations/teams/reminders/run", headers=_hdr(manager_id))
    assert reminder_resp.status_code == 200
    payload = reminder_resp.json()
    assert "due_within_24h" in payload
    assert "sent" in payload

    bot_help = client.post(
        "/integrations/teams/bot/messages",
        json={"type": "message", "text": "/help"},
    )
    assert bot_help.status_code == 200
    assert "commands" in bot_help.json().get("text", "")


def test_issue_jwt_and_call_authorized_endpoint() -> None:
    admin_id, _, _ = _bootstrap_users()
    settings.auth_disable_jwt_validation = False
    settings.auth_allow_header_fallback = False
    settings.auth_jwt_secret = "unit-test-secret"
    settings.auth_jwt_algorithm = "HS256"

    payload = {
        "sub": str(admin_id),
        "uid": int(admin_id),
        "role": "admin",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 1800,
    }
    access_token = jwt.encode(payload, settings.auth_jwt_secret, algorithm=settings.auth_jwt_algorithm)
    assert access_token

    metrics_resp = client.get("/monitoring/metrics", headers={"Authorization": f"Bearer {access_token}"})
    assert metrics_resp.status_code == 200

    unauthorized = client.get("/monitoring/metrics")
    assert unauthorized.status_code == 401

    settings.auth_disable_jwt_validation = True
    settings.auth_allow_header_fallback = True
