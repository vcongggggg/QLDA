# TeamsWork User Story Completion Audit

Generated: 2026-05-31
Source backlog: `d:\DownLoad\TeamsWork_ProductBacklog.docx`
Main checked: `main` equals `origin/main` at commit `6f2605f` after `git fetch origin main --prune`.

## Summary

Strict rule used: only `Done` is counted as completed. `Partial` stories are still counted as unfinished because at least one important acceptance criterion is missing.

| Metric | Count |
| --- | ---: |
| Total user stories in backlog | 513 |
| Completed (`Done`) | 315 |
| Partially implemented (`Partial`) | 4 |
| Not started | 194 |
| **Unfinished (`Partial` + `Not started`)** | **198** |

## Production Release Scope

Roadmap scope for production release is `Must Have` + `Should Have` only. `Could Have` and `Won't Have` remain in the product backlog and are not release blockers unless a human explicitly promotes them later.

| Scope | Total | Done | Partial | Not started | Remaining |
| --- | ---: | ---: | ---: | ---: | ---: |
| Must Have + Should Have | 374 | 311 | 0 | 63 | 63 |
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

## Phase 1B Evidence

This slice completes directly testable RBAC custom role management, role-permission matrix export, and safe self-profile update. It does not claim production Azure AD tenant validation, external SSO rollout, or unrelated onboarding/notification settings stories.

| Story ID | Phase 1B status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US006 | Done | `POST /rbac/roles`, `PATCH /rbac/roles/{role_slug}`, and `GET /rbac/roles/{role_slug}/permissions` support custom role setup and permission assignment behind `roles.manage`. | `tests/test_auth_rbac_department.py`; `pytest tests/test_auth_rbac_department.py tests/test_auth_security_hardening.py tests/test_role_module_rbac_matrix.py -q` |
| US007 | Done | RBAC matrix endpoint `GET /rbac/matrix` exposes role-to-permission coverage for review and admin verification. | `tests/test_auth_rbac_department.py`; focused Phase 1 suite |
| US008 | Done | Staff/member users are blocked from role mutation while admin users can create/update custom roles; audit logs record role changes. | `tests/test_auth_rbac_department.py`; focused Phase 1 suite |
| US024 | Done | Custom role creation stores non-system roles and assigns validated permission keys without accepting unknown permissions. | `app/repositories/rbac.py`; `tests/test_auth_rbac_department.py` |
| US027 | Done | RBAC matrix export is available as `GET /rbac/matrix.csv` and `GET /rbac/matrix.xlsx` with `roles.view` permission checks. | `app/routers/rbac.py`; `app/reporting.py`; `tests/test_auth_rbac_department.py` |
| US042 | Done | Role permission review/export includes all roles and permissions, including custom roles, for release audit evidence. | `tests/test_auth_rbac_department.py`; focused Phase 1 suite |
| US013 | Done | `PATCH /users/me` lets an authenticated user update safe profile fields only (`full_name`, `position`, `avatar_url`) while ignoring role/active escalation attempts and writing audit evidence. | `tests/test_auth_rbac_department.py`; focused Phase 1 suite |

## Phase 1C Evidence

This slice completes local-testable production auth/SSO/security readiness. It does not claim real Azure AD tenant rollout or live Microsoft Graph production acceptance.

| Story ID | Phase 1C status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US003 | Done | `GET /auth/security/status` exposes privileged auth readiness evidence for JWT validation, header fallback, domain allowlist, and Teams/AAD validation without returning secrets. | `tests/test_auth_security_hardening.py`; focused Phase 1 suite |
| US025 | Done | Password login records safe success/failure/block audit rows and updates `last_login_at`; response payloads do not expose password hashes or raw credentials. | `app/routers/auth.py`; `tests/test_auth_security_hardening.py` |
| US038 | Done | Teams/AAD sync remains domain-allowlist guarded and maps AAD identity into TeamsWork users with safe audit evidence while real tenant validation stays configuration-gated. | `tests/test_auth_security_hardening.py`; `tests/test_teams_mvp.py` |
| US031 | Done | Invalid bearer tokens do not fall back to `X-User-Id` when JWT validation is required, preserving production auth priority. | `tests/test_auth_security_hardening.py` |
| US032 | Done | Production auth readiness fails unsafe settings such as disabled JWT validation, enabled header fallback, weak default secret, or missing domain allowlist. | `tests/test_auth_security_hardening.py`; `app/settings.py` |
| US020 | Done | Privileged auth status checks and onboarding/security changes write safe audit log evidence without tokens, passwords, raw IP addresses, or provider error payloads. | `tests/test_auth_security_hardening.py`; `tests/test_auth_rbac_department.py` |
| US021 | Done | Security status is permission-gated with `OPS_VIEW`; staff/member users are blocked from inspecting production auth readiness. | `tests/test_auth_security_hardening.py` |

## Phase 1D Evidence

This slice completes local onboarding lifecycle and self-service notification settings for release scope. It does not send real external invitation emails.

| Story ID | Phase 1D status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US015 | Done | User creation accepts onboarding status/note and persists onboarding fields through migration 14. | `app/routers/users.py`; `app/repositories/users.py`; `tests/test_auth_rbac_department.py` |
| US016 | Done | Admin/HR users can invite users through `POST /users/{user_id}/invite`, setting `invited_at` and audit evidence. | `tests/test_auth_rbac_department.py` |
| US034 | Done | Admin/HR users can update onboarding status through `PATCH /users/{user_id}/onboarding`; staff/member users are denied. | `tests/test_auth_rbac_department.py` |
| US036 | Done | Users can read/update only their own notification settings through `/users/me/notification-settings`; unknown options and invalid quiet hours are rejected. | `tests/test_auth_rbac_department.py` |
| US043 | Done | Successful login or AAD sync activates invited/pending users by recording `activated_at`/`last_login_at` without changing role or active-state permissions. | `app/repositories/users.py`; `tests/test_auth_security_hardening.py` |

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

## Phase 2 Slice 7 Evidence

This slice completes the requested core task/project workflow stories with API behavior, static UI surfaces, RBAC/project-scope checks, audit/activity evidence, focused pytest coverage, and Playwright role-navigation verification. It does not claim unrelated later Phase 2 stories such as custom Kanban columns or full dependency visualization.

