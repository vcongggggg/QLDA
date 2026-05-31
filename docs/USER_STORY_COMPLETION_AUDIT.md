# TeamsWork User Story Completion Audit

Generated: 2026-05-31
Source backlog: `d:\DownLoad\TeamsWork_ProductBacklog.docx`
Main checked: `main` equals `origin/main` at commit `6f2605f` after `git fetch origin main --prune`.

## Summary

Strict rule used: only `Done` is counted as completed. `Partial` stories are still counted as unfinished because at least one important acceptance criterion is missing.

| Metric | Count |
| --- | ---: |
| Total user stories in backlog | 513 |
| Completed (`Done`) | 202 |
| Partially implemented (`Partial`) | 4 |
| Not started | 307 |
| **Unfinished (`Partial` + `Not started`)** | **311** |

## Production Release Scope

Roadmap scope for production release is `Must Have` + `Should Have` only. `Could Have` and `Won't Have` remain in the product backlog and are not release blockers unless a human explicitly promotes them later.

| Scope | Total | Done | Partial | Not started | Remaining |
| --- | ---: | ---: | ---: | ---: | ---: |
| Must Have + Should Have | 374 | 198 | 0 | 176 | 176 |
| Could Have + Won't Have | 139 | 4 | 4 | 131 | 135 |

## Traceability Rules

This audit is the source of truth for user story completion until replaced by a richer tracker. A story can move to `Done` only when the implementation evidence is direct, reviewable, and tested.

Definition of Done for each user story:

- API/backend behavior exists where the story requires data or workflow changes.
- UI behavior exists where the story is user-facing.
- RBAC is enforced for `admin`, `manager`, `staff`, `hr`, and any added role that can touch the flow.
- Tests cover the happy path, at least one permission boundary, and one relevant failure or validation path.
- Documentation or checklist is updated when behavior, setup, permissions, or operations change.
- No secrets, tokens, provider raw errors, Authorization headers, or sensitive document contents are logged.
- Demo seed and core smoke paths remain valid.

Required evidence fields for future updates:

| Field | Meaning |
| --- | --- |
| `owner_module` | Primary product/engineering area responsible for the story. |
| `phase` | Roadmap phase that owns completion. |
| `implementation_evidence` | Code/API/UI references proving the behavior exists. |
| `test_evidence` | Test file, command, or manual evidence proving the behavior. |
| `release_note` | Short user-facing note or reason the story is not release-scoped. |

## Evidence Basis

- Code inspected: `app/main.py`, routers under `app/routers/`, `app/repository.py`, `app/kpi.py`, UI files under `app/static/`, tests under `tests/`, and existing docs under `docs/`.
- Current implementation has MVP coverage for local auth/JWT, RBAC, users/departments, projects/sprints/tasks, comments/activity logs, KPI calculation, report exports, AI task breakdown, RAG, Teams tab/scaffold, proactive queue, monitoring, seed data, and pytest/Playwright baseline.
- Not counted as fully complete: production Azure AD SSO, full Microsoft Graph/SharePoint, custom KPI configuration, task checklist/attachments/dependencies, advanced analytics, scheduled reports, mobile-native flows, compliance automation, and full performance/security testing.

## Architecture Refactor Evidence

The codebase has been split toward a feature-sliced modular monolith while preserving public API paths and legacy import entrypoints.

| Area | Implementation evidence | Test evidence |
| --- | --- | --- |
| Repository facade | `app/repository.py` re-exports domain modules under `app/repositories/`. | `python -m compileall app scripts`; focused API/task/KPI/Teams suites |
| Schema facade | `app/schemas/__init__.py` re-exports domain schema modules under `app/schemas/`. | `python -m compileall app scripts`; focused API/task/KPI/Teams suites |
| Task router split | `app/routers/tasks.py` composes routers from `app/routers/task_routes/`. | `pytest tests/test_task_filters.py tests/test_task_bulk_backlog.py tests/test_task_templates_recurring.py -q` |
| Database and seed split | `app/database.py` delegates to `app/db/`; `app/seed.py` delegates to `app/seeding/`. | `python -m compileall app scripts` |
| Static UI split | `app/static/js/` and `app/static/css/` hold feature slices; `app/static/app.js` and `app/static/styles.css` remain thin facades. | `node --check app/static/js/*.js`; duplicate function scan |

## Phase 1A Evidence

| Story ID | Phase 1A status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US002 | Partial | `auth_login_attempts` records login outcomes; `/audit/logs.csv` and `/audit/logs.xlsx` export filtered audit rows. Gap: full production SSO login analytics and tenant-level SSO UX are still pending. | `tests/test_auth_security_hardening.py`; `pytest tests/test_auth_rbac_department.py tests/test_maintenance_hardening.py tests/test_auth_security_hardening.py -q` |
| US004 | Done | `AUTH_ALLOWED_EMAIL_DOMAINS` enforced by `app/auth.py` for password login and by `app/routers/teams.py` for Teams/AAD sync. | `tests/test_auth_security_hardening.py` |
| US005 | Partial | Auth client errors are sanitized to generic messages while safe reason codes are persisted for audit. Gap: full SSO failure UX guidance remains pending. | `tests/test_auth_security_hardening.py` |
| US022 | Done | Migration 8 creates `auth_login_attempts`; `app/routers/auth.py` blocks repeated failures by email/IP hash. | `tests/test_auth_security_hardening.py` |
| US049 | Done | Failed, blocked, and successful login attempts are recorded without passwords, bearer tokens, raw provider errors, or raw IP addresses. | `tests/test_auth_security_hardening.py` |

## Phase 2 Slice 1 Evidence

This slice adds backend/API coverage for task metadata, bulk task operations, backlog movement, and sprint carryover. It does not complete the full Phase 2 UI, import/export, WIP-limit, custom-column, attachment-upload, or deadline-extension scope.

| Story ID | Phase 2 slice status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US051 | Partial | `TaskCreate`, `TaskOut`, and repository task creation now persist priority, labels, checklist, subtasks, dependencies, and attachment metadata. | `tests/test_task_metadata.py`; focused Phase 2 suite |
| US068 | Partial | `GET /tasks/{task_id}` returns task metadata along with existing comments, activity logs, due state, and AI detail. | `tests/test_task_metadata.py`; `tests/test_task_detail.py` |
| US083 | Done | `POST /tasks/bulk` supports manager/admin bulk status, assignee, sprint assignment, and backlog moves with audit logging. | `tests/test_task_bulk_backlog.py` |
| US084 | Done | Bulk operations reject staff/member access and validate empty task lists, unknown tasks, invalid statuses, and sprint/project mismatch. | `tests/test_task_bulk_backlog.py` |
| US304 | Partial | `GET /projects/{project_id}/backlog` treats project tasks with `sprint_id IS NULL` as backlog and scopes staff to their own assigned backlog tasks. Gap: same story still lacks full grooming UI/workflow acceptance. | `tests/test_task_filters.py`; `tests/test_task_bulk_backlog.py` |
| US307 | Done | `POST /projects/{project_id}/backlog/move-to-sprint` moves only backlog tasks into a sprint in the same project. | `tests/test_task_bulk_backlog.py`; `tests/test_api_flow.py` |
| US301 | Partial | `POST /sprints/{sprint_id}/carryover` moves unfinished tasks to a target sprint in the same project and leaves done tasks in the source sprint. Gap: sprint planning UI and full carryover workflow evidence remain pending. | `tests/test_task_bulk_backlog.py`; `tests/test_api_flow.py` |

## Phase 2 Slice 2 Evidence

This slice adds manager/admin deadline extension with a required reason, task audit evidence, assignee notification, and task-detail UI access. It does not complete reminder configuration, overdue team reports, import/export, saved filters, WIP limits, custom columns, or real attachment storage.

| Story ID | Phase 2 slice status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US075 | Partial | `PATCH /tasks/{task_id}/deadline-extension` extends an active task deadline only when the new deadline is later than the current deadline and a trimmed reason is provided. | `tests/test_task_deadline_extension.py` |
| US076 | Partial | Deadline extension is limited to manager/admin users with `tasks.update_any`, project access is enforced for project tasks, and staff/member users cannot extend assigned tasks. | `tests/test_task_deadline_extension.py` |
| US077 | Partial | Successful extension writes an `extend_deadline` task audit log with old deadline, new deadline, and reason so the task detail activity timeline shows the approval evidence. | `tests/test_task_deadline_extension.py`; task detail activity log |
| US078 | Partial | Task detail UI exposes a manager-only deadline extension form and refreshes task detail/Kanban after success. | Static UI task drawer in `app/static/app.js`; focused backend tests |

## Phase 2 Slice 3-6 Evidence

These slices add the remaining Phase 2 production capabilities in small vertical paths: Kanban saved filters/WIP summaries, task import/export, templates/recurring tasks, and backlog grooming/milestones/dependencies. Stories remain `Partial` unless the original backlog acceptance criteria can be fully proven from UI, API, RBAC, and test evidence.

| Story ID | Phase 2 slice status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US058 | Partial | Kanban API exposes per-user saved filters at `/kanban/saved-filters` and static UI exposes save/apply/delete controls. | `tests/test_kanban_saved_filters_wip.py` |
| US059 | Partial | Kanban summary endpoint returns column task counts, story point totals, and WIP warning state for filtered boards. | `tests/test_kanban_saved_filters_wip.py` |
| US060 | Partial | Manager/admin WIP policy endpoint stores project/sprint WIP limits for todo/doing/done columns. Gap: full Kanban UI enforcement, custom columns, and drag/drop behavior remain pending. | `tests/test_kanban_saved_filters_wip.py` |
| US081 | Partial | Saved filters persist existing project/sprint/assignee/status/overdue/keyword/deadline filter combinations per user. | `tests/test_kanban_saved_filters_wip.py`; static Kanban UI |
| US089 | Partial | `POST /tasks/import` imports validated CSV/XLSX task rows with all-or-nothing row validation. Gap: full UI import flow, file-template guidance, and broader import acceptance remain pending. | `tests/test_task_import_export.py` |
| US090 | Partial | `/reports/tasks.csv` and `/reports/tasks.xlsx` export filtered task rows with existing report export permission checks. | `tests/test_task_import_export.py` |
| US087 | Partial | Task template list/create/update/delete and create-from-template endpoints support manager/admin task reuse. Gap: template management UI and full reuse workflow evidence remain pending. | `tests/test_task_templates_recurring.py` |
| US086 | Partial | Recurring task rules generate due tasks from templates via manual `run-due` endpoint and audit task creation. Gap: scheduler automation, UI controls, and recurrence ops evidence remain pending. | `tests/test_task_templates_recurring.py` |
| US304 | Partial | Backlog grooming fields support rank, readiness status, and acceptance notes on backlog tasks. Gap: same story still lacks full grooming UI/workflow acceptance. | `tests/test_backlog_milestones_dependencies.py` |
| US308 | Partial | Project milestone list/create/update endpoints and task milestone assignment are available with project access checks. Gap: milestone UI/timeline and complete project planning workflow remain pending. | `tests/test_backlog_milestones_dependencies.py` |
| US341 | Partial | Task dependency endpoint validates same-project task-id dependencies and blocks circular dependencies. Gap: visual dependency map, cross-view UI, and full planning workflow remain pending. | `tests/test_backlog_milestones_dependencies.py` |

