from app.repositories.shared import *

def create_audit_log(
    actor_user_id: int | None,
    action: str,
    entity: str,
    entity_id: int | None,
    detail: str | None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs (actor_user_id, action, entity, entity_id, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (actor_user_id, action, entity, entity_id, detail, _now_iso()),
        )


def list_audit_logs(
    limit: int = 100,
    actor_id: int | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    keyword: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT al.*, u.full_name AS actor_name
        FROM audit_logs al
        LEFT JOIN users u ON u.id = al.actor_user_id
        WHERE 1=1
    """
    params: list[Any] = []
    if actor_id is not None:
        query += " AND al.actor_user_id = ?"
        params.append(actor_id)
    if action:
        query += " AND al.action = ?"
        params.append(action)
    if entity_type:
        query += " AND al.entity = ?"
        params.append(entity_type)
    if date_from:
        query += " AND al.created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND al.created_at <= ?"
        params.append(date_to)
    if keyword:
        query += """
            AND (
                LOWER(COALESCE(al.detail, '')) LIKE ?
                OR LOWER(al.action) LIKE ?
                OR LOWER(al.entity) LIKE ?
                OR LOWER(COALESCE(u.full_name, '')) LIKE ?
            )
        """
        term = f"%{keyword.lower()}%"
        params.extend([term, term, term, term])
    query += " ORDER BY al.id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["detail"] = _redact_operational_text(item.get("detail"))
        output.append(item)
    return output
