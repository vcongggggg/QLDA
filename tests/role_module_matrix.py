ROLE_ACCOUNTS = {
    "ADMIN": ("admin@teamswork.local", "Admin@123"),
    "MANAGER": ("manager@teamswork.local", "Manager@123"),
    "LEADER": ("leader@teamswork.local", "Leader@123"),
    "MEMBER": ("member@teamswork.local", "Member@123"),
    "HR": ("hr@teamswork.local", "Hr@123"),
    "AUDITOR": ("auditor@teamswork.local", "Auditor@123"),
}


EXPECTED_ROLE_MODULES = {
    "ADMIN": ("dashboard", "projects", "kanban", "teams", "kpi", "reports", "ai", "ops", "admin"),
    "MANAGER": ("dashboard", "projects", "kanban", "teams", "kpi", "reports", "ai"),
    "LEADER": ("dashboard", "projects", "kanban", "teams", "kpi", "reports", "ai"),
    "MEMBER": ("dashboard", "kanban", "kpi"),
    "HR": ("dashboard", "admin", "kpi", "reports", "teams"),
    "AUDITOR": ("dashboard", "reports", "ops"),
}


MODULE_PRIMARY_ENDPOINTS = {
    "dashboard": (("GET", "/dashboard/summary?month=2026-08&as_of=2026-08-10T09:00:00%2B00:00"),),
    "projects": (("GET", "/projects"),),
    "kanban": (("GET", "/tasks"),),
    "teams": (("GET", "/integrations/teams/summary?month=2026-08"),),
    "kpi": (("GET", "/kpi/monthly?month=2026-08"),),
    "reports": (("GET", "/reports/kpi.csv?month=2026-08"),),
    "ai": (("GET", "/ai/task-breakdown/drafts"),),
    "ops": (("GET", "/monitoring/ops"),),
    "admin": (("GET", "/plan/completion"),),
}


ROLE_ADMIN_ENDPOINTS = {
    "ADMIN": (("GET", "/users"), ("GET", "/departments"), ("GET", "/rbac/roles")),
    "HR": (("GET", "/users"), ("GET", "/departments")),
}
