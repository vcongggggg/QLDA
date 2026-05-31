# Phase 5 Local Progress

Last updated: 2026-05-31

## Scope

Phase 5 is treated as local/demo-ready reporting and analytics work. This pass intentionally does not require production Microsoft Teams integration, external BI tooling, configured email delivery, or tenant infrastructure.

## Done For Local

| Area | Status | Evidence |
| --- | --- | --- |
| Dashboard insights | Done | `GET /reports/dashboard/insights` returns role-scoped cards, alerts, analytics, KPI preview, chart catalog, export links, and stable UI state metadata. |
| Analytics summary | Done | `GET /reports/analytics/summary` computes completion, workload, backlog, cycle-time, utilization, velocity, project effort, and dependency metrics from local task data. |
| Analytics export | Done | Analytics export endpoints support permissioned local exports for report handoff. |
| Reports | Done | Local report APIs expose KPI/report/portfolio-style data behind current report permissions. |
| Chart data | Done | Dashboard insights return API-ready datasets for status, workload, velocity, project effort, and dependency charts. |
| Scheduled reports | Done | Scheduled reports can be created, listed, run manually, and run when due with delivery-log evidence and next-run advancement. |
| RBAC | Done | Staff/member users receive personal dashboard scope; privileged report roles receive broader report scope and export links only when allowed. |
| Mobile shell | Done | Role-aware bottom navigation, off-canvas sidebar, and narrow viewport overflow checks are covered in Playwright. |
| UX shell | Done | Active navigation, stable page titles, skip-to-content flow, and keyboard controls are available across the static UI shell. |
| Accessibility hooks | Done | Skip link, focus-visible styling, aria-current state, labeled mobile nav, and reduced-motion CSS are present. |
| i18n shell | Done | VI/EN language toggle updates shell labels and persists preference in `localStorage`. |
| UI performance hooks | Done | Responsive behavior is CSS-first, mobile nav is rendered from the allowed role modules, and navigation performance marks are emitted. |

## Deferred

| Area | Reason |
| --- | --- |
| Production email delivery | Requires real SMTP/email configuration and retry/alert policy. Current local delivery log records skipped email status when unconfigured. |
| External BI integration | Not needed for local demo; remains a production/reporting-platform integration task. |
| Downloadable chart images | Current implementation provides chart-ready datasets, not image export. |
| Executive-only role | Current RBAC model does not define a dedicated executive role. |
| Formal WCAG/Playwright sign-off | Existing hooks and responsive states are present, but full acceptance evidence is still pending. |
| Full product translation | The shell/navigation supports VI/EN; every domain label and generated table cell has not been translated. |

## Test Evidence

Run after this pass:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_reports_analytics.py -q
.venv\Scripts\python.exe -m pytest tests/test_api_flow.py tests/test_ai_task_breakdown.py tests/test_kpi.py -q
```

Full `pytest -q` should still be run before merge/submission when time allows.
