from fastapi import HTTPException

from app.repository import get_project_by_id, is_project_member


def require_project_access(current_user: dict, project_id: int) -> None:
    """Raise 403/404 if current_user cannot access the project."""
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    if current_user["role"] in {"admin", "hr"}:
        return

    if int(project.get("manager_id") or 0) == int(current_user["id"]):
        return

    if is_project_member(project_id, int(current_user["id"])):
        return

    raise HTTPException(status_code=403, detail="forbidden project access")