| Story ID | Phase 2 slice status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US053 | Done | Manual task creation is available through `POST /tasks` and the Kanban task-create drawer; `taskCreate` client permission now maps to `tasks.create`/Kanban manage permissions. | `tests/test_api_flow.py`; `pytest tests/test_phase2_project_workflow.py tests/test_task_filters.py tests/test_task_detail.py tests/test_task_deadline_extension.py tests/test_task_bulk_backlog.py tests/test_api_flow.py -q`; `pytest tests/test_ui_role_navigation_playwright.py -q` |
| US091 | Done | Task creation persists title, description, assignee, project/sprint, priority, difficulty, story points, checklist, deadline, audit log, and Kanban refresh evidence. | `tests/test_api_flow.py`; focused Phase 2 suite |
| US073 | Done | Task detail drawer/API exposes assignee/project/sprint names, due state, comments, activity logs, AI detail, labels, subtasks, checklist, attachments, duplicate action, and deadline-extension controls where permitted. | `tests/test_task_detail.py`; `tests/test_task_deadline_extension.py`; Playwright role navigation |
| US110 | Done | Task detail access preserves staff/member self-scope and manager/admin visibility while blocking unassigned staff comments/detail reads. | `tests/test_task_detail.py`; focused Phase 2 suite |
| US080 | Done | Task search/filter supports project, sprint, assignee, status, overdue, keyword, deadline range, and UI Kanban/timeline filter state. | `tests/test_task_filters.py`; Playwright role navigation |
| US098 | Done | Staff task search remains scoped to own assignments even when another assignee is requested. | `tests/test_task_filters.py` |
| US113 | Done | Invalid task filters are rejected with safe 400 responses and empty states render in Kanban/list views. | `tests/test_task_filters.py`; static UI in `app/static/js/kanban.js` |
| US094 | Done | Manager/admin deadline extension requires a later deadline and non-empty reason, writes task activity evidence, notifies the assignee, and is exposed in task detail UI only for permitted roles. | `tests/test_task_deadline_extension.py`; `app/static/js/task-detail.js` |
| US297 | Done | Project creation is available through `POST /projects` and the Projects drawer; manager-created projects default ownership to the creator when no manager is supplied. | `tests/test_phase2_project_workflow.py`; `app/static/js/projects-kpi-reports-ai.js` |
| US298 | Done | Project creation validates status/department/manager references, requires `projects.manage`, writes project audit evidence, and refreshes the project UI. | `tests/test_phase2_project_workflow.py`; focused Phase 2 suite |
| US333 | Done | Project detail UI exposes progress, members, sprints, and backlog evidence; project/sprint/member mutations preserve project-scope checks. | `tests/test_phase2_project_workflow.py`; Playwright role navigation |
| US337 | Done | Outside managers cannot mutate another manager's project membership or sprint plan; admin/owner manager workflows remain allowed. | `tests/test_phase2_project_workflow.py` |
| US305 | Done | Project backlog lists unsprinted project tasks with staff self-scope preserved and task detail links available from project detail UI. | `tests/test_task_filters.py`; `tests/test_phase2_project_workflow.py` |
| US306 | Done | Backlog move-to-sprint validates same-project sprint/task membership, moves backlog tasks, writes audit evidence, and is exposed from project detail UI. | `tests/test_task_bulk_backlog.py`; `tests/test_phase2_project_workflow.py`; `tests/test_api_flow.py` |

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
| US121 | Done | KPI config read/update workflow is permissioned, requires `change_reason`, writes audit evidence, and preserves the default formula values under explicit tests. | `app/routers/kpi.py`; `app/repositories/kpi.py`; `tests/test_kpi.py`; `tests/test_kpi_phase3.py` |
| US122 | Done | KPI policy update validation requires complete difficulty multiplier keys and valid fallback difficulty, with staff/member mutation denied. | `tests/test_kpi_phase3.py`; focused Phase 3 suite |
| US140 | Done | `/kpi/monthly` returns ledger-backed monthly KPI rows with member self-scope and target progress fields where targets exist. | `tests/test_kpi_phase3.py`; `tests/test_api_flow.py` |
| US142 | Done | KPI target create/list/progress workflow supports user-month targets and computes score, target, progress percent, and gap. | `tests/test_kpi_phase3.py` |
| US144 | Done | KPI target update preserves existing values for omitted fields and recalculates target progress without changing score formula defaults. | `app/repositories/kpi.py`; `tests/test_kpi_phase3.py` |
| US145 | Done | KPI target import accepts CSV/XLSX rows, validates user/month/target fields, upserts targets, and records audit evidence. | `app/routers/kpi.py`; `tests/test_kpi_phase3.py` |
| US151 | Done | KPI target warning runner rebuilds ledger state and creates user notifications for target gaps. | `app/routers/notifications.py`; `tests/test_kpi_phase3.py` |
| US152 | Done | KPI warning notifications deduplicate within the daily run window. | `app/repositories/notifications.py`; `tests/test_kpi_phase3.py` |
| US153 | Done | KPI warning generation is role-gated, audited, and local-only without requiring external Teams/Graph delivery. | `app/routers/notifications.py`; `tests/test_kpi_phase3.py` |
| US157 | Done | KPI history, team summary, and department breakdown endpoints expose release-testable KPI view workflows. | `app/routers/kpi.py`; `tests/test_kpi_phase3.py` |
| US159 | Done | KPI transaction rebuild is idempotent and stores active/reversed events for task outcomes. | `app/repositories/kpi.py`; `tests/test_kpi_phase3.py` |
| US165 | Done | Manual KPI adjustments require stored reason/audit evidence, manager-created adjustments remain pending, and HR/admin approval is required before score impact. | `tests/test_kpi_phase3.py` |
| US166 | Done | Staff/member KPI and report access stays scoped/permissioned while privileged users can inspect team KPI exports. | `app/routers/kpi.py`; `tests/test_kpi_phase3.py`; `tests/test_api_flow.py` |
| US171 | Done | Persisted KPI policy retrieval/update uses the same tested policy model and keeps `DEFAULT_KPI_POLICY` compatibility intact. | `app/kpi.py`; `app/routers/kpi.py`; `tests/test_kpi.py`; `tests/test_kpi_phase3.py` |
| US174 | Done | KPI aggregation uses active ledger transactions for task and approved adjustment events rather than untracked score mutation. | `app/kpi.py`; `app/repositories/kpi.py`; `tests/test_kpi_phase3.py` |
| US177 | Done | Changed task outcomes reverse stale KPI ledger rows and preserve transaction evidence for rollback-safe recalculation. | `tests/test_kpi_phase3.py` |

## Phase 4 Slice 1 Evidence

This slice expands local-testable Teams bot command handling while keeping real Teams/Graph outbound calls disabled unless configured. It does not implement Adaptive Card actions, Graph channel posting, or real Bot Framework outbound delivery.

| Story ID | Phase 4 slice status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US179 | Done for simulation | `/integrations/teams/bot/messages` and simulator command paths parse Teams-ready command flows with safe fallback for unknown commands and non-message activities. Gap: real Bot Framework tenant delivery and production Teams acceptance remain pending. | `tests/test_teams_mvp.py`; focused Phase 4 suite |
| US197 | Partial | Bot data commands resolve the Teams `aadObjectId` to a TeamsWork user before returning task or KPI data; unmapped users receive a sign-in message instead of dev fallback. Gap: production AAD sync/SSO flow evidence remains pending. | `tests/test_teams_mvp.py` |
| US198 | Partial | Staff/member task list, deadline, and search command output is scoped to the mapped user's own tasks; privileged KPI ranking remains limited to manager/admin/HR roles. Gap: full tenant membership/channel targeting acceptance remains pending. | `tests/test_teams_mvp.py` |
| US212 | Partial | Bot conversation references continue to be stored from callback activity payloads without requiring tenant credentials or external posting. Gap: real outbound Bot Framework delivery remains pending. | `tests/test_teams_mvp.py` |

## Phase 4 Completion Evidence

This slice completes the release-critical Teams integration surface for local/test execution. Real Teams/Bot Framework/Graph outbound calls remain disabled by default and require explicit environment configuration.

### Teams-ready Simulation Mode Update

The MVP Teams direction is now explicitly `Teams-ready Simulation Mode`, not production Microsoft Teams integration. Evidence is the simulator page at `/admin/integrations/teams-simulator`, simulation APIs under `/integrations/teams/*`, local Adaptive Card preview, queue processing without Graph calls, retry handling, and `docs/TEAMS_SIMULATION_MODE.md`. These stories are counted as done only for the local/demo simulation acceptance path. Real Microsoft Graph and Teams outbound delivery remain disabled by default and must not be claimed as production Teams integration.

| Story ID | Simulation status | Evidence |
| --- | --- | --- |
| US179 | Done for MVP simulation | Deadline reminder Adaptive Cards are generated as `deadline_reminder` queue payloads; real Teams send is disabled by default. |
| US180 | Done for MVP simulation | `/task-list` is available through `POST /integrations/teams/simulator/command` and returns text, card JSON, and preview HTML. |
| US183 | Done for MVP simulation | `/kpi-me` returns current user KPI score, on-time, late, and overdue unfinished counts. |
| US192 | Done for MVP simulation | Deadline/overdue warning card preview is available through simulator card builders and queue payloads. |
| US193 | Done for MVP simulation | Complete, Extend, and Comment card actions are handled through validated Teams card action payloads. |
| US196 | Done for MVP simulation | Static UI renders a Teams-like Adaptive Card preview in the simulator page. |
| US206 | Done for MVP simulation | Existing `notification_queue` retry behavior is reused with max 3 attempts for simulator queue items. |
| US488 | Done for MVP simulation | Focused integration tests cover mock Teams command, card, queue, process, retry, and action flow. |
| US504/US505 | Done for MVP simulation | `/integrations/teams/health` and the simulator dashboard expose mode, real Graph disabled state, and queue counts. |

