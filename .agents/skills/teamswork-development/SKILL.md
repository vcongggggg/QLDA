---
name: teamswork-development
description: Use for TeamsWork changes across FastAPI backend, static UI, RBAC/auth, KPI, reports, Microsoft Teams integration, AI task breakdown, tests, docs, and release evidence.
---

# TeamsWork Development

Use this skill whenever changing or reviewing TeamsWork product code, tests, UI, docs, security settings, demo evidence, or release traceability.

## First Pass

- Read `AGENTS.md` before changing behavior. It is the source of truth for product rules, security boundaries, KPI policy, and quality gates.
- For UI or Microsoft Teams tab work, also read `DESIGN.md` or `references/design-baseline.md`.
- Inspect the relevant router, schema, repository function, test file, and docs before editing.
- Keep changes narrow. Do not refactor unrelated modules or broaden product scope.
- Preserve existing dirty worktree changes unless the user explicitly asks to revert them.

## Product Guardrails

- TeamsWork is an internal operations app for tasks, projects, sprints, KPI, reports, AI task preview/import, and Microsoft Teams workflows.
- Never invent KPI formulas, KPI adjustments, permission policy, AI-import approval policy, or product data.
- Current KPI defaults must remain compatible unless the task explicitly changes tested KPI policy:
  - difficulty multiplier: `easy=1.0`, `medium=1.5`, `hard=2.0`
  - on-time done task: `+10 * multiplier`
  - late done task: `+5 * multiplier`
  - unfinished overdue task in KPI month: `-5 * multiplier`
  - manual adjustments require a reason and audit evidence
- For auth, RBAC, KPI, Teams, reports, AI import, or uploads, add or update focused tests and docs/checklists.

## Backend Pattern

- Follow the existing FastAPI shape: router endpoint, Pydantic schema, repository function, and focused pytest coverage.
- Keep routers thin: validate request-level concerns, enforce auth/RBAC, call repository/service helpers, return declared `response_model`s.
- Use repository helpers and structured SQL parameters instead of ad hoc SQL in routers.
- Keep SQLite and PostgreSQL compatibility in schema and migration changes.
- Validate user input at system boundaries; return safe user-facing errors without stack traces or provider raw errors.
- Do not add dependencies unless the task requires them and the tradeoff is explicit.

## UI Pattern

- Use the existing static web shell: fixed sidebar, topbar, role-aware sections, dense tables, Kanban columns, dashboards, and drawers.
- Keep the UI compact, predictable, and work-focused. Do not create marketing-style hero pages or decorative layouts.
- Use full-width work areas and simple panels. Do not nest cards inside cards.
- Keep cards/panels near `8px` radius and use stable dimensions, fixed grid tracks, and overflow wrapping.
- Preserve role visibility: staff/member users see only their own allowed data; privileged controls stay hidden unless permissions allow them.
- Add explicit loading, empty, and error states for API-backed UI and Teams tab panels.
- For detailed UI rules, read `references/design-baseline.md`.

## Security And Integration

- Production auth must prioritize JWT bearer tokens. Header fallback is only for safe local/dev/demo/test settings.
- Privileged endpoints must enforce roles or permissions through existing auth helpers.
- Staff/member users must stay scoped to their own tasks/KPI unless product rules say otherwise.
- Never log or display secrets, bearer tokens, Authorization headers, Teams tokens, webhook URLs, client secrets, or raw provider errors.
- Treat Azure AD, Teams callbacks, Graph, webhooks, AI providers, and uploads as trust boundaries.
- Real external Teams/Graph calls should stay disabled by default unless configured through environment variables.

## Verification

Run focused tests for the touched domain first, then the broader gate when behavior changes.

```powershell
pytest -q
```

High-risk focused suites:

```powershell
pytest tests/test_api_flow.py tests/test_ai_task_breakdown.py tests/test_kpi.py
pytest tests/test_auth_rbac_department.py tests/test_auth_security_hardening.py
pytest tests/test_teams_mvp.py tests/test_notifications.py
```

- Run Playwright checks when UI navigation, role-visible surfaces, dialogs, layout, or Teams tab behavior changes.
- Run `python -m compileall app scripts` when Python code changes.
- Update `docs/USER_STORY_COMPLETION_AUDIT.md`, `docs/QUALITY_GATE.md`, demo docs, or release evidence when behavior or release status changes.
- Review `git diff` before reporting completion.

## References

- `references/design-baseline.md`: distilled TeamsWork UI and Teams tab design rules from `DESIGN.md`.
- `references/ecc-source-map.md`: ECC source skills and the parts intentionally extracted.
