from app.seeding.shared import *

def seed_auth_demo_accounts() -> None:
    departments = (
        ("Administration", "ADM"),
        ("Project Management", "PMO"),
        ("Engineering", "ENG"),
        ("Human Resources", "HR"),
        ("Audit", "AUD"),
    )
    with get_connection() as conn:
        for name, code in departments:
            conn.execute(
                """
                /* no-returning-id */ INSERT INTO departments (name, code, description, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(code) DO UPDATE SET name = excluded.name, is_active = 1
                """,
                (name, code, f"Default {name} department", DEMO_NOW_ISO),
            )
        dep_ids = {
            str(row["code"]): int(row["id"])
            for row in conn.execute("SELECT id, code FROM departments").fetchall()
        }
        for full_name, email, password, role_id, department_code, position in AUTH_DEMO_ACCOUNTS:
            department_id = dep_ids[department_code]
            department_name = conn.execute("SELECT name FROM departments WHERE id = ?", (department_id,)).fetchone()["name"]
            existing = conn.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email.lower(),)).fetchone()
            role = role_id.lower() if role_id != "MEMBER" else "staff"
            if existing:
                conn.execute(
                    """
                    UPDATE users
                    SET full_name = ?, role = ?, role_id = ?, department = ?, department_id = ?,
                        position = ?, password_hash = COALESCE(password_hash, ?), is_active = 1, updated_at = ?
                    WHERE id = ?
                    """,
                    (full_name, role, role_id, department_name, department_id, position, hash_password(password), DEMO_NOW_ISO, existing["id"]),
                )
                continue
            conn.execute(
                """
                INSERT INTO users
                (full_name, email, aad_object_id, role, department, password_hash, role_id, department_id, position, avatar_url, is_active, created_at, updated_at)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, NULL, 1, ?, ?)
                """,
                (full_name, email.lower(), role, department_name, hash_password(password), role_id, department_id, position, DEMO_NOW_ISO, DEMO_NOW_ISO),
            )
