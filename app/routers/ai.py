from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.ai_task_breakdown import breakdown_requirements, extract_docx_text
from app.auth import get_current_user, require_roles
from app.repository import create_audit_log, create_task, project_exists, sprint_exists, user_exists
from app.schemas import (
    TaskBreakdownRequest,
    TaskBreakdownResponse,
    TaskImportRequest,
    TaskImportResponse,
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/task-breakdown", response_model=TaskBreakdownResponse)
def task_breakdown_endpoint(
    payload: TaskBreakdownRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    result = breakdown_requirements(payload.text, payload.project_context, payload.max_tasks)
    create_audit_log(current_user["id"], "preview", "ai_task_breakdown", None, f"items={len(result.items)} source={result.source}")
    return {"source": result.source, "items": result.items, "warnings": result.warnings}


@router.post("/task-breakdown/docx", response_model=TaskBreakdownResponse)
async def task_breakdown_docx_endpoint(
    file: UploadFile = File(...),
    project_context: str | None = Form(default=None),
    max_tasks: int = Form(default=8),
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    filename = (file.filename or "").lower()
    if not filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="only .docx files are supported")
    if max_tasks < 1 or max_tasks > 30:
        raise HTTPException(status_code=400, detail="max_tasks must be between 1 and 30")
    try:
        text = extract_docx_text(await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="docx does not contain enough text")
    result = breakdown_requirements(text, project_context, max_tasks)
    create_audit_log(current_user["id"], "preview", "ai_task_breakdown_docx", None, f"items={len(result.items)} source={result.source}")
    return {"source": result.source, "items": result.items, "warnings": result.warnings}


@router.post("/task-breakdown/import", response_model=TaskImportResponse)
def import_ai_tasks_endpoint(
    payload: TaskImportRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    if not user_exists(payload.assignee_id):
        raise HTTPException(status_code=404, detail="assignee not found")
    if payload.project_id is not None and not project_exists(payload.project_id):
        raise HTTPException(status_code=404, detail="project not found")
    if payload.sprint_id is not None and not sprint_exists(payload.sprint_id):
        raise HTTPException(status_code=404, detail="sprint not found")

    base_deadline = payload.base_deadline or datetime.now(timezone.utc)
    created: list[dict] = []
    for item in payload.items:
        if not item.selected:
            continue
        if item.difficulty not in {"easy", "medium", "hard"}:
            raise HTTPException(status_code=400, detail="invalid difficulty")
        deadline = base_deadline + timedelta(days=item.deadline_offset_days)
        task = create_task(
            title=item.title,
            description=item.description,
            assignee_id=payload.assignee_id,
            project_id=payload.project_id,
            sprint_id=payload.sprint_id,
            story_points=item.story_points,
            difficulty=item.difficulty,
            deadline_iso=deadline.astimezone(timezone.utc).isoformat(),
        )
        created.append(task)
        create_audit_log(current_user["id"], "create", "task", task["id"], "created from AI task breakdown")
    return {"created_count": len(created), "tasks": created}
