# TeamsWork Phase + Slice Implementation Prompts

Generated: 2026-05-30

Use these prompts with `docs/USER_STORY_RELEASE_ROADMAP.md` and `docs/USER_STORY_COMPLETION_AUDIT.md`. Each implementation session should choose story IDs, deliver one small vertical slice, run focused tests, and update audit evidence.

## Universal Prompt

```text
You are Codex working in the TeamsWork repo at d:\QLDA. Implement one small vertical slice from the release roadmap. Do not broaden scope.

Read first:
- AGENTS.md
- docs/USER_STORY_RELEASE_ROADMAP.md
- docs/USER_STORY_COMPLETION_AUDIT.md
- The relevant router, schema, repository, service, UI, and test files for this slice

Constraints:
- Do not change KPI formulas unless this phase explicitly requires a tested configurable KPI policy.
- Do not weaken RBAC. Preserve admin, manager, staff, and HR boundaries.
- Do not rely on dev header fallback for production auth.
- Do not log secrets, bearer tokens, provider raw errors, or sensitive external payloads.
- Do not add a dependency unless the slice requires it and the tradeoff is documented.
- Do not mark a story Done for scaffold-only, untested UI-only, or dev-bypass-only behavior.

Workflow:
1. List the selected story IDs before coding.
2. State the smallest slice to implement in this session.
3. Add or update focused tests before or alongside the implementation.
4. Implement through the existing backend, UI, RBAC, repository, and docs patterns.
5. Run focused tests, then run pytest -q when shared behavior changed.
6. Update docs/USER_STORY_COMPLETION_AUDIT.md with status, owner module, implementation evidence, test evidence, and release note.
7. Report the main diff, tests run, and remaining risks.
```

## Phase Prompts

### Phase 0 - Traceability Foundation

```text
Implement Phase 0: Traceability Foundation.

Goal: make the backlog measurable before more feature work starts. Do not change product behavior.

Scope:
- Treat docs/USER_STORY_COMPLETION_AUDIT.md as the source of truth.
- Make Done, Partial, and Not started semantics explicit and strict.
- Ensure every story has the required evidence fields: owner module, implementation evidence, test evidence, and release note.
- Keep docs/USER_STORY_RELEASE_ROADMAP.md aligned with the audit where traceability is missing.

Test/check:
- Runtime tests are not required for docs-only changes.
- Manually check consistency between the roadmap and audit.
```

### Phase 1 - Production Foundation, Auth, RBAC, Security

```text
Implement one small Phase 1 slice for Auth/RBAC/Security.

Priority for the first slice:
- Select E1/E7/E8/E10 stories related to production auth or RBAC.
- Strengthen one production path: JWT/AAD validation, failed-login audit, session/logout, security headers/rate limits, or permission matrix.
- Keep local/dev fallback available only under safe settings already enforced by configuration.

Read first:
- app/main.py
- app/auth.py and auth router/security settings
- app/schemas.py
- app/repository.py
- Existing auth/RBAC/security tests

Tests:
- pytest tests/test_auth_rbac_department.py tests/test_role_module_rbac_matrix.py tests/test_maintenance_hardening.py -q
- Add focused SSO/AAD mock, failed-login audit, security header/rate-limit, or audit export tests when touching those paths.
```

### Phase 2 - Core Task, Kanban, Deadline, Backlog

```text
Implement one small Phase 2 slice for Task/Sprint/Backlog/Kanban.

Priority after the existing Slice 1:
- Select E2/E6 stories still Partial or Not started.
- Deliver one vertical slice with API, repository/data changes, RBAC, tests, and audit evidence.
- Good candidates: saved filters, WIP limits, deadline extension workflow, Excel import/export, UI Kanban enhancement, or attachment validation/storage.

Read first:
- Task, sprint, and project routers
- app/schemas.py
- app/repository.py
- Task filter/detail, bulk/backlog, sprint workload, and API flow tests

Tests:
- pytest tests/test_task_metadata.py tests/test_task_bulk_backlog.py tests/test_task_filters.py tests/test_task_detail.py tests/test_sprint_workload_warnings.py tests/test_api_flow.py -q
- If UI changes, run the relevant Playwright role/navigation smoke checks.
```

