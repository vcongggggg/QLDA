from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_permission
from app.repository import (
    create_audit_log,
    create_user,
    department_exists,
    get_user_notification_preferences,
    invite_user,
    list_roles,
    list_users,
    reset_user_password,
    update_user,
    update_user_active,
    update_user_notification_preferences,
    update_user_onboarding,
)
from app.schemas import (
    PasswordReset,
    UserCreate,
    UserNotificationPreferencesOut,
    UserNotificationPreferencesUpdate,
    UserOnboardingUpdate,
    UserOut,
    UserProfileUpdate,
    UserUpdate,
)

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
            onboarding_status=payload.onboarding_status,
            onboarding_note=payload.onboarding_note,
        )
        create_audit_log(current_user["id"], "create", "user", user["id"], f"create user {user['email']}")
        return user
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/users/me", response_model=UserOut)
def get_current_user_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    return current_user


@router.patch("/users/me", response_model=UserOut)
def update_current_user_endpoint(
    payload: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    updated = update_user(
        int(current_user["id"]),
        full_name=payload.full_name,
        position=payload.position,
        avatar_url=payload.avatar_url,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="user not found")
    create_audit_log(current_user["id"], "update_profile", "user", int(current_user["id"]), "update own profile")
    return updated


@router.get("/users/me/notification-settings", response_model=UserNotificationPreferencesOut)
def get_current_user_notification_settings_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    return get_user_notification_preferences(int(current_user["id"]))


@router.patch("/users/me/notification-settings", response_model=UserNotificationPreferencesOut)
def update_current_user_notification_settings_endpoint(
    payload: UserNotificationPreferencesUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    updated = update_user_notification_preferences(
        int(current_user["id"]),
        **payload.model_dump(exclude_unset=True),
    )
    create_audit_log(
        current_user["id"],
        "update_notification_settings",
        "user_notification_preferences",
        int(current_user["id"]),
        "update own notification settings",
    )
    return updated


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


@router.post("/users/{user_id}/invite", response_model=UserOut)
def invite_user_endpoint(user_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "USER_UPDATE")
    updated = invite_user(user_id)
    if not updated:
        raise HTTPException(status_code=404, detail="user not found")
    create_audit_log(current_user["id"], "invite", "user", user_id, "invite user")
    return updated


@router.patch("/users/{user_id}/onboarding", response_model=UserOut)
def update_user_onboarding_endpoint(
    user_id: int,
    payload: UserOnboardingUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "USER_UPDATE")
    updated = update_user_onboarding(user_id, payload.onboarding_status, payload.onboarding_note)
    if not updated:
        raise HTTPException(status_code=404, detail="user not found")
    create_audit_log(
        current_user["id"],
        "update_onboarding",
        "user",
        user_id,
        f"onboarding_status={payload.onboarding_status}",
    )
    return updated


@router.post("/users/{user_id}/reset-password")
def reset_password_endpoint(user_id: int, payload: PasswordReset, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "USER_RESET_PASSWORD")
    if not reset_user_password(user_id, payload.password):
        raise HTTPException(status_code=404, detail="user not found")
    create_audit_log(current_user["id"], "reset_password", "user", user_id, "password reset")
    return {"ok": True}