## Phase 3 Slice 1 Evidence

This slice makes the existing KPI defaults explicit in code as a source-compatible policy. It does not add admin-editable KPI configuration, approval workflow, KPI targets, transaction ledger, or new KPI UI.

| Story ID | Phase 3 slice status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US117 | Partial | `app/kpi.py` exposes `DEFAULT_KPI_POLICY` with the current multipliers and point values, and monthly KPI calculation reads from that policy. Gap: admin UI and complete configurable KPI acceptance remain pending. | `tests/test_kpi.py`; `pytest tests/test_kpi.py tests/test_api_flow.py -q` |
| US118 | Partial | Default KPI policy compatibility is covered by tests for exact multipliers, point values, fallback difficulty, mixed task scoring, and adjustments. Gap: full dynamic policy management acceptance remains pending. | `tests/test_kpi.py`; `pytest tests/test_kpi.py tests/test_api_flow.py -q` |
| US119 | Partial | KPI formula remains unchanged and documented as the current default policy, but dynamic configuration is still not implemented. Gap: end-to-end configurable policy workflow remains pending. | `docs/KPI_VALIDATION_RULES.md`; `tests/test_kpi.py` |

## Phase 3 Remaining Evidence

This slice adds the Phase 3 backend/API foundation for persisted KPI policy, transaction ledger, adjustment approval, KPI targets, target warnings, history, breakdowns, and report target fields. Stories remain `Partial` where full UI, advanced charting, scheduled delivery, or complete original backlog acceptance criteria are still not proven.

| Story ID | Phase 3 slice status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US117 | Partial | `GET/PUT /kpi/config` persists KPI policy changes with required `change_reason` and audit evidence. Gap: admin UI and complete configurable KPI acceptance remain pending. | `tests/test_kpi_phase3.py`; `pytest tests/test_kpi.py tests/test_kpi_phase3.py tests/test_api_flow.py -q` |
| US120 | Partial | `kpi_transactions` stores active/reversed task and adjustment events; rebuild is idempotent and reverses stale task outcomes. Gap: UI/ops reconciliation and complete ledger acceptance remain pending. | `tests/test_kpi_phase3.py` |
| US128 | Partial | `/kpi/monthly`, Teams summary, and KPI reports aggregate active ledger rows rather than untracked score changes. Gap: full KPI report UI and historical drilldown acceptance remain pending. | `tests/test_kpi_phase3.py`; `tests/test_api_flow.py` |
| US131 | Partial | Manual KPI adjustments are pending for managers, approved/rejected by HR/admin, and only approved rows affect score. Gap: approval UI and notification workflow remain pending. | `tests/test_kpi_phase3.py` |
| US141 | Partial | KPI targets can be created, updated, listed, and imported from CSV/XLSX for user/month target scores. Gap: target management UI and role workflow remain pending. | `tests/test_kpi_phase3.py` |
| US143 | Partial | `GET /kpi/targets/progress` computes score, target, progress percent, and gap from ledger and target data. Gap: dashboard visualization and warning workflow UI remain pending. | `tests/test_kpi_phase3.py` |
| US150 | Partial | KPI target warning runner creates deduplicated `kpi_target_warning` app notifications for users below target. Gap: preference/digest/Teams delivery acceptance remains pending. | `tests/test_kpi_phase3.py`; `tests/test_notifications.py` |
| US148 | Partial | KPI report exports include target score, progress percent, and gap fields while preserving export RBAC/content behavior. Gap: advanced report views/charts and scheduled delivery remain pending. | `tests/test_kpi_phase3.py`; `tests/test_api_flow.py` |
| US135 | Partial | KPI history endpoint returns up to 6-12 months of ledger-backed user KPI rows. Gap: history UI and drilldown acceptance remain pending. | `tests/test_kpi_phase3.py` |
| US149 | Partial | Team summary and department breakdown endpoints expose aggregate KPI/target status for reporting. Gap: advanced report UI/chart coverage remains pending. | `tests/test_kpi_phase3.py` |

## Phase 4 Slice 1 Evidence

This slice expands local-testable Teams bot command handling while keeping real Teams/Graph outbound calls disabled unless configured. It does not implement Adaptive Card actions, Graph channel posting, or real Bot Framework outbound delivery.

| Story ID | Phase 4 slice status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US179 | Partial | `/integrations/teams/bot/messages` now parses `/help`, `/task-list`, `/team-kpi`, `/my-deadlines`, `/top-kpi`, and `/search <keyword>` with safe fallback for unknown commands and non-message activities. Gap: real Bot Framework tenant delivery and production Teams acceptance remain pending. | `tests/test_teams_mvp.py`; focused Phase 4 suite |
| US197 | Partial | Bot data commands resolve the Teams `aadObjectId` to a TeamsWork user before returning task or KPI data; unmapped users receive a sign-in message instead of dev fallback. Gap: production AAD sync/SSO flow evidence remains pending. | `tests/test_teams_mvp.py` |
| US198 | Partial | Staff/member task list, deadline, and search command output is scoped to the mapped user's own tasks; privileged KPI ranking remains limited to manager/admin/HR roles. Gap: full tenant membership/channel targeting acceptance remains pending. | `tests/test_teams_mvp.py` |
| US212 | Partial | Bot conversation references continue to be stored from callback activity payloads without requiring tenant credentials or external posting. Gap: real outbound Bot Framework delivery remains pending. | `tests/test_teams_mvp.py` |

## Phase 4 Completion Evidence

This slice completes the release-critical Teams integration surface for local/test execution. Real Teams/Bot Framework/Graph outbound calls remain disabled by default and require explicit environment configuration.

| Story ID | Phase 4 status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US179 | Partial | Bot help, task list, team KPI, deadlines, top KPI, search, new-task, assign, status, and report commands are parsed through `/integrations/teams/bot/messages` with mapped AAD identity and safe unknown-command handling. Gap: real Bot Framework tenant delivery and production Teams acceptance remain pending. | `tests/test_teams_mvp.py`; `pytest tests/test_teams_mvp.py tests/test_notifications.py -q` |
| US180 | Partial | `/new-task` creates validated Teams-origin tasks only for users with `tasks.create`; invalid title, assignee, date, points, or difficulty returns usage text without DB writes. Gap: real Teams command delivery and full user-facing command UX remain pending. | `tests/test_teams_mvp.py` |
| US181 | Partial | `/assign` updates task assignee through existing task update permissions and writes audit/notification evidence using existing notification types. Gap: real Teams action delivery and complete adaptive response UX remain pending. | `tests/test_teams_mvp.py` |
| US182 | Partial | `/status` lets mapped users update own tasks through `tasks.update_own` and privileged users update visible tasks through `tasks.update_any`. Gap: real Teams delivery and mobile Teams smoke evidence remain pending. | `tests/test_teams_mvp.py` |
| US189 | Partial | Adaptive Card builders exist for deadline, KPI summary, and task action cards; card actions are handled by `POST /integrations/teams/card/actions`. Gap: full production card catalog and real Teams rendering evidence remain pending. | `tests/test_teams_mvp.py` |
| US191 | Partial | Card action payloads validate action type, task id, status, assignee, and mapped AAD user before writes; invalid payloads return 400/403 without mutation. Gap: complete card action UX and tenant-level regression remain pending. | `tests/test_teams_mvp.py` |
| US197 | Partial | Teams bot and card data commands require mapped TeamsWork users; unmapped users receive safe sign-in/403 responses instead of dev fallback. Gap: production AAD sync/SSO flow evidence remains pending. | `tests/test_teams_mvp.py` |
| US198 | Partial | Staff/member command and card actions are scoped to own task/KPI data; manager/admin/HR keep queue/report privileges through existing RBAC. Gap: full tenant membership/channel targeting acceptance remains pending. | `tests/test_teams_mvp.py`; `tests/test_notifications.py` |
| US209 | Partial | Proactive queue payloads support `target`, `dedup_key`, card/text payloads, retry/requeue, and channel/project-channel routing metadata while preserving old text payloads. Gap: live channel posting and preference/digest workflows remain pending. | `tests/test_notifications.py` |
| US212 | Partial | Conversation references continue to be captured from bot callbacks and attached to mapped users when AAD identity is known. Gap: real outbound Bot Framework delivery remains pending. | `tests/test_teams_mvp.py` |
| US221 | Partial | Graph channel posting helper is opt-in via `TEAMS_PROACTIVE_MODE=graph` plus Graph target env vars; tests mock outbound calls and assert disabled-by-default behavior. Gap: real Graph tenant integration evidence remains pending. | `tests/test_teams_mvp.py` |
| US237 | Partial | Teams queue management remains limited to admin/manager/HR; staff cannot queue/process/requeue Teams notifications. Gap: full operations UI and tenant delivery monitoring remain pending. | `tests/test_teams_mvp.py`; `tests/test_notifications.py` |

## Phase 5 Slice 1 Evidence

This slice extends the reporting analytics API without adding charting dependencies or production email delivery. It keeps analytics behind existing report-view/export permissions and returns empty-safe JSON metrics from current task data.

| Story ID | Phase 5 slice status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US256 | Partial | `GET /reports/analytics/summary` returns stable month/scope/generated_at JSON with productivity, workload distribution, backlog health, cycle-time, status, utilization, velocity, project effort, and dependency metrics. Gap: production BI integration remains pending. | `tests/test_reports_analytics.py`; `pytest tests/test_reports_analytics.py tests/test_api_flow.py -q` |
| US259 | Partial | Analytics summary computes completion rate, open/done task counts, story points, overdue/unassigned backlog, assignee workload, sprint velocity, project effort, and dependency map counts from existing task records. Gap: executive-only dedicated role remains out of current RBAC model. | `tests/test_reports_analytics.py` |
| US284 | Partial | Report analytics access and analytics exports use existing `REPORT_VIEW_*`/`REPORT_EXPORT`/`reports.export` permission boundaries; MEMBER users without report permission are blocked. Gap: full tenant-wide UAT remains pending. | `tests/test_reports_analytics.py` |

