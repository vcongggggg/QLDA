from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import create_project, create_task, create_user, list_tasks


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _unique(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"


def test_task_export_honors_filters_and_returns_csv_xlsx() -> None:
    init_db()
    marker = _unique("task-export")
    manager = create_user(f"{marker} Manager", f"{marker}.manager@example.com", "manager", "PMO")
    staff = create_user(f"{marker} Staff", f"{marker}.staff@example.com", "staff", "Engineering")
    project = create_project(f"{marker} Project", None, None, int(manager["id"]), None, None, "active")
    deadline = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    included = create_task(f"{marker} Included", None, int(staff["id"]), int(project["id"]), None, 3, "medium", deadline)
    create_task(f"{marker} Other", None, int(staff["id"]), None, None, 2, "easy", deadline)

    csv_resp = client.get(f"/reports/tasks.csv?project_id={project['id']}", headers=_hdr(int(manager["id"])))
    assert csv_resp.status_code == 200
    assert csv_resp.headers["content-type"].startswith("text/csv")
    assert str(included["id"]) in csv_resp.text
    assert f"{marker} Other" not in csv_resp.text

    xlsx_resp = client.get(f"/reports/tasks.xlsx?project_id={project['id']}", headers=_hdr(int(manager["id"])))
    assert xlsx_resp.status_code == 200
    assert xlsx_resp.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert xlsx_resp.content.startswith(b"PK")


def test_task_import_validates_all_rows_before_insert() -> None:
    init_db()
    marker = _unique("task-import")
    manager = create_user(f"{marker} Manager", f"{marker}.manager@example.com", "manager", "PMO")
    staff = create_user(f"{marker} Staff", f"{marker}.staff@example.com", "staff", "Engineering")
    before = len(list_tasks())

    bad_csv = (
        "title,description,assignee_email,story_points,difficulty,priority,labels,deadline\n"
        f"Good task,Valid,{staff['email']},3,medium,high,alpha;beta,{(datetime.now(timezone.utc) + timedelta(days=5)).isoformat()}\n"
        f"Bad task,Invalid,missing@example.com,3,medium,high,,{(datetime.now(timezone.utc) + timedelta(days=6)).isoformat()}\n"
    )
    invalid = client.post(
        "/tasks/import",
        headers=_hdr(int(manager["id"])),
        files={"file": ("tasks.csv", bad_csv.encode("utf-8"), "text/csv")},
    )
    assert invalid.status_code == 400
    assert len(list_tasks()) == before

    good_csv = (
        "title,description,assignee_email,story_points,difficulty,priority,labels,deadline\n"
        f"Imported task,Valid,{staff['email']},3,medium,high,alpha;beta,{(datetime.now(timezone.utc) + timedelta(days=5)).isoformat()}\n"
    )
    valid = client.post(
        "/tasks/import",
        headers=_hdr(int(manager["id"])),
        files={"file": ("tasks.csv", good_csv.encode("utf-8"), "text/csv")},
    )
    assert valid.status_code == 200
    assert valid.json()["created_count"] == 1
    assert valid.json()["tasks"][0]["labels"] == ["alpha", "beta"]
