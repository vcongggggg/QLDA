# TeamsWork Test Evidence

Last updated: 2026-05-31.
Environment: local Windows workspace, Python 3.12, SQLite local/dev mode unless otherwise noted.

This file records the repeatable evidence package for the final demo. Refresh the command outputs after any behavior-changing code change.

## Commands To Reproduce

```powershell
pip install -r requirements.txt
python -m playwright install chromium
python scripts/seed_full_demo.py --reset-demo
uvicorn app.main:app --reload
python scripts/smoke_check.py --base-url http://127.0.0.1:8000 --user-id 1 --expect-production-auth
python scripts/capture_demo_evidence.py --base-url http://127.0.0.1:8000
python scripts/benchmark_smoke.py --json
pytest -q
pytest tests/test_api_flow.py tests/test_ai_task_breakdown.py tests/test_kpi.py
pytest tests/test_full_demo_seed.py tests/test_ui_role_navigation_playwright.py
pytest tests/test_phase6_admin_compliance_maintenance.py tests/test_ops_dashboard.py tests/test_maintenance_hardening.py tests/test_auth_security_hardening.py tests/test_notifications.py -q
pytest tests/test_phase6_admin_compliance_maintenance.py::test_release_acceptance_matrix_promotes_phase_partial_scope_with_deferrals -q
python -m compileall app scripts
```

## Current Verification Results

| Check | Command | Result | Notes |
| --- | --- | --- | --- |
| Test collection | `pytest --collect-only -q` | PASS, 134 tests collected | Re-run after Phase 6 remaining implementation on 2026-05-31 |
| Full demo seed | `python scripts/seed_full_demo.py --reset-demo` | PASS | Reset mode, warnings `[]` |
| Smoke check | `python scripts/smoke_check.py --base-url http://127.0.0.1:8000 --user-id 1 --expect-production-auth` | PASS | Current env returns 401 without auth, as expected |
| Full tests | `pytest -q` | PASS, 137 passed | Deprecation warnings from dependencies/current code |
| Critical tests | `pytest tests/test_api_flow.py tests/test_ai_task_breakdown.py tests/test_kpi.py` | PASS, 11 passed | Covers API flow, AI, KPI |
| Demo/UI tests | `pytest tests/test_full_demo_seed.py tests/test_ui_role_navigation_playwright.py` | PASS, 5 passed | Playwright Chromium available |
| Compile check | `python -m compileall app scripts` | PASS | Matches CI compile smoke |
| Phase 6 ops release gate | `pytest tests/test_maintenance_hardening.py tests/test_ops_dashboard.py tests/test_auth_security_hardening.py tests/test_notifications.py -q` | PASS, 32 passed | Verifies privileged release-gate access, queue redaction, auth safety status, notification ops, audit export, and maintenance hardening |
| Phase 6 remaining APIs | `pytest tests/test_phase6_admin_compliance_maintenance.py tests/test_ops_dashboard.py tests/test_maintenance_hardening.py tests/test_auth_security_hardening.py tests/test_notifications.py -q` | PASS, 35 passed | Verifies admin search/activity/config/broadcast, compliance request/export/lineage, maintenance windows/retention/cleanup dry-run, and release-gate extensions |
| Release acceptance matrix | `pytest tests/test_phase6_admin_compliance_maintenance.py::test_release_acceptance_matrix_promotes_phase_partial_scope_with_deferrals -q` | PASS | Verifies `/monitoring/release-acceptance` returns 114 completed Phase 1-6 Must/Should stories, approved deferrals, RBAC blocking for staff, and no secret leakage |
| E2 Kanban release controls | `pytest tests/test_kanban_saved_filters_wip.py -q` | PASS, 4 passed | Verifies saved/default filters, WIP/story-point summary, overdue aggregate, staff self-scope, and static UI hooks for board/list, summary, and WIP safeguards |
| E2 Kanban JS syntax | `node --check app/static/js/kanban.js; node --check app/static/js/rag-teams.js` | PASS | Verifies Kanban and saved-filter scripts parse after UI updates |
| E2 Kanban focused gate | `pytest tests/test_kanban_saved_filters_wip.py tests/test_task_filters.py tests/test_task_detail.py tests/test_task_metadata.py -q` | PASS, 15 passed | Covers Kanban saved filters/WIP/summary plus task filter/detail/metadata regression |
| E2 Kanban UI gate | `pytest tests/test_ui_role_navigation_playwright.py tests/test_ui_full_button_audit_playwright.py -q` | PASS, 3 passed | Playwright role navigation and full button audit cover updated Kanban UI controls |
| E2 create/detail/backlog regression | `pytest tests/test_api_flow.py tests/test_task_bulk_backlog.py tests/test_backlog_milestones_dependencies.py -q` | PASS, 7 passed | Verifies task create/detail/API flow and backlog/milestone/dependency paths still work |
| Phase 6 benchmark smoke | `python scripts/benchmark_smoke.py --json` | PASS | Local TestClient checks health, readiness, metrics, release gate, and release acceptance |
| Phase 6 compile check | `python -m compileall app scripts` | PASS | Re-run after adding `/monitoring/release-gate` |
| Full tests after E2 Kanban release controls | `pytest -q` | PASS, 137 passed | Re-run after promoting US066, US096, US099, US101, US102, US115, and US116 |
| Diff whitespace check | `git diff --check` | PASS with line-ending warnings only | No whitespace errors; Git warned existing files may convert LF to CRLF on next touch |
| Evidence capture | `python scripts/capture_demo_evidence.py --start-server --base-url http://127.0.0.1:8000` | PASS with warning | Auditor restricted screenshot timed out; admin/member evidence and videos captured |