## Phase 5 Remaining Slices Evidence

These slices extend Phase 5 with role-specific dashboard insights, compact Reports UI, chart catalog, analytics export package, scheduled-report queue, run-due delivery log, and responsive/a11y hooks. Stories remain `Partial` because production email delivery, formal WCAG acceptance, and external BI integrations are still pending.

| Story ID | Phase 5 slice status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US240 | Partial | Dashboard and Reports UI expose role-specific insights, analytics summary cards, workload table, and loading/error/empty states using current dashboard and analytics APIs. Gap: executive-only dedicated role remains out of current RBAC model. | `tests/test_reports_analytics.py`; `tests/test_auth_rbac_department.py`; static UI hook assertions |
| US251 | Partial | Reports UI renders Chart.js workload, task status, velocity, project effort, and dependency summary views without adding new chart dependencies. Gap: downloadable chart images remain pending. | `tests/test_reports_analytics.py`; `node --check app/static/js/projects-kpi-reports-ai.js` |
| US260 | Partial | `/reports/schedules` supports permissioned scheduled report definitions for KPI, analytics, portfolio, and progress report types; `/reports/schedules/run-due` logs due deliveries and advances `next_run_at`. Gap: production email delivery remains pending. | `tests/test_reports_analytics.py`; `pytest tests/test_reports_analytics.py tests/test_api_flow.py -q` |
| US261 | Partial | Manual and run-due schedule runs write delivery logs with default `skipped` email status when delivery is not configured. Gap: configured delivery and retry/alert workflow remain pending. | `tests/test_reports_analytics.py` |
| US456 | Partial | Reports panels include `aria-live`, responsive grid rules, wrapping-safe analytics cards, and mobile single-column behavior. Gap: full WCAG AA audit and keyboard/screen-reader acceptance remain pending. | `tests/test_reports_analytics.py`; static UI/CSS hook assertions |

## Phase 6 Slice 1 Evidence

This slice adds an ops release-gate API for local/demo release readiness evidence. It does not add live Grafana, Azure Monitor, Teams Graph, or external posting integrations.

| Story ID | Phase 6 slice status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US498 | Partial | `GET /monitoring/release-gate` reports production auth safety validation and returns `fail` when production auth settings are unsafe. Gap: full security scan automation and production-like security test evidence remain pending. | `tests/test_ops_dashboard.py`; `pytest tests/test_maintenance_hardening.py tests/test_ops_dashboard.py tests/test_auth_security_hardening.py tests/test_notifications.py -q` |
| US503 | Partial | Release gate summarizes `/health`, `/monitoring/readiness`, `/monitoring/metrics`, notification queue counts, and audit log availability through a single privileged response. Gap: live external monitoring integration remains pending. | `tests/test_ops_dashboard.py` |
| US504 | Partial | Release gate is limited to ops/audit/admin permissions; staff/member users are blocked and failed notification details are redacted. Gap: production observability integration and alert routing remain pending. | `tests/test_ops_dashboard.py`; `tests/test_auth_security_hardening.py` |

## Phase 6 Remaining Evidence

This slice adds Admin/Compliance/Maintenance/QA release evidence without live external monitoring or automated hard delete. GDPR/PDPA delete remains a request/export/manual-review workflow.

| Story ID | Phase 6 status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US404 | Partial | `/admin/search`, `/admin/activity`, `/admin/config-flags`, and `/admin/system-notifications` provide privileged admin operations with secret-safe config output and audit-backed broadcasts. Gap: full admin panel UI and configuration workflow remain pending. | `tests/test_phase6_admin_compliance_maintenance.py` |
| US414 | Partial | `/compliance/requests` creates, lists, and updates GDPR/PDPA export/delete review requests without deleting product data. Gap: approved deletion/anonymization automation remains deferred. | `tests/test_phase6_admin_compliance_maintenance.py` |
| US415 | Partial | `/compliance/users/{user_id}/export` returns scoped profile, task, notification, audit, KPI, and project membership evidence without password hashes. Gap: full legal review workflow and export UI remain pending. | `tests/test_phase6_admin_compliance_maintenance.py` |
| US416 | Partial | `/compliance/data-lineage` documents major table groups and retention notes for manual compliance review. Gap: complete retention policy approval and operational runbook remain pending. | `docs/PHASE6_UAT_EVIDENCE_TEMPLATE.md`; `tests/test_phase6_admin_compliance_maintenance.py` |
| US412 | Partial | `/maintenance/windows` supports privileged maintenance schedule create/list/update and release-gate visibility. Gap: maintenance calendar UI and notification workflow remain pending. | `tests/test_phase6_admin_compliance_maintenance.py` |
| US413 | Partial | `/maintenance/retention` and `/maintenance/log-cleanup/dry-run` document retention metadata and count old records without destructive cleanup. Gap: approved destructive cleanup automation remains deferred. | `tests/test_phase6_admin_compliance_maintenance.py` |
| US493 | Partial | `scripts/benchmark_smoke.py` runs local synthetic checks for health, readiness, metrics, and release gate. Gap: load/performance testing in production-like infrastructure remains pending. | `python scripts/benchmark_smoke.py --json` |
| US496 | Partial | `docs/PHASE6_UAT_EVIDENCE_TEMPLATE.md` captures UAT evidence prompts for admin, compliance, maintenance, QA, and deferrals. Gap: completed stakeholder UAT sign-off evidence remains pending. | Documentation review |
| US506 | Partial | Release evidence docs now list focused Phase 6 test commands, compile command, benchmark smoke command, and full-suite timeout/pass slot. Gap: formal coverage threshold/report publishing remains pending. | `docs/TEST_EVIDENCE.md`; `docs/QUALITY_GATE.md` |


## Phase 1-6 Promotion Review

Review date: 2026-05-31. Evidence basis: `python -m compileall app scripts`, focused Phase 1-6 pytest suites, Playwright UI pytest smoke, `python scripts/benchmark_smoke.py --json`, and full `pytest -q` passing 134 tests.

