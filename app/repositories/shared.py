from datetime import datetime, timedelta, timezone

import json

import re

from typing import Any

from app.database import get_connection

from app.passwords import hash_password

ROLE_ALIASES = {
    "admin": "ADMIN",
    "manager": "MANAGER",
    "staff": "MEMBER",
    "member": "MEMBER",
    "hr": "HR",
    "leader": "LEADER",
    "auditor": "AUDITOR",
}

TASK_AI_DETAIL_LIST_FIELDS = (
    "subtasks",
    "acceptance_criteria",
    "data_requirements",
    "ui_components",
    "test_cases",
    "dependencies",
    "risks",
)

TASK_METADATA_LIST_FIELDS = (
    "labels",
    "checklist",
    "subtasks",
    "dependencies",
    "attachment_metadata",
)

_SECRET_PATTERNS = (
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"(client[_-]?secret|api[_-]?key|token|authorization)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"webhook[_-]?url\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\b\S*webhook[_-]?url\S*\b", re.IGNORECASE),
)

__all__ = [name for name in globals() if not name.startswith('__')]
