from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class AuditLogOut(BaseModel):
    id: int
    actor_user_id: int | None
    actor_name: str | None = None
    action: str
    entity: str
    entity_id: int | None = None
    detail: str | None = None
    created_at: datetime