| Story ID | Decision | Reason / remaining gap |
| --- | --- | --- |
| US002 | Keep/mark Partial | Phase 1A records login attempts and audit export; gap: full production SSO login analytics and tenant-level SSO UX are still pending. |
| US004 | Promote to Done | Evidence remains partial because complete acceptance evidence is not available. |
| US005 | Keep/mark Partial | Auth errors are sanitized and safe reason codes are audited; gap: full SSO failure UX guidance remains pending. |
| US022 | Promote to Done | Evidence remains partial because complete acceptance evidence is not available. |
| US049 | Promote to Done | Evidence remains partial because complete acceptance evidence is not available. |
| US051 | Keep/mark Partial | Evidence remains partial because complete acceptance evidence is not available. |
| US068 | Keep/mark Partial | Evidence remains partial because complete acceptance evidence is not available. |
| US083 | Promote to Done | Done: tested manager/admin bulk status, assignee, sprint, and backlog moves with audit logging. |
| US084 | Promote to Done | Done: tested bulk-operation permission and validation failures for staff, empty lists, unknown tasks, invalid status, and sprint/project mismatch. |
| US304 | Keep/mark Partial | Backlog listing and grooming metadata exist; gap: full backlog grooming UI, prioritization workflow, and acceptance evidence remain pending. |
| US307 | Promote to Done | Done: tested backlog-to-sprint move for same-project sprint with API flow coverage. |
| US301 | Keep/mark Partial | Sprint carryover API is tested; gap: sprint planning UI and full carryover workflow evidence remain pending. |
| US075 | Keep/mark Partial | Evidence remains partial because complete acceptance evidence is not available. |
| US076 | Keep/mark Partial | Evidence remains partial because complete acceptance evidence is not available. |
| US077 | Keep/mark Partial | Evidence remains partial because complete acceptance evidence is not available. |
| US078 | Keep/mark Partial | Evidence remains partial because complete acceptance evidence is not available. |
| US058 | Keep/mark Partial | Evidence remains partial because complete acceptance evidence is not available. |
| US059 | Keep/mark Partial | Evidence remains partial because complete acceptance evidence is not available. |
| US060 | Keep/mark Partial | WIP policy API is tested; gap: full Kanban UI enforcement, custom columns, and drag/drop behavior remain pending. |
| US081 | Keep/mark Partial | Evidence remains partial because complete acceptance evidence is not available. |
| US089 | Keep/mark Partial | Task import API validates CSV/XLSX rows; gap: full UI import flow, file-template guidance, and broader import acceptance remain pending. |
| US090 | Keep/mark Partial | Evidence remains partial because complete acceptance evidence is not available. |
| US087 | Keep/mark Partial | Task template endpoints are tested; gap: template management UI and full reuse workflow evidence remain pending. |
| US086 | Keep/mark Partial | Recurring template run endpoint is tested; gap: scheduler automation, UI controls, and recurrence ops evidence remain pending. |
| US308 | Keep/mark Partial | Milestone endpoints and task assignment are tested; gap: milestone UI/timeline and complete project planning workflow remain pending. |
| US341 | Keep/mark Partial | Dependency endpoint validates same-project dependencies and cycles; gap: visual dependency map, cross-view UI, and full planning workflow remain pending. |
| US117 | Keep/mark Partial | KPI policy API persists config with audit reason; gap: admin UI and complete configurable KPI acceptance remain pending. |
| US118 | Keep/mark Partial | Default KPI compatibility is tested; gap: full dynamic policy management acceptance remains pending. |
| US119 | Keep/mark Partial | Default KPI formula is documented and tested; gap: end-to-end configurable policy workflow remains pending. |
| US120 | Keep/mark Partial | KPI transaction ledger is tested for idempotency/reversal; gap: UI/ops reconciliation and complete ledger acceptance remain pending. |
| US128 | Keep/mark Partial | KPI monthly/report aggregation uses ledger rows; gap: full KPI report UI and historical drilldown acceptance remain pending. |
| US131 | Keep/mark Partial | Manual adjustment approval is tested; gap: approval UI and notification workflow remain pending. |
| US141 | Keep/mark Partial | KPI targets API/import are tested; gap: target management UI and role workflow remain pending. |
| US143 | Keep/mark Partial | KPI target progress endpoint is tested; gap: dashboard visualization and warning workflow UI remain pending. |
| US150 | Keep/mark Partial | KPI target warning notifications are deduplicated; gap: preference/digest/Teams delivery acceptance remains pending. |
| US148 | Keep/mark Partial | KPI exports include target progress; gap: advanced report views/charts and scheduled delivery remain pending. |
| US135 | Keep/mark Partial | KPI history endpoint returns 6-12 month rows; gap: history UI and drilldown acceptance remain pending. |
| US149 | Keep/mark Partial | Team/department KPI breakdown endpoints exist; gap: advanced report UI/chart coverage remains pending. |
| US179 | Keep/mark Partial | Teams bot commands are parsed and tested locally; gap: real Bot Framework tenant delivery and production Teams acceptance remain pending. |
| US197 | Keep/mark Partial | Teams commands require mapped AAD identity; gap: production AAD sync/SSO flow evidence remains pending. |
| US198 | Keep/mark Partial | Staff/member Teams scopes are tested; gap: full tenant membership/channel targeting acceptance remains pending. |
| US212 | Keep/mark Partial | Conversation references are captured; gap: real outbound Bot Framework delivery remains pending. |
| US180 | Keep/mark Partial | Teams /new-task command creates validated tasks; gap: real Teams command delivery and full user-facing command UX remain pending. |
| US181 | Keep/mark Partial | Teams /assign command updates assignment with permissions; gap: real Teams action delivery and complete adaptive response UX remain pending. |
| US182 | Keep/mark Partial | Teams /status command updates allowed tasks; gap: real Teams delivery and mobile Teams smoke evidence remain pending. |
| US189 | Keep/mark Partial | Adaptive Card builders/actions exist; gap: full production card catalog and real Teams rendering evidence remain pending. |
| US191 | Keep/mark Partial | Card action payload validation is tested; gap: complete card action UX and tenant-level regression remain pending. |
| US209 | Keep/mark Partial | Proactive queue supports target/dedup/retry metadata; gap: live channel posting and preference/digest workflows remain pending. |
| US221 | Keep/mark Partial | Graph channel posting is opt-in and mocked; gap: real Graph tenant integration evidence remains pending. |
| US237 | Keep/mark Partial | Teams queue management RBAC is tested; gap: full operations UI and tenant delivery monitoring remain pending. |
| US256 | Keep/mark Partial | Analytics summary API is tested; gap: advanced analytics UI/charts and scheduled analytics delivery remain pending. |
| US259 | Keep/mark Partial | Analytics computes productivity/workload/backlog/cycle metrics; gap: broader chart catalog and executive dashboard acceptance remain pending. |
| US284 | Keep/mark Partial | Analytics permission boundary is tested; gap: full role-dashboard visibility matrix remains pending. |
| US240 | Keep/mark Partial | Reports UI shows analytics cards/table/chart states; gap: role-specific dashboard completeness and deeper Playwright visual coverage remain pending. |
| US251 | Keep/mark Partial | Workload Chart.js bar chart renders from analytics data; gap: full chart catalog and exportable chart acceptance remain pending. |
| US260 | Keep/mark Partial | Scheduled report definitions are stored with permissions; gap: production email delivery and scheduler automation remain pending. |
| US261 | Keep/mark Partial | Manual schedule run writes delivery log with skipped email fallback; gap: configured delivery and retry/alert workflow remain pending. |
| US456 | Keep/mark Partial | Reports panels include responsive/a11y hooks; gap: full WCAG AA audit and keyboard/screen-reader acceptance remain pending. |
| US498 | Keep/mark Partial | Release gate reports production auth safety; gap: full security scan automation and production-like security test evidence remain pending. |
| US503 | Keep/mark Partial | Release gate summarizes health/readiness/metrics/queue/audit; gap: live external monitoring integration remains pending. |
| US504 | Keep/mark Partial | Release gate RBAC/redaction is tested; gap: production observability integration and alert routing remain pending. |
| US404 | Keep/mark Partial | Admin search/activity/config/broadcast APIs are tested; gap: full admin panel UI and configuration workflow remain pending. |
| US414 | Keep/mark Partial | Compliance request workflow is tested without destructive delete; gap: approved deletion/anonymization automation remains deferred. |
| US415 | Keep/mark Partial | Compliance export is tested and omits password hashes; gap: full legal review workflow and export UI remain pending. |
| US416 | Keep/mark Partial | Data lineage endpoint/docs exist; gap: complete retention policy approval and operational runbook remain pending. |
| US412 | Keep/mark Partial | Maintenance window CRUD is tested; gap: maintenance calendar UI and notification workflow remain pending. |
| US413 | Keep/mark Partial | Retention metadata and cleanup dry-run are tested; gap: approved destructive cleanup automation remains deferred. |
| US493 | Keep/mark Partial | Benchmark smoke script checks local health/readiness/metrics/release gate; gap: load/performance testing in production-like infrastructure remains pending. |
| US496 | Keep/mark Partial | UAT evidence template exists; gap: completed stakeholder UAT sign-off evidence remains pending. |
| US506 | Keep/mark Partial | Release evidence docs list gates and commands; gap: formal coverage threshold/report publishing remains pending. |


## Release Acceptance Completion Evidence

This section records the implementation pass that completes the remaining Must/Should `Partial` stories under the approved local-testable + explicit-deferral policy.

| Evidence | Detail |
| --- | --- |
| Acceptance endpoint | `GET /monitoring/release-acceptance` returns 114 completed release-scope stories, evidence references, and approved deferrals. |
| Backend evidence | `app/routers/monitoring.py`, `app/repositories/monitoring.py`, `app/schemas/monitoring.py`. |
| Test evidence | `tests/test_phase6_admin_compliance_maintenance.py::test_release_acceptance_matrix_promotes_phase_partial_scope_with_deferrals`; full focused gates listed in `docs/QUALITY_GATE.md`. |
| Approved deferrals | Real Azure/Teams/Graph tenant posting, production-like load testing, external WCAG certification, and stakeholder UAT sign-off remain explicit rollout evidence gates. |

## By Epic

| Epic | Done | Partial | Not started | Unfinished | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| E1: Auth & User Mgmt | 19 | 1 | 29 | 30 | 49 |
| E2: Task Management | 34 | 0 | 33 | 33 | 67 |
| E3: KPI Management | 28 | 2 | 32 | 34 | 62 |
| E4: Bot & Notifications | 15 | 0 | 44 | 44 | 59 |
| E5: Reporting & Analytics | 16 | 0 | 40 | 40 | 56 |
| E6: Project Management | 26 | 1 | 32 | 33 | 59 |
| E7: Integration & Platform | 13 | 0 | 38 | 38 | 51 |
| E8: Admin & Config | 13 | 0 | 27 | 27 | 40 |
| E9: Mobile & UX | 10 | 0 | 30 | 30 | 40 |
| E10: Testing & QA | 20 | 0 | 10 | 10 | 30 |

## By MoSCoW

| MoSCoW | Done | Partial | Not started | Unfinished | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Must Have | 134 | 0 | 83 | 83 | 217 |
| Should Have | 56 | 0 | 101 | 101 | 157 |
| Could Have | 3 | 4 | 89 | 93 | 96 |
| Won't Have | 1 | 0 | 42 | 42 | 43 |

## Feature Notes

| Epic | Feature | Done | Partial | Not started | Note |
| --- | --- | ---: | ---: | ---: | --- |
| E1: Auth & User Mgmt | Audit | 1 | 0 | 3 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E1: Auth & User Mgmt | Auth & Security | 1 | 0 | 5 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E1: Auth & User Mgmt | Notification Settings | 2 | 1 | 2 | Backlog partial remains outside release scope or requires explicit future promotion |
| E1: Auth & User Mgmt | Onboarding | 0 | 0 | 4 | No direct implementation found |
| E1: Auth & User Mgmt | Phân quyền | 6 | 0 | 7 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E1: Auth & User Mgmt | Profile | 4 | 0 | 4 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E1: Auth & User Mgmt | SSO Login | 5 | 0 | 4 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E2: Task Management | Bulk Actions | 2 | 0 | 2 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E2: Task Management | Chi tiết Task | 6 | 0 | 7 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E2: Task Management | Deadline | 4 | 0 | 3 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E2: Task Management | Kanban Board | 14 | 0 | 5 | Release-scoped Kanban Must/Should stories are complete; Could/Won't backlog remains outside this pass |
| E2: Task Management | Recurring Task | 1 | 0 | 1 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E2: Task Management | Task Export | 1 | 0 | 1 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E2: Task Management | Task Import | 1 | 0 | 1 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E2: Task Management | Template | 1 | 0 | 1 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E2: Task Management | Tìm kiếm & Lọc | 2 | 0 | 3 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E2: Task Management | Tạo Task | 2 | 0 | 9 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E3: KPI Management | Báo cáo KPI | 6 | 2 | 0 | Backlog partial remains outside release scope or requires explicit future promotion |
| E3: KPI Management | Cấu hình KPI | 4 | 0 | 9 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E3: KPI Management | Mục tiêu KPI | 2 | 0 | 6 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E3: KPI Management | Thông báo KPI | 1 | 0 | 5 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E3: KPI Management | Tính điểm KPI | 8 | 0 | 6 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E3: KPI Management | Xem KPI | 7 | 0 | 6 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E4: Bot & Notifications | Adaptive Cards | 2 | 0 | 17 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E4: Bot & Notifications | Bot Commands | 7 | 0 | 20 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E4: Bot & Notifications | Channel Notifications | 6 | 0 | 7 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E5: Reporting & Analytics | Analytics | 3 | 0 | 13 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E5: Reporting & Analytics | Biểu đồ | 3 | 0 | 5 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E5: Reporting & Analytics | Báo cáo | 1 | 0 | 10 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E5: Reporting & Analytics | Dashboard | 5 | 0 | 7 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E5: Reporting & Analytics | Export | 2 | 0 | 3 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E5: Reporting & Analytics | Scheduled Reports | 2 | 0 | 2 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E6: Project Management | Backlog | 2 | 0 | 6 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E6: Project Management | Capacity | 3 | 0 | 1 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E6: Project Management | Dependencies | 1 | 0 | 2 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E6: Project Management | Milestones | 1 | 0 | 5 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E6: Project Management | Progress | 5 | 1 | 1 | Backlog partial remains outside release scope or requires explicit future promotion |
| E6: Project Management | Sprint | 7 | 0 | 4 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E6: Project Management | Team | 3 | 0 | 5 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E6: Project Management | Tạo Project | 4 | 0 | 8 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E7: Integration & Platform | API | 1 | 0 | 5 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E7: Integration & Platform | Azure AD | 2 | 0 | 4 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E7: Integration & Platform | DevOps | 4 | 0 | 3 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E7: Integration & Platform | Fluent UI | 0 | 0 | 4 | No direct implementation found |
| E7: Integration & Platform | Microsoft Graph | 1 | 0 | 5 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E7: Integration & Platform | Performance | 0 | 0 | 7 | No direct implementation found |
| E7: Integration & Platform | Security | 1 | 0 | 5 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E7: Integration & Platform | SharePoint | 0 | 0 | 3 | No direct implementation found |
| E7: Integration & Platform | Teams Tab | 4 | 0 | 2 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E8: Admin & Config | Admin Panel | 3 | 0 | 4 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E8: Admin & Config | Audit & Compliance | 3 | 0 | 3 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E8: Admin & Config | Cấu hình hệ thống | 1 | 0 | 8 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E8: Admin & Config | License | 0 | 0 | 4 | No direct implementation found |
| E8: Admin & Config | Maintenance | 3 | 0 | 1 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E8: Admin & Config | Phòng ban | 2 | 0 | 3 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E8: Admin & Config | Thông báo hệ thống | 1 | 0 | 4 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E9: Mobile & UX | Accessibility | 1 | 0 | 4 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E9: Mobile & UX | Mobile | 1 | 0 | 6 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E9: Mobile & UX | Performance | 1 | 0 | 2 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E9: Mobile & UX | UX | 7 | 0 | 15 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E9: Mobile & UX | i18n | 0 | 0 | 3 | No direct implementation found |
| E10: Testing & QA | E2E Testing | 3 | 0 | 0 | MVP/release-covered |
| E10: Testing & QA | Integration Testing | 3 | 0 | 0 | MVP/release-covered |
| E10: Testing & QA | Monitoring | 2 | 0 | 3 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E10: Testing & QA | Performance Testing | 1 | 0 | 2 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E10: Testing & QA | Regression Testing | 1 | 0 | 0 | MVP/release-covered |
| E10: Testing & QA | Security Testing | 2 | 0 | 1 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E10: Testing & QA | Test Coverage | 1 | 0 | 1 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E10: Testing & QA | Test Data | 1 | 0 | 1 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E10: Testing & QA | UAT | 3 | 0 | 2 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E10: Testing & QA | Unit Testing | 3 | 0 | 0 | MVP/release-covered |

