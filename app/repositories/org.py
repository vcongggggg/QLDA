from app.repositories.shared import *

def department_exists(department_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM departments WHERE id = ?", (department_id,)).fetchone()
    return row is not None


def create_department(
    name: str,
    code: str,
    description: str | None = None,
    manager_user_id: int | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO departments (name, code, description, manager_user_id, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (name, code.upper(), description, manager_user_id, _now_iso()),
        )
        dep_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM departments WHERE id = ?", (dep_id,)).fetchone()
    return dict(row)


def list_departments(include_inactive: bool = False) -> list[dict[str, Any]]:
    with get_connection() as conn:
        query = """
            SELECT d.*, u.full_name AS manager_name, COUNT(m.id) AS member_count
            FROM departments d
            LEFT JOIN users u ON u.id = d.manager_user_id
            LEFT JOIN users m ON m.department_id = d.id
        """
        params: tuple[Any, ...] = ()
        if not include_inactive:
            query += " WHERE d.is_active = 1"
        query += " GROUP BY d.id, u.full_name ORDER BY d.id"
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_department_by_id(department_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM departments WHERE id = ?", (department_id,)).fetchone()
    return dict(row) if row else None


def update_department(
    department_id: int,
    *,
    name: str | None = None,
    code: str | None = None,
    description: str | None = None,
    manager_user_id: int | None = None,
    is_active: bool | None = None,
) -> dict[str, Any] | None:
    fields: list[str] = []
    params: list[Any] = []
    for column, value in (
        ("name", name),
        ("code", code.upper() if code else None),
        ("description", description),
        ("manager_user_id", manager_user_id),
        ("is_active", bool(is_active) if is_active is not None else None),
    ):
        if value is not None:
            fields.append(f"{column} = ?")
            params.append(value)
    if not fields:
        return get_department_by_id(department_id)
    params.append(department_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE departments SET {', '.join(fields)} WHERE id = ?", tuple(params))
        row = conn.execute("SELECT * FROM departments WHERE id = ?", (department_id,)).fetchone()
    return dict(row) if row else None


def list_department_members(department_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT u.*, r.name AS role_name, d.name AS department_name, d.code AS department_code
            FROM users u
            LEFT JOIN roles r ON r.slug = COALESCE(u.role_id, u.role)
            LEFT JOIN departments d ON d.id = u.department_id
            WHERE u.department_id = ?
            ORDER BY u.full_name
            """,
            (department_id,),
        ).fetchall()
    return [_user_profile_from_row(dict(r), include_permissions=False) for r in rows]
