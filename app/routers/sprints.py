from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, require_roles
from app.deps import require_project_access
from app.repository import (
    assign_tasks_to_sprint,
    create_audit_log,
    create_sprint,
    list_sprint_capacities,
    list_sprints,
    project_exists,
    sprint_burndown_points,
    sprint_exists,
    sprint_review_summary,
    update_sprint_status,
    upsert_sprint_capacity,
    user_exists,
)
from app.schemas import (
    BurndownPoint,
    SprintCapacityCreate,
    SprintCapacityOut,
    SprintCreate,
    SprintOut,
    SprintStatusUpdate,
    SprintTaskAssign,
    SprintVelocityOut,
)

router = APIRouter(tags=["sprints"])


@router.post("/projects/{project_id}/sprints", response_model=SprintOut)
def create_sprint_endpoint(
    project_id: int,
    payload: SprintCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    if not project_exists(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    if payload.end_date <= payload.start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")
    sprint = create_sprint(
        project_id=project_id,
        name=payload.name,
        goal=payload.goal,
        start_date=payload.start_date.astimezone(timezone.utc).isoformat(),
        end_date=payload.end_date.astimezone(timezone.utc).isoformat(),
    )
    create_audit_log(current_user["id"], "create", "sprint", sprint["id"], sprint["name"])
    return sprint


@router.get("/projects/{project_id}/sprints", response_model=list[SprintOut])
def list_sprints_endpoint(
    project_id: int,
    status: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    require_roles(current_user, {"admin", "manager", "hr", "staff"})
    require_project_access(current_user, project_id)
    return list_sprints(project_id, status=status)


@router.patch("/sprints/{sprint_id}/status", response_model=SprintOut)
def update_sprint_status_endpoint(
    sprint_id: int,
    payload: SprintStatusUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    if payload.status not in {"planned", "active", "completed"}:
        raise HTTPException(status_code=400, detail="invalid sprint status")
    sprint = update_sprint_status(sprint_id, payload.status)
    if not sprint:
        raise HTTPException(status_code=404, detail="sprint not found")
    create_audit_log(current_user["id"], "update", "sprint", sprint_id, f"status={payload.status}")
    return sprint


@router.post("/projects/{project_id}/sprints/{sprint_id}/tasks")
def assign_tasks_to_sprint_endpoint(
    project_id: int,
    sprint_id: int,
    payload: SprintTaskAssign,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    require_project_access(current_user, project_id)
    if not sprint_exists(sprint_id):
        raise HTTPException(status_code=404, detail="sprint not found")
    updated = assign_tasks_to_sprint(project_id, sprint_id, payload.task_ids)
    create_audit_log(current_user["id"], "assign", "sprint_tasks", sprint_id, f"count={updated}")
    return {"updated": updated}


@router.get("/sprints/{sprint_id}/burndown", response_model=list[BurndownPoint])
def sprint_burndown_endpoint(sprint_id: int, current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_roles(current_user, {"admin", "manager", "hr", "staff"})
    if not sprint_exists(sprint_id):
        raise HTTPException(status_code=404, detail="sprint not found")
    return sprint_burndown_points(sprint_id)


@router.post("/sprints/{sprint_id}/capacity", response_model=SprintCapacityOut)
def upsert_sprint_capacity_endpoint(
    sprint_id: int,
    payload: SprintCapacityCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    if not sprint_exists(sprint_id):
        raise HTTPException(status_code=404, detail="sprint not found")
    if not user_exists(payload.user_id):
        raise HTTPException(status_code=404, detail="user not found")
    item = upsert_sprint_capacity(
        sprint_id=sprint_id,
        user_id=payload.user_id,
        capacity_hours=payload.capacity_hours,
        allocated_hours=payload.allocated_hours,
    )
    create_audit_log(current_user["id"], "upsert", "sprint_capacity", item["id"], f"sprint={sprint_id}")
    return item


@router.get("/sprints/{sprint_id}/capacity", response_model=list[SprintCapacityOut])
def list_sprint_capacity_endpoint(sprint_id: int, current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_roles(current_user, {"admin", "manager", "hr"})
    if not sprint_exists(sprint_id):
        raise HTTPException(status_code=404, detail="sprint not found")
    return list_sprint_capacities(sprint_id)


@router.get("/sprints/{sprint_id}/review-summary")
def sprint_review_summary_endpoint(sprint_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    require_roles(current_user, {"admin", "manager", "hr", "staff"})
    if not sprint_exists(sprint_id):
        raise HTTPException(status_code=404, detail="sprint not found")
    return sprint_review_summary(sprint_id)
