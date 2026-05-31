from app.routers.task_routes import common as _common

globals().update(vars(_common))
router = APIRouter(tags=["tasks"])

@router.get("/task-templates", response_model=list[TaskTemplateOut])
def list_task_templates_endpoint(
    project_id: int | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    require_permission(current_user, "KANBAN_VIEW")
    if project_id is not None:
        _ensure_manager_project_access(project_id, current_user)
    return list_task_templates(project_id)


@router.post("/task-templates", response_model=TaskTemplateOut)
def create_task_template_endpoint(payload: TaskTemplateCreate, current_user: dict = Depends(get_current_user)) -> dict:
    require_roles(current_user, {"admin", "manager"})
    _validate_template_payload(payload)
    if payload.project_id is not None:
        if not project_exists(payload.project_id):
            raise HTTPException(status_code=404, detail="project not found")
        _ensure_manager_project_access(payload.project_id, current_user)
    row = create_task_template(
        name=payload.name.strip(),
        title=payload.title,
        description=payload.description,
        project_id=payload.project_id,
        story_points=payload.story_points,
        difficulty=payload.difficulty,
        priority=payload.priority,
        labels=payload.labels,
        checklist=payload.checklist,
        subtasks=payload.subtasks,
        created_by=int(current_user["id"]),
    )
    create_audit_log(current_user["id"], "create", "task_template", row["id"], f"name={row['name']}")
    return row


@router.put("/task-templates/{template_id}", response_model=TaskTemplateOut)
def update_task_template_endpoint(
    template_id: int,
    payload: TaskTemplateCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    existing = get_task_template(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="task template not found")
    if existing.get("project_id") is not None:
        _ensure_manager_project_access(int(existing["project_id"]), current_user)
    _validate_template_payload(payload)
    if payload.project_id is not None:
        _ensure_manager_project_access(payload.project_id, current_user)
    row = update_task_template(
        template_id,
        name=payload.name.strip(),
        title=payload.title,
        description=payload.description,
        project_id=payload.project_id,
        story_points=payload.story_points,
        difficulty=payload.difficulty,
        priority=payload.priority,
        labels=payload.labels,
        checklist=payload.checklist,
        subtasks=payload.subtasks,
    )
    create_audit_log(current_user["id"], "update", "task_template", template_id, f"name={payload.name.strip()}")
    return row


@router.delete("/task-templates/{template_id}")
def delete_task_template_endpoint(template_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    require_roles(current_user, {"admin", "manager"})
    existing = get_task_template(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="task template not found")
    if existing.get("project_id") is not None:
        _ensure_manager_project_access(int(existing["project_id"]), current_user)
    delete_task_template(template_id)
    create_audit_log(current_user["id"], "delete", "task_template", template_id, f"name={existing['name']}")
    return {"deleted": True}


@router.post("/task-templates/{template_id}/tasks", response_model=TaskOut)
def create_task_from_template_endpoint(
    template_id: int,
    payload: TaskFromTemplateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    require_permission(current_user, "tasks.create")
    template = get_task_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="task template not found")
    project_id = payload.project_id if payload.project_id is not None else template.get("project_id")
    if project_id is not None:
        _ensure_manager_project_access(int(project_id), current_user)
    if not user_exists(payload.assignee_id):
        raise HTTPException(status_code=404, detail="assignee not found")
    task = create_task(
        title=payload.title or str(template["title"]),
        description=template.get("description"),
        assignee_id=payload.assignee_id,
        project_id=project_id,
        sprint_id=payload.sprint_id,
        story_points=int(template["story_points"]),
        difficulty=str(template["difficulty"]),
        deadline_iso=payload.deadline.astimezone(timezone.utc).isoformat(),
        priority=str(template.get("priority") or "medium"),
        labels=list(template.get("labels") or []),
        checklist=list(template.get("checklist") or []),
        subtasks=list(template.get("subtasks") or []),
    )
    create_audit_log(current_user["id"], "create_from_template", "task", task["id"], f"template={template_id}")
    return task


@router.post("/recurring-task-rules", response_model=RecurringTaskRuleOut)
def create_recurring_task_rule_endpoint(
    payload: RecurringTaskRuleCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    template = get_task_template(payload.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="task template not found")
    if payload.frequency not in {"weekly", "monthly"}:
        raise HTTPException(status_code=400, detail="frequency must be weekly|monthly")
    project_id = payload.project_id if payload.project_id is not None else template.get("project_id")
    if project_id is not None:
        _ensure_manager_project_access(int(project_id), current_user)
    if not user_exists(payload.assignee_id):
        raise HTTPException(status_code=404, detail="assignee not found")
    row = create_recurring_task_rule(
        template_id=payload.template_id,
        assignee_id=payload.assignee_id,
        project_id=project_id,
        sprint_id=payload.sprint_id,
        frequency=payload.frequency,
        next_run_at=payload.next_run_at.astimezone(timezone.utc).isoformat(),
        active=payload.active,
        created_by=int(current_user["id"]),
    )
    create_audit_log(current_user["id"], "create", "recurring_task_rule", row["id"], f"template={payload.template_id}")
    return row


@router.get("/recurring-task-rules", response_model=list[RecurringTaskRuleOut])
def list_recurring_task_rules_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_roles(current_user, {"admin", "manager"})
    return list_recurring_task_rules()


@router.post("/recurring-task-rules/run-due", response_model=RecurringTaskRunResult)
def run_due_recurring_task_rules_endpoint(
    as_of: datetime | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    normalized = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    tasks = run_due_recurring_task_rules(normalized, int(current_user["id"]))
    return {"created_count": len(tasks), "tasks": tasks}


