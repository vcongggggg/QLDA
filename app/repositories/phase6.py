import os
from pathlib import Path

from app.repositories.shared import *
from app.settings import settings


SAFE_CONFIG_KEYS = (
    "app_env",
    "app_base_url",
    "database_url",
    "auth_disable_jwt_validation",
    "auth_allow_header_fallback",
    "auth_allowed_email_domains",
    "security_hsts_enabled",
    "teams_proactive_mode",
    "rag_embedding_enabled",
    "rag_vector_backend",
    "rag_pdf_enabled",
)

SENSITIVE_CONFIG_MARKERS = ("secret", "token", "key", "password", "webhook", "authorization")


def _phase6_system_counts() -> dict[str, int]:
    with get_connection() as conn:
        return {
            "users": int(conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] or 0),
            "projects": int(conn.execute("SELECT COUNT(*) AS c FROM projects").fetchone()["c"] or 0),
            "tasks": int(conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"] or 0),
            "queued_notifications": int(
                conn.execute("SELECT COUNT(*) AS c FROM notification_queue WHERE status = 'queued'").fetchone()["c"] or 0
            ),
            "failed_notifications": int(
                conn.execute("SELECT COUNT(*) AS c FROM notification_queue WHERE status = 'failed'").fetchone()["c"] or 0
            ),
        }


def _safe_url(entity_type: str, entity_id: int | None) -> str | None:
    if entity_id is None:
        return None
    return {
        "user": f"/ui/#admin?user={entity_id}",
        "department": f"/ui/#admin?department={entity_id}",
        "project": f"/ui/#projects?project={entity_id}",
        "task": f"/ui/#kanban?task={entity_id}",
        "audit": f"/ui/#ops?audit={entity_id}",
        "report": "/ui/#reports",
    }.get(entity_type)


def _search_row(entity_type: str, row: dict[str, Any], title_field: str, subtitle: str | None = None) -> dict[str, Any]:
    entity_id = row.get("id")
    return {
        "type": entity_type,
        "id": int(entity_id) if entity_id is not None else None,
        "title": str(row.get(title_field) or ""),
        "subtitle": subtitle,
        "url": _safe_url(entity_type, int(entity_id)) if entity_id is not None else _safe_url(entity_type, None),
    }


