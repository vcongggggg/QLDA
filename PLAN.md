# TeamsWork Implementation Plan (From Project Files)

## 1) Scope Baseline (Phase 1 MVP)
This implementation follows the documents in QLDA and focuses on core deliverables first:
- Task Management CRUD and Kanban statuses (`todo`, `doing`, `done`)
- KPI auto-calculation based on task outcomes and difficulty multipliers
- Dashboard summary for operational and KPI monitoring
- Seed sample data for demo and testing
- API-first backend ready for Microsoft Teams tab integration

Out of scope for this MVP code drop:
- Full Azure AD SSO and Graph production integration
- Full bot command suite and Adaptive Card workflows
- Full 513-user-story implementation

## 2) KPI Business Rule (Implemented)
Monthly KPI score per user:

`KPI = done_on_time*10 + done_late*5 - overdue_unfinished*5`

Difficulty multiplier:
- easy: x1.0
- medium: x1.5
- hard: x2.0

Applied formula:
- done on time: `+10 * multiplier`
- done late: `+5 * multiplier`
- overdue unfinished: `-5 * multiplier`

## 3) Sprint-Aligned Technical Plan
### Sprint 1 (implemented in this repo)
- Backend skeleton and database schema
- Task CRUD + status transition API
- KPI calculation module + monthly API
- Dashboard summary API
- Seed sample data endpoint

### Sprint 2 (next)
- RBAC permission checks per role
- Team/project filters and manager views
- KPI adjustment logs and audit trail

### Sprint 3 (next)
- Report export (Excel/PDF)
- Teams bot notification integration (24h deadline reminder)
- Production logging and retry strategies

### Sprint 4 (next)
- Azure AD SSO integration and token lifecycle
- Security hardening and QA automation
- UAT and release checklist

## 4) Deliverables Included
- Backend code in `app/`
- API docs via FastAPI OpenAPI
- Seed data generator in `app/seed.py`
- Unit tests for KPI engine in `tests/test_kpi.py`
- Run guide in `README.md`

## 5) Traceability to Source Docs
This plan/code is derived from extracted files:
- `_extracted/Kế hoạch dự án (2).txt`
- `_extracted/Báo cáo KTKT (3).txt`
- `_extracted/TeamsWork_ProductBacklog.txt`
- `_extracted/DuToan_TeamsWork_v3.txt`
