from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class RagDocumentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    source_label: str | None = Field(default=None, max_length=120)
    project_id: int
    content: str = Field(min_length=20, max_length=50000)

class RagDocumentOut(BaseModel):
    id: int
    title: str
    source_label: str | None = None
    project_id: int
    storage_path: str | None = None
    created_by: int
    created_at: datetime
    chunk_count: int = 0

class RagQueryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    limit: int = Field(default=5, ge=1, le=10)

class RagQueryMatch(BaseModel):
    chunk_id: int | None = None
    chunk_index: int | None = None
    document_id: int
    document_title: str
    project_id: int | None = None
    source_label: str | None = None
    content: str
    score: float
    source_info: dict | None = None

class RagQueryResponse(BaseModel):
    matches: list[RagQueryMatch]