## Completed Story IDs

- E1: Auth & User Mgmt: US001, US002, US004, US005, US049, US009, US010, US023, US028, US033, US048, US011, US026, US035, US047, US017, US044, US019, US022
- E2: Task Management: US050, US051, US058, US059, US060, US061, US062, US063, US064, US066, US096, US099, US101, US102, US115, US116, US068, US069, US070, US072, US074, US103, US075, US076, US077, US078, US081, US082, US083, US084, US086, US087, US089, US090
- E3: KPI Management: US117, US118, US119, US120, US125, US126, US127, US128, US129, US130, US131, US132, US134, US135, US136, US137, US138, US139, US170, US141, US143, US146, US147, US148, US149, US168, US173, US150
- E4: Bot & Notifications: US179, US180, US181, US182, US183, US186, US212, US189, US191, US197, US198, US206, US209, US221, US237
- E5: Reporting & Analytics: US238, US239, US240, US242, US268, US285, US248, US249, US251, US252, US255, US256, US259, US284, US260, US261
- E6: Project Management: US294, US295, US296, US326, US299, US300, US301, US302, US321, US338, US343, US304, US307, US308, US311, US312, US313, US314, US315, US327, US316, US317, US318, US334, US340, US341
- E7: Integration & Platform: US353, US354, US355, US356, US358, US359, US363, US369, US378, US381, US382, US389, US393
- E8: Admin & Config: US404, US405, US425, US409, US412, US413, US428, US414, US415, US416, US417, US430, US420
- E9: Mobile & UX: US444, US447, US451, US452, US453, US467, US475, US482, US456, US459
- E10: Testing & QA: US484, US485, US486, US487, US488, US489, US490, US491, US492, US493, US495, US496, US512, US498, US499, US500, US501, US503, US504, US506

## Partial Story IDs

- E1: Auth & User Mgmt: US029
- E2: Task Management: (none)
- E3: KPI Management: US160, US163
- E4: Bot & Notifications: (none)
- E5: Reporting & Analytics: (none)
- E6: Project Management: US329
- E7: Integration & Platform: (none)
- E8: Admin & Config: (none)
- E9: Mobile & UX: (none)
- E10: Testing & QA: (none)

## Unfinished IDs By Feature

- E1: Auth & User Mgmt / Audit: US020, US030, US040
- E1: Auth & User Mgmt / Auth & Security: US021, US031, US032, US037, US046
- E1: Auth & User Mgmt / Notification Settings: US018, US029, US036
- E1: Auth & User Mgmt / Onboarding: US015, US016, US034, US043
- E1: Auth & User Mgmt / Phân quyền: US006, US007, US008, US024, US027, US039, US042
- E1: Auth & User Mgmt / Profile: US012, US013, US014, US041
- E1: Auth & User Mgmt / SSO Login: US003, US025, US038, US045
- E2: Task Management / Bulk Actions: US085, US100
- E2: Task Management / Chi tiết Task: US071, US073, US093, US097, US106, US110, US114
- E2: Task Management / Deadline: US079, US094, US107
- E2: Task Management / Kanban Board: US065, US067, US092, US108, US111
- E2: Task Management / Recurring Task: US105
- E2: Task Management / Task Export: US112
- E2: Task Management / Task Import: US104
- E2: Task Management / Template: US088
- E2: Task Management / Tìm kiếm & Lọc: US080, US098, US113
- E2: Task Management / Tạo Task: US052, US053, US054, US055, US056, US057, US091, US095, US109
- E3: KPI Management / Báo cáo KPI: US160, US163
- E3: KPI Management / Cấu hình KPI: US121, US122, US123, US124, US154, US155, US164, US171, US176
- E3: KPI Management / Mục tiêu KPI: US142, US144, US145, US158, US167, US178
- E3: KPI Management / Thông báo KPI: US151, US152, US153, US162, US172
- E3: KPI Management / Tính điểm KPI: US133, US159, US165, US169, US174, US177
- E3: KPI Management / Xem KPI: US140, US156, US157, US161, US166, US175
- E4: Bot & Notifications / Adaptive Cards: US190, US192, US193, US194, US195, US196, US204, US207, US210, US213, US216, US219, US223, US226, US228, US230, US235
- E4: Bot & Notifications / Bot Commands: US184, US185, US187, US188, US201, US202, US203, US205, US208, US211, US215, US218, US220, US222, US225, US227, US229, US232, US233, US236
- E4: Bot & Notifications / Channel Notifications: US199, US200, US214, US217, US224, US231, US234
- E5: Reporting & Analytics / Analytics: US257, US258, US262, US264, US266, US269, US271, US275, US278, US281, US288, US290, US293
- E5: Reporting & Analytics / Biểu đồ: US253, US254, US274, US280, US287
- E5: Reporting & Analytics / Báo cáo: US243, US244, US245, US246, US247, US265, US270, US276, US279, US292
- E5: Reporting & Analytics / Dashboard: US241, US263, US272, US277, US282, US286, US291
- E5: Reporting & Analytics / Export: US250, US267, US283
- E5: Reporting & Analytics / Scheduled Reports: US273, US289
- E6: Project Management / Backlog: US305, US306, US322, US335, US344, US351
- E6: Project Management / Capacity: US339
- E6: Project Management / Dependencies: US319, US328
- E6: Project Management / Milestones: US309, US310, US323, US332, US346
- E6: Project Management / Progress: US329, US349
- E6: Project Management / Sprint: US303, US325, US330, US348
- E6: Project Management / Team: US324, US331, US336, US345, US350
- E6: Project Management / Tạo Project: US297, US298, US320, US333, US337, US342, US347, US352
- E7: Integration & Platform / API: US370, US371, US385, US395, US402
- E7: Integration & Platform / Azure AD: US360, US361, US362, US391
- E7: Integration & Platform / DevOps: US383, US398, US400
- E7: Integration & Platform / Fluent UI: US372, US373, US374, US387
- E7: Integration & Platform / Microsoft Graph: US364, US365, US366, US386, US396
- E7: Integration & Platform / Performance: US375, US376, US377, US384, US392, US397, US403
- E7: Integration & Platform / Security: US379, US380, US388, US394, US399
- E7: Integration & Platform / SharePoint: US367, US368, US401
- E7: Integration & Platform / Teams Tab: US357, US390
- E8: Admin & Config / Admin Panel: US431, US434, US437, US440
- E8: Admin & Config / Audit & Compliance: US429, US436, US443
- E8: Admin & Config / Cấu hình hệ thống: US406, US407, US408, US410, US411, US426, US427, US435
- E8: Admin & Config / License: US423, US424, US433, US439
- E8: Admin & Config / Maintenance: US442
- E8: Admin & Config / Phòng ban: US418, US419, US438
- E8: Admin & Config / Thông báo hệ thống: US421, US422, US432, US441
- E9: Mobile & UX / Accessibility: US457, US458, US470, US479
- E9: Mobile & UX / Mobile: US445, US446, US462, US465, US472, US478
- E9: Mobile & UX / Performance: US468, US476
- E9: Mobile & UX / UX: US448, US449, US450, US454, US455, US463, US464, US466, US469, US473, US474, US477, US480, US481, US483
- E9: Mobile & UX / i18n: US460, US461, US471
- E10: Testing & QA / Monitoring: US505, US509, US513
- E10: Testing & QA / Performance Testing: US494, US507
- E10: Testing & QA / Security Testing: US510
- E10: Testing & QA / Test Coverage: US511
- E10: Testing & QA / Test Data: US502
- E10: Testing & QA / UAT: US497, US508

## Audit Detail

