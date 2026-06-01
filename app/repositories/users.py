from app.repositories.shared import *

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_role_code(role: str | None) -> str:
    value = str(role or "MEMBER").strip()
    return ROLE_ALIASES.get(value.lower(), value.upper())


def legacy_role_slug(role: str | None) -> str:
    code = canonical_role_code(role)
    return {
        "ADMIN": "admin",
        "MANAGER": "manager",
        "MEMBER": "staff",
        "LEADER": "manager",
        "HR": "hr",
        "AUDITOR": "hr",
    }.get(code, str(role or "staff").lower())


def _sanitize_user(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item.pop("password_hash", None)
    return item


def _role_payload(role_slug: str | None, role_name: str | None = None) -> dict[str, Any]:
    code = canonical_role_code(role_slug)
    return {
        "code": code,
        "name": role_name or code.title(),
        "slug": role_slug or code,
    }


def _department_payload(row: dict[str, Any]) -> dict[str, Any] | None:
    dep_id = row.get("department_id")
    dep_name = row.get("department_name") or row.get("department")
    if dep_id is None and not dep_name:
        return None
    return {
        "id": dep_id,
        "code": row.get("department_code"),
        "name": dep_name,
    }


def _user_profile_from_row(row: dict[str, Any], *, include_permissions: bool = False) -> dict[str, Any]:
    item = _sanitize_user(row)
    role_slug = str(item.get("role_id") or item.get("role") or "")
    item["role_code"] = canonical_role_code(role_slug)
    item["role"] = item.get("role") or legacy_role_slug(role_slug)
    item["role_detail"] = _role_payload(role_slug or item["role"], item.get("role_name"))
    item["department_detail"] = _department_payload(item)
    item["is_active"] = bool(item.get("is_active", True))
    if include_permissions:
        item["permissions"] = list_permission_keys_for_role(role_slug or item["role"])
    return item


def create_user(
    full_name: str,
    email: str,
    role: str,
    department: str | None,
    aad_object_id: str | None = None,
    password: str | None = None,
    department_id: int | None = None,
    position: str | None = None,
    avatar_url: str | None = None,
    is_active: bool = True,
    onboarding_status: str = "active",
    onboarding_note: str | None = None,
) -> dict[str, Any]:
    now = _now_iso()
    role_id = canonical_role_code(role)
    stored_role = legacy_role_slug(role)
    password_hash = hash_password(password) if password else None
    with get_connection() as conn:
        if department_id is None and department:
            dep_row = conn.execute(
                "SELECT id, name FROM departments WHERE name = ? OR code = ? LIMIT 1",
                (department, department),
            ).fetchone()
            if dep_row:
                department_id = int(dep_row["id"])
                department = str(dep_row["name"])
        cursor = conn.execute(
            """
            INSERT INTO users
            (full_name, email, aad_object_id, role, department, password_hash, role_id, department_id, position, avatar_url, is_active, created_at, updated_at, onboarding_status, onboarding_note, activated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                full_name,
                email.lower(),
                aad_object_id,
                stored_role,
                department,
                password_hash,
                role_id,
                department_id,
                position,
                avatar_url,
                bool(is_active),
                now,
                now,
                onboarding_status,
                onboarding_note,
                now if onboarding_status == "active" else None,
            ),
        )
        user_id = cursor.lastrowid
    user = get_user_by_id(int(user_id))
    if not user:
        raise RuntimeError("created user not found")
    return user


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT u.*, r.name AS role_name, d.name AS department_name, d.code AS department_code
            FROM users u
            LEFT JOIN roles r ON r.slug = COALESCE(u.role_id, u.role)
            LEFT JOIN departments d ON d.id = u.department_id
            WHERE u.id = ?
            """,
            (user_id,),
        ).fetchone()
    return _user_profile_from_row(dict(row), include_permissions=True) if row else None


def get_user_by_username_or_email(username_or_email: str, *, include_password: bool = False) -> dict[str, Any] | None:
    value = username_or_email.strip().lower()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT u.*, r.name AS role_name, d.name AS department_name, d.code AS department_code
            FROM users u
            LEFT JOIN roles r ON r.slug = COALESCE(u.role_id, u.role)
            LEFT JOIN departments d ON d.id = u.department_id
            WHERE LOWER(u.email) = ?
            LIMIT 1
            """,
            (value,),
        ).fetchone()
    if not row:
        return None
    item = _user_profile_from_row(dict(row), include_permissions=True)
    if include_password:
        item["password_hash"] = dict(row).get("password_hash")
    return item


def get_user_by_aad_object_id(aad_object_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE aad_object_id = ?", (aad_object_id,)).fetchone()
    return _user_profile_from_row(dict(row), include_permissions=True) if row else None


def upsert_user_from_aad(aad_object_id: str, display_name: str | None, email: str | None) -> dict[str, Any]:
    existing = get_user_by_aad_object_id(aad_object_id)
    if existing:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE users
                SET full_name = COALESCE(?, full_name),
                    email = COALESCE(?, email),
                    onboarding_status = CASE WHEN onboarding_status IN ('invited','pending') THEN 'active' ELSE onboarding_status END,
                    activated_at = COALESCE(activated_at, ?),
                    last_login_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (display_name, email, _now_iso(), _now_iso(), _now_iso(), existing["id"]),
            )
        updated = get_user_by_id(int(existing["id"]))
        if not updated:
            raise RuntimeError("updated aad user not found")
        return updated

    safe_email = email or f"{aad_object_id}@aad.example.com"
    safe_name = display_name or "Teams User"
    return create_user(
        full_name=safe_name,
        email=safe_email,
        aad_object_id=aad_object_id,
        role="MEMBER",
        department="Unassigned",
        onboarding_status="active",
    )


def list_users() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT u.*, r.name AS role_name, d.name AS department_name, d.code AS department_code
            FROM users u
            LEFT JOIN roles r ON r.slug = COALESCE(u.role_id, u.role)
            LEFT JOIN departments d ON d.id = u.department_id
            ORDER BY u.id
            """
        ).fetchall()
    return [_user_profile_from_row(dict(r), include_permissions=False) for r in rows]


