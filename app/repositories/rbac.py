from app.repositories.shared import *

def list_roles() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM roles ORDER BY slug").fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["code"] = item.get("code") or item.get("slug")
        item["is_system_role"] = item.get("is_system_role", item.get("is_system", True))
        out.append(item)
    return out


def list_permissions() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM permissions ORDER BY category, key").fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["code"] = item.get("code") or item.get("key")
        item["module"] = item.get("module") or item.get("category")
        out.append(item)
    return out


def role_exists(role_slug: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT slug FROM roles WHERE slug = ?", (role_slug,)).fetchone()
    return row is not None


def create_role(
    role_slug: str,
    name: str,
    description: str | None = None,
    permission_keys: list[str] | None = None,
) -> dict[str, Any]:
    slug = canonical_role_code(role_slug)
    if role_exists(slug):
        raise ValueError("role already exists")
    keys = sorted(set(permission_keys or []))
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO roles (slug, name, description, is_system, code, is_system_role)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (slug, name, description, False, slug, False),
        )
        for permission_key in keys:
            conn.execute(
                "/* no-returning-id */ INSERT INTO role_permissions (role_slug, permission_key) VALUES (?, ?)",
                (slug, permission_key),
            )
    role = get_role(slug)
    if not role:
        raise RuntimeError("created role not found")
    return role


def get_role(role_slug: str) -> dict[str, Any] | None:
    candidates = sorted({role_slug, canonical_role_code(role_slug), legacy_role_slug(role_slug)})
    placeholders = ",".join(["?"] * len(candidates))
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT * FROM roles WHERE slug IN ({placeholders}) ORDER BY slug LIMIT 1",
            tuple(candidates),
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["code"] = item.get("code") or item.get("slug")
    item["is_system_role"] = item.get("is_system_role", item.get("is_system", True))
    return item


def update_role(
    role_slug: str,
    *,
    name: str | None = None,
    description: str | None = None,
) -> dict[str, Any] | None:
    existing = get_role(role_slug)
    if not existing:
        return None
    fields: list[str] = []
    params: list[Any] = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if description is not None:
        fields.append("description = ?")
        params.append(description)
    if fields:
        params.append(existing["slug"])
        with get_connection() as conn:
            conn.execute(f"UPDATE roles SET {', '.join(fields)} WHERE slug = ?", tuple(params))
    return get_role(str(existing["slug"]))


def permission_keys_exist(permission_keys: list[str]) -> bool:
    if not permission_keys:
        return True
    placeholders = ",".join(["?"] * len(permission_keys))
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT key FROM permissions WHERE key IN ({placeholders})",
            tuple(permission_keys),
        ).fetchall()
    return {str(row["key"]) for row in rows} == set(permission_keys)


def list_permissions_for_role(role_slug: str) -> list[dict[str, Any]]:
    role_candidates = sorted({role_slug, canonical_role_code(role_slug), legacy_role_slug(role_slug)})
    placeholders = ",".join(["?"] * len(role_candidates))
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT p.*
            FROM permissions p
            JOIN role_permissions rp ON rp.permission_key = p.key
            WHERE rp.role_slug IN ({placeholders})
            ORDER BY p.category, p.key
            """,
            tuple(role_candidates),
        ).fetchall()
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        key = str(item["key"])
        if key in seen:
            continue
        seen.add(key)
        item["code"] = item.get("code") or item.get("key")
        item["module"] = item.get("module") or item.get("category")
        out.append(item)
    return out


def list_permission_keys_for_role(role_slug: str) -> list[str]:
    return [str(item["key"]) for item in list_permissions_for_role(role_slug)]


def role_permission_matrix() -> dict[str, Any]:
    roles = list_roles()
    permissions = list_permissions()
    matrix = {str(role["slug"]): list_permission_keys_for_role(str(role["slug"])) for role in roles}
    return {"roles": roles, "permissions": permissions, "matrix": matrix}


def replace_role_permissions(role_slug: str, permission_keys: list[str]) -> list[dict[str, Any]]:
    unique_keys = sorted(set(permission_keys))
    role_targets = sorted({role_slug, canonical_role_code(role_slug)})
    with get_connection() as conn:
        for target in role_targets:
            conn.execute("DELETE FROM role_permissions WHERE role_slug = ?", (target,))
            for permission_key in unique_keys:
                conn.execute(
                    "/* no-returning-id */ INSERT INTO role_permissions (role_slug, permission_key) VALUES (?, ?)",
                    (target, permission_key),
                )
    return list_permissions_for_role(role_slug)


def role_has_permission(role_slug: str, permission_key: str) -> bool:
    role_candidates = sorted({role_slug, canonical_role_code(role_slug), legacy_role_slug(role_slug)})
    permission_candidates = sorted({permission_key})
    placeholders_roles = ",".join(["?"] * len(role_candidates))
    placeholders_perms = ",".join(["?"] * len(permission_candidates))
    with get_connection() as conn:
        row = conn.execute(
            f"""
            SELECT 1
            FROM role_permissions
            WHERE role_slug IN ({placeholders_roles}) AND permission_key IN ({placeholders_perms})
            LIMIT 1
            """,
            tuple(role_candidates + permission_candidates),
        ).fetchone()
    return row is not None
