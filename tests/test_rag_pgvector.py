from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.rag import HybridScores, chunk_text, combine_hybrid_score, query_rag
from app.repository import add_project_member, create_project, create_rag_document, create_user
from app.settings import Settings, parse_bool, settings


client = TestClient(app)


def _hdr(user_id: int) -> dict[str, str]:
    return {"X-User-Id": str(user_id)}


def _bootstrap_project() -> tuple[int, int, int, int, int]:
    init_db()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    admin = create_user("RAG Admin", f"rag.admin.{stamp}@example.com", "admin", "PMO")
    manager = create_user("RAG Manager", f"rag.manager.{stamp}@example.com", "manager", "PMO")
    staff = create_user("RAG Staff", f"rag.staff.{stamp}@example.com", "staff", "Engineering")
    outsider = create_user("RAG Outsider", f"rag.outsider.{stamp}@example.com", "manager", "Sales")
    project = create_project(
        f"RAG Project {stamp}",
        None,
        None,
        int(manager["id"]),
        None,
        None,
        "active",
    )
    add_project_member(int(project["id"]), int(staff["id"]), "member")
    return int(admin["id"]), int(manager["id"]), int(staff["id"]), int(outsider["id"]), int(project["id"])


def test_settings_boolean_parser_and_rag_defaults() -> None:
    assert parse_bool("false", default=True) is False
    assert parse_bool("0", default=True) is False
    assert parse_bool("no", default=True) is False
    assert parse_bool("off", default=True) is False

    cfg = Settings()

    assert cfg.rag_vector_backend == "pgvector"
    assert cfg.rag_embedding_enabled is False
    assert cfg.rag_embedding_provider == "openai_compatible"
    assert cfg.rag_embedding_model == "text-embedding-3-small"
    assert cfg.rag_embedding_dim == 1536
    assert cfg.rag_score_threshold == 0.45
    assert cfg.rag_search_limit == 5
    assert cfg.rag_storage_root == ".data/rag_uploads"
    assert cfg.rag_pdf_enabled is False


def test_chunk_text_uses_overlap_and_estimates_tokens() -> None:
    text = " ".join(f"word{i:04d}" for i in range(520))

    chunks = chunk_text(text)

    assert len(chunks) > 1
    assert all(900 <= item.char_count <= 1100 for item in chunks[:-1])
    assert all(item.token_estimate == -(-item.char_count // 4) for item in chunks)
    assert chunks[0].content[-150:] == chunks[1].content[:150]


def test_hybrid_score_weights_fallback_and_semantic_modes() -> None:
    scores = HybridScores(semantic=0.8, lexical=0.6, tfidf=0.5, phrase=1.0)

    assert combine_hybrid_score(scores, embedding_enabled=True) == pytest.approx(0.78)
    assert combine_hybrid_score(scores, embedding_enabled=False) == pytest.approx(0.6)


def test_repository_acl_filter_hides_restricted_rag_documents(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rag_embedding_enabled", False)
    _admin_id, manager_id, staff_id, outsider_id, project_id = _bootstrap_project()
    other_project = create_project("Hidden RAG Project", None, None, outsider_id, None, None, "active")

    visible = create_rag_document(
        title="Visible project spec",
        source_label="visible-spec",
        project_id=project_id,
        content_chunks=chunk_text("Manager and member can query sprint planning RAG material."),
        created_by=manager_id,
    )
    create_rag_document(
        title="Hidden project spec",
        source_label="hidden-spec",
        project_id=int(other_project["id"]),
        content_chunks=chunk_text("Outsider only confidential payroll migration material."),
        created_by=outsider_id,
    )

    staff_matches = query_rag("sprint planning payroll migration", current_user={"id": staff_id, "role": "staff"})
    outsider_matches = query_rag("sprint planning payroll migration", current_user={"id": outsider_id, "role": "manager"})

    assert {item["document_id"] for item in staff_matches} == {visible["id"]}
    assert all(item["source_label"] != "hidden-spec" for item in staff_matches)
    assert {item["source_label"] for item in outsider_matches} == {"hidden-spec"}


def test_rag_api_project_scoped_crud_and_acl(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rag_embedding_enabled", False)
    _admin_id, manager_id, staff_id, outsider_id, project_id = _bootstrap_project()

    missing_project = client.post(
        "/rag/documents",
        headers=_hdr(manager_id),
        json={"title": "Missing project", "source_label": "bad", "content": "Long enough content but no project."},
    )
    assert missing_project.status_code == 422

    created = client.post(
        "/rag/documents",
        headers=_hdr(manager_id),
        json={
            "title": "Project RAG spec",
            "source_label": "project-spec",
            "project_id": project_id,
            "content": "Manager can export KPI report to CSV and XLSX. Staff can only query allowed project context.",
        },
    )
    assert created.status_code == 200
    doc = created.json()
    assert doc["project_id"] == project_id
    assert doc["chunk_count"] >= 1

    listed = client.get("/rag/documents", headers=_hdr(staff_id))
    assert listed.status_code == 200
    assert any(item["id"] == doc["id"] for item in listed.json())

    outsider_query = client.post(
        "/rag/query",
        headers=_hdr(outsider_id),
        json={"query": "export KPI report", "limit": 3},
    )
    assert outsider_query.status_code == 200
    assert outsider_query.json()["matches"] == []

    staff_query = client.post(
        "/rag/query",
        headers=_hdr(staff_id),
        json={"query": "export KPI report", "limit": 3},
    )
    assert staff_query.status_code == 200
    assert staff_query.json()["matches"][0]["project_id"] == project_id

    outsider_delete = client.delete(f"/rag/documents/{doc['id']}", headers=_hdr(outsider_id))
    assert outsider_delete.status_code == 404

    deleted = client.delete(f"/rag/documents/{doc['id']}", headers=_hdr(manager_id))
    assert deleted.status_code == 200


def test_ai_text_does_not_query_rag_when_disabled(monkeypatch) -> None:
    _admin_id, manager_id, _staff_id, _outsider_id, _project_id = _bootstrap_project()
    monkeypatch.setattr(settings, "ai_api_key", "")

    def fail_query_rag(*_args, **_kwargs):
        raise AssertionError("query_rag should not be called")

    monkeypatch.setattr("app.routers.ai.query_rag", fail_query_rag)

    preview = client.post(
        "/ai/task-breakdown",
        headers=_hdr(manager_id),
        json={
            "text": "Can phan tich yeu cau xuat bao cao KPI thanh cong viec",
            "max_tasks": 3,
            "use_rag": False,
        },
    )

    assert preview.status_code == 200
    assert preview.json()["retrieved_context_count"] == 0
