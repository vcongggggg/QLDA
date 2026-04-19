from fastapi import Header, HTTPException
from jose import JWTError, jwt

from app.repository import get_user_by_id
from app.settings import settings


def _parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="invalid bearer token format")
    return parts[1]


def _get_user_from_jwt(token: str) -> dict:
    if settings.auth_disable_jwt_validation:
        raise HTTPException(status_code=401, detail="jwt auth disabled in current environment")

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
    return user


def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_id: int | None = Header(default=None),
) -> dict:
    token = _parse_bearer_token(authorization)
    if token:
        if settings.auth_disable_jwt_validation:
            if not settings.auth_allow_header_fallback:
                raise HTTPException(status_code=401, detail="jwt validation disabled and header fallback blocked")
        else:
            return _get_user_from_jwt(token)

    if not settings.auth_allow_header_fallback:
        raise HTTPException(status_code=401, detail="missing/invalid bearer token")
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="missing X-User-Id header")

    user = get_user_by_id(x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="invalid user")
    return user


def require_roles(user: dict, allowed_roles: set[str]) -> None:
    role = user.get("role")
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail="forbidden")
