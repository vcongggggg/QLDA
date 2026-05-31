from app.routers.task_routes import common as _common

globals().update(vars(_common))
router = APIRouter(tags=["tasks"])

@router.get("/projects/{project_id}/backlog", response_model=list[TaskOut])
def project_backlog_endpoint(project_id: int, current_user: dict = Depends(get_current_user)) -> list[dict]:
    tasks = list_project_backlog(project_id)
    if is_member_role(current_user):
        return [task for task in tasks if int(task["assignee_id"]) == int(current_user["id"])]
    require_project_access(current_user, project_id)
    return tasks


@router.post("/projects/{project_id}/backlog/move-to-sprint", response_model=TaskBulkActionResult)
def move_backlog_to_sprint_endpoint(
    project_id: int,
    payload: BacklogMoveToSprint,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    require_project_access(current_user, project_id)
    if not payload.task_ids:
        raise HTTPException(status_code=400, detail="task_ids is required")
    sprint = get_sprint_by_id(payload.sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="sprint not found")
    if int(sprint["project_id"]) != int(project_id):
        raise HTTPException(status_code=400, detail="sprint/project mismatch")
    tasks = _load_tasks_or_404(payload.task_ids)
    for task in tasks:
        if task.get("project_id") is None or int(task["project_id"]) != int(project_id):
            raise HTTPException(status_code=400, detail="task/project mismatch")
        if task.get("sprint_id") is not None:
            raise HTTPException(status_code=400, detail="only backlog tasks can be moved to sprint")
    updated = bulk_update_tasks(payload.task_ids, sprint_id=payload.sprint_id)
    create_audit_log(current_user["id"], "move_to_sprint", "backlog", project_id, f"count={updated};sprint={payload.sprint_id}")
    return {"updated": updated}


@router.post("/tasks/import", response_model=TaskImportResult)
async def import_tasks_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    require_permission(current_user, "tasks.create")
    rows = _read_task_import_rows(file, await file.read())
    if not rows:
        raise HTTPException(status_code=400, detail="import file has no task rows")
    errors: list[dict] = []
    prepared: list[dict] = []
    for index, row in enumerate(rows, start=2):
        try:
            title = str(row.get("title") or "").strip()
            if len(title) < 2:
                raise ValueError("title is required")
            email = str(row.get("assignee_email") or "").strip()
            assignee = get_user_by_username_or_email(email)
            if not assignee:
                raise ValueError("assignee_email not found")
            project_id = int(row["project_id"]) if row.get("project_id") not in (None, "") else None
            sprint_id = int(row["sprint_id"]) if row.get("sprint_id") not in (None, "") else None
            if project_id is not None:
                if not project_exists(project_id):
                    raise ValueError("project_id not found")
                _ensure_manager_project_access(project_id, current_user)
            if sprint_id is not None:
                sprint = get_sprint_by_id(sprint_id)
                if not sprint:
                    raise ValueError("sprint_id not found")
                if project_id is not None and int(sprint["project_id"]) != project_id:
                    raise ValueError("sprint/project mismatch")
            difficulty = str(row.get("difficulty") or "medium").strip()
            if difficulty not in {"easy", "medium", "hard"}:
                raise ValueError("difficulty must be easy|medium|hard")
            priority = str(row.get("priority") or "medium").strip()
            if priority not in {"low", "medium", "high", "urgent"}:
                raise ValueError("priority must be low|medium|high|urgent")
            prepared.append(
                {
                    "title": title,
                    "description": str(row.get("description") or "").strip() or None,
                    "assignee_id": int(assignee["id"]),
                    "project_id": project_id,
                    "sprint_id": sprint_id,
                    "story_points": int(row.get("story_points") or 1),
                    "difficulty": difficulty,
                    "priority": priority,
                    "labels": _parse_labels(row.get("labels")),
                    "deadline": _parse_import_deadline(str(row.get("deadline") or "")),
                }
            )
        except (TypeError, ValueError) as exc:
            errors.append({"row": index, "error": str(exc)})
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})
    created = [
        create_task(
            title=item["title"],
            description=item["description"],
            assignee_id=item["assignee_id"],
            project_id=item["project_id"],
            sprint_id=item["sprint_id"],
            story_points=item["story_points"],
            difficulty=item["difficulty"],
            priority=item["priority"],
            labels=item["labels"],
            deadline_iso=item["deadline"].isoformat(),
        )
        for item in prepared
    ]
    create_audit_log(current_user["id"], "import", "task", None, f"count={len(created)};source={file.filename}")
    return {"created_count": len(created), "tasks": created}


