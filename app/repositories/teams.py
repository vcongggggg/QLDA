from app.repositories.shared import *

def upsert_teams_conversation_ref(
    user_id: int | None,
    aad_object_id: str | None,
    conversation_id: str,
    service_url: str | None,
    tenant_id: str | None,
    channel_id: str | None,
) -> dict[str, Any]:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM teams_conversation_refs WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE teams_conversation_refs
                SET user_id = ?, aad_object_id = ?, service_url = ?, tenant_id = ?, channel_id = ?
                WHERE id = ?
                """,
                (user_id, aad_object_id, service_url, tenant_id, channel_id, existing["id"]),
            )
            row = conn.execute(
                "SELECT * FROM teams_conversation_refs WHERE id = ?",
                (existing["id"],),
            ).fetchone()
            return dict(row)

        cursor = conn.execute(
            """
            INSERT INTO teams_conversation_refs
            (user_id, aad_object_id, conversation_id, service_url, tenant_id, channel_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, aad_object_id, conversation_id, service_url, tenant_id, channel_id, _now_iso()),
        )
        row = conn.execute(
            "SELECT * FROM teams_conversation_refs WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row)


def list_teams_conversation_refs(user_id: int | None = None, limit: int = 20) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if user_id is None:
            rows = conn.execute(
                "SELECT * FROM teams_conversation_refs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM teams_conversation_refs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]
