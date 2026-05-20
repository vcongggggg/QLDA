from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_permission
from app.repository import (
    create_audit_log,
    list_permissions,
    list_permissions_for_role,
    list_roles,
    permission_keys_exist,
    replace_role_permissions,
    role_exists,
)
from app.schemas import PermissionOut, RoleOut, RolePermissionsOut, RolePermissionsUpdate

router = APIRouter(prefix="/rbac", tags=["rbac"])


@router.get("/roles", response_model=list[RoleOut])
def list_roles_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_permission(current_user, "roles.view")
    return list_roles()


@router.get("/permissions", response_model=list[PermissionOut])
def list_permissions_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_permission(current_user, "roles.view")
    return list_permissions()


@router.get("/roles/{role_slug}/permissions", response_model=RolePermissionsOut)
def role_permissions_endpoint(role_slug: str, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "roles.view")
    roles = [role for role in list_roles() if role["slug"] == role_slug]
    if not roles:
        raise HTTPException(status_code=404, detail="role not found")
    return {"role": roles[0], "permissions": list_permissions_for_role(role_slug)}


@router.put("/roles/{role_slug}/permissions", response_model=RolePermissionsOut)
def update_role_permissions_endpoint(
    role_slug: str,
    payload: RolePermissionsUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "roles.manage")
    if not role_exists(role_slug):
        raise HTTPException(status_code=404, detail="role not found")
    permission_keys = sorted(set(payload.permission_keys))
    if not permission_keys_exist(permission_keys):
        raise HTTPException(status_code=400, detail="unknown permission key")
    permissions = replace_role_permissions(role_slug, permission_keys)
    create_audit_log(current_user["id"], "update", "role_permissions", None, f"role={role_slug}")
    role = [item for item in list_roles() if item["slug"] == role_slug][0]
    return {"role": role, "permissions": permissions}
