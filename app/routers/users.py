from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_permission
from app.repository import create_audit_log, create_user, list_roles, list_users
from app.schemas import UserCreate, UserOut

router = APIRouter(tags=["users"])


@router.post("/users", response_model=UserOut)
def create_user_endpoint(payload: UserCreate, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "users.create")
    valid_roles = {role["slug"] for role in list_roles()}
    if payload.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"role must be one of {sorted(valid_roles)}")
    try:
        user = create_user(payload.full_name, payload.email, payload.role, payload.department)
        create_audit_log(current_user["id"], "create", "user", user["id"], f"create user {user['email']}")
        return user
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/users/me", response_model=UserOut)
def get_current_user_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    return current_user


@router.get("/users", response_model=list[UserOut])
def list_users_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_permission(current_user, "users.view")
    return list_users()