def admin_global_search(query: str, limit: int = 25) -> dict[str, Any]:
    q = str(query or "").strip()
    term = f"%{q.lower()}%"
    per_group = max(1, min(limit, 25))
    results: list[dict[str, Any]] = []
    with get_connection() as conn:
        users = conn.execute(
            """
            SELECT id, full_name, email, role, department
            FROM users
            WHERE LOWER(full_name) LIKE ? OR LOWER(email) LIKE ? OR LOWER(COALESCE(role, '')) LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (term, term, term, per_group),
        ).fetchall()
        departments = conn.execute(
            """
            SELECT id, name, code
            FROM departments
            WHERE LOWER(name) LIKE ? OR LOWER(code) LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (term, term, per_group),
        ).fetchall()
        projects = conn.execute(
            """
            SELECT id, name, status
            FROM projects
            WHERE LOWER(name) LIKE ? OR LOWER(COALESCE(description, '')) LIKE ? OR LOWER(status) LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (term, term, term, per_group),
        ).fetchall()
        tasks = conn.execute(
            """
            SELECT id, title, status
            FROM tasks
            WHERE LOWER(title) LIKE ? OR LOWER(COALESCE(description, '')) LIKE ? OR LOWER(status) LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (term, term, term, per_group),
        ).fetchall()
        audit_logs = conn.execute(
            """
            SELECT id, action, entity, detail
            FROM audit_logs
            WHERE LOWER(action) LIKE ? OR LOWER(entity) LIKE ? OR LOWER(COALESCE(detail, '')) LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (term, term, term, per_group),
        ).fetchall()

    for row in users:
        item = dict(row)
        results.append(_search_row("user", item, "full_name", item.get("email")))
    for row in departments:
        item = dict(row)
        results.append(_search_row("department", item, "name", item.get("code")))
    for row in projects:
        item = dict(row)
        results.append(_search_row("project", item, "name", item.get("status")))
    for row in tasks:
        item = dict(row)
        results.append(_search_row("task", item, "title", item.get("status")))
    for row in audit_logs:
        item = dict(row)
        item["action"] = f"{item.get('action')}:{item.get('entity')}"
        results.append(_search_row("audit", item, "action", _redact_operational_text(item.get("detail"))))

    if q and "report" in q.lower():
        results.append(
            {
                "type": "report",
                "id": None,
                "title": "Reports workspace",
                "subtitle": "KPI, portfolio, project progress, sprint review, analytics",
                "url": _safe_url("report", None),
            }
        )
    return {"query": q, "results": results[:limit]}


def admin_config_flags() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for key in SAFE_CONFIG_KEYS:
        value = getattr(settings, key, None)
        if isinstance(value, (tuple, list, set)):
            value = ",".join(str(item) for item in value)
        if key == "database_url" and isinstance(value, str) and "@" in value:
            value = value.split("@", 1)[-1]
        output.append({"key": key.upper(), "value": value, "source": "settings", "sensitive": False})
    for key in sorted(os.environ):
        lowered = key.lower()
        if any(marker in lowered for marker in SENSITIVE_CONFIG_MARKERS):
            output.append({"key": key, "value": "[redacted]", "source": "environment", "sensitive": True})
    return output


def admin_system_config_overview() -> dict[str, Any]:
    flags = admin_config_flags()
    safe = [item for item in flags if not item["sensitive"]]
    sensitive_count = sum(1 for item in flags if item["sensitive"])
    auth_flags = {
        "app_env": getattr(settings, "app_env", "development"),
        "jwt_validation_disabled": bool(getattr(settings, "auth_disable_jwt_validation", False)),
        "header_fallback_allowed": bool(getattr(settings, "auth_allow_header_fallback", False)),
        "allowed_email_domains_configured": bool(getattr(settings, "auth_allowed_email_domains", ())),
    }
    teams_flags = {
        "proactive_mode": getattr(settings, "teams_proactive_mode", "disabled"),
        "graph_outbound_default": "disabled_unless_configured",
    }
    ai_flags = {
        "rag_embedding_enabled": bool(getattr(settings, "rag_embedding_enabled", False)),
        "rag_vector_backend": getattr(settings, "rag_vector_backend", "sqlite"),
        "external_provider_required": False,
    }
    return {
        "status": "ok",
        "safe_config_count": len(safe),
        "redacted_sensitive_count": sensitive_count,
        "auth": auth_flags,
        "teams": teams_flags,
        "ai": ai_flags,
        "change_policy": "configuration changes require privileged review; secrets are never returned",
        "flags": flags,
    }


def admin_license_status() -> dict[str, Any]:
    metrics = _phase6_system_counts()
    active_users = 0
    inactive_users = 0
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT COALESCE(is_active, 1) AS is_active, COUNT(*) AS c FROM users GROUP BY COALESCE(is_active, 1)"
        ).fetchall()
    for row in rows:
        if int(row["is_active"] or 0):
            active_users += int(row["c"] or 0)
        else:
            inactive_users += int(row["c"] or 0)
    return {
        "mode": "local_demo_unlicensed",
        "status": "ok",
        "active_users": active_users,
        "inactive_users": inactive_users,
        "project_count": metrics["projects"],
        "task_count": metrics["tasks"],
        "limits": {
            "users": None,
            "projects": None,
            "tasks": None,
        },
        "external_license_integration": "not_configured_for_local_demo",
        "renewal_required": False,
    }


def admin_department_ops_evidence() -> dict[str, Any]:
    departments = list_departments(include_inactive=True)
    with get_connection() as conn:
        user_rows = conn.execute(
            """
            SELECT d.id AS department_id, d.name AS department_name, COUNT(u.id) AS user_count
            FROM departments d
            LEFT JOIN users u ON u.department_id = d.id
            GROUP BY d.id, d.name
            ORDER BY d.name
            """
        ).fetchall()
    return {
        "total_departments": len(departments),
        "active_departments": sum(1 for item in departments if item.get("is_active")),
        "inactive_departments": sum(1 for item in departments if not item.get("is_active")),
        "manager_assigned_count": sum(1 for item in departments if item.get("manager_user_id")),
        "departments": departments,
        "user_distribution": [dict(row) for row in user_rows],
        "review_policy": "department changes are privileged and preserved through audit/admin workflow",
    }


def system_notification_evidence() -> dict[str, Any]:
    with get_connection() as conn:
        totals = conn.execute(
            """
            SELECT
              COUNT(*) AS total,
              SUM(CASE WHEN is_read THEN 1 ELSE 0 END) AS read_count,
              SUM(CASE WHEN NOT is_read THEN 1 ELSE 0 END) AS unread_count
            FROM app_notifications
            WHERE entity_type = 'system_notification'
            """
        ).fetchone()
        latest = conn.execute(
            """
            SELECT id, user_id, title, is_read, created_at
            FROM app_notifications
            WHERE entity_type = 'system_notification'
            ORDER BY id DESC
            LIMIT 10
            """
        ).fetchall()
    return {
        "total": int(totals["total"] or 0) if totals else 0,
        "read_count": int(totals["read_count"] or 0) if totals else 0,
        "unread_count": int(totals["unread_count"] or 0) if totals else 0,
        "latest": [dict(row) for row in latest],
        "audiences": ["all", "admin", "manager", "hr"],
    }


def list_users_for_system_notification(audience: str) -> list[dict[str, Any]]:
    role_filter = {
        "admin": {"admin", "ADMIN"},
        "manager": {"manager", "MANAGER", "leader", "LEADER"},
        "hr": {"hr", "HR", "auditor", "AUDITOR"},
    }.get(audience)
    users = list_users()
    if audience == "all":
        return [user for user in users if user.get("is_active", True)]
    return [
        user
        for user in users
        if user.get("is_active", True)
        and (str(user.get("role")) in role_filter or str(user.get("role_code")) in role_filter)
    ]


def create_system_notification_broadcast(title: str, message: str, audience: str, actor_user_id: int) -> dict[str, Any]:
    recipients = list_users_for_system_notification(audience)
    for user in recipients:
        create_app_notification(
            user_id=int(user["id"]),
            notification_type="task_status_changed",
            title=title,
            message=message,
            entity_type="system_notification",
            entity_id=0,
        )
    create_audit_log(actor_user_id, "broadcast", "system_notification", None, f"audience={audience};count={len(recipients)}")
    return {"created": len(recipients), "audience": audience}


def create_compliance_request(subject_user_id: int, request_type: str, reason: str, created_by: int) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO compliance_requests
            (subject_user_id, request_type, status, reason, resolution_note, created_by, created_at, updated_at)
            VALUES (?, ?, 'open', ?, NULL, ?, ?, ?)
            """,
            (subject_user_id, request_type, reason, created_by, now, now),
        )
        row = conn.execute("SELECT * FROM compliance_requests WHERE id = ?", (cursor.lastrowid,)).fetchone()
    create_audit_log(created_by, "create", "compliance_request", int(row["id"]), f"type={request_type};subject={subject_user_id}")
    return _compliance_request_payload(dict(row))


