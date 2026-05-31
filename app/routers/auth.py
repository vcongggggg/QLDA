from datetime import datetime, timedelta, timezone
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from jose import jwt

from app.auth import authenticate_user, create_access_token, get_current_user, require_roles
from app.repository import get_user_by_id, recent_failed_login_attempt_summary, record_auth_login_attempt
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


def _client_ip_hash(request: Request) -> str:
    raw_ip = request.client.host if request.client else "unknown"
    return sha256(f"{settings.auth_jwt_secret}:{raw_ip}".encode("utf-8")).hexdigest()


def _login_window_start() -> str:
    minutes = int(getattr(settings, "auth_failed_login_window_minutes", 30))
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def _failure_reason(exc: HTTPException) -> str:
    if exc.status_code == 403 and exc.detail == "email domain is not allowed":
        return "domain_not_allowed"
    if exc.status_code == 403 and exc.detail == "user is inactive":
        return "inactive_user"
    return "invalid_credentials"


def _is_login_blocked(email: str, ip_hash: str) -> bool:
    summary = recent_failed_login_attempt_summary(email, ip_hash, _login_window_start())
    limit = int(getattr(settings, "auth_failed_login_limit", 5))
    if summary["count"] < limit:
        return False
    latest = summary.get("latest_created_at")
    if not latest:
        return True
    try:
        latest_at = datetime.fromisoformat(str(latest))
    except ValueError:
        return True
    block_minutes = int(getattr(settings, "auth_failed_login_block_minutes", 30))
    return datetime.now(timezone.utc) < latest_at + timedelta(minutes=block_minutes)


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request) -> dict:
    email = payload.usernameOrEmail.strip().lower()
    ip_hash = _client_ip_hash(request)
    if _is_login_blocked(email, ip_hash):
        record_auth_login_attempt(email, ip_hash, "blocked", "rate_limited")
        raise HTTPException(status_code=429, detail="too many login attempts; try again later")

    try:
        user = authenticate_user(email, payload.password)
    except HTTPException as exc:
        record_auth_login_attempt(email, ip_hash, "failure", _failure_reason(exc))
        raise

    record_auth_login_attempt(email, ip_hash, "success", "authenticated")
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
