from datetime import datetime, timezone

from fastapi import Header, HTTPException
from jose import JWTError, jwt

from app.passwords import verify_password
from app.repository import canonical_role_code, get_user_by_id, get_user_by_username_or_email, role_has_permission
from app.settings import settings


def _parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="invalid bearer token format")
    return parts[1]


def _get_user_from_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.auth_jwt_secret, algorithms=[settings.auth_jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"invalid access token: {exc}") from exc

    raw_user_id = payload.get("uid") or payload.get("user_id") or payload.get("sub")
    try:
        user_id = int(raw_user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="invalid token subject") from exc

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="token user not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="user is inactive")
    return user


def create_access_token(user: dict, expires_minutes: int = 480) -> str:
    exp = int(datetime.now(timezone.utc).timestamp()) + expires_minutes * 60
    payload = {
        "sub": str(user["id"]),
        "uid": int(user["id"]),
        "role": canonical_role_code(user.get("role_id") or user.get("role")),
        "exp": exp,
    }
    return jwt.encode(payload, settings.auth_jwt_secret, algorithm=settings.auth_jwt_algorithm)


def authenticate_user(username_or_email: str, password: str) -> dict:
    user = get_user_by_username_or_email(username_or_email, include_password=True)
    if not user or not verify_password(password, user.get("password_hash")):
        raise HTTPException(status_code=401, detail="invalid username/email or password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="user is inactive")
    user.pop("password_hash", None)
    return user


def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_id: int | None = Header(default=None),
) -> dict:
    token = _parse_bearer_token(authorization)
    if token:
        try:
            return _get_user_from_jwt(token)
        except HTTPException:
            if not settings.auth_disable_jwt_validation or not settings.auth_allow_header_fallback:
                raise

    if not settings.auth_allow_header_fallback:
        raise HTTPException(status_code=401, detail="missing/invalid bearer token")
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="missing X-User-Id header")

    user = get_user_by_id(x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="invalid user")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="user is inactive")
    return user


def require_roles(user: dict, allowed_roles: set[str]) -> None:
    role_candidates = {
        str(user.get("role") or ""),
        str(user.get("role_id") or ""),
        str(user.get("role_code") or ""),
        canonical_role_code(str(user.get("role_id") or user.get("role") or "")),
    }
    allowed_candidates = set(allowed_roles) | {canonical_role_code(role) for role in allowed_roles}
    if role_candidates.isdisjoint(allowed_candidates):
        raise HTTPException(status_code=403, detail="forbidden")


def current_role_code(user: dict) -> str:
    return canonical_role_code(user.get("role_id") or user.get("role_code") or user.get("role"))


def is_member_role(user: dict) -> bool:
    return current_role_code(user) == "MEMBER"


def has_permission(user: dict, permission_key: str) -> bool:
    role = str(user.get("role_id") or user.get("role_code") or user.get("role") or "")
    return role_has_permission(role, permission_key)


def require_permission(user: dict, permission_key: str) -> None:
    if not has_permission(user, permission_key):
        raise HTTPException(status_code=403, detail="forbidden")
