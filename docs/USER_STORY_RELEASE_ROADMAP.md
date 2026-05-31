# TeamsWork User Story Release Roadmap

Generated: 2026-05-31

This roadmap implements the production-release scope from `docs/USER_STORY_COMPLETION_AUDIT.md`: finish `Must Have` and `Should Have` user stories first. `Could Have` and `Won't Have` stories stay in backlog unless explicitly promoted.

## Release Baseline

| Metric | Count |
| --- | ---: |
| Must Have + Should Have stories | 374 |
| Already Done | 190 |
| Partial, still unfinished | 0 |
| Not started | 184 |
| Remaining release stories | 184 |

Quality gate for every phase:

- Update `docs/USER_STORY_COMPLETION_AUDIT.md` with story status, owner module, implementation evidence, test evidence, and release note.
- Keep KPI defaults backward compatible unless the phase explicitly implements tested configurable KPI policy.
- Preserve staff self-scope, manager/team/project scope, and HR/admin permission boundaries.
- Run `pytest -q`; run focused tests for the touched domain.
- Run Playwright checks when UI navigation, dialogs, or role-visible surfaces change.

## Module Ownership Map

TeamsWork now follows a feature-sliced modular monolith layout. Keep compatibility facades in place for existing imports, but add new code in the owning module:

| Area | Owning modules |
| --- | --- |
| Users/Auth/RBAC | `app/schemas/auth.py`, `app/repositories/users.py`, `app/repositories/rbac.py`, `app/routers/auth.py`, `app/routers/users.py`, `app/routers/rbac.py` |
| Tasks/Kanban/Backlog | `app/schemas/tasks.py`, `app/repositories/tasks.py`, `app/repositories/kanban.py`, `app/repositories/task_templates.py`, `app/routers/task_routes/` |
| KPI/Reports | `app/schemas/kpi.py`, `app/schemas/reports.py`, `app/repositories/kpi.py`, `app/reporting.py`, `app/routers/kpi.py`, `app/routers/reports.py` |
| Org/Projects/Sprints | `app/schemas/org.py`, `app/schemas/projects.py`, `app/schemas/sprints.py`, `app/repositories/org.py`, `app/repositories/projects.py`, `app/repositories/sprints.py` |
| Teams/Notifications/Ops | `app/schemas/teams.py`, `app/schemas/notifications.py`, `app/schemas/monitoring.py`, `app/repositories/teams.py`, `app/repositories/notifications.py`, `app/repositories/monitoring.py` |
| Data/Seed/UI | `app/db/`, `app/seeding/`, `app/static/js/`, `app/static/css/` |

Size guardrail: prefer modules under ~400 lines and routers under ~300 lines. If a file grows past that, split by domain behavior before adding unrelated feature code. Keep `app/repository.py`, `app/database.py`, `app/seed.py`, and `app/schemas/__init__.py` as compatibility entrypoints only.

## Phase 0 - Traceability Foundation

Goal: make the backlog measurable before more feature work starts.

Deliverables:

- Treat `docs/USER_STORY_COMPLETION_AUDIT.md` as the source of truth for user story status.
- Keep `Done`, `Partial`, and `Not started` semantics strict: `Partial` remains unfinished.
- Use the Definition of Done in the audit file for every status promotion.
- Add or refresh traceability rows after each phase, not at the end of the whole release.

Exit criteria:

- Audit has production-release scope, Definition of Done, and required evidence fields.
- Roadmap exists and maps remaining stories to phases.

## Phase 1 - Production Foundation, Auth, RBAC, Security

Primary owner modules: Auth, RBAC, Users, Departments, Admin, Monitoring/Security.

Main story groups:

- E1: SSO Login, Phan quyen, Profile, Audit, Auth & Security.
- E7: Azure AD, Security, DevOps production-readiness items.
- E8: Admin Panel, Cau hinh he thong, Maintenance, Phong ban, Audit & Compliance essentials.
- E10: Security Testing and dependency/security scan baseline.

Implementation direction:

- Add production Azure AD/Teams SSO with token validation, refresh behavior, logout/session timeout, failed-login audit, domain whitelist, and AAD sync operations.
- Expand RBAC to support custom roles, role-permission matrix export, project-level permission, active/inactive user reporting, and Excel import for users/groups where scoped.
- Add security middleware and configuration for HTTPS/HSTS deployment guidance, strict CORS, CSP, rate limiting, input validation, audit filters, and audit export.
- Keep local/dev JWT/header fallback available only under safe settings already enforced by configuration.

