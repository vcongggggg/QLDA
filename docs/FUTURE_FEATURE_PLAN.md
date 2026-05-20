# Future Feature Plan

## Current Repo Capability

- TeamsWork hiện có FastAPI app, static web UI, Microsoft Teams tab, RBAC theo permission, audit log, KPI, reports, AI task breakdown và RAG keyword-based.
- Task filtering đã tồn tại ở `GET /tasks`: `project_id`, `sprint_id`, `assignee_id`, `status`, `overdue`, `keyword`, `deadline_from`, `deadline_to`; có test trong `tests/test_task_filters.py`.
- AI task workflow đã có backend draft/review/import: `ai_task_drafts`, endpoint list/detail/review/import, audit log, test trong `tests/test_ai_task_breakdown.py`. UI hiện còn cần cập nhật vì flow import trong `app/static/app.js` chưa gửi `ai_draft_id`.
- Workload/capacity hiện có `sprint_capacity_plans` và API capacity theo sprint, nhưng chưa thấy warning/threshold chính thức.
- Audit/Ops hiện có `/monitoring/metrics`, `/audit/logs`, Teams queue stats, Admin UI hiển thị audit logs; chưa có dashboard ops chuyên dụng với filter/drilldown.
- RAG hiện nhận text thủ công qua `POST /rag/documents`, chunk keyword matching trong `app/rag.py`; chưa thấy upload `.docx`/`.pdf` cho RAG, permission theo tài liệu, hay embedding/vector search.

## Feature Priority Table

| Priority | Feature | Reason |
|---:|---|---|
| 1 | Workflow duyệt task AI trước khi import | Backend gần xong, UI/API mismatch đang ảnh hưởng luồng đã có. Rủi ro thấp, giá trị cao. |
| 2 | Tìm kiếm/lọc task nâng cao | Backend đã có nền tốt; chủ yếu hoàn thiện UI, docs, edge-case test. |
| 3 | Workload/capacity warning | Dựa được trên capacity hiện có, giúp manager xử lý quá tải trước sprint. |
| 4 | Audit/Ops dashboard | Dùng audit/metrics/queue sẵn có, phục vụ admin/manager/hr. |
| 5 | RAG nâng cấp docx/pdf + permission + embedding | Lớn nhất, cần chia phase vì liên quan upload, permission, parsing PDF, embedding/storage/search. |

## Feature-by-Feature Scope

### 1. Tìm kiếm/lọc task nâng cao

- Preserve current `GET /tasks` response as `TaskOut[]`.
- Keep existing filters and UI filter bar in Kanban.
- Add only clearly supported refinements: better empty/error state, visible active filter summary, reset behavior, and tests for combined filters.
- Do not add `priority` filter unless task schema is extended later; current README notes task has no `priority`.

### 2. Workflow duyệt task AI trước khi import

- Align static UI with existing backend draft flow:
  - store `ai_draft_id` after preview;
  - allow manager/admin to edit/select generated items;
  - call `PATCH /ai/task-breakdown/drafts/{draft_id}/review`;
  - call `POST /ai/task-breakdown/import` with `ai_draft_id`.
- Add draft list/detail UI for `draft`, `reviewed`, `imported`.
- Preserve human approval requirement from `AGENTS.md` and `docs/AI_TASK_GENERATION_SPEC.md`.
- Do not auto-create tasks from preview.

### 3. Workload/capacity warning

- Derive warnings from existing `sprint_capacity_plans`, sprint tasks, assignee, and story points.
- Needs confirmation: conversion rule from story points to hours is not found.
- Recommended default until confirmed: compare `allocated_hours / capacity_hours`; show warning at `>= 85%`, danger at `> 100%`.
- Add API summary per sprint/user and UI badges in sprint/project surfaces.
- Do not change KPI formula.

### 4. Audit/Ops dashboard

- Build on existing `/monitoring/metrics`, `/audit/logs`, Teams queue endpoints, and plan completion.
- Add dashboard sections for system metrics, audit log table, failed queue items, recent AI imports/reviews, and high-level risks.
- Add filters for audit logs by actor/action/entity/date if implemented.
- Keep privileged visibility: `monitoring.view` for summary; `monitoring.admin` for audit details.

### 5. RAG nâng cấp docx/pdf + permission + embedding

Phase this feature:

- Phase 5A: RAG upload for `.docx`; reuse existing `python-docx` capability from AI task breakdown.
- Phase 5B: Permission metadata for RAG documents: owner, scope, optional project/sprint/role access.
- Phase 5C: PDF ingestion; parser dependency/approach needs confirmation because no PDF text extraction dependency for RAG was found.
- Phase 5D: Embedding search; embedding provider/storage not found and needs architecture decision. Current RAG is keyword matching only.

