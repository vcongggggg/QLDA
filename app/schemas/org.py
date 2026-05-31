from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=20)
    description: str | None = Field(default=None, max_length=500)
    manager_user_id: int | None = None

class DepartmentOut(BaseModel):
    id: int
    name: str
    code: str
    description: str | None = None
    manager_user_id: int | None = None
    manager_name: str | None = None
    is_active: bool = True
    member_count: int | None = None
    created_at: datetime

class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=20)
    description: str | None = Field(default=None, max_length=500)
    manager_user_id: int | None = None
    is_active: bool | None = None