Tests:

- `pytest tests/test_auth_rbac_department.py tests/test_role_module_rbac_matrix.py tests/test_maintenance_hardening.py`
- Add SSO/AAD mock tests, failed-login audit tests, security header/rate-limit tests, and audit export tests.

Exit criteria:

- E1 Must/Should security and RBAC stories are either `Done` or explicitly deferred with release note.
- Production auth path no longer depends on dev header fallback.

## Phase 2 - Core Task, Kanban, Deadline, Backlog

Primary owner modules: Tasks, Sprints, Projects, UI Kanban, Reports.

Main story groups:

- E2: Tao Task, Kanban Board, Chi tiet Task, Deadline, Tim kiem & Loc, Bulk Actions, Template, Task Import/Export.
- E6: Backlog, Sprint carryover, project/sprint workflow, task/project dependencies where Must/Should.

Implementation direction:

- Extend task data model with priority, labels, checklist, subtasks, attachment metadata, dependencies, templates, duplicate, and Excel import/export.
- Complete Kanban production behavior: drag/drop, custom columns, WIP limits, list view, saved filters, column counts, story point totals, and stable Teams tab task views.
- Complete task detail: inline edit, comments with mention parsing, attachment validation, activity/status timeline, KPI preview, and URL references.
- Add deadline workflows: due countdown, overdue team report, manager deadline extension with required reason, and reminder configuration hooks.
- Add backlog workflow: product backlog, grooming fields, move backlog to sprint, bulk move, sprint carryover for unfinished tasks.

Tests:

- `pytest tests/test_task_filters.py tests/test_task_detail.py tests/test_sprint_workload_warnings.py tests/test_api_flow.py`
- Add tests for task metadata validation, bulk actions, attachment validation, backlog-to-sprint transitions, and import/export content types.

Slice 1 evidence:

- Backend/API implemented for task metadata, bulk actions, backlog listing/move-to-sprint, task duplicate, and sprint carryover.
- Focused tests: `pytest tests/test_task_metadata.py tests/test_task_bulk_backlog.py tests/test_task_filters.py tests/test_task_detail.py tests/test_sprint_workload_warnings.py tests/test_api_flow.py -q`.
- Deferred to later Phase 2 slices: UI Kanban enhancements, Excel import/export, saved filters, WIP limits, custom columns, real attachment upload/storage, and deadline extension workflow.

Exit criteria:

- Core task and sprint workflows can be run by manager/admin and safely scoped for staff.
- All E2/E6 Must stories targeted by this phase have direct implementation and test evidence.

## Phase 3 - KPI Configuration, Targets, Transactions

Primary owner modules: KPI, Reports, Audit, Dashboard.

Main story groups:

- E3: Cau hinh KPI, Tinh diem KPI, Xem KPI, Muc tieu KPI, Bao cao KPI, Thong bao KPI.
- Related E5 report/chart stories that directly depend on KPI data.

Implementation direction:

- Add KPI configuration with default policy matching current rules: `easy=1.0`, `medium=1.5`, `hard=2.0`, on-time `+10`, late `+5`, unfinished overdue in KPI month `-5`.
- Add KPI transaction ledger for duplicate prevention, reopen/delete rollback, and manual adjustment audit.
- Add approval workflow for manual KPI adjustments where required by HR/manager policy.
- Add KPI targets for user/team/month, import support, target progress, and warning notifications.
- Add KPI history/report views for 6-12 months, department/project breakdowns, histogram/top/matrix outputs, and export coverage.

Tests:

- `pytest tests/test_kpi.py tests/test_api_flow.py`
- Add config compatibility tests, transaction idempotency tests, adjustment approval tests, target progress tests, and report export tests.

Exit criteria:

- Existing KPI formula remains the default and existing KPI tests continue to pass.
- KPI stories do not allow AI or user input to invent score changes without stored reason/audit evidence.

## Phase 4 - Microsoft Teams, Bot, Adaptive Cards

Primary owner modules: Teams integration, Notifications, Bot, Graph/AAD.

Main story groups:

- E4: Bot Commands, Adaptive Cards, Channel Notifications.
- E7: Teams Tab, Azure AD, Microsoft Graph.
- E2/E3 stories involving Teams task/KPI actions.

Implementation direction:

