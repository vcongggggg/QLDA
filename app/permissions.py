from __future__ import annotations


DEFAULT_ROLES: tuple[dict[str, str], ...] = (
    {"slug": "admin", "name": "Admin", "description": "Full system administration"},
    {"slug": "manager", "name": "Manager", "description": "Manage projects, tasks, reports, and AI workflow"},
    {"slug": "hr", "name": "HR", "description": "View people, KPI, reports, and operational status"},
    {"slug": "staff", "name": "Staff", "description": "Work on assigned tasks and accessible projects"},
)


DEFAULT_PERMISSIONS: tuple[dict[str, str], ...] = (
    {"key": "users.create", "name": "Create users", "category": "users"},
    {"key": "users.view", "name": "View users", "category": "users"},
    {"key": "roles.view", "name": "View roles and permissions", "category": "rbac"},
    {"key": "roles.manage", "name": "Manage role permissions", "category": "rbac"},
    {"key": "tasks.create", "name": "Create tasks", "category": "tasks"},
    {"key": "tasks.update_any", "name": "Update any task", "category": "tasks"},
    {"key": "tasks.update_own", "name": "Update own task", "category": "tasks"},
    {"key": "projects.manage", "name": "Manage projects", "category": "projects"},
    {"key": "projects.view", "name": "View accessible projects", "category": "projects"},
    {"key": "sprints.manage", "name": "Manage sprints", "category": "sprints"},
    {"key": "sprints.view", "name": "View sprints", "category": "sprints"},
    {"key": "kpi.view", "name": "View KPI", "category": "kpi"},
    {"key": "kpi.adjust", "name": "Adjust KPI", "category": "kpi"},
    {"key": "reports.export", "name": "Export reports", "category": "reports"},
    {"key": "ai.preview", "name": "Preview AI task breakdown", "category": "ai"},
    {"key": "ai.import", "name": "Import AI tasks", "category": "ai"},
    {"key": "rag.manage", "name": "Manage RAG documents", "category": "rag"},
    {"key": "rag.query", "name": "Query RAG context", "category": "rag"},
    {"key": "teams.view", "name": "View Teams integration", "category": "teams"},
    {"key": "teams.manage", "name": "Manage Teams queue and reminders", "category": "teams"},
    {"key": "monitoring.view", "name": "View monitoring", "category": "monitoring"},
    {"key": "monitoring.admin", "name": "Admin monitoring actions", "category": "monitoring"},
)


ADMIN_PERMISSIONS = tuple(item["key"] for item in DEFAULT_PERMISSIONS)

DEFAULT_ROLE_PERMISSION_KEYS: dict[str, tuple[str, ...]] = {
    "admin": ADMIN_PERMISSIONS,
    "manager": (
        "users.view",
        "projects.manage",
        "projects.view",
        "tasks.create",
        "tasks.update_any",
        "tasks.update_own",
        "sprints.manage",
        "sprints.view",
        "kpi.view",
        "reports.export",
        "ai.preview",
        "ai.import",
        "rag.manage",
        "rag.query",
        "teams.view",
        "teams.manage",
        "monitoring.view",
    ),
    "hr": (
        "users.view",
        "projects.view",
        "sprints.view",
        "kpi.view",
        "kpi.adjust",
        "reports.export",
        "teams.view",
        "teams.manage",
        "monitoring.view",
    ),
    "staff": (
        "projects.view",
        "tasks.update_own",
        "sprints.view",
        "kpi.view",
        "teams.view",
    ),
}
