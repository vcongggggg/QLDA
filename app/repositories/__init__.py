from __future__ import annotations

from importlib import import_module

_MODULE_NAMES = (
    "users",
    "rbac",
    "tasks",
    "kanban",
    "task_templates",
    "notifications",
    "audit",
    "ai_drafts",
    "rag",
    "kpi",
    "org",
    "projects",
    "sprints",
    "teams",
    "monitoring",
    "reports",
    "phase6",
)

_modules = [import_module(f"{__name__}.{name}") for name in _MODULE_NAMES]
_public = {}
for _module in _modules:
    for _name, _value in vars(_module).items():
        if _name.startswith("__") or _name in {"Any", "datetime", "timedelta", "timezone", "json", "re"}:
            continue
        _public[_name] = _value

# Repository functions historically lived in one module and call helpers across domains.
# Populate each split module with the combined namespace so those call sites remain stable.
for _module in _modules:
    vars(_module).update(_public)

globals().update(_public)
__all__ = sorted(_public)