- Harden Teams app behavior for Personal Tab, Channel Tab by project, Teams mobile smoke path, and deploy/admin checklist.
- Add Graph-backed channel posting behind environment-controlled configuration with mocked test path.
- Implement bot commands: `/task-list`, `/team-kpi`, `/new-task`, `/assign`, `/status`, `/report`, `/my-deadlines`, `/top-kpi`, `/search`, `/help`.
- Implement Adaptive Cards for deadline/KPI summaries and task actions; validate all action payloads before DB writes.
- Complete notification routing, retry, deduplication, channel selection, and role/project membership targeting.

Tests:

- `pytest tests/test_teams_mvp.py tests/test_notifications.py`
- Add Graph mock tests, card action validation tests, bot command tests, retry/dedup tests, and Teams permission boundary tests.

Exit criteria:

- Real external Teams/Graph calls are disabled by default unless configured through environment variables.
- Local test suite proves card/command workflows without tenant credentials.

## Phase 5 - Reporting, Analytics, Dashboards, UX

Primary owner modules: Dashboard, Reports, Analytics, Static UI.

Main story groups:

- E5: Dashboard, Bao cao, Export, Bieu do, Analytics, Scheduled Reports.
- E9: Mobile, UX, Accessibility, Performance, i18n release-critical items.

Implementation direction:

- Add role-specific dashboards for staff, manager, HR, admin, and executive views.
- Add reporting and analytics for productivity, utilization, cycle time, workload distribution, velocity, overdue/unassigned backlog, project effort, and dependency map.
- Add charts supported by current data: task status, KPI trend, velocity, simple Gantt/timeline, heatmap/histogram where data exists.
- Add scheduled report queue with delivery log; email sending remains environment-configured.
- Harden UI for responsive layouts, keyboard navigation, WCAG AA contrast, loading skeletons, confirmation dialogs, breadcrumbs, split-view task detail, and autocomplete search.

Current release evidence:

- Full local/demo E5 slice includes role dashboard insights, analytics summary expansion, Chart.js reports catalog, analytics JSON/CSV/XLSX exports, scheduled report queue, and local run-due logging.
- Remaining non-local gaps are production email delivery, formal WCAG acceptance, downloadable chart images, external BI integrations, and a dedicated executive-only RBAC role.

Tests:

- `pytest tests/test_api_flow.py tests/test_ui_role_navigation_playwright.py tests/test_ui_full_button_audit_playwright.py`
- Add analytics endpoint tests, scheduled-report tests, responsive/a11y Playwright smoke tests, and role-dashboard visibility tests.

Exit criteria:

- Release-critical dashboards and reports have permission checks and test evidence.
- UI remains usable on desktop and mobile viewport without overlapping text or broken role navigation.

## Phase 6 - Admin, Compliance, Operations, QA Release Gate

Primary owner modules: Admin, Compliance, Monitoring, QA, DevOps.

Main story groups:

- E8: Admin Panel, Audit & Compliance, Maintenance, License, System Notification.
- E10: Performance Testing, UAT, Security Testing, Monitoring, Test Coverage, Test Data.

Implementation direction:

- Add admin global search, recent admin activity, maintenance scheduling, backup/config retention controls, feature flags, and system notifications.
- Add GDPR/PDPA export/delete workflow, data lineage notes, admin IP whitelist controls, and old-log cleanup.
- Add uptime/error tracking integration points, Grafana/Azure Monitor compatible metrics, synthetic journey checks, and tracing plan.
- Add performance benchmark scripts, security/dependency audit automation, coverage report generation, and UAT evidence templates.
- Refresh demo evidence, final test evidence, release checklist, and traceability audit.

Tests:

- `pytest -q`
- Add admin/compliance tests, monitoring tests, benchmark smoke scripts, security scan documentation, and Playwright release-path checks.

Exit criteria:

- All Must/Should release stories are `Done` or have explicit approved deferral notes.
- `pytest -q` passes, core Playwright paths pass, docs and demo evidence are current.

## Release Status Workflow

Use this workflow for every implementation PR or coding session:

Prompt library: `docs/PHASE_SLICE_IMPLEMENTATION_PROMPTS.md`.

1. Select story IDs from this roadmap and list them before coding.
2. Add or update tests first when behavior is clear; otherwise add tests in the same change before marking stories `Done`.
3. Implement the smallest coherent vertical slice across data, API, UI, RBAC, and docs.
4. Run focused tests, then `pytest -q`.
5. Update `docs/USER_STORY_COMPLETION_AUDIT.md` with status, owner module, implementation evidence, test evidence, and release note.
6. Do not mark `Done` for scaffold-only behavior, untested UI-only behavior, or behavior that works only with dev bypasses.
