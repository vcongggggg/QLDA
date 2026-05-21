from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.ai_task_breakdown import breakdown_requirements, extract_docx_text
from app.auth import get_current_user, require_permission
from app.rag import build_rag_context, query_rag
from app.repository import (
    create_ai_task_draft,
    create_audit_log,
    create_task,
    get_ai_task_draft,
    list_ai_task_drafts,
    mark_ai_task_draft_imported,
    project_exists,
    review_ai_task_draft,
    sprint_exists,
    user_exists,
)
from app.schemas import (
    AiTaskDraftDetail,
    AiTaskDraftReviewRequest,
    AiTaskDraftSummary,
    TaskBreakdownRequest,
    TaskBreakdownResponse,
    TaskImportRequest,
    TaskImportResponse,
)

router = APIRouter(prefix="/ai", tags=["ai"])


def _items_as_dicts(items: list) -> list[dict]:
    output: list[dict] = []
    for item in items:
        if hasattr(item, "model_dump"):
            output.append(item.model_dump())
        elif hasattr(item, "dict"):
            output.append(item.dict())
        else:
            output.append(dict(item))
    return output


def _source_summary(text: str) -> str:
    normalized = " ".join(text.split())
    return normalized[:240]


@router.post("/task-breakdown", response_model=TaskBreakdownResponse)
def task_breakdown_endpoint(
    payload: TaskBreakdownRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "ai.preview")
    project_context = payload.project_context
    retrieved_sources: list[str] = []
    if payload.use_rag:
        matches = query_rag(payload.rag_query or payload.text, limit=5, current_user=current_user)
        retrieved_context, retrieved_sources = build_rag_context(matches)
        if retrieved_context:
            project_context = "\n\n".join(part for part in (payload.project_context, retrieved_context) if part)
    result = breakdown_requirements(payload.text, project_context, payload.max_tasks)
    draft = create_ai_task_draft(
        source_type="text",
        source_summary=_source_summary(payload.text),
        source_name=None,
        generated_tasks=_items_as_dicts(result.items),
        created_by=int(current_user["id"]),
    )
    create_audit_log(
        current_user["id"],
        "preview",
        "ai_task_breakdown",
        draft["id"],
        f"items={len(result.items)} source={result.source} rag={len(retrieved_sources)}",
    )
    return {
        "ai_draft_id": draft["id"],
        "status": draft["status"],
        "source": result.source,
        "items": result.items,
        "warnings": result.warnings,
        "retrieved_context_count": len(retrieved_sources),
        "retrieved_sources": retrieved_sources,
    }


@router.post("/task-breakdown/docx", response_model=TaskBreakdownResponse)
async def task_breakdown_docx_endpoint(
    file: UploadFile = File(...),
    project_context: str | None = Form(default=None),
    max_tasks: int = Form(default=8),
    use_rag: bool = Form(default=False),
    rag_query: str | None = Form(default=None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "ai.preview")
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
    retrieved_sources: list[str] = []
    if use_rag:
        matches = query_rag(rag_query or text, limit=5, current_user=current_user)
        retrieved_context, retrieved_sources = build_rag_context(matches)
        if retrieved_context:
            project_context = "\n\n".join(part for part in (project_context, retrieved_context) if part)
    result = breakdown_requirements(text, project_context, max_tasks)
    draft = create_ai_task_draft(
        source_type="docx",
        source_summary=_source_summary(text),
        source_name=file.filename,
        generated_tasks=_items_as_dicts(result.items),
        created_by=int(current_user["id"]),
    )
    create_audit_log(
        current_user["id"],
        "preview",
        "ai_task_breakdown_docx",
        draft["id"],
        f"items={len(result.items)} source={result.source} rag={len(retrieved_sources)}",
    )
    return {
        "ai_draft_id": draft["id"],
        "status": draft["status"],
        "source": result.source,
        "items": result.items,
        "warnings": result.warnings,
        "retrieved_context_count": len(retrieved_sources),
        "retrieved_sources": retrieved_sources,
    }


@router.get("/task-breakdown/drafts", response_model=list[AiTaskDraftSummary])
def list_ai_task_drafts_endpoint(
    status: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    require_permission(current_user, "ai.preview")
    if status is not None and status not in {"draft", "reviewed", "imported"}:
        raise HTTPException(status_code=400, detail="invalid draft status")
    return list_ai_task_drafts(status=status)


@router.get("/task-breakdown/drafts/{draft_id}", response_model=AiTaskDraftDetail)
def get_ai_task_draft_endpoint(
    draft_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "ai.preview")
    draft = get_ai_task_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="ai draft not found")
    return draft


@router.patch("/task-breakdown/drafts/{draft_id}/review", response_model=AiTaskDraftDetail)
def review_ai_task_draft_endpoint(
    draft_id: int,
    payload: AiTaskDraftReviewRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "ai.import")
    existing = get_ai_task_draft(draft_id)
    if not existing:
        raise HTTPException(status_code=404, detail="ai draft not found")
    if existing["status"] == "imported":
        raise HTTPException(status_code=400, detail="imported ai draft cannot be reviewed")
    reviewed = review_ai_task_draft(
        draft_id=draft_id,
        generated_tasks=_items_as_dicts(payload.items),
        reviewer_id=int(current_user["id"]),
        review_note=payload.review_note,
        edit_reason=payload.edit_reason,
    )
    if not reviewed:
        raise HTTPException(status_code=404, detail="ai draft not found")
    create_audit_log(
        current_user["id"],
        "review",
        "ai_task_draft",
        draft_id,
        f"items={len(payload.items)}",
    )
    return reviewed


@router.post("/task-breakdown/import", response_model=TaskImportResponse)
def import_ai_tasks_endpoint(
    payload: TaskImportRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "ai.import")
    draft = get_ai_task_draft(payload.ai_draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="ai draft not found")
    if draft["status"] == "imported":
        raise HTTPException(status_code=400, detail="ai draft already imported")
    if not user_exists(payload.assignee_id):
        raise HTTPException(status_code=404, detail="assignee not found")
    if payload.project_id is not None and not project_exists(payload.project_id):
        raise HTTPException(status_code=404, detail="project not found")
    if payload.sprint_id is not None and not sprint_exists(payload.sprint_id):
        raise HTTPException(status_code=404, detail="sprint not found")

    base_deadline = payload.base_deadline or datetime.now(timezone.utc)
    items = draft["items"]
    selected_items = [item for item in items if item.get("selected", True) is not False]
    if not selected_items:
        raise HTTPException(status_code=400, detail="no selected ai draft items to import")
    created: list[dict] = []
    for item in selected_items:
        if item.get("difficulty") not in {"easy", "medium", "hard"}:
            raise HTTPException(status_code=400, detail="invalid difficulty")
        deadline = base_deadline + timedelta(days=int(item.get("deadline_offset_days", 7)))
        task = create_task(
            title=item["title"],
            description=item.get("description"),
            assignee_id=payload.assignee_id,
            project_id=payload.project_id,
            sprint_id=payload.sprint_id,
            story_points=int(item.get("story_points", 3)),
            difficulty=item["difficulty"],
            deadline_iso=deadline.astimezone(timezone.utc).isoformat(),
        )
        created.append(task)
        create_audit_log(
            current_user["id"],
            "create",
            "task",
            task["id"],
            f"created from AI task draft {payload.ai_draft_id}",
        )
    mark_ai_task_draft_imported(payload.ai_draft_id)
    create_audit_log(
        current_user["id"],
        "import",
        "ai_task_draft",
        payload.ai_draft_id,
        f"created_tasks={len(created)}",
    )
    return {"created_count": len(created), "tasks": created}
