from app.routers.task_routes import common as _common

globals().update(vars(_common))
router = APIRouter(tags=["tasks"])

@router.post("/tasks", response_model=TaskOut)
def create_task_endpoint(payload: TaskCreate, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "tasks.create")
    if payload.difficulty not in {"easy", "medium", "hard"}:
        raise HTTPException(status_code=400, detail="difficulty must be one of easy|medium|hard")
    _validate_metadata_payload(payload)
    if not user_exists(payload.assignee_id):
        raise HTTPException(status_code=404, detail="assignee not found")
    if payload.project_id is not None and not project_exists(payload.project_id):
        raise HTTPException(status_code=404, detail="project not found")
    if payload.sprint_id is not None and not sprint_exists(payload.sprint_id):
        raise HTTPException(status_code=404, detail="sprint not found")
    task = create_task(
        title=payload.title,
        description=payload.description,
        assignee_id=payload.assignee_id,
        project_id=payload.project_id,
        sprint_id=payload.sprint_id,
        story_points=payload.story_points,
        difficulty=payload.difficulty,
        deadline_iso=payload.deadline.astimezone(timezone.utc).isoformat(),
        priority=payload.priority,
        labels=payload.labels,
        checklist=payload.checklist,
        subtasks=payload.subtasks,
        dependencies=payload.dependencies,
        attachment_metadata=payload.attachment_metadata,
    )
    create_audit_log(current_user["id"], "create", "task", task["id"], f"assign_to={task['assignee_id']}")
    return task


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks_endpoint(
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
) -> list[dict]:
    return _filtered_tasks_for_request(
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


