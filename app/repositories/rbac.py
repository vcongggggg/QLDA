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
