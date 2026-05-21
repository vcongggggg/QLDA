from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_permission
from app.rag import chunk_text, query_rag
from app.repository import create_audit_log, create_rag_document, delete_rag_document, list_rag_documents
from app.schemas import RagDocumentCreate, RagDocumentOut, RagQueryRequest, RagQueryResponse

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/documents", response_model=RagDocumentOut)
def create_rag_document_endpoint(
    payload: RagDocumentCreate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_permission(current_user, "rag.manage")
    chunks = chunk_text(payload.content)
    if not chunks:
        raise HTTPException(status_code=400, detail="document content is empty")
    item = create_rag_document(
        title=payload.title,
        source_label=payload.source_label,
        content_chunks=chunks,
        created_by=int(current_user["id"]),
    )
    create_audit_log(current_user["id"], "create", "rag_document", item["id"], f"chunks={len(chunks)}")
    return item


@router.get("/documents", response_model=list[RagDocumentOut])
def list_rag_documents_endpoint(current_user: dict = Depends(get_current_user)) -> list[dict]:
    require_permission(current_user, "rag.query")
    return list_rag_documents()


@router.delete("/documents/{document_id}")
def delete_rag_document_endpoint(document_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "rag.manage")
    if not delete_rag_document(document_id):
        raise HTTPException(status_code=404, detail="rag document not found")
    create_audit_log(current_user["id"], "delete", "rag_document", document_id, None)
    return {"deleted": True}


@router.post("/query", response_model=RagQueryResponse)
def query_rag_endpoint(payload: RagQueryRequest, current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, "rag.query")
    return {"matches": query_rag(payload.query, payload.limit)}