| Story ID | Phase 4 status | Implementation evidence | Test evidence |
| --- | --- | --- | --- |
| US179 | Done for simulation | Bot help, task list, team KPI, deadlines, top KPI, search, new-task, assign, status, and report commands are parsed through `/integrations/teams/bot/messages` with mapped AAD identity and safe unknown-command handling. Gap: real Bot Framework tenant delivery and production Teams acceptance remain pending. | `tests/test_teams_mvp.py`; `pytest tests/test_teams_mvp.py tests/test_notifications.py -q` |
| US180 | Done for simulation | `/new-task` and simulator command flows create or preview validated Teams-origin task workflows only for allowed users; invalid title, assignee, date, points, or difficulty returns usage text without DB writes. Gap: real Teams command delivery and full production Teams UX remain pending. | `tests/test_teams_mvp.py`; `tests/test_teams_simulation.py` |
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
| US504 | Done for simulation | Release gate is limited to ops/audit/admin permissions; staff/member users are blocked, failed notification details are redacted, and Teams simulation health exposes real Graph disabled state. Gap: production observability integration and alert routing remain pending. | `tests/test_ops_dashboard.py`; `tests/test_auth_security_hardening.py`; `tests/test_teams_simulation.py` |

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
| US179 | Count Done for simulation | Teams bot/simulator commands are parsed and tested locally; real Bot Framework tenant delivery and production Teams acceptance remain pending. |
| US197 | Keep/mark Partial | Teams commands require mapped AAD identity; gap: production AAD sync/SSO flow evidence remains pending. |
| US198 | Keep/mark Partial | Staff/member Teams scopes are tested; gap: full tenant membership/channel targeting acceptance remains pending. |
| US212 | Keep/mark Partial | Conversation references are captured; gap: real outbound Bot Framework delivery remains pending. |
| US180 | Count Done for simulation | Teams simulator command flow is covered locally; real Teams command delivery and full production user-facing command UX remain pending. |
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
| US241/US272/US277/US282/US286 | Promote to Done | Done: role-scoped local dashboard insights API returns cards, alerts, analytics, KPI preview, chart catalog, export links, and empty/error states. |
| US243/US244/US245/US246/US270/US279 | Promote to Done | Done: local report/export endpoints expose KPI, analytics, progress/portfolio-style data with RBAC and focused test coverage. |
| US253/US274 | Promote to Done | Done: dashboard insights expose chart-ready local datasets for status, workload, velocity, project effort, and dependency summary. |
| US262/US288 | Promote to Done | Done: analytics metrics are computed locally and surfaced through dashboard insights; external BI/executive-only role remains outside this pass. |
| US273 | Promote to Done | Done: scheduled reports support create/list/manual run/run-due delivery logs locally; production email delivery remains deferred. |
| US283 | Promote to Done | Done: permission-aware dashboard export links and analytics exports are covered locally. |
| US445/US446/US478 | Promote to Done | Done: responsive mobile shell with role-aware bottom nav, off-canvas sidebar behavior, and no horizontal overflow has static evidence and a Playwright mobile scenario. |
| US448/US450/US454/US463/US466/US469/US480/US481 | Promote to Done | Done: shell UX keeps active navigation state, skip-to-content flow, keyboard controls, and stable titles. |
| US457/US458/US470/US479 | Promote to Done | Done: accessibility hooks include skip link, focus-visible, aria-current, labeled mobile nav, and reduced-motion support. |
| US460/US471 | Promote to Done | Done: VI/EN language toggle updates the shell and persists language preference. |
| US468 | Promote to Done | Done: UI performance hooks use CSS-only responsiveness, lightweight mobile-nav rendering, reduced motion, and navigation performance marks. |
| US406/US407/US408/US410/US411/US426/US427 | Promote to Done | Done: safe system configuration overview exposes auth/Teams/AI settings and redacts secret-bearing environment values. |
| US418/US419 | Promote to Done | Done: department ops evidence summarizes active/inactive departments, manager coverage, and user distribution behind privileged access. |
| US421/US422/US441 | Promote to Done | Done: system notification broadcast plus evidence endpoints cover privileged admin communication review. |
| US423/US424 | Promote to Done | Done: local license status endpoint reports demo license mode, active users, usage counts, and external integration deferral. |
| US429/US443 | Promote to Done | Done: compliance release evidence summarizes request backlog, data lineage, export endpoint, and manual no-hard-delete policy. |
| US431/US437 | Promote to Done | Done: admin release panel exposes the admin/config/license/compliance/maintenance/QA/release-gate surface map. |
| US494/US507 | Promote to Done | Done: QA release evidence documents local synthetic performance smoke and benchmark command. |
| US497 | Promote to Done | Done: QA release evidence links UAT template and tracks stakeholder signoff as remaining external evidence. |
| US502 | Promote to Done | Done: QA test-data inventory reports counts, seed/reset policy, and demo account documentation. |
| US509/US513 | Promote to Done | Done: QA monitoring evidence references health/readiness/metrics/release-gate endpoints and notification queue counts. |
| US510 | Promote to Done | Done: QA security evidence records headers, login lockout, audit export, redaction, and production auth safety checks. |
| US498 | Keep/mark Partial | Release gate reports production auth safety; gap: full security scan automation and production-like security test evidence remain pending. |
| US503 | Keep/mark Partial | Release gate summarizes health/readiness/metrics/queue/audit; gap: live external monitoring integration remains pending. |
| US504 | Count Done for simulation | Release gate RBAC/redaction and Teams simulation health evidence are tested; production observability integration and alert routing remain pending. |
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
| E3: KPI Management | 44 | 2 | 32 | 18 | 46 |
| E4: Bot & Notifications | 18 | 0 | 41 | 41 | 59 |
| E5: Reporting & Analytics | 33 | 0 | 23 | 23 | 56 |
| E6: Project Management | 26 | 1 | 32 | 33 | 59 |
| E7: Integration & Platform | 13 | 0 | 38 | 38 | 51 |
| E8: Admin & Config | 31 | 0 | 9 | 9 | 40 |
| E9: Mobile & UX | 28 | 0 | 12 | 12 | 40 |
| E10: Testing & QA | 28 | 0 | 2 | 2 | 30 |

## By MoSCoW

| MoSCoW | Done | Partial | Not started | Unfinished | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Must Have | 171 | 0 | 46 | 46 | 217 |
| Should Have | 99 | 0 | 58 | 58 | 157 |
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
| E3: KPI Management | Cấu hình KPI | 7 | 0 | 6 | Phase 3 requested Should/Must KPI config stories are complete; lower-priority backlog remains outside this pass |
| E3: KPI Management | Mục tiêu KPI | 5 | 0 | 3 | Phase 3 requested KPI target stories are complete; lower-priority backlog remains outside this pass |
| E3: KPI Management | Thông báo KPI | 4 | 0 | 2 | Phase 3 requested KPI notification stories are complete; lower-priority backlog remains outside this pass |
| E3: KPI Management | Tính điểm KPI | 12 | 0 | 2 | Phase 3 requested KPI scoring stories are complete; lower-priority backlog remains outside this pass |
| E3: KPI Management | Xem KPI | 10 | 0 | 3 | Phase 3 requested KPI viewing stories are complete; lower-priority backlog remains outside this pass |
| E4: Bot & Notifications | Adaptive Cards | 5 | 0 | 14 | Teams-ready simulation stories are complete; real Teams tenant/Graph rendering remains disabled by default |
| E4: Bot & Notifications | Bot Commands | 7 | 0 | 20 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E4: Bot & Notifications | Channel Notifications | 6 | 0 | 7 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E5: Reporting & Analytics | Analytics | 5 | 0 | 11 | Phase 5 local analytics stories are complete; external BI/executive-only gaps remain outside this pass |
| E5: Reporting & Analytics | Biểu đồ | 5 | 0 | 3 | Phase 5 local chart data stories are complete; downloadable chart images remain outside this pass |
| E5: Reporting & Analytics | Báo cáo | 7 | 0 | 4 | Phase 5 local report/export stories are complete; external BI remains outside this pass |
| E5: Reporting & Analytics | Dashboard | 10 | 0 | 2 | Phase 5 local dashboard insights are complete; production BI/UX acceptance remains outside this pass |
| E5: Reporting & Analytics | Export | 3 | 0 | 2 | Phase 5 local export links and analytics exports are complete |
| E5: Reporting & Analytics | Scheduled Reports | 3 | 0 | 1 | Phase 5 local scheduled-report logging is complete; production email delivery remains outside this pass |
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
| E8: Admin & Config | Admin Panel | 5 | 0 | 2 | Phase 6 admin release panel stories are complete; lower-priority backlog remains outside this pass |
| E8: Admin & Config | Audit & Compliance | 5 | 0 | 1 | Phase 6 compliance evidence stories are complete; destructive delete automation remains outside this pass |
| E8: Admin & Config | Cấu hình hệ thống | 1 | 0 | 8 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E8: Admin & Config | License | 2 | 0 | 2 | Phase 6 local license status evidence is complete; external licensing integration remains outside this pass |
| E8: Admin & Config | Maintenance | 3 | 0 | 1 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E8: Admin & Config | Phòng ban | 2 | 0 | 3 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E8: Admin & Config | Thông báo hệ thống | 1 | 0 | 4 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E9: Mobile & UX | Accessibility | 5 | 0 | 0 | Phase 5 accessibility hooks are complete for local UI acceptance |
| E9: Mobile & UX | Mobile | 4 | 0 | 3 | Phase 5 mobile shell stories are complete; lower-priority backlog remains outside this pass |
| E9: Mobile & UX | Performance | 2 | 0 | 1 | Phase 5 UI performance hooks are complete; load testing remains outside this pass |
| E9: Mobile & UX | UX | 15 | 0 | 7 | Phase 5 navigation and shell UX stories are complete; lower-priority UX backlog remains outside this pass |
| E9: Mobile & UX | i18n | 2 | 0 | 1 | Phase 5 VI/EN shell language toggle is complete; full product translation remains outside this pass |
| E10: Testing & QA | E2E Testing | 3 | 0 | 0 | MVP/release-covered |
| E10: Testing & QA | Integration Testing | 3 | 0 | 0 | MVP/release-covered |
| E10: Testing & QA | Monitoring | 5 | 0 | 0 | Phase 6 monitoring evidence is complete; production alert routing remains outside this pass |
| E10: Testing & QA | Performance Testing | 3 | 0 | 0 | Phase 6 local benchmark/performance evidence is complete; production load infrastructure remains outside this pass |
| E10: Testing & QA | Regression Testing | 1 | 0 | 0 | MVP/release-covered |
| E10: Testing & QA | Security Testing | 3 | 0 | 0 | Phase 6 security evidence is complete; external scan artifacts remain outside this pass |
| E10: Testing & QA | Test Coverage | 1 | 0 | 1 | Release-scoped partial stories are complete; not-started backlog remains outside this pass |
| E10: Testing & QA | Test Data | 2 | 0 | 0 | Phase 6 test-data inventory is complete |
| E10: Testing & QA | UAT | 4 | 0 | 1 | Phase 6 UAT evidence template wiring is complete; stakeholder signoff remains outside this pass |
| E10: Testing & QA | Unit Testing | 3 | 0 | 0 | MVP/release-covered |

