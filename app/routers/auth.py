from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from jose import jwt

from app.auth import get_current_user, require_roles
from app.repository import get_user_by_id
from app.settings import settings

router = APIRouter(tags=["auth"])


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