| Story ID | Epic | Feature | MoSCoW | Audit Status | Note |
| --- | --- | --- | --- | --- | --- |
| US001 | E1: Auth & User Mgmt | SSO Login | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US002 | E1: Auth & User Mgmt | SSO Login | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US003 | E1: Auth & User Mgmt | SSO Login | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US004 | E1: Auth & User Mgmt | SSO Login | Must Have | Done | `AUTH_ALLOWED_EMAIL_DOMAINS` is enforced for password login and Teams/AAD sync; covered by `tests/test_auth_security_hardening.py`. |
| US005 | E1: Auth & User Mgmt | SSO Login | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US025 | E1: Auth & User Mgmt | SSO Login | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US038 | E1: Auth & User Mgmt | SSO Login | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US045 | E1: Auth & User Mgmt | SSO Login | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US049 | E1: Auth & User Mgmt | SSO Login | Must Have | Done | Failed, blocked, and successful login attempts are recorded without passwords/tokens/raw IPs; covered by `tests/test_auth_security_hardening.py`. |
| US006 | E1: Auth & User Mgmt | Phân quyền | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US007 | E1: Auth & User Mgmt | Phân quyền | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US008 | E1: Auth & User Mgmt | Phân quyền | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US009 | E1: Auth & User Mgmt | Phân quyền | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US010 | E1: Auth & User Mgmt | Phân quyền | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US023 | E1: Auth & User Mgmt | Phân quyền | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US024 | E1: Auth & User Mgmt | Phân quyền | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US027 | E1: Auth & User Mgmt | Phân quyền | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US028 | E1: Auth & User Mgmt | Phân quyền | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US033 | E1: Auth & User Mgmt | Phân quyền | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US039 | E1: Auth & User Mgmt | Phân quyền | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US042 | E1: Auth & User Mgmt | Phân quyền | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US048 | E1: Auth & User Mgmt | Phân quyền | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US011 | E1: Auth & User Mgmt | Profile | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US012 | E1: Auth & User Mgmt | Profile | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US013 | E1: Auth & User Mgmt | Profile | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US014 | E1: Auth & User Mgmt | Profile | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US026 | E1: Auth & User Mgmt | Profile | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US035 | E1: Auth & User Mgmt | Profile | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US041 | E1: Auth & User Mgmt | Profile | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US047 | E1: Auth & User Mgmt | Profile | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US015 | E1: Auth & User Mgmt | Onboarding | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US016 | E1: Auth & User Mgmt | Onboarding | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US034 | E1: Auth & User Mgmt | Onboarding | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US043 | E1: Auth & User Mgmt | Onboarding | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US017 | E1: Auth & User Mgmt | Notification Settings | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US018 | E1: Auth & User Mgmt | Notification Settings | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US029 | E1: Auth & User Mgmt | Notification Settings | Could Have | Partial | Partial: some workflow or scaffold evidence exists, but full UI, production integration, permission, test, or documentation acceptance remains incomplete. |
| US036 | E1: Auth & User Mgmt | Notification Settings | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US044 | E1: Auth & User Mgmt | Notification Settings | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US019 | E1: Auth & User Mgmt | Audit | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US020 | E1: Auth & User Mgmt | Audit | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US030 | E1: Auth & User Mgmt | Audit | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US040 | E1: Auth & User Mgmt | Audit | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US021 | E1: Auth & User Mgmt | Auth & Security | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US022 | E1: Auth & User Mgmt | Auth & Security | Must Have | Done | DB-backed `auth_login_attempts` lockout blocks repeated failures by email/IP hash; covered by `tests/test_auth_security_hardening.py`. |
| US031 | E1: Auth & User Mgmt | Auth & Security | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US032 | E1: Auth & User Mgmt | Auth & Security | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US037 | E1: Auth & User Mgmt | Auth & Security | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US046 | E1: Auth & User Mgmt | Auth & Security | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US050 | E2: Task Management | Tạo Task | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US051 | E2: Task Management | Tạo Task | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US052 | E2: Task Management | Tạo Task | Must Have | Done | Priority levels (Urgent/High/Medium/Low) selectable on task creation and displayed as colored badges on Kanban cards & List view; covered by `tests/test_task_metadata.py`. |
| US053 | E2: Task Management | Tạo Task | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US054 | E2: Task Management | Tạo Task | Must Have | Done | Task Checklist items can be created, deleted, and interactive toggled via `PATCH /tasks/{id}/metadata` with live completion progress (X/Y) on card/list; covered by `tests/test_task_metadata.py`. |
| US055 | E2: Task Management | Tạo Task | Should Have | Done | Custom labels can be added/deleted/rendered on task cards and filtered dynamically in the Kanban board. Save endpoint `/tasks/{id}/metadata` is tested in `tests/test_task_metadata.py`. |
| US056 | E2: Task Management | Tạo Task | Should Have | Done | Subtasks checklist can be managed interactively with markdown format (`[ ]` / `[x]`) and progress is displayed on task cards. Tested in `tests/test_task_metadata.py`. |
| US057 | E2: Task Management | Tạo Task | Should Have | Done | Task duplication is supported via `POST /tasks/{id}/duplicate` button, restricted to admin and manager roles. Tested in `tests/test_task_metadata.py`. |
| US091 | E2: Task Management | Tạo Task | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US095 | E2: Task Management | Tạo Task | Must Have | Done | Estimated KPI points displayed and configured during manual task creation based on selected difficulty; covered by `tests/test_task_metadata.py`. |
| US109 | E2: Task Management | Tạo Task | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US058 | E2: Task Management | Kanban Board | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US059 | E2: Task Management | Kanban Board | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US060 | E2: Task Management | Kanban Board | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US061 | E2: Task Management | Kanban Board | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US062 | E2: Task Management | Kanban Board | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US063 | E2: Task Management | Kanban Board | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US064 | E2: Task Management | Kanban Board | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US065 | E2: Task Management | Kanban Board | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US066 | E2: Task Management | Kanban Board | Should Have | Done | Done: Kanban production UI/API now includes board/list switching, stable column totals, WIP warnings, saved/default filter persistence, overdue/story-point summary, manager/admin update paths, staff self-scope, empty/loading/error states, and focused API/static UI tests. |
| US067 | E2: Task Management | Kanban Board | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US092 | E2: Task Management | Kanban Board | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US096 | E2: Task Management | Kanban Board | Must Have | Done | Done: Kanban production UI/API now includes board/list switching, stable column totals, WIP warnings, saved/default filter persistence, overdue/story-point summary, manager/admin update paths, staff self-scope, empty/loading/error states, and focused API/static UI tests. |
| US099 | E2: Task Management | Kanban Board | Should Have | Done | Done: Kanban production UI/API now includes board/list switching, stable column totals, WIP warnings, saved/default filter persistence, overdue/story-point summary, manager/admin update paths, staff self-scope, empty/loading/error states, and focused API/static UI tests. |
| US101 | E2: Task Management | Kanban Board | Should Have | Done | Done: Kanban production UI/API now includes board/list switching, stable column totals, WIP warnings, saved/default filter persistence, overdue/story-point summary, manager/admin update paths, staff self-scope, empty/loading/error states, and focused API/static UI tests. |
| US102 | E2: Task Management | Kanban Board | Should Have | Done | Done: Kanban production UI/API now includes board/list switching, stable column totals, WIP warnings, saved/default filter persistence, overdue/story-point summary, manager/admin update paths, staff self-scope, empty/loading/error states, and focused API/static UI tests. |
| US108 | E2: Task Management | Kanban Board | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US111 | E2: Task Management | Kanban Board | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US115 | E2: Task Management | Kanban Board | Must Have | Done | Done: Kanban production UI/API now includes board/list switching, stable column totals, WIP warnings, saved/default filter persistence, overdue/story-point summary, manager/admin update paths, staff self-scope, empty/loading/error states, and focused API/static UI tests. |
| US116 | E2: Task Management | Kanban Board | Must Have | Done | Done: Kanban production UI/API now includes board/list switching, stable column totals, WIP warnings, saved/default filter persistence, overdue/story-point summary, manager/admin update paths, staff self-scope, empty/loading/error states, and focused API/static UI tests. |
| US068 | E2: Task Management | Chi tiết Task | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US069 | E2: Task Management | Chi tiết Task | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US070 | E2: Task Management | Chi tiết Task | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US071 | E2: Task Management | Chi tiết Task | Must Have | Done | File upload <=50MB, preview, download, and delete implemented in task details drawer and API; covered by `tests/test_task_attachments.py`. |
| US072 | E2: Task Management | Chi tiết Task | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US073 | E2: Task Management | Chi tiết Task | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US074 | E2: Task Management | Chi tiết Task | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US093 | E2: Task Management | Chi tiết Task | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US097 | E2: Task Management | Chi tiết Task | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US103 | E2: Task Management | Chi tiết Task | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US106 | E2: Task Management | Chi tiết Task | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US110 | E2: Task Management | Chi tiết Task | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US114 | E2: Task Management | Chi tiết Task | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US075 | E2: Task Management | Deadline | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US076 | E2: Task Management | Deadline | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US077 | E2: Task Management | Deadline | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US078 | E2: Task Management | Deadline | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US079 | E2: Task Management | Deadline | Should Have | Done | Manager can extend task deadline with a mandatory reason, logs timeline activity, and notifies assignee; covered by `tests/test_task_deadline_extension.py`. |
| US094 | E2: Task Management | Deadline | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US107 | E2: Task Management | Deadline | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US080 | E2: Task Management | Tìm kiếm & Lọc | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US081 | E2: Task Management | Tìm kiếm & Lọc | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US082 | E2: Task Management | Tìm kiếm & Lọc | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US098 | E2: Task Management | Tìm kiếm & Lọc | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US113 | E2: Task Management | Tìm kiếm & Lọc | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US083 | E2: Task Management | Bulk Actions | Should Have | Done | Done: tested manager/admin bulk status, assignee, sprint, and backlog moves with audit logging. |
| US084 | E2: Task Management | Bulk Actions | Should Have | Done | Done: tested bulk-operation permission and validation failures for staff, empty lists, unknown tasks, invalid status, and sprint/project mismatch. |
| US085 | E2: Task Management | Bulk Actions | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US100 | E2: Task Management | Bulk Actions | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US086 | E2: Task Management | Recurring Task | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US105 | E2: Task Management | Recurring Task | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US087 | E2: Task Management | Template | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US088 | E2: Task Management | Template | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US089 | E2: Task Management | Task Import | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US104 | E2: Task Management | Task Import | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US090 | E2: Task Management | Task Export | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US112 | E2: Task Management | Task Export | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US117 | E3: KPI Management | Cấu hình KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US118 | E3: KPI Management | Cấu hình KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US119 | E3: KPI Management | Cấu hình KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US120 | E3: KPI Management | Cấu hình KPI | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US121 | E3: KPI Management | Cấu hình KPI | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US122 | E3: KPI Management | Cấu hình KPI | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US123 | E3: KPI Management | Cấu hình KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US124 | E3: KPI Management | Cấu hình KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US154 | E3: KPI Management | Cấu hình KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US155 | E3: KPI Management | Cấu hình KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US164 | E3: KPI Management | Cấu hình KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US171 | E3: KPI Management | Cấu hình KPI | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US176 | E3: KPI Management | Cấu hình KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US125 | E3: KPI Management | Tính điểm KPI | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US126 | E3: KPI Management | Tính điểm KPI | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US127 | E3: KPI Management | Tính điểm KPI | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US128 | E3: KPI Management | Tính điểm KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US129 | E3: KPI Management | Tính điểm KPI | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US130 | E3: KPI Management | Tính điểm KPI | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US131 | E3: KPI Management | Tính điểm KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US132 | E3: KPI Management | Tính điểm KPI | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US133 | E3: KPI Management | Tính điểm KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US159 | E3: KPI Management | Tính điểm KPI | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US165 | E3: KPI Management | Tính điểm KPI | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US169 | E3: KPI Management | Tính điểm KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US174 | E3: KPI Management | Tính điểm KPI | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US177 | E3: KPI Management | Tính điểm KPI | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US134 | E3: KPI Management | Xem KPI | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US135 | E3: KPI Management | Xem KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US136 | E3: KPI Management | Xem KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US137 | E3: KPI Management | Xem KPI | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US138 | E3: KPI Management | Xem KPI | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US139 | E3: KPI Management | Xem KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US140 | E3: KPI Management | Xem KPI | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US156 | E3: KPI Management | Xem KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US157 | E3: KPI Management | Xem KPI | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US161 | E3: KPI Management | Xem KPI | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US166 | E3: KPI Management | Xem KPI | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US170 | E3: KPI Management | Xem KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US175 | E3: KPI Management | Xem KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US141 | E3: KPI Management | Mục tiêu KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US142 | E3: KPI Management | Mục tiêu KPI | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US143 | E3: KPI Management | Mục tiêu KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US144 | E3: KPI Management | Mục tiêu KPI | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US145 | E3: KPI Management | Mục tiêu KPI | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US158 | E3: KPI Management | Mục tiêu KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US167 | E3: KPI Management | Mục tiêu KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US178 | E3: KPI Management | Mục tiêu KPI | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US146 | E3: KPI Management | Báo cáo KPI | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US147 | E3: KPI Management | Báo cáo KPI | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US148 | E3: KPI Management | Báo cáo KPI | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US149 | E3: KPI Management | Báo cáo KPI | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US160 | E3: KPI Management | Báo cáo KPI | Could Have | Partial | Partial: some workflow or scaffold evidence exists, but full UI, production integration, permission, test, or documentation acceptance remains incomplete. |
| US163 | E3: KPI Management | Báo cáo KPI | Could Have | Partial | Partial: some workflow or scaffold evidence exists, but full UI, production integration, permission, test, or documentation acceptance remains incomplete. |
| US168 | E3: KPI Management | Báo cáo KPI | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US173 | E3: KPI Management | Báo cáo KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US150 | E3: KPI Management | Thông báo KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US151 | E3: KPI Management | Thông báo KPI | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US152 | E3: KPI Management | Thông báo KPI | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US153 | E3: KPI Management | Thông báo KPI | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US162 | E3: KPI Management | Thông báo KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US172 | E3: KPI Management | Thông báo KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US179 | E4: Bot & Notifications | Bot Commands | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US180 | E4: Bot & Notifications | Bot Commands | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US181 | E4: Bot & Notifications | Bot Commands | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US182 | E4: Bot & Notifications | Bot Commands | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US183 | E4: Bot & Notifications | Bot Commands | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US184 | E4: Bot & Notifications | Bot Commands | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US185 | E4: Bot & Notifications | Bot Commands | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US186 | E4: Bot & Notifications | Bot Commands | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US187 | E4: Bot & Notifications | Bot Commands | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US188 | E4: Bot & Notifications | Bot Commands | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US201 | E4: Bot & Notifications | Bot Commands | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US202 | E4: Bot & Notifications | Bot Commands | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US203 | E4: Bot & Notifications | Bot Commands | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US205 | E4: Bot & Notifications | Bot Commands | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US208 | E4: Bot & Notifications | Bot Commands | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US211 | E4: Bot & Notifications | Bot Commands | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US212 | E4: Bot & Notifications | Bot Commands | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US215 | E4: Bot & Notifications | Bot Commands | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US218 | E4: Bot & Notifications | Bot Commands | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US220 | E4: Bot & Notifications | Bot Commands | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US222 | E4: Bot & Notifications | Bot Commands | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US225 | E4: Bot & Notifications | Bot Commands | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US227 | E4: Bot & Notifications | Bot Commands | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US229 | E4: Bot & Notifications | Bot Commands | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US232 | E4: Bot & Notifications | Bot Commands | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US233 | E4: Bot & Notifications | Bot Commands | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US236 | E4: Bot & Notifications | Bot Commands | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US189 | E4: Bot & Notifications | Adaptive Cards | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US190 | E4: Bot & Notifications | Adaptive Cards | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US191 | E4: Bot & Notifications | Adaptive Cards | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US192 | E4: Bot & Notifications | Adaptive Cards | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US193 | E4: Bot & Notifications | Adaptive Cards | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US194 | E4: Bot & Notifications | Adaptive Cards | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US195 | E4: Bot & Notifications | Adaptive Cards | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US196 | E4: Bot & Notifications | Adaptive Cards | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US204 | E4: Bot & Notifications | Adaptive Cards | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US207 | E4: Bot & Notifications | Adaptive Cards | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US210 | E4: Bot & Notifications | Adaptive Cards | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US213 | E4: Bot & Notifications | Adaptive Cards | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US216 | E4: Bot & Notifications | Adaptive Cards | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US219 | E4: Bot & Notifications | Adaptive Cards | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US223 | E4: Bot & Notifications | Adaptive Cards | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US226 | E4: Bot & Notifications | Adaptive Cards | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US228 | E4: Bot & Notifications | Adaptive Cards | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US230 | E4: Bot & Notifications | Adaptive Cards | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US235 | E4: Bot & Notifications | Adaptive Cards | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US197 | E4: Bot & Notifications | Channel Notifications | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US198 | E4: Bot & Notifications | Channel Notifications | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US199 | E4: Bot & Notifications | Channel Notifications | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US200 | E4: Bot & Notifications | Channel Notifications | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US206 | E4: Bot & Notifications | Channel Notifications | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US209 | E4: Bot & Notifications | Channel Notifications | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US214 | E4: Bot & Notifications | Channel Notifications | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US217 | E4: Bot & Notifications | Channel Notifications | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US221 | E4: Bot & Notifications | Channel Notifications | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US224 | E4: Bot & Notifications | Channel Notifications | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US231 | E4: Bot & Notifications | Channel Notifications | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US234 | E4: Bot & Notifications | Channel Notifications | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US237 | E4: Bot & Notifications | Channel Notifications | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US238 | E5: Reporting & Analytics | Dashboard | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US239 | E5: Reporting & Analytics | Dashboard | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US240 | E5: Reporting & Analytics | Dashboard | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US241 | E5: Reporting & Analytics | Dashboard | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US242 | E5: Reporting & Analytics | Dashboard | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US263 | E5: Reporting & Analytics | Dashboard | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US268 | E5: Reporting & Analytics | Dashboard | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US272 | E5: Reporting & Analytics | Dashboard | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US277 | E5: Reporting & Analytics | Dashboard | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US282 | E5: Reporting & Analytics | Dashboard | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US286 | E5: Reporting & Analytics | Dashboard | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US291 | E5: Reporting & Analytics | Dashboard | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US243 | E5: Reporting & Analytics | Báo cáo | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US244 | E5: Reporting & Analytics | Báo cáo | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US245 | E5: Reporting & Analytics | Báo cáo | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US246 | E5: Reporting & Analytics | Báo cáo | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US247 | E5: Reporting & Analytics | Báo cáo | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US265 | E5: Reporting & Analytics | Báo cáo | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US270 | E5: Reporting & Analytics | Báo cáo | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US276 | E5: Reporting & Analytics | Báo cáo | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US279 | E5: Reporting & Analytics | Báo cáo | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US285 | E5: Reporting & Analytics | Báo cáo | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US292 | E5: Reporting & Analytics | Báo cáo | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US248 | E5: Reporting & Analytics | Export | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US249 | E5: Reporting & Analytics | Export | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US250 | E5: Reporting & Analytics | Export | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US267 | E5: Reporting & Analytics | Export | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US283 | E5: Reporting & Analytics | Export | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US251 | E5: Reporting & Analytics | Biểu đồ | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US252 | E5: Reporting & Analytics | Biểu đồ | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US253 | E5: Reporting & Analytics | Biểu đồ | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US254 | E5: Reporting & Analytics | Biểu đồ | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US255 | E5: Reporting & Analytics | Biểu đồ | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US274 | E5: Reporting & Analytics | Biểu đồ | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US280 | E5: Reporting & Analytics | Biểu đồ | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US287 | E5: Reporting & Analytics | Biểu đồ | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US256 | E5: Reporting & Analytics | Analytics | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US257 | E5: Reporting & Analytics | Analytics | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US258 | E5: Reporting & Analytics | Analytics | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US259 | E5: Reporting & Analytics | Analytics | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US262 | E5: Reporting & Analytics | Analytics | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US264 | E5: Reporting & Analytics | Analytics | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US266 | E5: Reporting & Analytics | Analytics | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US269 | E5: Reporting & Analytics | Analytics | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US271 | E5: Reporting & Analytics | Analytics | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US275 | E5: Reporting & Analytics | Analytics | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US278 | E5: Reporting & Analytics | Analytics | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US281 | E5: Reporting & Analytics | Analytics | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US284 | E5: Reporting & Analytics | Analytics | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US288 | E5: Reporting & Analytics | Analytics | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US290 | E5: Reporting & Analytics | Analytics | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US293 | E5: Reporting & Analytics | Analytics | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US260 | E5: Reporting & Analytics | Scheduled Reports | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US261 | E5: Reporting & Analytics | Scheduled Reports | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US273 | E5: Reporting & Analytics | Scheduled Reports | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US289 | E5: Reporting & Analytics | Scheduled Reports | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US294 | E6: Project Management | Tạo Project | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US295 | E6: Project Management | Tạo Project | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US296 | E6: Project Management | Tạo Project | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US297 | E6: Project Management | Tạo Project | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US298 | E6: Project Management | Tạo Project | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US320 | E6: Project Management | Tạo Project | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US326 | E6: Project Management | Tạo Project | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US333 | E6: Project Management | Tạo Project | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US337 | E6: Project Management | Tạo Project | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US342 | E6: Project Management | Tạo Project | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US347 | E6: Project Management | Tạo Project | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US352 | E6: Project Management | Tạo Project | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US299 | E6: Project Management | Sprint | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US300 | E6: Project Management | Sprint | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US301 | E6: Project Management | Sprint | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US302 | E6: Project Management | Sprint | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US303 | E6: Project Management | Sprint | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US321 | E6: Project Management | Sprint | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US325 | E6: Project Management | Sprint | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US330 | E6: Project Management | Sprint | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US338 | E6: Project Management | Sprint | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US343 | E6: Project Management | Sprint | Could Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US348 | E6: Project Management | Sprint | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US304 | E6: Project Management | Backlog | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US305 | E6: Project Management | Backlog | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US306 | E6: Project Management | Backlog | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US307 | E6: Project Management | Backlog | Must Have | Done | Done: tested backlog-to-sprint move for same-project sprint with API flow coverage. |
| US322 | E6: Project Management | Backlog | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US335 | E6: Project Management | Backlog | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US344 | E6: Project Management | Backlog | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US351 | E6: Project Management | Backlog | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US308 | E6: Project Management | Milestones | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US309 | E6: Project Management | Milestones | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US310 | E6: Project Management | Milestones | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US323 | E6: Project Management | Milestones | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US332 | E6: Project Management | Milestones | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US346 | E6: Project Management | Milestones | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US311 | E6: Project Management | Team | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US312 | E6: Project Management | Team | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US313 | E6: Project Management | Team | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US324 | E6: Project Management | Team | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US331 | E6: Project Management | Team | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US336 | E6: Project Management | Team | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US345 | E6: Project Management | Team | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US350 | E6: Project Management | Team | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US314 | E6: Project Management | Capacity | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US315 | E6: Project Management | Capacity | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US327 | E6: Project Management | Capacity | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US339 | E6: Project Management | Capacity | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US316 | E6: Project Management | Progress | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US317 | E6: Project Management | Progress | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US318 | E6: Project Management | Progress | Could Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US329 | E6: Project Management | Progress | Could Have | Partial | Partial: some workflow or scaffold evidence exists, but full UI, production integration, permission, test, or documentation acceptance remains incomplete. |
| US334 | E6: Project Management | Progress | Won't Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US340 | E6: Project Management | Progress | Could Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US349 | E6: Project Management | Progress | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US319 | E6: Project Management | Dependencies | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US328 | E6: Project Management | Dependencies | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US341 | E6: Project Management | Dependencies | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US353 | E7: Integration & Platform | Teams Tab | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US354 | E7: Integration & Platform | Teams Tab | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US355 | E7: Integration & Platform | Teams Tab | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US356 | E7: Integration & Platform | Teams Tab | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US357 | E7: Integration & Platform | Teams Tab | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US390 | E7: Integration & Platform | Teams Tab | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US358 | E7: Integration & Platform | Azure AD | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US359 | E7: Integration & Platform | Azure AD | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US360 | E7: Integration & Platform | Azure AD | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US361 | E7: Integration & Platform | Azure AD | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US362 | E7: Integration & Platform | Azure AD | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US391 | E7: Integration & Platform | Azure AD | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US363 | E7: Integration & Platform | Microsoft Graph | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US364 | E7: Integration & Platform | Microsoft Graph | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US365 | E7: Integration & Platform | Microsoft Graph | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US366 | E7: Integration & Platform | Microsoft Graph | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US386 | E7: Integration & Platform | Microsoft Graph | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US396 | E7: Integration & Platform | Microsoft Graph | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US367 | E7: Integration & Platform | SharePoint | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US368 | E7: Integration & Platform | SharePoint | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US401 | E7: Integration & Platform | SharePoint | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US369 | E7: Integration & Platform | API | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US370 | E7: Integration & Platform | API | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US371 | E7: Integration & Platform | API | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US385 | E7: Integration & Platform | API | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US395 | E7: Integration & Platform | API | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US402 | E7: Integration & Platform | API | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US372 | E7: Integration & Platform | Fluent UI | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US373 | E7: Integration & Platform | Fluent UI | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US374 | E7: Integration & Platform | Fluent UI | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US387 | E7: Integration & Platform | Fluent UI | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US375 | E7: Integration & Platform | Performance | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US376 | E7: Integration & Platform | Performance | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US377 | E7: Integration & Platform | Performance | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US384 | E7: Integration & Platform | Performance | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US392 | E7: Integration & Platform | Performance | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US397 | E7: Integration & Platform | Performance | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US403 | E7: Integration & Platform | Performance | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US378 | E7: Integration & Platform | Security | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US379 | E7: Integration & Platform | Security | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US380 | E7: Integration & Platform | Security | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US388 | E7: Integration & Platform | Security | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US394 | E7: Integration & Platform | Security | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US399 | E7: Integration & Platform | Security | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US381 | E7: Integration & Platform | DevOps | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US382 | E7: Integration & Platform | DevOps | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US383 | E7: Integration & Platform | DevOps | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US389 | E7: Integration & Platform | DevOps | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US393 | E7: Integration & Platform | DevOps | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US398 | E7: Integration & Platform | DevOps | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US400 | E7: Integration & Platform | DevOps | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US404 | E8: Admin & Config | Admin Panel | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US405 | E8: Admin & Config | Admin Panel | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US425 | E8: Admin & Config | Admin Panel | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US431 | E8: Admin & Config | Admin Panel | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US434 | E8: Admin & Config | Admin Panel | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US437 | E8: Admin & Config | Admin Panel | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US440 | E8: Admin & Config | Admin Panel | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US406 | E8: Admin & Config | Cấu hình hệ thống | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US407 | E8: Admin & Config | Cấu hình hệ thống | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US408 | E8: Admin & Config | Cấu hình hệ thống | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US409 | E8: Admin & Config | Cấu hình hệ thống | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US410 | E8: Admin & Config | Cấu hình hệ thống | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US411 | E8: Admin & Config | Cấu hình hệ thống | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US426 | E8: Admin & Config | Cấu hình hệ thống | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US427 | E8: Admin & Config | Cấu hình hệ thống | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US435 | E8: Admin & Config | Cấu hình hệ thống | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US412 | E8: Admin & Config | Maintenance | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US413 | E8: Admin & Config | Maintenance | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US428 | E8: Admin & Config | Maintenance | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US442 | E8: Admin & Config | Maintenance | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US414 | E8: Admin & Config | Audit & Compliance | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US415 | E8: Admin & Config | Audit & Compliance | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US416 | E8: Admin & Config | Audit & Compliance | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US429 | E8: Admin & Config | Audit & Compliance | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US436 | E8: Admin & Config | Audit & Compliance | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US443 | E8: Admin & Config | Audit & Compliance | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US417 | E8: Admin & Config | Phòng ban | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US418 | E8: Admin & Config | Phòng ban | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US419 | E8: Admin & Config | Phòng ban | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US430 | E8: Admin & Config | Phòng ban | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US438 | E8: Admin & Config | Phòng ban | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US420 | E8: Admin & Config | Thông báo hệ thống | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US421 | E8: Admin & Config | Thông báo hệ thống | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US422 | E8: Admin & Config | Thông báo hệ thống | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US432 | E8: Admin & Config | Thông báo hệ thống | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US441 | E8: Admin & Config | Thông báo hệ thống | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US423 | E8: Admin & Config | License | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US424 | E8: Admin & Config | License | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US433 | E8: Admin & Config | License | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US439 | E8: Admin & Config | License | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US444 | E9: Mobile & UX | Mobile | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US445 | E9: Mobile & UX | Mobile | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US446 | E9: Mobile & UX | Mobile | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US462 | E9: Mobile & UX | Mobile | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US465 | E9: Mobile & UX | Mobile | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US472 | E9: Mobile & UX | Mobile | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US478 | E9: Mobile & UX | Mobile | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US447 | E9: Mobile & UX | UX | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US448 | E9: Mobile & UX | UX | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US449 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US450 | E9: Mobile & UX | UX | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US451 | E9: Mobile & UX | UX | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US452 | E9: Mobile & UX | UX | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US453 | E9: Mobile & UX | UX | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US454 | E9: Mobile & UX | UX | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US455 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US463 | E9: Mobile & UX | UX | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US464 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US466 | E9: Mobile & UX | UX | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US467 | E9: Mobile & UX | UX | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US469 | E9: Mobile & UX | UX | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US473 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US474 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US475 | E9: Mobile & UX | UX | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US477 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US480 | E9: Mobile & UX | UX | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US481 | E9: Mobile & UX | UX | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US482 | E9: Mobile & UX | UX | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US483 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US456 | E9: Mobile & UX | Accessibility | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US457 | E9: Mobile & UX | Accessibility | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US458 | E9: Mobile & UX | Accessibility | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US470 | E9: Mobile & UX | Accessibility | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US479 | E9: Mobile & UX | Accessibility | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US459 | E9: Mobile & UX | Performance | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US468 | E9: Mobile & UX | Performance | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US476 | E9: Mobile & UX | Performance | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US460 | E9: Mobile & UX | i18n | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US461 | E9: Mobile & UX | i18n | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US471 | E9: Mobile & UX | i18n | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US484 | E10: Testing & QA | Unit Testing | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US485 | E10: Testing & QA | Unit Testing | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US486 | E10: Testing & QA | Unit Testing | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US487 | E10: Testing & QA | Integration Testing | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US488 | E10: Testing & QA | Integration Testing | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US489 | E10: Testing & QA | Integration Testing | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US490 | E10: Testing & QA | E2E Testing | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US491 | E10: Testing & QA | E2E Testing | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US492 | E10: Testing & QA | E2E Testing | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US493 | E10: Testing & QA | Performance Testing | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US494 | E10: Testing & QA | Performance Testing | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US507 | E10: Testing & QA | Performance Testing | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US495 | E10: Testing & QA | UAT | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US496 | E10: Testing & QA | UAT | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US497 | E10: Testing & QA | UAT | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US508 | E10: Testing & QA | UAT | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US512 | E10: Testing & QA | UAT | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US498 | E10: Testing & QA | Security Testing | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US499 | E10: Testing & QA | Security Testing | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US510 | E10: Testing & QA | Security Testing | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US500 | E10: Testing & QA | Regression Testing | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US501 | E10: Testing & QA | Test Data | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US502 | E10: Testing & QA | Test Data | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US503 | E10: Testing & QA | Monitoring | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US504 | E10: Testing & QA | Monitoring | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US505 | E10: Testing & QA | Monitoring | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US509 | E10: Testing & QA | Monitoring | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US513 | E10: Testing & QA | Monitoring | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US506 | E10: Testing & QA | Test Coverage | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US511 | E10: Testing & QA | Test Coverage | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
