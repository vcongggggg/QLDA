from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, require_roles
from app.deps import require_project_access
from app.repository import (
    add_project_member,
    create_audit_log,
    create_project,
    create_project_risk,
    create_weekly_status_update,
    department_exists,
    list_departments,
    list_project_members,
    list_project_risks,
    list_projects,
    list_weekly_status_updates,
    create_department,
    project_exists,
    project_progress,
    portfolio_summary,
    sprint_velocity_history,
    sprint_exists,
    user_exists,
)
from app.schemas import (
    DepartmentCreate,
    DepartmentOut,
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberOut,
    ProjectOut,
    ProjectProgressOut,
    ProjectRiskCreate,
    ProjectRiskOut,
    SprintVelocityOut,
    WeeklyStatusCreate,
    WeeklyStatusOut,
)

router = APIRouter(tags=["org"])


# ── Departments ────────────────────────────────────────────────────────────────

@router.post("/departments", response_model=DepartmentOut)
def create_department_endpoint(payload: DepartmentCreate, current_user: dict = Depends(get_current_user)) -> dict:
    require_roles(current_user, {"admin", "manager"})
    try:
        dep = create_department(payload.name, payload.code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    create_audit_log(current_user["id"], "create", "department", dep["id"], dep["code"])
    return dep


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_roles(current_user, {"admin", "manager", "hr"})
    return list_departments()


# ── Projects ───────────────────────────────────────────────────────────────────

@router.post("/projects", response_model=ProjectOut)
def create_project_endpoint(payload: ProjectCreate, current_user: dict = Depends(get_current_user)) -> dict:
    require_roles(current_user, {"admin", "manager"})
    if payload.department_id is not None and not department_exists(payload.department_id):
        raise HTTPException(status_code=404, detail="department not found")
    if payload.manager_id is not None and not user_exists(payload.manager_id):
        raise HTTPException(status_code=404, detail="manager not found")
    if payload.status not in {"active", "on_hold", "done", "archived"}:
        raise HTTPException(status_code=400, detail="invalid project status")

    project = create_project(
        name=payload.name,
        description=payload.description,
        department_id=payload.department_id,
        manager_id=payload.manager_id,
        start_date=payload.start_date.astimezone(timezone.utc).isoformat() if payload.start_date else None,
        end_date=payload.end_date.astimezone(timezone.utc).isoformat() if payload.end_date else None,
        status=payload.status,
    )
    create_audit_log(current_user["id"], "create", "project", project["id"], project["name"])
    return project


@router.get("/projects", response_model=list[ProjectOut])
def list_projects_endpoint(
    status: str | None = Query(default=None),
    department_id: int | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    require_roles(current_user, {"admin", "manager", "hr", "staff"})
    rows = list_projects(status=status, department_id=department_id)
    if current_user["role"] in {"admin", "hr"}:
        return rows
    filtered: list[dict] = []
    for item in rows:
        try:
            require_project_access(current_user, int(item["id"]))
            filtered.append(item)
        except HTTPException:
            pass
    return filtered


@router.post("/projects/{project_id}/members", response_model=ProjectMemberOut)
def add_project_member_endpoint(
    project_id: int,
    payload: ProjectMemberCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager"})
    if not project_exists(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    if not user_exists(payload.user_id):
        raise HTTPException(status_code=404, detail="user not found")
    try:
        item = add_project_member(project_id, payload.user_id, payload.role)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    create_audit_log(current_user["id"], "create", "project_member", item["id"], f"project={project_id}")
    return item


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberOut])
def list_project_members_endpoint(project_id: int, current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_roles(current_user, {"admin", "manager", "hr", "staff"})
    require_project_access(current_user, project_id)
    return list_project_members(project_id)


@router.get("/projects/{project_id}/progress", response_model=ProjectProgressOut)
def project_progress_endpoint(project_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    require_roles(current_user, {"admin", "manager", "hr", "staff"})
    require_project_access(current_user, project_id)
    return project_progress(project_id)


@router.get("/projects/{project_id}/velocity", response_model=list[SprintVelocityOut])
def project_velocity_endpoint(project_id: int, current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_roles(current_user, {"admin", "manager", "hr", "staff"})
    require_project_access(current_user, project_id)
    return sprint_velocity_history(project_id)


# ── Risks ──────────────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/risks", response_model=ProjectRiskOut)
def create_project_risk_endpoint(
    project_id: int,
    payload: ProjectRiskCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager", "hr"})
    require_project_access(current_user, project_id)
    if payload.owner_user_id is not None and not user_exists(payload.owner_user_id):
        raise HTTPException(status_code=404, detail="owner user not found")
    if payload.probability not in {"low", "medium", "high"}:
        raise HTTPException(status_code=400, detail="invalid probability")
    if payload.impact not in {"low", "medium", "high"}:
        raise HTTPException(status_code=400, detail="invalid impact")
    if payload.status not in {"open", "mitigated", "closed"}:
        raise HTTPException(status_code=400, detail="invalid risk status")

    risk = create_project_risk(
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        probability=payload.probability,
        impact=payload.impact,
        mitigation_plan=payload.mitigation_plan,
        owner_user_id=payload.owner_user_id,
        status=payload.status,
    )
    create_audit_log(current_user["id"], "create", "project_risk", risk["id"], payload.title)
    return risk


@router.get("/projects/{project_id}/risks", response_model=list[ProjectRiskOut])
def list_project_risks_endpoint(
    project_id: int,
    status: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    require_roles(current_user, {"admin", "manager", "hr", "staff"})
    require_project_access(current_user, project_id)
    return list_project_risks(project_id, status=status)


# ── Weekly Status ──────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/weekly-status", response_model=WeeklyStatusOut)
def create_weekly_status_endpoint(
    project_id: int,
    payload: WeeklyStatusCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager", "hr"})
    require_project_access(current_user, project_id)
    if payload.sprint_id is not None and not sprint_exists(payload.sprint_id):
        raise HTTPException(status_code=404, detail="sprint not found")
    if payload.rag_status not in {"red", "amber", "green"}:
        raise HTTPException(status_code=400, detail="invalid rag_status")

    item = create_weekly_status_update(
        project_id=project_id,
        sprint_id=payload.sprint_id,
        week_label=payload.week_label,
        progress_percent=payload.progress_percent,
        rag_status=payload.rag_status,
        summary=payload.summary,
        next_steps=payload.next_steps,
        blocker=payload.blocker,
        created_by=current_user["id"],
    )
    create_audit_log(current_user["id"], "create", "weekly_status", item["id"], payload.week_label)
    return item


@router.get("/projects/{project_id}/weekly-status", response_model=list[WeeklyStatusOut])
def list_weekly_status_endpoint(
    project_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    require_roles(current_user, {"admin", "manager", "hr", "staff"})
    require_project_access(current_user, project_id)
    return list_weekly_status_updates(project_id, limit=limit)


# ── Portfolio ──────────────────────────────────────────────────────────────────

@router.get("/portfolio/summary")
def portfolio_summary_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_roles(current_user, {"admin", "manager", "hr"})
    return portfolio_summary()