def update_user(
    user_id: int,
    *,
    full_name: str | None = None,
    email: str | None = None,
    role: str | None = None,
    department_id: int | None = None,
    position: str | None = None,
    avatar_url: str | None = None,
    is_active: bool | None = None,
) -> dict[str, Any] | None:
    existing = get_user_by_id(user_id)
    if not existing:
        return None
    fields: list[str] = []
    params: list[Any] = []
    if full_name is not None:
        fields.append("full_name = ?")
        params.append(full_name)
    if email is not None:
        fields.append("email = ?")
        params.append(email.lower())
    if role is not None:
        fields.extend(["role = ?", "role_id = ?"])
        params.extend([legacy_role_slug(role), canonical_role_code(role)])
    if department_id is not None:
        fields.append("department_id = ?")
        params.append(department_id)
        with get_connection() as conn:
            dep = conn.execute("SELECT name FROM departments WHERE id = ?", (department_id,)).fetchone()
        fields.append("department = ?")
        params.append(str(dep["name"]) if dep else None)
    if position is not None:
        fields.append("position = ?")
        params.append(position)
    if avatar_url is not None:
        fields.append("avatar_url = ?")
        params.append(avatar_url)
    if is_active is not None:
        fields.append("is_active = ?")
        params.append(bool(is_active))
    if not fields:
        return existing
    fields.append("updated_at = ?")
    params.append(_now_iso())
    params.append(user_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", tuple(params))
    return get_user_by_id(user_id)


def update_user_active(user_id: int, is_active: bool) -> dict[str, Any] | None:
    return update_user(user_id, is_active=is_active)


def update_user_last_login(user_id: int) -> dict[str, Any] | None:
    now = _now_iso()
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE users
            SET last_login_at = ?,
                onboarding_status = CASE WHEN onboarding_status IN ('invited','pending') THEN 'active' ELSE onboarding_status END,
                activated_at = COALESCE(activated_at, ?),
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, now, user_id),
        )
    return get_user_by_id(user_id)


