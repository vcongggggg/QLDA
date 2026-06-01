# TeamsWork Demo Report Guide

Last updated: 2026-06-01.
Audience: project reviewer, technical reviewer, and product stakeholder.
Recommended demo duration: 7-10 minutes.

## Executive Summary

TeamsWork is an internal project operations system for controlled delivery work. The demo should show that the product supports projects, sprints, Kanban tasks, KPI, reports, RBAC, AI task drafts, RAG context search, Microsoft Teams simulation, audit/ops monitoring, and release evidence.

The strongest message is control: AI suggests work but does not silently create tasks or change KPI; users only see role-appropriate modules; reports and release gates are backed by repeatable tests.

## Report Narrative

1. Product opening
   - Present TeamsWork as a management workspace for projects, sprints, tasks, KPI, reports, Microsoft Teams workflows, and AI-assisted task breakdown.
   - Show `/health`, `/docs`, and the UI at `http://127.0.0.1:8000/ui/`.

2. Architecture
   - Browser or Teams tab connects to FastAPI.
   - Static UI is served at `/ui/`.
   - SQLite is used for local/demo; PostgreSQL and pgvector are optional for production-like RAG.

3. RBAC and authentication
   - Roles: admin, manager, leader, member, hr, auditor.
   - Production auth uses JWT bearer tokens.
   - Header fallback is only for local/dev/demo settings.
   - Mention test evidence from `tests/role_module_matrix.py`, `tests/test_role_module_rbac_matrix.py`, and `tests/test_ui_role_navigation_playwright.py`.

4. Delivery workflow
   - Demonstrate Projects, Sprints, Kanban, task filters, task detail, comments, deadlines, story points, difficulty, and assignee data.
   - Explain that demo seed links departments, users, projects, sprints, tasks, workload plans, risks, weekly updates, comments, notifications, AI drafts, and RAG documents.

5. KPI and reports
   - KPI formula is deterministic and lives in `app/kpi.py`.
   - On-time done: `+10 * difficulty_multiplier`.
   - Late done: `+5 * difficulty_multiplier`.
   - Unfinished task with a deadline in the KPI month: `-5 * difficulty_multiplier`.
   - Multipliers: easy `1.0`, medium `1.5`, hard `2.0`.
   - Manual adjustment is added to final score and requires a reason plus audit evidence.
   - Show KPI CSV/XLSX/PDF, portfolio reports, project progress reports, and sprint review reports.

6. AI and RAG
   - AI task breakdown creates an AI draft only.
   - Manager/admin review is required before import creates real Kanban tasks.
   - Local demo can use heuristic fallback when no external AI key is configured.
   - Local RAG supports lexical search; PostgreSQL pgvector embeddings are optional.

7. Teams simulation
   - Use `/admin/integrations/teams-simulator`.
   - Show `/task-list`, `/kpi-me`, `/help`, Adaptive Card JSON, queue status, process queue, and retry failed flow.
   - State clearly that local demo does not call Microsoft Graph or send real Teams messages.

8. Ops and evidence
   - Show audit log, failed queue panel, overdue spike panel, readiness/metrics endpoints, `/monitoring/release-gate`, and `/monitoring/release-acceptance`.
   - Close with `docs/TEST_EVIDENCE.md` and `docs/TRACEABILITY_MATRIX.md`.

## Commands To Run

Run from `d:\QLDA`.

```powershell
pip install -r requirements.txt
python -m playwright install chromium
python scripts/seed_full_demo.py --reset-demo
uvicorn app.main:app --reload
python scripts/smoke_check.py --base-url http://127.0.0.1:8000 --user-id 1 --expect-production-auth
python scripts/capture_demo_evidence.py --base-url http://127.0.0.1:8000
python scripts/benchmark_smoke.py --json
pytest -q
python -m compileall app scripts
git diff --check
```

Use `--reset-demo` only in local/dev/demo/test environments. To avoid changing the tracked `teamswork.db`, run demo commands against a temporary SQLite database:

```powershell
$env:DATABASE_URL = "sqlite:///D:/QLDA/.tmp/demo-report.db"
python scripts/seed_full_demo.py --reset-demo
```

## Current Evidence

Evidence from the 2026-06-01 local Windows workspace:

