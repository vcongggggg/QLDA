from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_permission
from app.repository import (
    create_audit_log,
    create_user,
    department_exists,
    list_roles,
    list_users,
    reset_user_password,
    update_user,
    update_user_active,
)
from app.schemas import PasswordReset, UserCreate, UserOut, UserUpdate

router = APIRouter(tags=["users"])


@router.post("/users", response_model=UserOut)
def create_user_endpoint(payload: UserCreate, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "USER_CREATE")
    valid_roles = {role["slug"] for role in list_roles()}
    if payload.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"role must be one of {sorted(valid_roles)}")
    if payload.department_id is not None and not department_exists(payload.department_id):
        raise HTTPException(status_code=404, detail="department not found")
    try:
        user = create_user(
            payload.full_name,
            str(payload.email),
            payload.role,
            payload.department,
            password=payload.password,
            department_id=payload.department_id,
            position=payload.position,
            avatar_url=payload.avatar_url,
        )
        create_audit_log(current_user["id"], "create", "user", user["id"], f"create user {user['email']}")
        return user
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/users/me", response_model=UserOut)
def get_current_user_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    return current_user


@router.get("/users", response_model=list[UserOut])
def list_users_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_permission(current_user, "USER_VIEW")
    return list_users()


@router.put("/users/{user_id}", response_model=UserOut)
def update_user_endpoint(user_id: int, payload: UserUpdate, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "USER_UPDATE")
    if payload.department_id is not None and not department_exists(payload.department_id):
        raise HTTPException(status_code=404, detail="department not found")
    updated = update_user(
        user_id,
        full_name=payload.full_name,
        email=str(payload.email) if payload.email else None,
        role=payload.role,
        department_id=payload.department_id,
        position=payload.position,
        avatar_url=payload.avatar_url,
        is_active=payload.is_active,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="user not found")
    create_audit_log(current_user["id"], "update", "user", user_id, "update user profile")
    return updated


@router.patch("/users/{user_id}/active", response_model=UserOut)
def set_user_active_endpoint(user_id: int, payload: UserUpdate, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "USER_DEACTIVATE")
    if payload.is_active is None:
        raise HTTPException(status_code=400, detail="is_active is required")
    updated = update_user_active(user_id, payload.is_active)
    if not updated:
        raise HTTPException(status_code=404, detail="user not found")
    create_audit_log(current_user["id"], "update_active", "user", user_id, f"is_active={payload.is_active}")
    return updated


@router.post("/users/{user_id}/reset-password")
def reset_password_endpoint(user_id: int, payload: PasswordReset, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "USER_RESET_PASSWORD")
    if not reset_user_password(user_id, payload.password):
        raise HTTPException(status_code=404, detail="user not found")
    create_audit_log(current_user["id"], "reset_password", "user", user_id, "password reset")
    return {"ok": True}
