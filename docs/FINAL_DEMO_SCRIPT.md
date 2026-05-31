# TeamsWork Final Demo Script

Audience: project reviewer, technical reviewer, and product stakeholder.
Target duration: 7-10 minutes.
Local URL: `http://127.0.0.1:8000/ui/`.
API docs: `http://127.0.0.1:8000/docs`.

## Pre-Demo Checklist

Run these commands from the repository root:

```powershell
pip install -r requirements.txt
python -m playwright install chromium
python scripts/seed_full_demo.py --reset-demo
uvicorn app.main:app --reload
python scripts/smoke_check.py --base-url http://127.0.0.1:8000 --user-id 1 --expect-production-auth
python scripts/benchmark_smoke.py --json
```

Use demo mode only for local/dev. Do not run `--reset-demo` against production data.

## Demo Accounts

| Role | Email | Password | What to show |
| --- | --- | --- | --- |
| ADMIN | `admin@teamswork.local` | `Admin@123` | Full system, RBAC, ops, reports |
| MANAGER | `manager@teamswork.local` | `Manager@123` | Delivery, KPI, AI import, reports |
| LEADER | `leader@teamswork.local` | `Leader@123` | Team delivery and AI workflow |
| MEMBER | `member@teamswork.local` | `Member@123` | Own work and own KPI only |
| HR | `hr@teamswork.local` | `Hr@123` | Users, KPI, reports, Teams summary |
| AUDITOR | `auditor@teamswork.local` | `Auditor@123` | Reports and audit/ops review |

## 7-10 Minute Talk Track

### 0:00-0:45 - Opening

TeamsWork is an internal work management system for projects, sprints, tasks, KPI, reports, Microsoft Teams integration, and AI-assisted task breakdown. The key point is controlled operations: AI suggests tasks, managers review them, and RBAC limits what each role can see or change.

Show:

- `README.md` or `/docs` briefly if needed.
- `http://127.0.0.1:8000/health` returns healthy.
- UI at `/ui/`.

### 0:45-2:00 - RBAC And Navigation

Log in as `admin@teamswork.local`. Show the full sidebar: Dashboard, Projects, Kanban, Teams, KPI, Reports, AI, Ops, Admin.

Then mention that the role matrix is tested in `tests/test_ui_role_navigation_playwright.py` and `tests/role_module_matrix.py`. Optional quick switch to `member@teamswork.local` to show that Projects, Reports, AI, Ops, and Admin are not exposed.

Key message:

- Production auth uses JWT bearer.
- Local/dev can use header fallback when enabled; the current evidence run used `--expect-production-auth` because this workspace returns `401` without token/header.
- Privileged endpoints call permission or role guards.

### 2:00-3:15 - Project, Sprint, And Kanban Flow

Open Projects and Kanban.

Show:

- Project list from seeded demo projects.
- Kanban columns: todo, doing, done.
- Filters for project, sprint, assignee, status, overdue, keyword, deadline.
- Task cards include assignee, difficulty, story points, deadline, and detail drawer.

Key message:

- The seed creates linked departments, users, projects, sprints, members, tasks, workload plans, comments, risks, updates, and notifications.
- The UI is not a landing page; it is an operator workspace.

### 3:15-4:30 - KPI And Reports

Open KPI, then Reports.

Show:

- Monthly KPI table and KPI chart.
- Report buttons for KPI CSV/XLSX/PDF, portfolio CSV/XLSX, project progress CSV/XLSX, and sprint review CSV/XLSX.

Explain the current formula from `app/kpi.py` and `docs/KPI_VALIDATION_RULES.md`:

- On-time done task: `+10 * difficulty_multiplier`.
- Late done task: `+5 * difficulty_multiplier`.
- Unfinished task with a deadline in the KPI month: `-5 * difficulty_multiplier`.
- Difficulty multipliers: easy `1.0`, medium `1.5`, hard `2.0`.
- Manual adjustment is added to the final score and must have a reason and audit trail.

### 4:30-6:00 - AI Task Breakdown And RAG

Open AI Tasks.

Show:

- Requirement textarea.
- RAG checkbox/query.
- Generate task suggestions.
- AI draft list.
- Review-before-import concept.
- RAG document list.

Key message:

- AI creates an `ai_task_drafts` record only.
- Tasks enter Kanban only after manager/admin review and import.
- If no external AI key is configured, the local heuristic fallback still supports the demo.
- Local/dev RAG defaults to lexical search; PostgreSQL pgvector embeddings are optional.

### 6:00-7:10 - Teams-ready Simulation Mode

Open `/admin/integrations/teams-simulator`.

Show:

- Simulation Mode badge and health panel.
- `/task-list`, `/kpi-me`, and `/help` command simulator.
- Adaptive Card JSON and Teams-like preview.
- Notification queue stats, Process queue, and Retry failed flow.

Key message:

- MVP does not send real Teams messages or call Microsoft Graph.
- Student Teams accounts usually cannot upload tenant apps or configure production SSO.
- Real Teams can be enabled later with a Microsoft 365 Developer/E5 tenant.

### 7:10-8:30 - Audit, Ops, And Evidence

Open Audit & Ops.

Show:

- Audit log.
- Failed queue panel.
- Overdue spike panel.
- Monitoring/readiness/metrics endpoints.
- `/monitoring/release-gate` summary.
- Phase 6 admin/compliance/maintenance API surface in `/docs`.

Then show `docs/TEST_EVIDENCE.md` and `docs/TRACEABILITY_MATRIX.md`.

Key message:

- The final package maps every claim to code, tests, and docs.
- CI runs `pytest -q` on Python 3.11 and 3.12 plus `python -m compileall app scripts`.
- Compliance delete is request/export/manual-review only; no hard delete is automated in this phase.
- Live Grafana/Azure Monitor and real tenant observability are documented deferrals, not hidden gaps.

### 8:30-10:00 - Wrap And Q&A

Close with:

- TeamsWork supports controlled delivery operations: RBAC, KPI, reports, AI/RAG, Teams, and auditability.
- The demo is reproducible from seed and evidence commands.
- Known limitations are documented instead of hidden.

## Expected Questions

### RBAC

Q: How do you know roles see the right modules?

A: The expected role-to-module matrix is in `tests/role_module_matrix.py`; UI navigation is checked by `tests/test_ui_role_navigation_playwright.py`, and API module access is checked by `tests/test_role_module_rbac_matrix.py`.

### KPI

Q: Can AI change KPI scores?

A: No. KPI is calculated in `app/kpi.py`. AI task breakdown can suggest tasks, but it does not create KPI adjustments or change the formula. Manual adjustments require a reason and are audited.

### AI/RAG

Q: What happens when the AI provider is unavailable?

A: `app/ai_task_breakdown.py` falls back to local heuristic generation. RAG also works locally through lexical retrieval when embeddings/pgvector are disabled.

### Teams

Q: Does the local demo send messages to Microsoft Teams?

A: No. The local demo shows tab pages, summary, bot callback shape, reminder previews, and queue processing. Real posting requires configured Teams/Azure credentials and webhook settings.

### CI/Test

Q: What proves the demo is reproducible?

A: `scripts/seed_full_demo.py` is idempotent and tested by `tests/test_full_demo_seed.py`. CI runs the pytest suite and compile check in `.github/workflows/ci.yml`.
