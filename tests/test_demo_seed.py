from app.database import get_connection, init_db
from app.main import app
from app.repository import create_project, create_task, create_user
from app.seed import USERS, seed_data
from app.settings import settings
from fastapi.testclient import TestClient


DEMO_EMAILS = {email for _name, email, _aad_id, _role, _department in USERS}
DIRTY_EXACT_NAMES = (
    "Task Detail Staff",
    "Teams Staff",
    "Ops Staff",
    "Teams Manager",
    "Notification Staff",
    "Assigned Staff",
)


def test_demo_seed_resets_business_data_and_preserves_rbac(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "demo_seed.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")

    init_db()
    _insert_dirty_kpi_data()

    first = seed_data()
    second = seed_data()

    assert first["counts"]["users"] == 20
    assert second["counts"]["users"] == 20
    assert second["counts"]["departments"] == 7
    assert second["counts"]["projects"] == 3
    assert second["counts"]["sprints"] == 21
    assert second["counts"]["tasks"] == 100
    assert second["counts"]["project_risks"] >= 6
    assert second["counts"]["weekly_status_updates"] >= 12
    assert second["counts"]["kpi_adjustments"] == 5
    assert second["counts"]["task_comments"] == 250
    assert second["counts"]["app_notifications"] == 7
    assert second["counts"]["notification_queue"] == 4
    assert second["counts"]["ai_task_drafts"] == 4
    assert second["counts"]["rag_documents"] == 4
    assert second["counts"]["rag_chunks"] == 8

    with get_connection() as conn:
        roles = {row["slug"] for row in conn.execute("SELECT slug FROM roles").fetchall()}
        projects = {row["name"] for row in conn.execute("SELECT name FROM projects").fetchall()}
        status_counts = {
            row["status"]: int(row["c"])
            for row in conn.execute("SELECT status, COUNT(*) AS c FROM tasks GROUP BY status").fetchall()
        }
        done_on_time = conn.execute(
            "SELECT COUNT(*) AS c FROM tasks WHERE status = 'done' AND completed_at <= deadline"
        ).fetchone()["c"]
        done_late = conn.execute(
            "SELECT COUNT(*) AS c FROM tasks WHERE status = 'done' AND completed_at > deadline"
        ).fetchone()["c"]
        overdue_open = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM tasks
            WHERE status != 'done' AND deadline < '2026-08-10T09:00:00+00:00'
            """
        ).fetchone()["c"]
        kpi_months = {
            row["month"]
            for row in conn.execute(
                "SELECT DISTINCT substr(deadline, 1, 7) AS month FROM tasks ORDER BY month"
            ).fetchall()
        }
        dirty_users = conn.execute(
            """
            SELECT full_name
            FROM users
            WHERE full_name LIKE ?
               OR full_name LIKE ?
               OR full_name LIKE ?
               OR full_name IN (?, ?, ?, ?, ?, ?)
            """,
            ("workload-%", "filter-%", "% Test", *DIRTY_EXACT_NAMES),
        ).fetchall()
        imported_drafts = conn.execute(
            "SELECT COUNT(*) AS c FROM ai_task_drafts WHERE status = 'imported'"
        ).fetchone()["c"]
        demo_doc = conn.execute(
            "SELECT id FROM rag_documents WHERE source_label = 'demo-readiness-checklist'"
        ).fetchone()
        min_comments = conn.execute(
            """
            SELECT MIN(comment_count) AS c
            FROM (
                SELECT task_id, COUNT(*) AS comment_count
                FROM task_comments
                GROUP BY task_id
            )
            """
        ).fetchone()["c"]
        sample_comment = conn.execute(
            """
            SELECT t.title, tc.body
            FROM tasks t
            JOIN task_comments tc ON tc.task_id = t.id
            ORDER BY t.id, tc.id
            LIMIT 1
            """
        ).fetchone()

    assert {"admin", "manager", "staff", "hr"}.issubset(roles)
    assert projects == {
        "TeamsWork Internal PM & KPI",
        "ShopMate Mobile Commerce",
        "FieldOps Service Mobile",
    }
    assert status_counts == {"doing": 30, "done": 55, "todo": 15}
    assert int(done_on_time) == 40
    assert int(done_late) == 15
    assert int(overdue_open) == 10
    assert kpi_months == {"2026-06", "2026-07", "2026-08"}
    assert dirty_users == []
    assert int(imported_drafts) == 2
    assert demo_doc is not None
    assert int(min_comments) >= 2
    assert sample_comment is not None
    assert sample_comment["title"] in sample_comment["body"]

    client = TestClient(app)
    headers = {"X-User-Id": str(_seeded_user_id("an.nguyen@teamswork.example.com"))}
    overdue_resp = client.get(
        "/tasks?overdue=true&as_of=2026-08-10T09:00:00%2B00:00",
        headers=headers,
    )
    assert overdue_resp.status_code == 200
    assert len(overdue_resp.json()) == 10

    dashboard_resp = client.get(
        "/dashboard/summary?month=2026-08&as_of=2026-08-10T09:00:00%2B00:00",
        headers=headers,
    )
    assert dashboard_resp.status_code == 200
    assert dashboard_resp.json()["overdue_tasks"] == 10

    may_kpi_resp = client.get("/kpi/monthly?month=2026-05", headers=headers)
    assert may_kpi_resp.status_code == 200
    assert may_kpi_resp.json() == []

    demo_user_ids = _seeded_user_ids(DEMO_EMAILS)
    for month in ("2026-06", "2026-07", "2026-08"):
        kpi_resp = client.get(f"/kpi/monthly?month={month}", headers=headers)
        assert kpi_resp.status_code == 200
        assert {int(row["user_id"]) for row in kpi_resp.json()}.issubset(demo_user_ids)


def _seeded_user_id(email: str) -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    assert row is not None
    return int(row["id"])


def _seeded_user_ids(emails: set[str]) -> set[int]:
    placeholders = ", ".join("?" for _ in emails)
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT id FROM users WHERE email IN ({placeholders})",
            tuple(sorted(emails)),
        ).fetchall()
    return {int(row["id"]) for row in rows}


def _insert_dirty_kpi_data() -> None:
    manager = create_user("Teams Manager", "dirty.manager@example.com", "manager", "PMO")
    staff_names = (
        "workload-20260521000000 Under",
        "workload-20260521000000 Missing Capacity",
        "workload-20260521000000 Over",
        "filter-20260521000000 Staff",
        *DIRTY_EXACT_NAMES,
        "Legacy Test",
    )
    project = create_project("Dirty KPI Project", None, None, int(manager["id"]), None, None, "active")
    for index, name in enumerate(staff_names):
        staff = create_user(
            name,
            f"dirty.staff.{index}@example.com",
            "staff",
            "Engineering",
        )
        create_task(
            f"Dirty May task {index}",
            None,
            int(staff["id"]),
            int(project["id"]),
            None,
            1,
            "easy",
            "2026-05-21T18:00:00+00:00",
        )
