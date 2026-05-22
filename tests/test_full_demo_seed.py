from app.database import get_connection
from app.rag import query_rag
from app.seed import DEMO_PROJECT_NAMES, seed_full_demo_data, seed_rag_demo_data
from app.settings import settings


IMPORTANT_TABLES = (
    "users",
    "departments",
    "projects",
    "sprints",
    "project_members",
    "tasks",
    "sprint_capacity_plans",
    "project_risks",
    "weekly_status_updates",
    "kpi_adjustments",
    "task_comments",
    "app_notifications",
    "notification_queue",
    "audit_logs",
    "ai_task_drafts",
    "rag_documents",
    "rag_chunks",
)


def _counts() -> dict[str, int]:
    with get_connection() as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"])
            for table in IMPORTANT_TABLES
        }


def _user(email: str) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT id, role FROM users WHERE LOWER(email) = ?", (email.lower(),)).fetchone()
    assert row is not None
    return {"id": int(row["id"]), "role": row["role"]}


def test_full_demo_seed_is_idempotent_and_scoped(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rag_embedding_enabled", False)

    first = seed_full_demo_data(mode="upsert")
    first_counts = _counts()
    second = seed_full_demo_data(mode="upsert")
    second_counts = _counts()

    assert first["mode"] == "upsert"
    assert second["warnings"] == []
    assert second_counts == first_counts
    assert second_counts["projects"] == 3
    assert second_counts["sprints"] == 21
    assert second_counts["tasks"] == 100
    assert second_counts["rag_documents"] == 12
    assert second_counts["ai_task_drafts"] == 6

    with get_connection() as conn:
        projects = {
            row["name"]
            for row in conn.execute("SELECT name FROM projects ORDER BY name").fetchall()
        }
        duplicate_docs = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM (
                SELECT project_id, source_label
                FROM rag_documents
                GROUP BY project_id, source_label
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()["c"]
        role_rows = {
            row["email"]: (row["role"], row["role_id"], row["department_id"])
            for row in conn.execute(
                """
                SELECT email, role, role_id, department_id
                FROM users
                WHERE email IN ('admin@teamswork.local', 'leader@teamswork.local', 'auditor@teamswork.local')
                """
            ).fetchall()
        }

    assert projects == set(DEMO_PROJECT_NAMES)
    assert int(duplicate_docs) == 0
    assert role_rows["admin@teamswork.local"][0:2] == ("admin", "ADMIN")
    assert role_rows["leader@teamswork.local"][0:2] == ("manager", "LEADER")
    assert role_rows["auditor@teamswork.local"][0:2] == ("hr", "AUDITOR")
    assert all(row[2] is not None for row in role_rows.values())


def test_rag_demo_seed_is_idempotent_and_lexical_queries_work(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rag_embedding_enabled", False)

    seed_full_demo_data(mode="upsert")
    first = seed_rag_demo_data(mode="upsert")
    second = seed_rag_demo_data(mode="upsert")

    assert first["counts"]["rag_documents"] == 12
    assert second["counts"]["rag_documents"] == 12

    users = {
        "admin": _user("admin@teamswork.local"),
        "manager": _user("phuc.tran@teamswork.example.com"),
        "member": _user("khoa.le@teamswork.example.com"),
        "hr": _user("hr@teamswork.local"),
        "auditor": _user("auditor@teamswork.local"),
    }
    queries = (
        ("Member có thể xem những chức năng nào?", users["member"]),
        ("Manager theo dõi tiến độ task của team như thế nào?", users["manager"]),
        ("Admin quản lý người dùng và phòng ban như thế nào?", users["admin"]),
        ("KPI được tính như thế nào?", users["manager"]),
        ("Dự án demo hiện tại có những sprint/task nào?", users["member"]),
        ("Khi task bị quá hạn thì xử lý thế nào?", users["manager"]),
        ("Auditor có quyền xem gì?", users["auditor"]),
        ("HR có thể xem KPI nhân sự không?", users["hr"]),
    )

    for text, current_user in queries:
        matches = query_rag(text, limit=3, current_user=current_user)
        assert matches, text
        assert all(match["source_label"] for match in matches)


def test_full_demo_reset_is_guarded_in_production(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")

    try:
        seed_full_demo_data(mode="reset")
    except RuntimeError as exc:
        assert "Refusing demo seed reset" in str(exc)
    else:
        raise AssertionError("production reset should be guarded")
