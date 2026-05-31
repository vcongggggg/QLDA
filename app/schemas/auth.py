from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=200)
    role: str = Field(description="admin|manager|staff|hr")
    department: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    department_id: int | None = None
    position: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    onboarding_status: Literal["invited", "pending", "active", "suspended"] = "invited"
    onboarding_note: str | None = Field(default=None, max_length=500)

class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    aad_object_id: str | None = None
    role: str
    department: str | None = None
    role_code: str | None = None
    role_detail: dict | None = None
    department_id: int | None = None
    department_detail: dict | None = None
    position: str | None = None
    avatar_url: str | None = None
    is_active: bool = True
    permissions: list[str] | None = None
    onboarding_status: str | None = None
    onboarding_note: str | None = None
    invited_at: datetime | None = None
    activated_at: datetime | None = None
    last_login_at: datetime | None = None

class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=200)
    role: str | None = None
    department_id: int | None = None
    position: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    position: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)

class UserOnboardingUpdate(BaseModel):
    onboarding_status: Literal["invited", "pending", "active", "suspended"]
    onboarding_note: str | None = Field(default=None, max_length=500)

class UserNotificationPreferencesOut(BaseModel):
    user_id: int
    app_enabled: bool = True
    email_enabled: bool = False
    teams_enabled: bool = True
    digest_enabled: bool = False
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    updated_at: datetime

class UserNotificationPreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_enabled: bool | None = None
    email_enabled: bool | None = None
    teams_enabled: bool | None = None
    digest_enabled: bool | None = None
    quiet_hours_start: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    quiet_hours_end: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    usernameOrEmail: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=1, max_length=128)

class AuthUserOut(BaseModel):
    id: int
    fullName: str
    email: str
    role: dict
    department: dict | None = None
    permissions: list[str]

class LoginResponse(BaseModel):
    accessToken: str
    tokenType: str = "Bearer"
    user: AuthUserOut

class AuthSecurityStatusOut(BaseModel):
    app_env: str
    status: Literal["ok", "warn", "fail"]
    jwt_validation_required: bool
    header_fallback_enabled: bool
    email_domain_allowlist_configured: bool
    teams_aad_validation_required: bool
    teams_real_graph_enabled: bool
    findings: list[str]

class RoleOut(BaseModel):
    slug: str
    name: str
    description: str | None = None
    is_system: bool | int = True

class PermissionOut(BaseModel):
    key: str
    name: str
    description: str | None = None
    category: str

class RolePermissionsOut(BaseModel):
    role: RoleOut
    permissions: list[PermissionOut]

class RolePermissionsUpdate(BaseModel):
    permission_keys: list[str] = Field(default_factory=list, max_length=100)

class RoleCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=60, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=250)
    permission_keys: list[str] = Field(default_factory=list, max_length=100)

class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=250)
    permission_keys: list[str] | None = Field(default=None, max_length=100)

class RolePermissionMatrixOut(BaseModel):
    roles: list[RoleOut]
    permissions: list[PermissionOut]
    matrix: dict[str, list[str]]
