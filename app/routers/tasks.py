from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, require_permission
from app.repository import (
    create_audit_log,
    create_app_notification,
    create_task,
    create_task_comment,
    get_task_by_id,
    get_task_detail_by_id,
    get_user_by_id,
    list_task_activity_logs,
    list_task_comments,
    list_tasks,
    project_exists,
    sprint_exists,
    update_task_status,
    user_exists,
)
from app.schemas import TaskCommentCreate, TaskCommentOut, TaskCreate, TaskDetailOut, TaskOut, TaskStatusUpdate

router = APIRouter(tags=["tasks"])


def _ensure_task_visible(task: dict, current_user: dict) -> None:
    if current_user["role"] == "staff" and int(task["assignee_id"]) != int(current_user["id"]):
        raise HTTPException(status_code=403, detail="staff can access only assigned tasks")


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _due_state(task: dict) -> str:
    deadline = _parse_dt(str(task["deadline"]))
    completed_at = task.get("completed_at")
    if completed_at:
        return "on_time" if _parse_dt(str(completed_at)) <= deadline else "late"
    return "overdue" if deadline < datetime.now(timezone.utc) else "on_time"


def _task_detail_payload(task_id: int) -> dict:
    task = get_task_detail_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return {
        **task,
        "due_state": _due_state(task),
        "comments": list_task_comments(task_id),
        "activity_logs": list_task_activity_logs(task_id),
    }


def _status_label(status: str) -> str:
    return {"todo": "To-do", "doing": "Doing", "done": "Done"}.get(status, status)


@router.post("/tasks", response_model=TaskOut)
def create_task_endpoint(payload: TaskCreate, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "tasks.create")
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


@router.get("/tasks/{task_id}", response_model=TaskDetailOut)
def get_task_detail_endpoint(task_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    _ensure_task_visible(task, current_user)
    return _task_detail_payload(task_id)


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