## Files Likely Affected

- Backend/API: `app/routers/tasks.py`, `app/routers/ai.py`, `app/routers/rag.py`, `app/routers/monitoring.py`, `app/routers/sprints.py`.
- Data/contracts: `app/schemas.py`, `app/repository.py`, `app/database.py`, `app/migrations.py`, `app/permissions.py`.
- UI: `app/static/index.html`, `app/static/app.js`, `app/static/styles.css`, Teams tab only if ops/task filters are exposed there.
- Tests/docs: existing tests under `tests/`, plus this new `docs/FUTURE_FEATURE_PLAN.md`.

## Database Changes Needed

- Feature 1: none for current filter set; indexes already exist for common task filters.
- Feature 2: likely none for backend basics; `ai_task_drafts` already exists with `draft/reviewed/imported`.
- Feature 3: likely none for v1 derived warnings; needs schema only if storing warning acknowledgements or custom thresholds.
- Feature 4: none for read-only v1; optional indexes if audit filters become slow.
- Feature 5: required for permission/embedding phases:
  - document metadata such as file type, scope, owner/project/sprint fields;
  - chunk metadata for source page/paragraph;
  - embedding fields/table once provider/storage is confirmed.

## API Changes Needed

- Feature 1: keep `GET /tasks`; optionally document filters more clearly.
- Feature 2: no new backend endpoint required for v1; fix UI to use existing draft/review/import endpoints.
- Feature 3: add workload summary endpoint, likely under sprint/project scope, returning per-user capacity, allocation, utilization, and warning level.
- Feature 4: add ops summary endpoint or compose existing endpoints in UI; add audit filter params only if needed.
- Feature 5: add RAG upload endpoints for docx/pdf, permission-aware list/query/delete, and later embedding-backed query.

## UI Changes Needed According to DESIGN.md

- Keep dense operational layout, fixed sidebar, simple panels, tables, drawers, and compact controls.
- Task filters should remain in Kanban toolbar with stable dimensions and no nested cards.
- AI review should use a table/drawer workflow with explicit draft status, warnings, selected items, review note, and import action.
- Capacity warnings should use amber/red status badges and compact summary panels.
- Ops dashboard should use tables for audit/queue data and role-aware sections.
- RAG admin should show source, type, owner/scope, chunks, permission state, and clear empty/error states.

## RBAC/Security Concerns According to AGENTS.md

- Staff must remain scoped to own assigned tasks and own KPI/task data.
- AI preview requires `ai.preview`; review/import requires `ai.import`.
- RAG manage/query must continue using `rag.manage` and `rag.query`; per-document permission must not leak restricted chunks through AI context.
- Monitoring/audit details require `monitoring.admin`; summary can use `monitoring.view`.
- Uploads must validate extension, size, and minimum content. `.docx` rule exists; `.pdf` rules are not found and need confirmation.
- Do not log secrets, bearer tokens, provider raw errors, or sensitive document contents in audit detail.

## Test Plan

- Docs-only change: pytest not required by quality gate.
- Feature 1: extend `tests/test_task_filters.py` for UI/API-supported combinations and invalid ranges.
- Feature 2: extend `tests/test_ai_task_breakdown.py` for review-before-import behavior, imported draft rejection, UI contract expectations if covered.
- Feature 3: add tests for normal, warning, over-capacity, missing capacity, staff visibility.
- Feature 4: add tests for audit filtering, monitoring permission boundaries, queue failed stats.
- Feature 5: extend `tests/test_rbac_rag.py` for upload validation, permission filtering, query leakage prevention, and embedding fallback behavior once architecture is chosen.

## Suggested Implementation Order

1. Fix AI review/import UI contract first because backend support already exists and current UI payload appears stale.
2. Polish task advanced filtering UI/docs/tests using existing API behavior.
3. Add workload/capacity warning as derived read-only summaries.
4. Build Audit/Ops dashboard from existing metrics, logs, and queue data.
5. Phase RAG upgrade: docx upload, permissions, PDF ingestion, then embeddings.

## Risks and Non-Goals

- Do not add dependencies until a specific implementation phase justifies them.
- Do not change task schema, KPI formula, RBAC defaults, or production auth in this planning/doc pass.
- RAG embedding is not currently implemented; provider, storage model, and cost/performance tradeoff need confirmation.
- PDF ingestion is not found in current RAG stack; parser choice needs confirmation.
- Capacity warning thresholds and story-point-to-hour mapping are not found; default thresholds should be confirmed before coding.
- Do not expand beyond the five requested features.
