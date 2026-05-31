from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=200)
    role: str = Field(description="admin|manager|staff|hr")
    department: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    department_id: int | None = None
    position: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)

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

class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=200)
    role: str | None = None
    department_id: int | None = None
    position: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

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