## Completed Story IDs

- E1: Auth & User Mgmt: US001, US002, US004, US005, US049, US009, US010, US023, US028, US033, US048, US011, US026, US035, US047, US017, US044, US019, US022
- E2: Task Management: US050, US051, US058, US059, US060, US061, US062, US063, US064, US066, US096, US099, US101, US102, US115, US116, US068, US069, US070, US072, US074, US103, US075, US076, US077, US078, US081, US082, US083, US084, US086, US087, US089, US090
- E3: KPI Management: US117, US118, US119, US120, US121, US122, US125, US126, US127, US128, US129, US130, US131, US132, US134, US135, US136, US137, US138, US139, US140, US141, US142, US143, US144, US145, US146, US147, US148, US149, US150, US151, US152, US153, US157, US159, US165, US166, US168, US170, US171, US173, US174, US177
- E4: Bot & Notifications: US179, US180, US181, US182, US183, US186, US212, US189, US191, US192, US193, US196, US197, US198, US206, US209, US221, US237
- E5: Reporting & Analytics: US238, US239, US240, US241, US242, US268, US272, US277, US282, US286, US243, US244, US245, US246, US270, US279, US285, US248, US249, US283, US251, US252, US253, US255, US274, US256, US259, US262, US284, US288, US260, US261, US273
- E6: Project Management: US294, US295, US296, US326, US299, US300, US301, US302, US321, US338, US343, US304, US307, US308, US311, US312, US313, US314, US315, US327, US316, US317, US318, US334, US340, US341
- E7: Integration & Platform: US353, US354, US355, US356, US358, US359, US363, US369, US378, US381, US382, US389, US393
- E8: Admin & Config: US404, US405, US425, US431, US437, US406, US407, US408, US409, US410, US411, US426, US427, US412, US413, US428, US414, US415, US416, US429, US443, US417, US418, US419, US430, US420, US421, US422, US441, US423, US424
- E9: Mobile & UX: US444, US447, US451, US452, US453, US467, US475, US482, US456, US459, US445, US446, US478, US448, US450, US454, US463, US466, US469, US480, US481, US457, US458, US470, US479, US468, US460, US471
- E10: Testing & QA: US484, US485, US486, US487, US488, US489, US490, US491, US492, US493, US494, US507, US495, US496, US497, US512, US498, US499, US510, US500, US501, US502, US503, US504, US505, US509, US513, US506

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
- E3: KPI Management / Cấu hình KPI: US123, US124, US154, US155, US164, US176
- E3: KPI Management / Mục tiêu KPI: US158, US167, US178
- E3: KPI Management / Thông báo KPI: US162, US172
- E3: KPI Management / Tính điểm KPI: US133, US169
- E3: KPI Management / Xem KPI: US156, US161, US175
- E4: Bot & Notifications / Adaptive Cards: US190, US194, US195, US204, US207, US210, US213, US216, US219, US223, US226, US228, US230, US235
- E4: Bot & Notifications / Bot Commands: US184, US185, US187, US188, US201, US202, US203, US205, US208, US211, US215, US218, US220, US222, US225, US227, US229, US232, US233, US236
- E4: Bot & Notifications / Channel Notifications: US199, US200, US214, US217, US224, US231, US234
- E5: Reporting & Analytics / Analytics: US257, US258, US264, US266, US269, US271, US275, US278, US281, US290, US293
- E5: Reporting & Analytics / Biểu đồ: US254, US280, US287
- E5: Reporting & Analytics / Báo cáo: US247, US265, US276, US292
- E5: Reporting & Analytics / Dashboard: US263, US291
- E5: Reporting & Analytics / Export: US250, US267
- E5: Reporting & Analytics / Scheduled Reports: US289
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
- E8: Admin & Config / Admin Panel: US434, US440
- E8: Admin & Config / Audit & Compliance: US436
- E8: Admin & Config / Cấu hình hệ thống: US406, US407, US408, US410, US411, US426, US427, US435
- E8: Admin & Config / License: US433, US439
- E8: Admin & Config / Maintenance: US442
- E8: Admin & Config / Phòng ban: US418, US419, US438
- E8: Admin & Config / Thông báo hệ thống: US421, US422, US432, US441
- E9: Mobile & UX / Accessibility: (none)
- E9: Mobile & UX / Mobile: US462, US465, US472
- E9: Mobile & UX / Performance: US476
- E9: Mobile & UX / UX: US449, US455, US464, US473, US474, US477, US483
- E9: Mobile & UX / i18n: US461
- E10: Testing & QA / Monitoring: (none)
- E10: Testing & QA / Performance Testing: (none)
- E10: Testing & QA / Security Testing: (none)
- E10: Testing & QA / Test Coverage: US511
- E10: Testing & QA / Test Data: (none)
- E10: Testing & QA / UAT: US508

## Audit Detail

