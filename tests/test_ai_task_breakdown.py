from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.ai_task_breakdown import breakdown_requirements, breakdown_requirements_locally
from app.database import init_db
from app.main import app
from app.repository import create_user
from app.schemas import TaskBreakdownItem
from app.settings import settings


client = TestClient(app)


def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}


def _bootstrap() -> tuple[int, int, int]:
    init_db()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    admin = create_user("AI Admin", f"ai.admin.{stamp}@example.com", "admin", "PMO")
    manager = create_user("AI Manager", f"ai.manager.{stamp}@example.com", "manager", "PMO")
    staff = create_user("AI Staff", f"ai.staff.{stamp}@example.com", "staff", "Engineering")
    return int(admin["id"]), int(manager["id"]), int(staff["id"])


def test_local_breakdown_extracts_actionable_tasks() -> None:
    text = """
    Hệ thống cần cho phép quản lý tạo task, kéo thả Kanban và xuất báo cáo KPI.
    Yêu cầu tích hợp Microsoft Teams để người dùng mở dashboard trong tab Teams.
    """

    items = breakdown_requirements_locally(text, max_tasks=5)

    assert len(items) >= 2
    assert all(item.title for item in items)
    assert {item.difficulty for item in items}.issubset({"easy", "medium", "hard"})
    assert all(1 <= item.story_points <= 13 for item in items)


def test_ai_breakdown_uses_fallback_model_when_primary_fails(monkeypatch) -> None:
    settings.ai_provider = "openai_compatible"
    settings.ai_api_key = "ollama"
    settings.ai_model = "qwen3:8b"
    settings.ai_fallback_model = "qwen2.5:7b"
    called_models: list[str | None] = []

    def fake_breakdown(text: str, project_context: str | None, max_tasks: int, model: str | None = None):
        called_models.append(model)
        if model == "qwen3:8b":
            raise RuntimeError("primary unavailable")
        return [
            TaskBreakdownItem(
                title="Fallback task",
                description=text,
                story_points=3,
                difficulty="medium",
                deadline_offset_days=7,
            )
        ]

    monkeypatch.setattr("app.ai_task_breakdown._breakdown_with_openai_compatible", fake_breakdown)

    result = breakdown_requirements("Tạo báo cáo KPI", max_tasks=3)

    assert result.source == "openai_compatible"
    assert result.items[0].title == "Fallback task"
    assert called_models == ["qwen3:8b", "qwen2.5:7b"]
    assert any("trying fallback model qwen2.5:7b" in warning for warning in result.warnings)


def test_task_breakdown_preview_and_import_flow() -> None:
    settings.ai_api_key = ""
    _admin_id, manager_id, staff_id = _bootstrap()
    text = """
    Xây dựng module AI phân rã yêu cầu từ tài liệu docx.
    Người quản lý có thể xem danh sách task đề xuất và chọn task để import vào Kanban.
    Hệ thống cần ghi audit log sau khi tạo task.
    """

    preview = client.post(
        "/ai/task-breakdown",
        headers=_hdr(manager_id),
        json={"text": text, "max_tasks": 4},
    )
    assert preview.status_code == 200
    payload = preview.json()
    assert payload["source"] in {"heuristic", "openai_compatible"}
    assert len(payload["items"]) >= 2
    assert payload["items"][0]["title"]

    import_resp = client.post(
        "/ai/task-breakdown/import",
        headers=_hdr(manager_id),
        json={
            "assignee_id": staff_id,
            "project_id": None,
            "sprint_id": None,
            "items": payload["items"][:2],
        },
    )
    assert import_resp.status_code == 200
    imported = import_resp.json()
    assert imported["created_count"] == 2
    assert len(imported["tasks"]) == 2
    assert all(task["assignee_id"] == staff_id for task in imported["tasks"])


def test_staff_cannot_generate_or_import_ai_tasks() -> None:
    settings.ai_api_key = ""
    _admin_id, _manager_id, staff_id = _bootstrap()

    preview = client.post(
        "/ai/task-breakdown",
        headers=_hdr(staff_id),
        json={"text": "Tạo dashboard KPI", "max_tasks": 3},
    )

    assert preview.status_code == 403
