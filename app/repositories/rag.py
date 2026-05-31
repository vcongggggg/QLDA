from app.repositories.shared import *

def create_rag_document(
    title: str,
    source_label: str | None,
    project_id: int,
    content_chunks: list[Any],
    created_by: int,
    storage_path: str | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO rag_documents (title, source_label, project_id, storage_path, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, source_label, project_id, storage_path, created_by, _now_iso()),
        )
        document_id = int(cursor.lastrowid)
        for index, chunk in enumerate(content_chunks):
            content = str(getattr(chunk, "content", chunk))
            char_count = int(getattr(chunk, "char_count", len(content)))
            token_estimate = int(getattr(chunk, "token_estimate", max(1, -(-char_count // 4))))
            conn.execute(
                """
                INSERT INTO rag_chunks
                (document_id, content, source_label, chunk_index, char_count, token_estimate, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, content, source_label, index, char_count, token_estimate, _now_iso()),
            )
        conn.execute(
            """
            /* no-returning-id */ INSERT INTO rag_document_permissions
            (document_id, project_id, user_id, role_slug, access_level, created_at)
            VALUES (?, ?, NULL, NULL, 'query', ?)
            ON CONFLICT(document_id, project_id, user_id, role_slug) DO NOTHING
            """,
            (document_id, project_id, _now_iso()),
        )
        row = conn.execute("SELECT * FROM rag_documents WHERE id = ?", (document_id,)).fetchone()
    item = dict(row)
    item["chunk_count"] = len(content_chunks)
    return item


def _rag_acl_clause(current_user: dict[str, Any] | None) -> tuple[str, list[Any]]:
    if current_user is None:
        return "1=1", []
    user_id = int(current_user["id"])
    role = str(current_user.get("role") or "")
    if role in {"admin", "hr"}:
        return "d.project_id IS NOT NULL", []
    return (
        """
        d.project_id IS NOT NULL
        AND EXISTS (
            SELECT 1
            FROM rag_document_permissions rdp
            JOIN projects p ON p.id = rdp.project_id
            LEFT JOIN project_members pm ON pm.project_id = rdp.project_id AND pm.user_id = ?
            WHERE rdp.document_id = d.id
              AND rdp.access_level IN ('query', 'manage')
              AND (
                p.manager_id = ?
                OR pm.id IS NOT NULL
                OR rdp.user_id = ?
                OR rdp.role_slug = ?
              )
        )
        """,
        [user_id, user_id, user_id, role],
    )


def list_rag_documents(current_user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    acl_sql, params = _rag_acl_clause(current_user)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT d.*, COUNT(c.id) AS chunk_count
            FROM rag_documents d
            LEFT JOIN rag_chunks c ON c.document_id = d.id
            WHERE {acl_sql}
            GROUP BY d.id, d.title, d.source_label, d.project_id, d.storage_path, d.created_by, d.created_at
            ORDER BY d.id DESC
            """,
            tuple(params),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_rag_document(document_id: int, current_user: dict[str, Any] | None = None) -> bool:
    acl_sql, params = _rag_acl_clause(current_user)
    with get_connection() as conn:
        existing = conn.execute(
            f"SELECT d.id FROM rag_documents d WHERE d.id = ? AND {acl_sql}",
            (document_id, *params),
        ).fetchone()
        if not existing:
            return False
        chunk_rows = conn.execute("SELECT id FROM rag_chunks WHERE document_id = ?", (document_id,)).fetchall()
        for row in chunk_rows:
            conn.execute("DELETE FROM rag_chunk_embeddings WHERE chunk_id = ?", (row["id"],))
        conn.execute("DELETE FROM rag_document_permissions WHERE document_id = ?", (document_id,))
        conn.execute("DELETE FROM rag_chunks WHERE document_id = ?", (document_id,))
        conn.execute("DELETE FROM rag_documents WHERE id = ?", (document_id,))
    return True


def list_rag_chunks(limit: int = 500, current_user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    acl_sql, params = _rag_acl_clause(current_user)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT c.*, d.title AS document_title, d.project_id AS project_id
            FROM rag_chunks c
            JOIN rag_documents d ON d.id = c.document_id
            WHERE {acl_sql}
            ORDER BY c.id DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def list_rag_chunks_for_document(document_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.*
            FROM rag_chunks c
            WHERE c.document_id = ?
            ORDER BY c.chunk_index ASC
            """,
            (document_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def store_rag_chunk_embedding(
    chunk_id: int,
    provider: str,
    model: str,
    dim: int,
    version: str,
    embedding: list[float],
) -> None:
    import json

    with get_connection() as conn:
        if conn.dialect == "postgresql":
            vector_value = "[" + ",".join(str(float(value)) for value in embedding) + "]"
            conn.execute(
                """
                /* no-returning-id */ INSERT INTO rag_chunk_embeddings
                (chunk_id, provider, model, dim, version, embedding, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id, provider, model, version) DO UPDATE SET
                    dim = excluded.dim,
                    embedding = excluded.embedding,
                    created_at = excluded.created_at
                """,
                (chunk_id, provider, model, dim, version, vector_value, _now_iso()),
            )
            return
        conn.execute(
            """
            /* no-returning-id */ INSERT INTO rag_chunk_embeddings
            (chunk_id, provider, model, dim, version, embedding_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id, provider, model, version) DO UPDATE SET
                dim = excluded.dim,
                embedding_json = excluded.embedding_json,
                created_at = excluded.created_at
            """,
            (chunk_id, provider, model, dim, version, json.dumps(embedding, ensure_ascii=True), _now_iso()),
        )


def search_rag_chunks_by_embedding(
    embedding: list[float],
    provider: str,
    model: str,
    version: str,
    limit: int,
    current_user: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    vector_value = "[" + ",".join(str(float(value)) for value in embedding) + "]"
    acl_sql, params = _rag_acl_clause(current_user)
    with get_connection() as conn:
        if conn.dialect != "postgresql":
            return []
        rows = conn.execute(
            f"""
            SELECT
                c.*,
                d.title AS document_title,
                d.project_id AS project_id,
                (e.embedding <=> ?::vector) AS distance
            FROM rag_chunk_embeddings e
            JOIN rag_chunks c ON c.id = e.chunk_id
            JOIN rag_documents d ON d.id = c.document_id
            WHERE e.provider = ?
              AND e.model = ?
              AND e.version = ?
              AND {acl_sql}
            ORDER BY e.embedding <=> ?::vector ASC
            LIMIT ?
            """,
            (vector_value, provider, model, version, *params, vector_value, limit),
        ).fetchall()
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["semantic_score"] = max(0.0, 1.0 - float(item.pop("distance") or 1.0))
        output.append(item)
    return output
