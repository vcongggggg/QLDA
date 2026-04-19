from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, require_roles
from app.repository import (
    create_audit_log,
    create_task,
    get_task_by_id,
    list_tasks,
    project_exists,
    sprint_exists,
    update_task_status,
    user_exists,
)
from app.schemas import TaskCreate, TaskOut, TaskStatusUpdate

router = APIRouter(tags=["tasks"])


@router.post("/tasks", response_model=TaskOut)
def create_task_endpoint(payload: TaskCreate, current_user: dict = Depends(get_current_user)) -> dict:
    require_roles(current_user, {"admin", "manager"})
    if payload.difficulty not in {"easy", "medium", "hard"}:
        raise HTTPException(status_code=400, detail="difficulty must be one of easy|medium|hard")
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
    )
    create_audit_log(current_user["id"], "create", "task", task["id"], f"assign_to={task['assignee_id']}")
    return task


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks_endpoint(
    assignee_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    sprint_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    if current_user["role"] == "staff":
        assignee_id = current_user["id"]
    if status is not None and status not in {"todo", "doing", "done"}:
        raise HTTPException(status_code=400, detail="status must be one of todo|doing|done")
    return list_tasks(assignee_id=assignee_id, project_id=project_id, sprint_id=sprint_id, status=status)


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
    if current_user["role"] == "staff" and int(task_before["assignee_id"]) != int(current_user["id"]):
        raise HTTPException(status_code=403, detail="staff can update only assigned tasks")
    row = update_task_status(task_id, payload.status)
    if row is None:
        raise HTTPException(status_code=404, detail="task not found")
    create_audit_log(current_user["id"], "update_status", "task", task_id, f"status={payload.status}")
    return row
