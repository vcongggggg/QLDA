from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_roles
from app.repository import create_audit_log, create_user, list_users
from app.schemas import UserCreate, UserOut

router = APIRouter(tags=["users"])


@router.post("/users", response_model=UserOut)
def create_user_endpoint(payload: UserCreate, current_user: dict = Depends(get_current_user)) -> dict:
    require_roles(current_user, {"admin"})
    valid_roles = {"admin", "manager", "staff", "hr"}
    if payload.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"role must be one of {sorted(valid_roles)}")
    try:
        user = create_user(payload.full_name, payload.email, payload.role, payload.department)
        create_audit_log(current_user["id"], "create", "user", user["id"], f"create user {user['email']}")
        return user
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/users", response_model=list[UserOut])
def list_users_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_roles(current_user, {"admin", "manager", "hr"})
    return list_users()