| Check | Command | Result |
| --- | --- | --- |
| Test collection | `pytest --collect-only -q` | PASS, 170 tests collected |
| Critical API/AI/KPI tests | `pytest tests/test_api_flow.py tests/test_ai_task_breakdown.py tests/test_kpi.py` | PASS, 18 passed |
| Demo/UI tests | `pytest tests/test_full_demo_seed.py tests/test_ui_role_navigation_playwright.py` | PASS, 8 passed |
| Phase 6 ops/API gate | `pytest tests/test_phase6_admin_compliance_maintenance.py tests/test_ops_dashboard.py tests/test_maintenance_hardening.py tests/test_auth_security_hardening.py tests/test_notifications.py -q` | PASS, 42 passed |
| Full test suite | `pytest -q` | PASS, 170 passed |
| Compile check | `python -m compileall app scripts` | PASS |
| Diff whitespace check | `git diff --check` | PASS, LF/CRLF warnings only |
| Benchmark smoke | `python scripts/benchmark_smoke.py --json` with temp DB | PASS, all checks HTTP 200 |
| Full demo seed | `python scripts/seed_full_demo.py --reset-demo` with temp DB | PASS, 26 users, 3 projects, 21 sprints, 100 tasks, 12 RAG docs |
| Deployment smoke | `python scripts/smoke_check.py --base-url http://127.0.0.1:8000 --user-id 1 --expect-production-auth` with temp DB/server | PASS, health/readiness/Teams tab/KPI CSV/metrics/auth check |
| Evidence capture | `python scripts/capture_demo_evidence.py --start-server --base-url http://127.0.0.1:8000` with temp DB | PARTIAL PASS, admin screenshots/videos captured; restricted member/auditor screenshots hit `window.navigate` timing errors |

Benchmark smoke covered:

- `/health`
- `/monitoring/readiness`
- `/monitoring/metrics`
- `/monitoring/release-gate`
- `/monitoring/release-acceptance`

Latest temp demo seed summary:

```json
{
  "message": "Full demo data seeded",
  "mode": "reset",
  "demo_namespace": "teamswork_full_demo",
  "demo_now": "2026-08-10T09:00:00+00:00",
  "warnings": [],
  "counts": {
    "users": 26,
    "departments": 11,
    "projects": 3,
    "sprints": 21,
    "project_members": 24,
    "tasks": 100,
    "sprint_capacity_plans": 168,
    "project_risks": 8,
    "weekly_status_updates": 21,
    "kpi_adjustments": 5,
    "task_comments": 250,
    "app_notifications": 12,
    "notification_queue": 5,
    "audit_logs": 4,
    "ai_task_drafts": 6,
    "rag_documents": 12,
    "rag_chunks": 72
  }
}
```

Latest screenshot/video artifact directory:

```text
.tmp/demo-evidence/20260601T003805Z
```

Captured admin artifacts:

- `admin-dashboard.png`
- `admin-projects.png`
- `admin-kanban.png`
- `admin-kpi.png`
- `admin-reports.png`
- `admin-ai.png`
- `admin-teams.png`
- `admin-ops.png`
- `admin-admin.png`
- `admin-ai-generated-draft.png`
- 3 `.webm` videos

Capture caveat:

- Member restricted-project and auditor restricted-AI screenshots were not captured in the latest run because `window.navigate` was not ready in those browser contexts.
- Use the admin screenshots/videos for the current report, or rerun capture after hardening the script's restricted-role navigation wait.

## Demo Accounts

| Role | Email | Password | Demo focus |
| --- | --- | --- | --- |
| ADMIN | `admin@teamswork.local` | `Admin@123` | Full system, RBAC, ops, reports |
| MANAGER | `manager@teamswork.local` | `Manager@123` | Delivery, KPI, AI import, reports |
| LEADER | `leader@teamswork.local` | `Leader@123` | Team delivery and AI workflow |
| MEMBER | `member@teamswork.local` | `Member@123` | Own work and own KPI |
| HR | `hr@teamswork.local` | `Hr@123` | Users, KPI, reports, Teams summary |
| AUDITOR | `auditor@teamswork.local` | `Auditor@123` | Reports, audit, ops review |

## Reporting Notes

- Do not claim real Azure AD, Microsoft Graph posting, or tenant deployment from the local demo.
- Do not claim pgvector semantic ranking unless PostgreSQL pgvector and embeddings are enabled.
- Do not claim external AI model quality when only local heuristic fallback is used.
- Screenshots and videos are runtime artifacts under `.tmp/demo-evidence/<timestamp>/` and are not tracked by git.
- `teamswork.db` in this workspace may not match the newest migration shape; use a fresh temp DB for reproducible demo evidence.