### Phase 3 - KPI Configuration, Targets, Transactions

```text
Implement one small Phase 3 slice for KPI.

Scope:
- Preserve the current default KPI policy: easy=1.0, medium=1.5, hard=2.0, on-time +10, late +5, unfinished overdue in KPI month -5.
- Add one tested capability: KPI config compatibility, transaction ledger idempotency, reopen/delete rollback, manual adjustment approval, KPI targets, or KPI export/report.
- Do not allow AI or user input to create score changes without stored reason and audit evidence.

Read first:
- app/kpi.py
- KPI router/schema/repository paths
- docs/KPI_VALIDATION_RULES.md
- tests/test_kpi.py

Tests:
- pytest tests/test_kpi.py tests/test_api_flow.py -q
- Add focused tests for the selected capability: config defaults, idempotency, rollback, approval, target progress, or report export.
```

### Phase 4 - Microsoft Teams, Bot, Adaptive Cards

```text
Implement one small Phase 4 slice for Teams/Bot/Notifications.

Scope:
- Keep real Teams/Graph calls disabled by default unless configured through environment variables.
- Treat every callback, bot command, and adaptive card action as a trust boundary.
- Validate action payloads before any database write.
- Choose one slice: bot command, adaptive card action, Graph mock posting, retry/dedup notification, or Teams permission boundary.

Read first:
- Teams router/service files
- Notification queue/retry code
- Auth/RBAC helpers
- tests/test_teams_mvp.py
- tests/test_notifications.py

Tests:
- pytest tests/test_teams_mvp.py tests/test_notifications.py -q
- Add Graph mock, card payload validation, bot command, retry/dedup, or Teams permission tests for the selected slice.
```

### Phase 5 - Reporting, Analytics, Dashboards, UX

```text
Implement one small Phase 5 slice for Reports/Dashboard/UX.

Scope:
- Select one report, dashboard, or analytics capability with a clear permission boundary.
- Keep UI compact, role-aware, responsive, and free of overlapping text.
- Ensure exports return correct content type, filename, data source, and RBAC behavior.
- Keep scheduled email/report delivery environment-configured.

Read first:
- Report and dashboard routers/services
- Static UI shell
- Existing export, API flow, and role navigation tests

Tests:
- pytest tests/test_api_flow.py tests/test_ui_role_navigation_playwright.py tests/test_ui_full_button_audit_playwright.py -q
- Add analytics endpoint, scheduled-report, responsive/a11y, or role-dashboard visibility tests for the selected slice.
```

### Phase 6 - Admin, Compliance, Operations, QA Release Gate

```text
Implement one small Phase 6 slice for Admin/Compliance/Ops/QA.

Scope:
- Select one capability: admin global search, recent admin activity, maintenance scheduling, backup/config retention, feature flags, system notifications, GDPR/PDPA export/delete, monitoring metrics, benchmark smoke, or UAT evidence.
- Do not create a live external integration unless configuration and mock tests are already in place.
- Update release checklist and traceability evidence when behavior or release status changes.

Read first:
- Admin, maintenance, compliance, and monitoring routers/services
- Release docs and audit file
- Existing admin/compliance/monitoring/security tests

Tests:
- pytest -q when touching shared behavior or release-gate logic
- Add focused admin, compliance, monitoring, benchmark smoke, security, or documentation checks for the selected slice.
```

## Slice Planning Prompt

```text
Break Phase <N> into 3-5 sequential implementation slices.

Input:
- Phase: <paste the phase section from docs/USER_STORY_RELEASE_ROADMAP.md>
- Audit source: docs/USER_STORY_COMPLETION_AUDIT.md
- Priority: Must Have first, Should Have second
- Each slice must be a vertical slice small enough for one implementation session

Output:
- Slice name
- Story IDs
- User-visible behavior
- Backend/data/UI/docs to touch
- Focused tests to add/run
- Audit evidence to update
- Non-goals
- RBAC/security/KPI/Teams risks, if any

Do not implement code in this step. Produce only a decision-complete slice plan.
```

## Defaults

- "Price" is interpreted as "piece/slice".
- Use the Phase + Slice flow: a phase prompt sets direction, then slice prompts keep each implementation session small.
- Do not implement a full phase in one session unless it is Phase 0 docs-only work.
