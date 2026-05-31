from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth import get_current_user, require_permission
from app.reporting import build_rbac_matrix_csv, build_rbac_matrix_xlsx
from app.repository import (
    create_audit_log,
    create_role,
    get_role,
    list_permissions,
    list_permissions_for_role,
    list_roles,
    permission_keys_exist,
    replace_role_permissions,
    role_exists,
    role_permission_matrix,
    update_role,
)
from app.schemas import (
    PermissionOut,
    RoleCreate,
    RoleOut,
    RolePermissionMatrixOut,
    RolePermissionsOut,
    RolePermissionsUpdate,
    RoleUpdate,
)

router = APIRouter(prefix="/rbac", tags=["rbac"])


@router.get("/roles", response_model=list[RoleOut])
def list_roles_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_permission(current_user, "roles.view")
    return list_roles()


@router.post("/roles", response_model=RoleOut)
def create_role_endpoint(payload: RoleCreate, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "roles.manage")
    permission_keys = sorted(set(payload.permission_keys))
    if not permission_keys_exist(permission_keys):
        raise HTTPException(status_code=400, detail="unknown permission key")
    try:
        role = create_role(payload.slug, payload.name, payload.description, permission_keys)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    create_audit_log(current_user["id"], "create", "role", None, f"role={role['slug']}")
    return role


@router.patch("/roles/{role_slug}", response_model=RolePermissionsOut)
def update_role_endpoint(
    role_slug: str,
    payload: RoleUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "roles.manage")
    role = get_role(role_slug)
    if not role:
        raise HTTPException(status_code=404, detail="role not found")
    if payload.permission_keys is not None and not permission_keys_exist(sorted(set(payload.permission_keys))):
        raise HTTPException(status_code=400, detail="unknown permission key")
    updated = update_role(str(role["slug"]), name=payload.name, description=payload.description)
    if payload.permission_keys is not None:
        permissions = replace_role_permissions(str(role["slug"]), sorted(set(payload.permission_keys)))
    else:
        permissions = list_permissions_for_role(str(role["slug"]))
    create_audit_log(current_user["id"], "update", "role", None, f"role={role['slug']}")
    return {"role": updated or role, "permissions": permissions}


@router.get("/permissions", response_model=list[PermissionOut])
def list_permissions_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_permission(current_user, "roles.view")
    return list_permissions()


@router.get("/matrix", response_model=RolePermissionMatrixOut)
def role_permission_matrix_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "roles.view")
    return role_permission_matrix()


@router.get("/matrix.csv")
def role_permission_matrix_csv_endpoint(current_user: dict = Depends(get_current_user)) -> Response:
    require_permission(current_user, "roles.view")
    return Response(
        build_rbac_matrix_csv(role_permission_matrix()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=teamswork-rbac-matrix.csv"},
    )


@router.get("/matrix.xlsx")
def role_permission_matrix_xlsx_endpoint(current_user: dict = Depends(get_current_user)) -> Response:
    require_permission(current_user, "roles.view")
    return Response(
        build_rbac_matrix_xlsx(role_permission_matrix()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=teamswork-rbac-matrix.xlsx"},
    )


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
