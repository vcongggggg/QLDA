# TeamsWork Backend (Phase 1 -> Production-like)

This repository now contains a production-like backend foundation for the TeamsWork project.

## Features implemented
- User and task management API
- Task status transitions: `todo`, `doing`, `done`
- KPI monthly auto-calculation with difficulty multipliers
- Manual KPI adjustments (manager/admin/hr)
- Dashboard summary endpoint
- Audit log for critical actions
- Report export: CSV, XLSX, PDF
- Seed sample data endpoint for demo
- RBAC with JWT bearer auth for production and optional header fallback for local dev

## Tech stack
- Python 3.12+
- FastAPI
- SQLite (runtime default) and PostgreSQL migration scripts
- Uvicorn
- Pytest

## Setup
Install dependencies:

```bash
pip install -r requirements.txt
```

Run API:

```bash
uvicorn app.main:app --reload
```

Open docs:
- http://127.0.0.1:8000/docs

Open standalone frontend app:
- http://127.0.0.1:8000/ui/

## Authentication model (hardened)
Production mode:
- JWT bearer token validation (`Authorization: Bearer <token>`)
- Disable insecure mode with:
	- `AUTH_DISABLE_JWT_VALIDATION=false`
	- `AUTH_ALLOW_HEADER_FALLBACK=false`

Local/dev fallback:
- `X-User-Id: <user_id>` still supported only when `AUTH_ALLOW_HEADER_FALLBACK=true`

RBAC roles:
- `admin`
- `manager`
- `staff`
- `hr`

Notes:
- `staff` only sees/updates own tasks and own KPI view.
- privileged endpoints require `admin`/`manager`/`hr` depending on action.

## Bootstrap data
1. Create at least one admin user (via repository/bootstrap script).
2. Call `POST /seed/init` with `X-User-Id` of admin.

The seeded dataset includes demo users and tasks for dashboard/KPI/report testing.

## Main endpoints
- `POST /users`
- `POST /auth/token` (admin-only helper endpoint)
- `GET /users`
- `POST /departments`
- `GET /departments`
- `POST /projects`
- `GET /projects`
- `POST /projects/{project_id}/members`
- `GET /projects/{project_id}/members`
- `POST /projects/{project_id}/sprints`
- `GET /projects/{project_id}/sprints`
- `PATCH /sprints/{sprint_id}/status`
- `POST /projects/{project_id}/sprints/{sprint_id}/tasks`
- `GET /projects/{project_id}/progress`
- `GET /sprints/{sprint_id}/burndown`
- `POST /sprints/{sprint_id}/capacity`
- `GET /sprints/{sprint_id}/capacity`
- `GET /projects/{project_id}/velocity`
- `POST /projects/{project_id}/risks`
- `GET /projects/{project_id}/risks`
- `POST /projects/{project_id}/weekly-status`
- `GET /projects/{project_id}/weekly-status`
- `GET /sprints/{sprint_id}/review-summary`
- `GET /reports/sprints/{sprint_id}/review.csv`
- `GET /reports/sprints/{sprint_id}/review.xlsx`
- `GET /portfolio/summary`
- `GET /reports/portfolio/summary.csv`
- `GET /reports/portfolio/summary.xlsx`
- `POST /integrations/teams/proactive/queue`
- `GET /integrations/teams/proactive/queue`
- `POST /integrations/teams/proactive/process`
- `POST /integrations/teams/proactive/requeue/{notification_id}`
- `GET /monitoring/readiness`
- `GET /monitoring/metrics`
- `POST /tasks`
- `GET /tasks` (supports `assignee_id`, `status`, `project_id`, `sprint_id`)
- `PATCH /tasks/{task_id}/status`
- `POST /kpi/adjustments`
- `GET /kpi/monthly?month=YYYY-MM`
- `GET /dashboard/summary?month=YYYY-MM`
- `GET /audit/logs?limit=100`
- `GET /reports/kpi.csv?month=YYYY-MM`
- `GET /reports/kpi.xlsx?month=YYYY-MM`
- `GET /reports/kpi.pdf?month=YYYY-MM`
- `GET /reports/projects/progress.csv`
- `GET /reports/projects/progress.xlsx`
- `POST /seed/init`

## KPI rule
For each user in a given month:
- Done on time: `+10 * difficulty_multiplier`
- Done late: `+5 * difficulty_multiplier`
- Overdue and unfinished: `-5 * difficulty_multiplier`

Multiplier map:
- easy: `1.0`
- medium: `1.5`
- hard: `2.0`

## Tests
Run tests:

```bash
pytest -q
```

## Container run
Build and run with Docker Compose:

```bash
docker compose up --build
```

## PostgreSQL migration and backup
Migrate data from SQLite to PostgreSQL:

```bash
python scripts/migrate_sqlite_to_postgres.py --sqlite teamswork.db --postgres-dsn "postgresql://teamswork:teamswork@localhost:5432/teamswork"
```

Backup PostgreSQL (PowerShell + pg_dump installed):

```powershell
./scripts/backup_postgres.ps1 -PostgresDsn "postgresql://teamswork:teamswork@localhost:5432/teamswork" -OutputDir "backups"
```

## CI
GitHub Actions workflow is available at:
- `.github/workflows/ci.yml`

## Microsoft Teams integration (implemented scaffold)
Current code now includes Teams integration components:
- Teams tab page: `GET /teams/tab`
- Teams production tab page: `GET /teams/tab/prod`
- Azure AD token introspection endpoint: `GET /integrations/teams/aad/me`
- Azure AD user sync endpoint: `POST /integrations/teams/aad/sync`
- Deadline reminder runner (Adaptive Card webhook): `POST /integrations/teams/reminders/run`
- Bot Framework callback endpoint: `POST /integrations/teams/bot/messages`
- Proactive queue processor: `POST /integrations/teams/proactive/process`
- Proactive requeue endpoint for failed messages: `POST /integrations/teams/proactive/requeue/{notification_id}`
- Teams app manifest scaffold: `teams-app/manifest.json`
- Packaging script: `scripts/package_teams_app.py`

Queue behavior:
- Queue accepts `max_attempts` (`POST /integrations/teams/proactive/queue?message=...&max_attempts=3`)
- Processor picks only due queued items (`next_retry_at` reached)
- Failed sends are retried with increasing delay; item becomes `failed` after max attempts
- `TEAMS_PROACTIVE_MODE=bot` enables Bot Framework proactive send using saved conversation references

### Configure
1. Copy `.env.example` to `.env` and set:
- `APP_BASE_URL`
- `TEAMS_CLIENT_ID`
- `TEAMS_TENANT_ID`
- `TEAMS_INCOMING_WEBHOOK_URL` (optional for sending reminders)
2. For local demo without Azure AD, keep:
- `TEAMS_DISABLE_JWT_VALIDATION=true`

### Notes
- This implementation is integration-ready and testable in local/dev.
- Production deployment still needs tenant-specific Azure AD app registration and Teams app packaging with icons.
- Publish checklist: `teams-app/PUBLISH_CHECKLIST.md`

Environment templates:
- `.env.staging.example`
- `.env.production.example`

Go-live runbook:
- `DEPLOYMENT_RUNBOOK.md`