def _compliance_request_payload(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    with get_connection() as conn:
        user = conn.execute("SELECT email FROM users WHERE id = ?", (item["subject_user_id"],)).fetchone()
    item["subject_email"] = user["email"] if user else None
    return item


def list_compliance_requests(status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    query = "SELECT * FROM compliance_requests WHERE 1=1"
    params: list[Any] = []
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [_compliance_request_payload(dict(row)) for row in rows]


def update_compliance_request(request_id: int, status: str, resolution_note: str | None, actor_user_id: int) -> dict[str, Any] | None:
    now = _now_iso()
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM compliance_requests WHERE id = ?", (request_id,)).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE compliance_requests
            SET status = ?, resolution_note = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, resolution_note, now, request_id),
        )
        row = conn.execute("SELECT * FROM compliance_requests WHERE id = ?", (request_id,)).fetchone()
    create_audit_log(actor_user_id, "update", "compliance_request", request_id, f"status={status}")
    return _compliance_request_payload(dict(row))


def compliance_user_export(user_id: int) -> dict[str, Any] | None:
    user = get_user_by_id(user_id)
    if not user:
        return None
    with get_connection() as conn:
        tasks = conn.execute(
            "SELECT id, title, status, project_id, sprint_id, deadline FROM tasks WHERE assignee_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
        notifications = conn.execute(
            "SELECT id, type, title, entity_type, entity_id, is_read, created_at FROM app_notifications WHERE user_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
        audit_refs = conn.execute(
            "SELECT id, action, entity, entity_id, created_at FROM audit_logs WHERE actor_user_id = ? ORDER BY id DESC LIMIT 200",
            (user_id,),
        ).fetchall()
        kpi_adjustments = conn.execute(
            "SELECT id, month, points, reason, created_at FROM kpi_adjustments WHERE user_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
        project_memberships = conn.execute(
            """
            SELECT pm.id, pm.project_id, p.name AS project_name, pm.role, pm.joined_at
            FROM project_members pm
            LEFT JOIN projects p ON p.id = pm.project_id
            WHERE pm.user_id = ?
            ORDER BY pm.id
            """,
            (user_id,),
        ).fetchall()
    return {
        "user": user,
        "tasks": [dict(row) for row in tasks],
        "notifications": [dict(row) for row in notifications],
        "audit_references": [dict(row) for row in audit_refs],
        "kpi_references": [dict(row) for row in kpi_adjustments],
        "project_memberships": [dict(row) for row in project_memberships],
        "delete_policy": "request_export_manual_review_no_hard_delete",
    }


def data_lineage_notes() -> dict[str, Any]:
    return {
        "policy": "Request + export; delete requests require manual review and do not hard-delete product history automatically.",
        "domains": [
            {"domain": "users", "tables": ["users", "roles", "departments"], "retention": "active employment plus admin review"},
            {"domain": "tasks", "tables": ["tasks", "task_comments", "task_ai_details"], "retention": "project lifecycle evidence"},
            {"domain": "kpi", "tables": ["kpi_adjustments", "kpi_transactions", "kpi_targets"], "retention": "HR/reporting evidence"},
            {"domain": "notifications", "tables": ["app_notifications", "notification_queue"], "retention": "operational troubleshooting"},
            {"domain": "audit", "tables": ["audit_logs", "auth_login_attempts"], "retention": "security/compliance evidence"},
            {"domain": "rag_ai", "tables": ["rag_documents", "rag_chunks", "ai_task_drafts"], "retention": "AI preview and knowledge traceability"},
        ],
    }


def create_maintenance_window(title: str, message: str, starts_at: str, ends_at: str, status: str, created_by: int) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO maintenance_windows
            (title, message, starts_at, ends_at, status, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, message, starts_at, ends_at, status, created_by, now, now),
        )
        row = conn.execute("SELECT * FROM maintenance_windows WHERE id = ?", (cursor.lastrowid,)).fetchone()
    create_audit_log(created_by, "create", "maintenance_window", int(row["id"]), f"status={status}")
    return dict(row)


def list_maintenance_windows(status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    query = "SELECT * FROM maintenance_windows WHERE 1=1"
    params: list[Any] = []
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY starts_at DESC, id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def update_maintenance_window(window_id: int, fields: dict[str, Any], actor_user_id: int) -> dict[str, Any] | None:
    existing = get_maintenance_window(window_id)
    if not existing:
        return None
    updates: list[str] = []
    params: list[Any] = []
    for key in ("title", "message", "starts_at", "ends_at", "status"):
        if key in fields and fields[key] is not None:
            updates.append(f"{key} = ?")
            params.append(fields[key])
    if not updates:
        return existing
    updates.append("updated_at = ?")
    params.append(_now_iso())
    params.append(window_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE maintenance_windows SET {', '.join(updates)} WHERE id = ?", tuple(params))
        row = conn.execute("SELECT * FROM maintenance_windows WHERE id = ?", (window_id,)).fetchone()
    create_audit_log(actor_user_id, "update", "maintenance_window", window_id, f"fields={','.join(fields.keys())}")
    return dict(row)


def get_maintenance_window(window_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM maintenance_windows WHERE id = ?", (window_id,)).fetchone()
    return dict(row) if row else None


def active_maintenance_summary() -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        active = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM maintenance_windows
            WHERE status IN ('scheduled','active') AND ends_at >= ?
            """,
            (now,),
        ).fetchone()
    return {"active_or_upcoming_count": int(active["c"] if active else 0)}


def retention_metadata() -> dict[str, Any]:
    backup_script = Path("scripts/backup_postgres.ps1")
    return {
        "backup_script": str(backup_script),
        "backup_script_exists": backup_script.exists(),
        "retention_days": {
            "audit_logs": 365,
            "notification_queue": 90,
            "auth_login_attempts": 180,
        },
        "external_backup_integration": "documented_only",
    }


def log_cleanup_dry_run(retention_days: int = 90) -> dict[str, Any]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
    counts: dict[str, int] = {}
    with get_connection() as conn:
        for table in ("audit_logs", "notification_queue", "auth_login_attempts"):
            row = conn.execute(f"SELECT COUNT(*) AS c FROM {table} WHERE created_at < ?", (cutoff,)).fetchone()
            counts[table] = int(row["c"] if row else 0)
    return {"mode": "dry_run", "cutoff": cutoff, "retention_days": retention_days, "counts": counts}


def compliance_backlog_summary() -> dict[str, Any]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS c
            FROM compliance_requests
            GROUP BY status
            """
        ).fetchall()
    counts = {"open": 0, "in_review": 0, "approved": 0, "rejected": 0, "fulfilled": 0}
    counts.update({str(row["status"]): int(row["c"] or 0) for row in rows})
    return {"open_count": counts["open"], "in_review_count": counts["in_review"], "by_status": counts}


def compliance_release_evidence() -> dict[str, Any]:
    backlog = compliance_backlog_summary()
    lineage = data_lineage_notes()
    return {
        "backlog": backlog,
        "data_lineage_domains": len(lineage["domains"]),
        "delete_policy": "manual_review_no_hard_delete",
        "export_endpoint": "/compliance/users/{user_id}/export",
        "request_endpoint": "/compliance/requests",
        "lineage_endpoint": "/compliance/data-lineage",
    }


def qa_evidence_summary() -> dict[str, Any]:
    return {
        "focused_phase6_command": "pytest tests/test_phase6_admin_compliance_maintenance.py tests/test_ops_dashboard.py tests/test_maintenance_hardening.py -q",
        "security_command": "pytest tests/test_auth_security_hardening.py tests/test_maintenance_hardening.py -q",
        "performance_command": "python scripts/benchmark_smoke.py --json",
        "monitoring_command": "pytest tests/test_ops_dashboard.py -q",
        "test_data_command": "pytest tests/test_demo_seed.py tests/test_full_demo_seed.py -q",
        "compile_command": "python -m compileall app scripts",
        "full_suite_command": "pytest -q",
        "uat_template": "docs/PHASE6_UAT_EVIDENCE_TEMPLATE.md",
        "test_evidence_doc": "docs/TEST_EVIDENCE.md",
        "quality_gate_doc": "docs/QUALITY_GATE.md",
    }


def synthetic_journey_summary() -> dict[str, Any]:
    return {
        "mode": "documented_local_smoke",
        "script": "scripts/benchmark_smoke.py",
        "journeys": ["health", "readiness", "metrics", "release_gate"],
        "external_integrations": "disabled_by_default",
    }


def qa_release_evidence() -> dict[str, Any]:
    metrics = _phase6_system_counts()
    return {
        "status": "ready_for_local_release_review",
        "generated_at": _now_iso(),
        "qa": qa_evidence_summary(),
        "performance": {
            "script": "scripts/benchmark_smoke.py",
            "mode": "local_synthetic_smoke",
            "journeys": ["health", "readiness", "metrics", "release_gate"],
            "production_load_test": "deferred_external_infrastructure",
        },
        "security": {
            "checks": [
                "security headers",
                "failed-login lockout",
                "audit export",
                "release-gate redaction",
                "production auth safety validation",
            ],
            "secrets_policy": "redacted_from_api_responses",
        },
        "monitoring": {
            "health": "/health",
            "readiness": "/monitoring/readiness",
            "metrics": "/monitoring/metrics",
            "release_gate": "/monitoring/release-gate",
            "queued_notifications": metrics["queued_notifications"],
            "failed_notifications": metrics["failed_notifications"],
        },
        "test_data": test_data_inventory(),
        "uat": {
            "template": "docs/PHASE6_UAT_EVIDENCE_TEMPLATE.md",
            "status": "template_ready_pending_stakeholder_signoff",
        },
    }


def test_data_inventory() -> dict[str, Any]:
    with get_connection() as conn:
        counts = {
            "users": int(conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] or 0),
            "departments": int(conn.execute("SELECT COUNT(*) AS c FROM departments").fetchone()["c"] or 0),
            "projects": int(conn.execute("SELECT COUNT(*) AS c FROM projects").fetchone()["c"] or 0),
            "sprints": int(conn.execute("SELECT COUNT(*) AS c FROM sprints").fetchone()["c"] or 0),
            "tasks": int(conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"] or 0),
            "notifications": int(conn.execute("SELECT COUNT(*) AS c FROM app_notifications").fetchone()["c"] or 0),
        }
    return {
        "mode": "local_seeded_or_test_bootstrap",
        "counts": counts,
        "seed_command": "POST /seed/init",
        "demo_seed_command": "python scripts/seed_demo.py",
        "reset_policy": "tests call init_db and create isolated timestamped records",
        "accounts_doc": "docs/DEMO_SEED.md",
    }


def admin_release_panel_summary() -> dict[str, Any]:
    return {
        "admin_search": "/admin/search",
        "activity": "/admin/activity",
        "config": "/admin/system-config/overview",
        "license": "/admin/license/status",
        "departments": "/admin/departments/ops-evidence",
        "system_notifications": "/admin/system-notifications",
        "compliance": "/compliance/evidence",
        "maintenance": "/maintenance/windows",
        "qa": "/qa/release-evidence",
        "release_gate": "/monitoring/release-gate",
    }