## Seed Evidence

Expected seeded demo scope, asserted by `tests/test_full_demo_seed.py`:

- 3 demo projects.
- 21 sprints.
- 100 tasks.
- 12 RAG documents.
- 6 AI task drafts.
- Demo accounts for ADMIN, MANAGER, LEADER, MEMBER, HR, AUDITOR.
- Idempotent `--upsert` behavior.
- Guarded `--reset-demo` behavior outside local/dev/demo/test unless forced.

Paste the latest seed JSON summary here after running:

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
    "kpi_adjustments": 10,
    "task_comments": 250,
    "app_notifications": 12,
    "notification_queue": 9,
    "audit_logs": 11,
    "ai_task_drafts": 11,
    "rag_documents": 12,
    "rag_chunks": 72
  }
}
```

## Screenshot And Video Evidence

Capture command:

```powershell
python scripts/capture_demo_evidence.py --base-url http://127.0.0.1:8000
```

Expected artifact index:

- `.tmp/demo-evidence/<timestamp>/summary.json`
- `.tmp/demo-evidence/<timestamp>/screenshots/admin-dashboard.png`
- `.tmp/demo-evidence/<timestamp>/screenshots/admin-projects.png`
- `.tmp/demo-evidence/<timestamp>/screenshots/admin-kanban.png`
- `.tmp/demo-evidence/<timestamp>/screenshots/admin-kpi.png`
- `.tmp/demo-evidence/<timestamp>/screenshots/admin-reports.png`
- `.tmp/demo-evidence/<timestamp>/screenshots/admin-ai.png`
- `.tmp/demo-evidence/<timestamp>/screenshots/admin-ai-generated-draft.png`
- `.tmp/demo-evidence/<timestamp>/screenshots/admin-teams.png`
- `.tmp/demo-evidence/<timestamp>/screenshots/admin-ops.png`
- `.tmp/demo-evidence/<timestamp>/screenshots/admin-admin.png`
- `.tmp/demo-evidence/<timestamp>/screenshots/member-access-denied-projects.png`
- `.tmp/demo-evidence/<timestamp>/videos/*.webm`

Latest artifact directory:

```text
.tmp/demo-evidence/20260530T050404Z
```

Latest capture warning:

```text
AUDITOR ai: Page.wait_for_function timeout while capturing the optional auditor restricted screenshot.
```

## Manual Demo Acceptance

- Local UI opens at `http://127.0.0.1:8000/ui/`.
- `/health`, `/docs`, and `/monitoring/readiness` respond.
- Demo accounts can log in with credentials from `docs/DEMO_SEED.md`.
- Admin can see all demo modules.
- Member cannot access privileged project/report/AI/admin surfaces.
- Auditor can inspect reports and ops, but cannot access AI.
- KPI and reports use the same calculation rules as `app/kpi.py`.
- AI preview creates drafts; real task creation requires review/import.
- RAG query works locally through lexical retrieval.
- Teams local demo shows tab URLs, summary, and queue status without sending real external messages.

## Known Limitations

- Local demo does not prove production Azure AD or Teams tenant configuration.
- Local RAG does not prove pgvector semantic ranking unless PostgreSQL pgvector and embeddings are enabled.
- Local AI fallback does not prove external model quality; it proves the workflow remains available.
- Screenshots and videos are runtime artifacts in `.tmp/` and are not tracked by git.
