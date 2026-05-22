from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from jose import jwt

from app.auth import authenticate_user, create_access_token, get_current_user, require_roles
from app.repository import get_user_by_id
from app.schemas import AuthUserOut, LoginRequest, LoginResponse
from app.settings import settings

router = APIRouter(tags=["auth"])


def _auth_user_payload(user: dict) -> dict:
    return {
        "id": int(user["id"]),
        "fullName": user["full_name"],
        "email": user["email"],
        "role": user.get("role_detail") or {"code": user.get("role_code") or user.get("role"), "name": user.get("role")},
        "department": user.get("department_detail"),
        "permissions": user.get("permissions") or [],
    }


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> dict:
    user = authenticate_user(payload.usernameOrEmail, payload.password)
    return {
        "accessToken": create_access_token(user),
        "tokenType": "Bearer",
        "user": _auth_user_payload(user),
    }


@router.get("/auth/me", response_model=AuthUserOut)
def auth_me(current_user: dict = Depends(get_current_user)) -> dict:
    return _auth_user_payload(current_user)


@router.post("/auth/logout")
def logout(_: dict = Depends(get_current_user)) -> dict:
    return {"ok": True}


@router.post("/auth/token")
def issue_access_token(
    user_id: int = Query(..., ge=1),
    expires_minutes: int = Query(default=480, ge=5, le=1440),
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin"})
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    exp = int(datetime.now(timezone.utc).timestamp()) + expires_minutes * 60
    payload = {
        "sub": str(user["id"]),
        "uid": int(user["id"]),
        "role": user.get("role"),
        "exp": exp,
    }
    token = jwt.encode(payload, settings.auth_jwt_secret, algorithm=settings.auth_jwt_algorithm)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_minutes * 60,
        "user_id": int(user["id"]),
        "role": user.get("role"),
    }
