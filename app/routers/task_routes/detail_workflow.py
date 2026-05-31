from app.routers.task_routes import common as _common

globals().update(vars(_common))
router = APIRouter(tags=["tasks"])

@router.get("/projects/{project_id}/milestones", response_model=list[MilestoneOut])
def list_project_milestones_endpoint(project_id: int, current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_project_access(current_user, project_id)
    return list_project_milestones(project_id)


@router.post("/projects/{project_id}/milestones", response_model=MilestoneOut)
def create_project_milestone_endpoint(
    project_id: int,
    payload: MilestoneCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    require_project_access(current_user, project_id)
    if payload.status not in {"planned", "active", "done"}:
        raise HTTPException(status_code=400, detail="status must be planned|active|done")
    row = create_project_milestone(
        project_id,
        payload.name.strip(),
        payload.description,
        payload.due_date.astimezone(timezone.utc).isoformat() if payload.due_date else None,
        payload.status,
    )
    create_audit_log(current_user["id"], "create", "project_milestone", row["id"], f"project={project_id}")
    return row


@router.patch("/milestones/{milestone_id}", response_model=MilestoneOut)
def update_project_milestone_endpoint(
    milestone_id: int,
    payload: MilestoneUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    existing = get_project_milestone(milestone_id)
    if not existing:
        raise HTTPException(status_code=404, detail="milestone not found")
    require_roles(current_user, {"admin", "manager"})
    require_project_access(current_user, int(existing["project_id"]))
    if payload.status is not None and payload.status not in {"planned", "active", "done"}:
        raise HTTPException(status_code=400, detail="status must be planned|active|done")
    row = update_project_milestone(
        milestone_id,
        name=payload.name.strip() if payload.name else None,
        description=payload.description,
        due_date=payload.due_date.astimezone(timezone.utc).isoformat() if payload.due_date else None,
        status=payload.status,
    )
    create_audit_log(current_user["id"], "update", "project_milestone", milestone_id, f"project={existing['project_id']}")
    return row


@router.get("/tasks/{task_id}", response_model=TaskDetailOut)
def get_task_detail_endpoint(task_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    _ensure_task_visible(task, current_user)
    return _task_detail_payload(task_id)


@router.patch("/tasks/{task_id}/metadata", response_model=TaskOut)
def update_task_metadata_endpoint(
    task_id: int,
    payload: TaskMetadataUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    _validate_metadata_payload(payload)
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    _ensure_task_visible(task, current_user)
    if int(task["assignee_id"]) == int(current_user["id"]):
        require_permission(current_user, "tasks.update_own")
    else:
        require_permission(current_user, "tasks.update_any")
        _ensure_task_project_access(task, current_user)
    row = update_task_metadata(
        task_id,
        priority=payload.priority,
        labels=payload.labels,
        checklist=payload.checklist,
        subtasks=payload.subtasks,
        dependencies=payload.dependencies,
        attachment_metadata=payload.attachment_metadata,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="task not found")
    create_audit_log(current_user["id"], "update_metadata", "task", task_id, "metadata_changed")
    return row


@router.patch("/tasks/{task_id}/backlog-grooming", response_model=TaskOut)
def update_task_backlog_grooming_endpoint(
    task_id: int,
    payload: BacklogGroomingUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    _ensure_task_project_access(task, current_user)
    if payload.readiness_status is not None and payload.readiness_status not in {"draft", "ready", "blocked"}:
        raise HTTPException(status_code=400, detail="readiness_status must be draft|ready|blocked")
    row = update_task_backlog_grooming(task_id, payload.backlog_rank, payload.readiness_status, payload.acceptance_notes)
    create_audit_log(current_user["id"], "groom_backlog", "task", task_id, f"rank={payload.backlog_rank};status={payload.readiness_status}")
    return row


@router.patch("/tasks/{task_id}/milestone", response_model=TaskOut)
def update_task_milestone_endpoint(
    task_id: int,
    payload: TaskMilestoneUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    _ensure_task_project_access(task, current_user)
    if payload.milestone_id is not None:
        milestone = get_project_milestone(payload.milestone_id)
        if not milestone:
            raise HTTPException(status_code=404, detail="milestone not found")
        if task.get("project_id") is None or int(milestone["project_id"]) != int(task["project_id"]):
            raise HTTPException(status_code=400, detail="milestone/project mismatch")
    row = update_task_milestone(task_id, payload.milestone_id)
    create_audit_log(current_user["id"], "update_milestone", "task", task_id, f"milestone={payload.milestone_id}")
    return row


@router.patch("/tasks/{task_id}/dependencies", response_model=TaskOut)
def update_task_dependencies_endpoint(
    task_id: int,
    payload: TaskDependencyUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    _ensure_task_project_access(task, current_user)
    try:
        row = replace_task_dependencies(task_id, payload.dependency_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    create_audit_log(current_user["id"], "update_dependencies", "task", task_id, f"dependencies={payload.dependency_ids}")
    return row


@router.post("/tasks/{task_id}/duplicate", response_model=TaskOut)
def duplicate_task_endpoint(
    task_id: int,
    payload: TaskDuplicateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    _ensure_task_project_access(task, current_user)
    if payload.assignee_id is not None and not user_exists(payload.assignee_id):
        raise HTTPException(status_code=404, detail="assignee not found")
    if payload.sprint_id is not None:
        sprint = get_sprint_by_id(payload.sprint_id)
        if not sprint:
            raise HTTPException(status_code=404, detail="sprint not found")
        if task.get("project_id") is not None and int(sprint["project_id"]) != int(task["project_id"]):
            raise HTTPException(status_code=400, detail="sprint/project mismatch")
    row = duplicate_task(
        task_id,
        title=payload.title,
        assignee_id=payload.assignee_id,
        sprint_id=payload.sprint_id,
        deadline_iso=payload.deadline.astimezone(timezone.utc).isoformat() if payload.deadline else None,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="task not found")
    create_audit_log(current_user["id"], "duplicate", "task", row["id"], f"source={task_id}")
    return row


@router.patch("/tasks/{task_id}/deadline-extension", response_model=TaskOut)
def extend_task_deadline_endpoint(
    task_id: int,
    payload: TaskDeadlineExtension,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    require_permission(current_user, "tasks.update_any")
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    _ensure_task_project_access(task, current_user)
    if task["status"] == "done":
        raise HTTPException(status_code=400, detail="completed tasks cannot be extended")
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=400, detail="extension reason is required")
    old_deadline = _parse_dt(str(task["deadline"]))
    new_deadline = payload.deadline.astimezone(timezone.utc)
    if new_deadline <= old_deadline:
        raise HTTPException(status_code=400, detail="deadline must be later than current deadline")
    row = update_task_deadline(task_id, new_deadline.isoformat())
    if row is None:
        raise HTTPException(status_code=404, detail="task not found")
    create_audit_log(
        current_user["id"],
        "extend_deadline",
        "task",
        task_id,
        f"old_deadline={old_deadline.isoformat()};new_deadline={new_deadline.isoformat()};reason={reason}",
    )
    if int(current_user["id"]) != int(task["assignee_id"]):
        create_app_notification(
            user_id=int(task["assignee_id"]),
            notification_type="task_status_changed",
            title="Task deadline extended",
            message=f'"{task["title"]}" deadline was extended to {new_deadline.date().isoformat()}',
            entity_type="task",
            entity_id=task_id,
        )
    return row


@router.post("/sprints/{sprint_id}/carryover", response_model=TaskBulkActionResult)
def sprint_carryover_endpoint(
    sprint_id: int,
    payload: SprintCarryoverRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    source = get_sprint_by_id(sprint_id)
    target = get_sprint_by_id(payload.target_sprint_id)
    if not source or not target:
        raise HTTPException(status_code=404, detail="sprint not found")
    if int(source["project_id"]) != int(target["project_id"]):
        raise HTTPException(status_code=400, detail="sprint/project mismatch")
    require_project_access(current_user, int(source["project_id"]))
    updated = carryover_sprint_tasks(sprint_id, payload.target_sprint_id)
    create_audit_log(
        current_user["id"],
        "carryover",
        "sprint",
        sprint_id,
        f"count={updated};target_sprint={payload.target_sprint_id}",
    )
    return {"updated": updated}


@router.post("/tasks/{task_id}/comments", response_model=TaskCommentOut)
def create_task_comment_endpoint(
    task_id: int,
    payload: TaskCommentCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    _ensure_task_visible(task, current_user)
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="comment body is required")
    comment = create_task_comment(task_id=task_id, author_user_id=int(current_user["id"]), body=body)
    create_audit_log(current_user["id"], "comment", "task", task_id, f"comment_id={comment['id']}")
    if int(current_user["id"]) != int(task["assignee_id"]):
        commenter = get_user_by_id(int(current_user["id"]))
        commenter_name = commenter["full_name"] if commenter else f"User {current_user['id']}"
        create_app_notification(
            user_id=int(task["assignee_id"]),
            notification_type="task_comment",
            title="New comment on your task",
            message=f'{commenter_name} commented on "{task["title"]}"',
            entity_type="task",
            entity_id=task_id,
        )
    return comment


@router.patch("/tasks/{task_id}/status", response_model=TaskOut)
def update_task_status_endpoint(
    task_id: int,
    payload: TaskStatusUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    if payload.status not in {"todo", "doing", "done"}:
        raise HTTPException(status_code=400, detail="status must be one of todo|doing|done")
    task_before = get_task_by_id(task_id)
    if not task_before:
        raise HTTPException(status_code=404, detail="task not found")
    _ensure_task_visible(task_before, current_user)
    if int(task_before["assignee_id"]) == int(current_user["id"]):
        require_permission(current_user, "tasks.update_own")
    else:
        require_permission(current_user, "tasks.update_any")
    row = update_task_status(task_id, payload.status)
    if row is None:
        raise HTTPException(status_code=404, detail="task not found")
    create_audit_log(current_user["id"], "update_status", "task", task_id, f"status={payload.status}")
    if task_before["status"] != payload.status:
        create_app_notification(
            user_id=int(row["assignee_id"]),
            notification_type="task_status_changed",
            title="Task status updated",
            message=f'"{row["title"]}" moved to {_status_label(payload.status)}',
            entity_type="task",
            entity_id=task_id,
        )
    return row


from pathlib import Path
import uuid
from pydantic import BaseModel

class AttachmentDeletePayload(BaseModel):
    url: str

@router.post("/tasks/{task_id}/attachments", response_model=TaskOut)
def upload_task_attachment_endpoint(
    task_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    _ensure_task_visible(task, current_user)
    
    if int(task["assignee_id"]) == int(current_user["id"]):
        require_permission(current_user, "tasks.update_own")
    else:
        require_permission(current_user, "tasks.update_any")
        _ensure_task_project_access(task, current_user)

    MAX_SIZE = 50 * 1024 * 1024  # 50MB
    file_size = 0
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    upload_dir = Path("app/static/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / unique_filename

    try:
        with file_path.open("wb") as buffer:
            while chunk := file.file.read(1024 * 1024):
                file_size += len(chunk)
                if file_size > MAX_SIZE:
                    buffer.close()
                    if file_path.exists():
                        file_path.unlink()
                    raise HTTPException(status_code=400, detail="file size exceeds 50MB limit")
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    attachments = list(task.get("attachment_metadata") or [])
    new_attachment = {
        "name": file.filename,
        "url": f"/ui/uploads/{unique_filename}",
        "size": file_size,
        "content_type": file.content_type or "application/octet-stream"
    }
    attachments.append(new_attachment)
    
    row = update_task_metadata(
        task_id,
        attachment_metadata=attachments
    )
    if row is None:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=404, detail="task not found")
        
    create_audit_log(current_user["id"], "upload_attachment", "task", task_id, f"filename={file.filename}")
    return row


@router.delete("/tasks/{task_id}/attachments", response_model=TaskOut)
def delete_task_attachment_endpoint(
    task_id: int,
    payload: AttachmentDeletePayload,
    current_user: dict = Depends(get_current_user),
) -> dict:
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    _ensure_task_visible(task, current_user)
    
    if int(task["assignee_id"]) == int(current_user["id"]):
        require_permission(current_user, "tasks.update_own")
    else:
        require_permission(current_user, "tasks.update_any")
        _ensure_task_project_access(task, current_user)

    attachments = list(task.get("attachment_metadata") or [])
    matching_attachment = None
    for att in attachments:
        if att.get("url") == payload.url:
            matching_attachment = att
            break
            
    if not matching_attachment:
        raise HTTPException(status_code=400, detail="attachment not found for this task")
        
    attachments.remove(matching_attachment)
    
    row = update_task_metadata(
        task_id,
        attachment_metadata=attachments
    )
    if row is None:
        raise HTTPException(status_code=404, detail="task not found")
        
    if payload.url.startswith("/ui/uploads/"):
        filename = payload.url.replace("/ui/uploads/", "")
        file_path = Path("app/static/uploads") / filename
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass
                
    create_audit_log(current_user["id"], "delete_attachment", "task", task_id, f"url={payload.url}")
    return row