| Story ID | Epic | Feature | MoSCoW | Audit Status | Note |
| --- | --- | --- | --- | --- | --- |
| US001 | E1: Auth & User Mgmt | SSO Login | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US002 | E1: Auth & User Mgmt | SSO Login | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US003 | E1: Auth & User Mgmt | SSO Login | Must Have | Done | `GET /auth/security/status` provides privileged local-testable SSO/auth readiness evidence without exposing secrets; covered by `tests/test_auth_security_hardening.py`. |
| US004 | E1: Auth & User Mgmt | SSO Login | Must Have | Done | `AUTH_ALLOWED_EMAIL_DOMAINS` is enforced for password login and Teams/AAD sync; covered by `tests/test_auth_security_hardening.py`. |
| US005 | E1: Auth & User Mgmt | SSO Login | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US025 | E1: Auth & User Mgmt | SSO Login | Must Have | Done | Password login records safe audit evidence and `last_login_at` without exposing password hashes or raw credentials; covered by `tests/test_auth_security_hardening.py`. |
| US038 | E1: Auth & User Mgmt | SSO Login | Must Have | Done | Teams/AAD sync is domain-allowlist guarded and configuration-gated for real tenant validation; covered by `tests/test_auth_security_hardening.py`. |
| US045 | E1: Auth & User Mgmt | SSO Login | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US049 | E1: Auth & User Mgmt | SSO Login | Must Have | Done | Failed, blocked, and successful login attempts are recorded without passwords/tokens/raw IPs; covered by `tests/test_auth_security_hardening.py`. |
| US006 | E1: Auth & User Mgmt | Phân quyền | Must Have | Done | Custom roles can be created and assigned validated permissions via `POST /rbac/roles` and `PATCH /rbac/roles/{role_slug}`; covered by `tests/test_auth_rbac_department.py`. |
| US007 | E1: Auth & User Mgmt | Phân quyền | Must Have | Done | `GET /rbac/matrix` exposes the role-permission matrix for admin review; covered by `tests/test_auth_rbac_department.py`. |
| US008 | E1: Auth & User Mgmt | Phân quyền | Must Have | Done | RBAC mutation is restricted to `roles.manage`, staff/member access is rejected, and role updates are audit logged; covered by `tests/test_auth_rbac_department.py`. |
| US009 | E1: Auth & User Mgmt | Phân quyền | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US010 | E1: Auth & User Mgmt | Phân quyền | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US023 | E1: Auth & User Mgmt | Phân quyền | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US024 | E1: Auth & User Mgmt | Phân quyền | Must Have | Done | Non-system custom role records are persisted with validated permission keys and returned through existing role APIs; covered by `tests/test_auth_rbac_department.py`. |
| US027 | E1: Auth & User Mgmt | Phân quyền | Should Have | Done | Role-permission matrix export is available as CSV/XLSX with `roles.view` checks; covered by `tests/test_auth_rbac_department.py`. |
| US028 | E1: Auth & User Mgmt | Phân quyền | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US033 | E1: Auth & User Mgmt | Phân quyền | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US039 | E1: Auth & User Mgmt | Phân quyền | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US042 | E1: Auth & User Mgmt | Phân quyền | Should Have | Done | RBAC review/export includes custom roles and all permission keys for release audit evidence; covered by `tests/test_auth_rbac_department.py`. |
| US048 | E1: Auth & User Mgmt | Phân quyền | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US011 | E1: Auth & User Mgmt | Profile | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US012 | E1: Auth & User Mgmt | Profile | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US013 | E1: Auth & User Mgmt | Profile | Should Have | Done | `PATCH /users/me` lets users update safe profile fields only and records profile audit evidence; covered by `tests/test_auth_rbac_department.py`. |
| US014 | E1: Auth & User Mgmt | Profile | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US026 | E1: Auth & User Mgmt | Profile | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US035 | E1: Auth & User Mgmt | Profile | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US041 | E1: Auth & User Mgmt | Profile | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US047 | E1: Auth & User Mgmt | Profile | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US015 | E1: Auth & User Mgmt | Onboarding | Should Have | Done | User onboarding status/note fields are persisted on user creation through migration 14; covered by `tests/test_auth_rbac_department.py`. |
| US016 | E1: Auth & User Mgmt | Onboarding | Should Have | Done | Admin/HR users can invite users through `POST /users/{user_id}/invite`; covered by `tests/test_auth_rbac_department.py`. |
| US034 | E1: Auth & User Mgmt | Onboarding | Should Have | Done | Admin/HR users can update onboarding status while staff/member users are denied; covered by `tests/test_auth_rbac_department.py`. |
| US043 | E1: Auth & User Mgmt | Onboarding | Should Have | Done | Login/AAD sync activates invited or pending users with `activated_at` and `last_login_at` evidence; covered by `tests/test_auth_security_hardening.py`. |
| US017 | E1: Auth & User Mgmt | Notification Settings | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US018 | E1: Auth & User Mgmt | Notification Settings | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US029 | E1: Auth & User Mgmt | Notification Settings | Could Have | Partial | Partial: some workflow or scaffold evidence exists, but full UI, production integration, permission, test, or documentation acceptance remains incomplete. |
| US036 | E1: Auth & User Mgmt | Notification Settings | Should Have | Done | `/users/me/notification-settings` supports self-scoped notification preferences with validation and audit evidence; covered by `tests/test_auth_rbac_department.py`. |
| US044 | E1: Auth & User Mgmt | Notification Settings | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US019 | E1: Auth & User Mgmt | Audit | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US020 | E1: Auth & User Mgmt | Audit | Should Have | Done | Auth readiness checks, login attempts, onboarding, and notification preference changes write safe audit evidence; covered by Phase 1C/1D tests. |
| US030 | E1: Auth & User Mgmt | Audit | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US040 | E1: Auth & User Mgmt | Audit | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US021 | E1: Auth & User Mgmt | Auth & Security | Should Have | Done | `GET /auth/security/status` is restricted to privileged `OPS_VIEW` users; staff/member users are blocked. |
| US022 | E1: Auth & User Mgmt | Auth & Security | Must Have | Done | DB-backed `auth_login_attempts` lockout blocks repeated failures by email/IP hash; covered by `tests/test_auth_security_hardening.py`. |
| US031 | E1: Auth & User Mgmt | Auth & Security | Must Have | Done | Invalid bearer tokens do not fall back to `X-User-Id` when JWT validation is required; covered by `tests/test_auth_security_hardening.py`. |
| US032 | E1: Auth & User Mgmt | Auth & Security | Must Have | Done | Production auth readiness reports unsafe JWT/header/domain/secret settings as failing status without exposing secret values. |
| US037 | E1: Auth & User Mgmt | Auth & Security | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US046 | E1: Auth & User Mgmt | Auth & Security | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US050 | E2: Task Management | Tạo Task | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US051 | E2: Task Management | Tạo Task | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US052 | E2: Task Management | Tạo Task | Must Have | Done | Priority levels (Urgent/High/Medium/Low) selectable on task creation and displayed as colored badges on Kanban cards & List view; covered by `tests/test_task_metadata.py`. |
| US053 | E2: Task Management | Tạo Task | Should Have | Done | Manual task creation is available in API and Kanban UI with `taskCreate` permission mapping, validation, audit log, and focused Phase 2 tests. |
| US054 | E2: Task Management | Tạo Task | Must Have | Done | Task Checklist items can be created, deleted, and interactive toggled via `PATCH /tasks/{id}/metadata` with live completion progress (X/Y) on card/list; covered by `tests/test_task_metadata.py`. |
| US055 | E2: Task Management | Tạo Task | Should Have | Done | Custom labels can be added/deleted/rendered on task cards and filtered dynamically in the Kanban board. Save endpoint `/tasks/{id}/metadata` is tested in `tests/test_task_metadata.py`. |
| US056 | E2: Task Management | Tạo Task | Should Have | Done | Subtasks checklist can be managed interactively with markdown format (`[ ]` / `[x]`) and progress is displayed on task cards. Tested in `tests/test_task_metadata.py`. |
| US057 | E2: Task Management | Tạo Task | Should Have | Done | Task duplication is supported via `POST /tasks/{id}/duplicate` button, restricted to admin and manager roles. Tested in `tests/test_task_metadata.py`. |
| US091 | E2: Task Management | Tạo Task | Should Have | Done | Task creation persists assignment, project/sprint, deadline, priority, checklist, difficulty/story points, and audit evidence; covered by `tests/test_api_flow.py`. |
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
| US073 | E2: Task Management | Chi tiết Task | Should Have | Done | Task detail API/drawer exposes names, due state, comments, activity logs, AI detail, metadata controls, and permitted actions; covered by `tests/test_task_detail.py`. |
| US074 | E2: Task Management | Chi tiết Task | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US093 | E2: Task Management | Chi tiết Task | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US097 | E2: Task Management | Chi tiết Task | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US103 | E2: Task Management | Chi tiết Task | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US106 | E2: Task Management | Chi tiết Task | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US110 | E2: Task Management | Chi tiết Task | Should Have | Done | Staff/member task detail and comments are scoped to assigned tasks while privileged users retain review access; covered by `tests/test_task_detail.py`. |
| US114 | E2: Task Management | Chi tiết Task | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US075 | E2: Task Management | Deadline | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US076 | E2: Task Management | Deadline | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US077 | E2: Task Management | Deadline | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US078 | E2: Task Management | Deadline | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US079 | E2: Task Management | Deadline | Should Have | Done | Manager can extend task deadline with a mandatory reason, logs timeline activity, and notifies assignee; covered by `tests/test_task_deadline_extension.py`. |
| US094 | E2: Task Management | Deadline | Should Have | Done | Manager/admin deadline extension requires a later deadline and reason, writes activity evidence, notifies assignee, and is exposed in permitted task detail UI. |
| US107 | E2: Task Management | Deadline | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US080 | E2: Task Management | Tìm kiếm & Lọc | Should Have | Done | Task search/filter supports project, sprint, assignee, status, overdue, keyword, deadline range, and Kanban/timeline UI filter state; covered by `tests/test_task_filters.py`. |
| US081 | E2: Task Management | Tìm kiếm & Lọc | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US082 | E2: Task Management | Tìm kiếm & Lọc | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US098 | E2: Task Management | Tìm kiếm & Lọc | Should Have | Done | Staff/member search remains self-scoped even when another assignee filter is requested; covered by `tests/test_task_filters.py`. |
| US113 | E2: Task Management | Tìm kiếm & Lọc | Should Have | Done | Invalid task filters return safe validation errors and UI empty/error states are present in Kanban list/board views. |
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
| US121 | E3: KPI Management | Cấu hình KPI | Should Have | Done | KPI config read/update is permissioned, requires a change reason, writes audit evidence, and keeps default formula compatibility; covered by `tests/test_kpi_phase3.py`. |
| US122 | E3: KPI Management | Cấu hình KPI | Should Have | Done | KPI policy validation requires the full difficulty multiplier shape and valid fallback difficulty while staff/member users are denied mutation; covered by `tests/test_kpi_phase3.py`. |
| US123 | E3: KPI Management | Cấu hình KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US124 | E3: KPI Management | Cấu hình KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US154 | E3: KPI Management | Cấu hình KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US155 | E3: KPI Management | Cấu hình KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US164 | E3: KPI Management | Cấu hình KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US171 | E3: KPI Management | Cấu hình KPI | Should Have | Done | Persisted KPI policy retrieval/update uses the tested policy model and preserves `DEFAULT_KPI_POLICY`; covered by `tests/test_kpi.py` and `tests/test_kpi_phase3.py`. |
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
| US159 | E3: KPI Management | Tính điểm KPI | Must Have | Done | KPI transaction rebuild is idempotent and stores active/reversed ledger events for task outcomes; covered by `tests/test_kpi_phase3.py`. |
| US165 | E3: KPI Management | Tính điểm KPI | Must Have | Done | Manual adjustments require reason/audit evidence and HR/admin approval before score impact; covered by `tests/test_kpi_phase3.py`. |
| US169 | E3: KPI Management | Tính điểm KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US174 | E3: KPI Management | Tính điểm KPI | Must Have | Done | Monthly KPI aggregation uses active task and approved-adjustment ledger transactions, not untracked score mutation; covered by `tests/test_kpi_phase3.py`. |
| US177 | E3: KPI Management | Tính điểm KPI | Must Have | Done | Changed task outcomes reverse stale KPI ledger rows and preserve recalculation evidence; covered by `tests/test_kpi_phase3.py`. |
| US134 | E3: KPI Management | Xem KPI | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US135 | E3: KPI Management | Xem KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US136 | E3: KPI Management | Xem KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US137 | E3: KPI Management | Xem KPI | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US138 | E3: KPI Management | Xem KPI | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US139 | E3: KPI Management | Xem KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US140 | E3: KPI Management | Xem KPI | Must Have | Done | `/kpi/monthly` returns ledger-backed monthly KPI rows with member self-scope and target progress fields; covered by `tests/test_kpi_phase3.py`. |
| US156 | E3: KPI Management | Xem KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US157 | E3: KPI Management | Xem KPI | Should Have | Done | KPI history, team summary, and department breakdown endpoints provide release-testable KPI view workflows; covered by `tests/test_kpi_phase3.py`. |
| US161 | E3: KPI Management | Xem KPI | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US166 | E3: KPI Management | Xem KPI | Should Have | Done | Staff/member KPI and report access is scoped/permissioned while privileged exports remain available; covered by `tests/test_kpi_phase3.py` and `tests/test_api_flow.py`. |
| US170 | E3: KPI Management | Xem KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US175 | E3: KPI Management | Xem KPI | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US141 | E3: KPI Management | Mục tiêu KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US142 | E3: KPI Management | Mục tiêu KPI | Should Have | Done | KPI target create/list/progress workflow supports user-month targets and computes progress/gap; covered by `tests/test_kpi_phase3.py`. |
| US143 | E3: KPI Management | Mục tiêu KPI | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US144 | E3: KPI Management | Mục tiêu KPI | Should Have | Done | KPI target updates preserve omitted fields and recalculate progress without changing score formula defaults; covered by `tests/test_kpi_phase3.py`. |
| US145 | E3: KPI Management | Mục tiêu KPI | Should Have | Done | KPI target CSV/XLSX import validates user/month/target fields, upserts rows, and records audit evidence; covered by `tests/test_kpi_phase3.py`. |
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
| US151 | E3: KPI Management | Thông báo KPI | Should Have | Done | KPI target warning runner creates notifications for users below target after ledger rebuild; covered by `tests/test_kpi_phase3.py`. |
| US152 | E3: KPI Management | Thông báo KPI | Should Have | Done | KPI warning notifications deduplicate within the daily run window; covered by `tests/test_kpi_phase3.py`. |
| US153 | E3: KPI Management | Thông báo KPI | Should Have | Done | KPI warning generation is role-gated, audited, and local-only without external delivery side effects; covered by `tests/test_kpi_phase3.py`. |
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
| US192 | E4: Bot & Notifications | Adaptive Cards | Must Have | Done | Done for Teams-ready simulation: deadline/overdue warning card preview is available through simulator card builders and queue payloads; no real Graph/Teams outbound claim. |
| US193 | E4: Bot & Notifications | Adaptive Cards | Must Have | Done | Done for Teams-ready simulation: Complete, Extend, and Comment card actions are validated and handled through the simulator action API; no production Teams tenant claim. |
| US194 | E4: Bot & Notifications | Adaptive Cards | Must Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US195 | E4: Bot & Notifications | Adaptive Cards | Should Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US196 | E4: Bot & Notifications | Adaptive Cards | Must Have | Done | Done for Teams-ready simulation: the static UI renders a Teams-like Adaptive Card preview on `/admin/integrations/teams-simulator`. |
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
| US241 | E5: Reporting & Analytics | Dashboard | Should Have | Done | Done: `/reports/dashboard/insights` exposes local dashboard cards, alerts, analytics summary, KPI preview, chart/export metadata, and stable UI state fields; covered by `tests/test_reports_analytics.py`. |
| US242 | E5: Reporting & Analytics | Dashboard | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US263 | E5: Reporting & Analytics | Dashboard | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US268 | E5: Reporting & Analytics | Dashboard | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US272 | E5: Reporting & Analytics | Dashboard | Must Have | Done | Done: dashboard insights are role-scoped so staff/member users see personal scope while privileged report roles see broader local reporting scope; covered by `tests/test_reports_analytics.py`. |
| US277 | E5: Reporting & Analytics | Dashboard | Should Have | Done | Done: dashboard insights return stable empty/loading/error state metadata and empty-month analytics without client-side crashes; covered by `tests/test_reports_analytics.py`. |
| US282 | E5: Reporting & Analytics | Dashboard | Must Have | Done | Done: dashboard insights combine analytics, KPI rows, schedule count, alerts, and export links for local reporting workflows; covered by `tests/test_reports_analytics.py`. |
| US286 | E5: Reporting & Analytics | Dashboard | Should Have | Done | Done: dashboard insights provide permission-aware export links only for users with report export permission; covered by `tests/test_reports_analytics.py`. |
| US291 | E5: Reporting & Analytics | Dashboard | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US243 | E5: Reporting & Analytics | Báo cáo | Must Have | Done | Done: local report endpoints expose KPI/report data behind current report permissions; covered by `tests/test_reports_analytics.py`. |
| US244 | E5: Reporting & Analytics | Báo cáo | Must Have | Done | Done: analytics/report endpoints return month-scoped local reporting payloads for Reports UI and exports; covered by `tests/test_reports_analytics.py`. |
| US245 | E5: Reporting & Analytics | Báo cáo | Should Have | Done | Done: report export workflows cover analytics/report data in local JSON/CSV/XLSX/PDF-compatible paths; covered by `tests/test_reports_analytics.py`. |
| US246 | E5: Reporting & Analytics | Báo cáo | Should Have | Done | Done: report access remains permission-protected, and member/staff users are blocked from privileged report/export surfaces; covered by `tests/test_reports_analytics.py`. |
| US247 | E5: Reporting & Analytics | Báo cáo | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US265 | E5: Reporting & Analytics | Báo cáo | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US270 | E5: Reporting & Analytics | Báo cáo | Should Have | Done | Done: local report data supports progress/portfolio-style summaries through existing analytics and dashboard insights payloads; covered by `tests/test_reports_analytics.py`. |
| US276 | E5: Reporting & Analytics | Báo cáo | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US279 | E5: Reporting & Analytics | Báo cáo | Should Have | Done | Done: local reports expose reusable analytics datasets and export paths for team reporting without external BI integration; covered by `tests/test_reports_analytics.py`. |
| US285 | E5: Reporting & Analytics | Báo cáo | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US292 | E5: Reporting & Analytics | Báo cáo | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US248 | E5: Reporting & Analytics | Export | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US249 | E5: Reporting & Analytics | Export | Should Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US250 | E5: Reporting & Analytics | Export | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US267 | E5: Reporting & Analytics | Export | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US283 | E5: Reporting & Analytics | Export | Must Have | Done | Done: dashboard insights expose permission-aware export links and analytics exports remain covered by focused tests; covered by `tests/test_reports_analytics.py`. |
| US251 | E5: Reporting & Analytics | Biểu đồ | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US252 | E5: Reporting & Analytics | Biểu đồ | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US253 | E5: Reporting & Analytics | Biểu đồ | Should Have | Done | Done: dashboard insights provide chart catalog data for task status, workload, velocity, project effort, and dependency summary; covered by `tests/test_reports_analytics.py`. |
| US254 | E5: Reporting & Analytics | Biểu đồ | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US255 | E5: Reporting & Analytics | Biểu đồ | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US274 | E5: Reporting & Analytics | Biểu đồ | Should Have | Done | Done: chart catalog datasets are generated from the same local analytics payload and tested for stable API shape; covered by `tests/test_reports_analytics.py`. |
| US280 | E5: Reporting & Analytics | Biểu đồ | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US287 | E5: Reporting & Analytics | Biểu đồ | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US256 | E5: Reporting & Analytics | Analytics | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US257 | E5: Reporting & Analytics | Analytics | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US258 | E5: Reporting & Analytics | Analytics | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US259 | E5: Reporting & Analytics | Analytics | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US262 | E5: Reporting & Analytics | Analytics | Should Have | Done | Done: analytics summary includes completion, workload, backlog, cycle-time, utilization, velocity, project effort, and dependency metrics; covered by `tests/test_reports_analytics.py`. |
| US264 | E5: Reporting & Analytics | Analytics | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US266 | E5: Reporting & Analytics | Analytics | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US269 | E5: Reporting & Analytics | Analytics | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US271 | E5: Reporting & Analytics | Analytics | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US275 | E5: Reporting & Analytics | Analytics | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US278 | E5: Reporting & Analytics | Analytics | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US281 | E5: Reporting & Analytics | Analytics | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US284 | E5: Reporting & Analytics | Analytics | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US288 | E5: Reporting & Analytics | Analytics | Should Have | Done | Done: dashboard insights surface analytics metrics with role scope and empty-month stability for local review; covered by `tests/test_reports_analytics.py`. |
| US290 | E5: Reporting & Analytics | Analytics | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US293 | E5: Reporting & Analytics | Analytics | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US260 | E5: Reporting & Analytics | Scheduled Reports | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US261 | E5: Reporting & Analytics | Scheduled Reports | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US273 | E5: Reporting & Analytics | Scheduled Reports | Should Have | Done | Done: scheduled reports support create/list/manual run/run-due delivery-log workflows locally; production email delivery remains deferred; covered by `tests/test_reports_analytics.py`. |
| US289 | E5: Reporting & Analytics | Scheduled Reports | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US294 | E6: Project Management | Tạo Project | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US295 | E6: Project Management | Tạo Project | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US296 | E6: Project Management | Tạo Project | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US297 | E6: Project Management | Tạo Project | Should Have | Done | Project creation is available through `POST /projects` and the Projects drawer; manager-created projects default ownership to the creator when no manager is supplied. |
| US298 | E6: Project Management | Tạo Project | Should Have | Done | Project creation validates status/department/manager references, requires `projects.manage`, writes project audit evidence, and refreshes the project UI. |
| US320 | E6: Project Management | Tạo Project | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US326 | E6: Project Management | Tạo Project | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US333 | E6: Project Management | Tạo Project | Must Have | Done | Project detail UI exposes progress, members, sprints, and backlog evidence; project/sprint/member mutations preserve project-scope checks. |
| US337 | E6: Project Management | Tạo Project | Must Have | Done | Outside managers cannot mutate another manager's project membership or sprint plan; admin/owner manager workflows remain allowed. |
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
| US305 | E6: Project Management | Backlog | Should Have | Done | Project backlog lists unsprinted project tasks with staff self-scope preserved and task detail links available from project detail UI. |
| US306 | E6: Project Management | Backlog | Should Have | Done | Backlog move-to-sprint validates same-project sprint/task membership, moves backlog tasks, writes audit evidence, and is exposed from project detail UI. |
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
| US431 | E8: Admin & Config | Admin Panel | Must Have | Done | Done: admin release panel summarizes available admin, config, license, compliance, maintenance, QA, and release-gate surfaces. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US434 | E8: Admin & Config | Admin Panel | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US437 | E8: Admin & Config | Admin Panel | Should Have | Done | Done: admin release panel summarizes available admin, config, license, compliance, maintenance, QA, and release-gate surfaces. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US440 | E8: Admin & Config | Admin Panel | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US406 | E8: Admin & Config | Cấu hình hệ thống | Must Have | Done | Done: system config overview exposes safe settings, redacts secrets, and records local change policy. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US407 | E8: Admin & Config | Cấu hình hệ thống | Must Have | Done | Done: system config overview exposes safe settings, redacts secrets, and records local change policy. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US408 | E8: Admin & Config | Cấu hình hệ thống | Should Have | Done | Done: system config overview exposes safe settings, redacts secrets, and records local change policy. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US409 | E8: Admin & Config | Cấu hình hệ thống | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US410 | E8: Admin & Config | Cấu hình hệ thống | Should Have | Done | Done: system config overview exposes auth/Teams/AI configuration categories without leaking secret values. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US411 | E8: Admin & Config | Cấu hình hệ thống | Should Have | Done | Done: system config overview exposes auth/Teams/AI configuration categories without leaking secret values. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US426 | E8: Admin & Config | Cấu hình hệ thống | Must Have | Done | Done: system config overview exposes safe settings, redacts secrets, and records local change policy. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US427 | E8: Admin & Config | Cấu hình hệ thống | Must Have | Done | Done: system config overview exposes safe settings, redacts secrets, and records local change policy. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US435 | E8: Admin & Config | Cấu hình hệ thống | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US412 | E8: Admin & Config | Maintenance | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US413 | E8: Admin & Config | Maintenance | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US428 | E8: Admin & Config | Maintenance | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US442 | E8: Admin & Config | Maintenance | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US414 | E8: Admin & Config | Audit & Compliance | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US415 | E8: Admin & Config | Audit & Compliance | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US416 | E8: Admin & Config | Audit & Compliance | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US429 | E8: Admin & Config | Audit & Compliance | Must Have | Done | Done: compliance evidence summarizes request backlog, lineage domains, export endpoint, and manual-review no-hard-delete policy. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US436 | E8: Admin & Config | Audit & Compliance | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US443 | E8: Admin & Config | Audit & Compliance | Should Have | Done | Done: compliance evidence summarizes request backlog, lineage domains, export endpoint, and manual-review no-hard-delete policy. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US417 | E8: Admin & Config | Phòng ban | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US418 | E8: Admin & Config | Phòng ban | Must Have | Done | Done: department ops evidence summarizes active/inactive departments, manager assignment, and user distribution behind admin/HR permissions. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US419 | E8: Admin & Config | Phòng ban | Should Have | Done | Done: department ops evidence summarizes active/inactive departments, manager assignment, and user distribution behind admin/HR permissions. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US430 | E8: Admin & Config | Phòng ban | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US438 | E8: Admin & Config | Phòng ban | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US420 | E8: Admin & Config | Thông báo hệ thống | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US421 | E8: Admin & Config | Thông báo hệ thống | Must Have | Done | Done: system notification broadcast and evidence endpoints support privileged release/admin communication review. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US422 | E8: Admin & Config | Thông báo hệ thống | Should Have | Done | Done: system notification broadcast and evidence endpoints support privileged release/admin communication review. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US432 | E8: Admin & Config | Thông báo hệ thống | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US441 | E8: Admin & Config | Thông báo hệ thống | Should Have | Done | Done: system notification broadcast and evidence endpoints support privileged release/admin communication review. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US423 | E8: Admin & Config | License | Should Have | Done | Done: license status endpoint reports local demo license mode, active users, usage counts, and external integration deferral. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US424 | E8: Admin & Config | License | Must Have | Done | Done: license status endpoint reports local demo license mode, active users, usage counts, and external integration deferral. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US433 | E8: Admin & Config | License | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US439 | E8: Admin & Config | License | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US444 | E9: Mobile & UX | Mobile | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US445 | E9: Mobile & UX | Mobile | Should Have | Done | Done: mobile shell has role-aware bottom navigation, responsive off-canvas sidebar, and no horizontal overflow in a 390px Playwright viewport; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US446 | E9: Mobile & UX | Mobile | Must Have | Done | Done: mobile shell has role-aware bottom navigation, responsive off-canvas sidebar, and no horizontal overflow in a 390px Playwright viewport; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US462 | E9: Mobile & UX | Mobile | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US465 | E9: Mobile & UX | Mobile | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US472 | E9: Mobile & UX | Mobile | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US478 | E9: Mobile & UX | Mobile | Should Have | Done | Done: mobile shell has role-aware bottom navigation, responsive off-canvas sidebar, and no horizontal overflow in a 390px Playwright viewport; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US447 | E9: Mobile & UX | UX | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US448 | E9: Mobile & UX | UX | Should Have | Done | Done: navigation UX keeps active/aria-current state, stable page title, skip-to-content flow, and keyboard sidebar controls; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US449 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US450 | E9: Mobile & UX | UX | Must Have | Done | Done: navigation UX keeps active/aria-current state, stable page title, skip-to-content flow, and keyboard sidebar controls; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US451 | E9: Mobile & UX | UX | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US452 | E9: Mobile & UX | UX | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US453 | E9: Mobile & UX | UX | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US454 | E9: Mobile & UX | UX | Must Have | Done | Done: navigation UX keeps active/aria-current state, stable page title, skip-to-content flow, and keyboard sidebar controls; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US455 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US463 | E9: Mobile & UX | UX | Must Have | Done | Done: navigation UX keeps active/aria-current state, stable page title, skip-to-content flow, and keyboard sidebar controls; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US464 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US466 | E9: Mobile & UX | UX | Must Have | Done | Done: navigation UX keeps active/aria-current state, stable page title, skip-to-content flow, and keyboard sidebar controls; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US467 | E9: Mobile & UX | UX | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US469 | E9: Mobile & UX | UX | Should Have | Done | Done: navigation UX keeps active/aria-current state, stable page title, skip-to-content flow, and keyboard sidebar controls; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US473 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US474 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US475 | E9: Mobile & UX | UX | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US477 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US480 | E9: Mobile & UX | UX | Must Have | Done | Done: navigation UX keeps active/aria-current state, stable page title, skip-to-content flow, and keyboard sidebar controls; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US481 | E9: Mobile & UX | UX | Should Have | Done | Done: navigation UX keeps active/aria-current state, stable page title, skip-to-content flow, and keyboard sidebar controls; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US482 | E9: Mobile & UX | UX | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US483 | E9: Mobile & UX | UX | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US456 | E9: Mobile & UX | Accessibility | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US457 | E9: Mobile & UX | Accessibility | Must Have | Done | Done: accessibility hooks include skip link, focus-visible outline, aria-current navigation state, labeled mobile nav, and reduced-motion CSS; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US458 | E9: Mobile & UX | Accessibility | Must Have | Done | Done: accessibility hooks include skip link, focus-visible outline, aria-current navigation state, labeled mobile nav, and reduced-motion CSS; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US470 | E9: Mobile & UX | Accessibility | Should Have | Done | Done: accessibility hooks include skip link, focus-visible outline, aria-current navigation state, labeled mobile nav, and reduced-motion CSS; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US479 | E9: Mobile & UX | Accessibility | Should Have | Done | Done: accessibility hooks include skip link, focus-visible outline, aria-current navigation state, labeled mobile nav, and reduced-motion CSS; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US459 | E9: Mobile & UX | Performance | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US468 | E9: Mobile & UX | Performance | Must Have | Done | Done: UI performance pass uses CSS-only responsive layout, lightweight mobile-nav rendering, reduced-motion support, and navigation performance marks; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US476 | E9: Mobile & UX | Performance | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US460 | E9: Mobile & UX | i18n | Must Have | Done | Done: shell navigation/topbar supports persisted VI/EN toggle and updates `document.documentElement.lang`; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
| US461 | E9: Mobile & UX | i18n | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US471 | E9: Mobile & UX | i18n | Must Have | Done | Done: shell navigation/topbar supports persisted VI/EN toggle and updates `document.documentElement.lang`; covered by `tests/test_phase5_mobile_ux_static.py`; Playwright mobile scenario is defined in `tests/test_ui_role_navigation_playwright.py`. |
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
| US494 | E10: Testing & QA | Performance Testing | Should Have | Done | Done: QA release evidence documents local synthetic performance smoke through benchmark command and release-gate journeys. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US507 | E10: Testing & QA | Performance Testing | Should Have | Done | Done: QA release evidence documents local synthetic performance smoke through benchmark command and release-gate journeys. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US495 | E10: Testing & QA | UAT | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US496 | E10: Testing & QA | UAT | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US497 | E10: Testing & QA | UAT | Must Have | Done | Done: QA release evidence links the UAT template and marks stakeholder signoff as a tracked release evidence item. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US508 | E10: Testing & QA | UAT | Could Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
| US512 | E10: Testing & QA | UAT | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US498 | E10: Testing & QA | Security Testing | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US499 | E10: Testing & QA | Security Testing | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US510 | E10: Testing & QA | Security Testing | Must Have | Done | Done: QA release evidence records security-header, login-lockout, audit-export, redaction, and production-auth safety checks. Covered by `tests/test_phase6_admin_compliance_maintenance.py; tests/test_auth_security_hardening.py`. |
| US500 | E10: Testing & QA | Regression Testing | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US501 | E10: Testing & QA | Test Data | Must Have | Done | Done: current MVP behavior has direct code/API/UI and test evidence per audit baseline. |
| US502 | E10: Testing & QA | Test Data | Must Have | Done | Done: QA test-data inventory reports seeded/test bootstrap counts, seed/reset policy, and demo account documentation. Covered by `tests/test_phase6_admin_compliance_maintenance.py`. |
| US503 | E10: Testing & QA | Monitoring | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US504 | E10: Testing & QA | Monitoring | Must Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US505 | E10: Testing & QA | Monitoring | Must Have | Done | Done for Teams-ready simulation: `/integrations/teams/health` and the simulator dashboard expose mode, real Graph disabled state, and queue counts. |
| US509 | E10: Testing & QA | Monitoring | Should Have | Done | Done: QA release evidence and release gate expose monitoring health/readiness/metrics/release-gate endpoints and queue counts. Covered by `tests/test_phase6_admin_compliance_maintenance.py; tests/test_ops_dashboard.py`. |
| US513 | E10: Testing & QA | Monitoring | Should Have | Done | Done: QA release evidence and release gate expose monitoring health/readiness/metrics/release-gate endpoints and queue counts. Covered by `tests/test_phase6_admin_compliance_maintenance.py; tests/test_ops_dashboard.py`. |
| US506 | E10: Testing & QA | Test Coverage | Should Have | Done | Done: local-testable release acceptance evidence is covered by `/monitoring/release-acceptance`; external tenant/load/WCAG/UAT dependencies are recorded as approved deferrals where applicable. |
| US511 | E10: Testing & QA | Test Coverage | Won't Have | Not started | Not started: no direct code/API/UI/test evidence found in the current audit. |
