from app.routers.task_routes import common as _common

globals().update(vars(_common))
router = APIRouter(tags=["tasks"])

@router.get("/kanban/saved-filters", response_model=list[KanbanSavedFilterOut])
def kanban_saved_filters_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_permission(current_user, "KANBAN_VIEW")
    return list_kanban_saved_filters(int(current_user["id"]))


@router.post("/kanban/saved-filters", response_model=KanbanSavedFilterOut)
def create_kanban_saved_filter_endpoint(
    payload: KanbanSavedFilterCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "KANBAN_VIEW")
    clean_filters = _validate_filters_payload(payload.filters)
    row = create_kanban_saved_filter(int(current_user["id"]), payload.name.strip(), clean_filters, payload.is_default)
    create_audit_log(current_user["id"], "create", "kanban_saved_filter", row["id"], f"name={row['name']}")
    return row


@router.put("/kanban/saved-filters/{filter_id}", response_model=KanbanSavedFilterOut)
def update_kanban_saved_filter_endpoint(
    filter_id: int,
    payload: KanbanSavedFilterCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "KANBAN_VIEW")
    existing = get_kanban_saved_filter(filter_id)
    if not existing:
        raise HTTPException(status_code=404, detail="saved filter not found")
    if int(existing["user_id"]) != int(current_user["id"]):
        raise HTTPException(status_code=403, detail="saved filter belongs to another user")
    row = update_kanban_saved_filter(filter_id, payload.name.strip(), _validate_filters_payload(payload.filters), payload.is_default)
    create_audit_log(current_user["id"], "update", "kanban_saved_filter", filter_id, f"name={payload.name.strip()}")
    return row


@router.delete("/kanban/saved-filters/{filter_id}")
def delete_kanban_saved_filter_endpoint(filter_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "KANBAN_VIEW")
    existing = get_kanban_saved_filter(filter_id)
    if not existing:
        raise HTTPException(status_code=404, detail="saved filter not found")
    if int(existing["user_id"]) != int(current_user["id"]):
        raise HTTPException(status_code=403, detail="saved filter belongs to another user")
    delete_kanban_saved_filter(filter_id)
    create_audit_log(current_user["id"], "delete", "kanban_saved_filter", filter_id, f"name={existing['name']}")
    return {"deleted": True}


@router.put("/kanban/wip-policy", response_model=KanbanWipPolicyOut)
def upsert_kanban_wip_policy_endpoint(
    payload: KanbanWipPolicyUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    if payload.project_id is None and payload.sprint_id is None:
        raise HTTPException(status_code=400, detail="project_id or sprint_id is required")
    if payload.project_id is not None and not project_exists(payload.project_id):
        raise HTTPException(status_code=404, detail="project not found")
    project_id = payload.project_id
    if payload.sprint_id is not None:
        sprint = get_sprint_by_id(payload.sprint_id)
        if not sprint:
            raise HTTPException(status_code=404, detail="sprint not found")
        project_id = int(sprint["project_id"])
    _ensure_manager_project_access(project_id, current_user)
    row = upsert_kanban_wip_policy(project_id, payload.sprint_id, payload.todo_limit, payload.doing_limit, payload.done_limit)
    create_audit_log(current_user["id"], "upsert", "kanban_wip_policy", row["id"], f"project={project_id};sprint={payload.sprint_id}")
    return row


@router.get("/kanban/summary", response_model=KanbanSummaryOut)
def kanban_summary_endpoint(
    assignee_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    sprint_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=200),
    deadline_from: datetime | None = Query(default=None),
    deadline_to: datetime | None = Query(default=None),
    as_of: datetime | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "KANBAN_VIEW")
    tasks = _filtered_tasks_for_request(
        current_user,
        assignee_id=assignee_id,
        project_id=project_id,
        sprint_id=sprint_id,
        status=status,
        overdue=overdue,
        keyword=keyword,
        deadline_from=deadline_from,
        deadline_to=deadline_to,
        as_of=as_of,
    )
    policy = get_kanban_wip_policy(project_id=project_id, sprint_id=sprint_id)
    return build_kanban_summary(tasks, policy)


@router.post("/tasks/bulk", response_model=TaskBulkActionResult)
def bulk_task_action_endpoint(payload: TaskBulkAction, current_user: dict = Depends(get_current_user)) -> dict:
    require_roles(current_user, {"admin", "manager"})
    if not payload.task_ids:
        raise HTTPException(status_code=400, detail="task_ids is required")
    if payload.status is None and payload.assignee_id is None and payload.sprint_id is None and not payload.move_to_backlog:
        raise HTTPException(status_code=400, detail="at least one bulk action is required")
    if payload.status is not None and payload.status not in {"todo", "doing", "done"}:
        raise HTTPException(status_code=400, detail="status must be one of todo|doing|done")
    if payload.assignee_id is not None and not user_exists(payload.assignee_id):
        raise HTTPException(status_code=404, detail="assignee not found")
    if payload.move_to_backlog and payload.sprint_id is not None:
        raise HTTPException(status_code=400, detail="move_to_backlog cannot be combined with sprint_id")
    tasks = _load_tasks_or_404(payload.task_ids)
    for task in tasks:
        _ensure_task_project_access(task, current_user)
    if payload.sprint_id is not None:
        sprint = get_sprint_by_id(payload.sprint_id)
        if not sprint:
            raise HTTPException(status_code=404, detail="sprint not found")
        for project_id in task_project_ids(payload.task_ids):
            if project_id is not None and int(project_id) != int(sprint["project_id"]):
                raise HTTPException(status_code=400, detail="sprint/project mismatch")
    updated = bulk_update_tasks(
        payload.task_ids,
        status=payload.status,
        assignee_id=payload.assignee_id,
        sprint_id=payload.sprint_id,
        move_to_backlog=payload.move_to_backlog,
    )
    create_audit_log(current_user["id"], "bulk_update", "task", None, f"count={updated}")
    return {"updated": updated}