def invite_user(user_id: int) -> dict[str, Any] | None:
    now = _now_iso()
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE users
            SET onboarding_status = 'invited',
                invited_at = COALESCE(invited_at, ?),
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, user_id),
        )
    return get_user_by_id(user_id)


def update_user_onboarding(
    user_id: int,
    onboarding_status: str,
    onboarding_note: str | None = None,
) -> dict[str, Any] | None:
    now = _now_iso()
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE users
            SET onboarding_status = ?,
                onboarding_note = ?,
                invited_at = CASE WHEN ? = 'invited' THEN COALESCE(invited_at, ?) ELSE invited_at END,
                activated_at = CASE WHEN ? = 'active' THEN COALESCE(activated_at, ?) ELSE activated_at END,
                updated_at = ?
            WHERE id = ?
            """,
            (onboarding_status, onboarding_note, onboarding_status, now, onboarding_status, now, now, user_id),
        )
    return get_user_by_id(user_id)


def get_user_notification_preferences(user_id: int) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_notification_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            conn.execute(
                """
                INSERT INTO user_notification_preferences
                (user_id, app_enabled, email_enabled, teams_enabled, digest_enabled, quiet_hours_start, quiet_hours_end, updated_at)
                VALUES (?, TRUE, FALSE, TRUE, FALSE, NULL, NULL, ?)
                """,
                (user_id, now),
            )
            row = conn.execute(
                "SELECT * FROM user_notification_preferences WHERE user_id = ?",
                (user_id,),
            ).fetchone()
    return dict(row)


def update_user_notification_preferences(
    user_id: int,
    **updates: Any,
) -> dict[str, Any]:
    current = get_user_notification_preferences(user_id)
    allowed = {
        "app_enabled",
        "email_enabled",
        "teams_enabled",
        "digest_enabled",
        "quiet_hours_start",
        "quiet_hours_end",
    }
    fields: list[str] = []
    params: list[Any] = []
    for key, value in updates.items():
        if key not in allowed or value is None:
            continue
        fields.append(f"{key} = ?")
        params.append(bool(value) if key.endswith("_enabled") else value)
    if not fields:
        return current
    fields.append("updated_at = ?")
    params.append(_now_iso())
    params.append(user_id)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE user_notification_preferences SET {', '.join(fields)} WHERE user_id = ?",
            tuple(params),
        )
    return get_user_notification_preferences(user_id)


def effective_user_notification_settings(user_id: int, *, at_time: str | None = None) -> dict[str, Any]:
    prefs = get_user_notification_preferences(user_id)
    enabled_channels = [
        channel
        for channel, enabled in (
            ("app", prefs.get("app_enabled")),
            ("email", prefs.get("email_enabled")),
            ("teams", prefs.get("teams_enabled")),
            ("digest", prefs.get("digest_enabled")),
        )
        if bool(enabled)
    ]
    start = prefs.get("quiet_hours_start")
    end = prefs.get("quiet_hours_end")
    quiet_configured = bool(start and end)
    current_time = at_time or datetime.now(timezone.utc).strftime("%H:%M")
    quiet_active = False
    if quiet_configured:
        if str(start) <= str(end):
            quiet_active = str(start) <= current_time < str(end)
        else:
            quiet_active = current_time >= str(start) or current_time < str(end)
    summary = "muted during quiet hours" if quiet_active else f"{len(enabled_channels)} active channel(s)"
    return {
        **prefs,
        "enabled_channels": enabled_channels,
        "quiet_hours_configured": quiet_configured,
        "quiet_hours_active": quiet_active,
        "delivery_summary": summary,
    }


def reset_user_password(user_id: int, password: str) -> bool:
    existing = get_user_by_id(user_id)
    if not existing:
        return False
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (hash_password(password), _now_iso(), user_id),
        )
    return True


def count_users() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    return int(row[0] if row else 0)


def user_exists(user_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    return row is not None
