# TeamsWork Final Demo Slides

Format: Markdown deck.
Target talk time: 7-10 minutes.
Suggested style: dense operator dashboard, restrained colors, proof-first language.

---

## 1. TeamsWork

Internal project operations in one workspace.

- Projects, sprints, Kanban tasks
- KPI and exportable reports
- RBAC by real operating roles
- AI task drafts with human approval
- RAG and Microsoft Teams integration

Speaker note: Open with the product boundary: this is an internal operations tool, not a marketing site.

---

## 2. Architecture

Browser or Teams tab -> FastAPI -> SQLite/PostgreSQL.

- Static UI served at `/ui/`
- Routers for auth, org, tasks, sprints, KPI, reports, AI, RAG, Teams, monitoring
- SQLite for local demo
- PostgreSQL and pgvector optional for production-like RAG

Speaker note: Keep this to 45 seconds. Point to `/docs` for API surface.

---

## 3. RBAC Is The Control Layer

Roles: ADMIN, MANAGER, LEADER, MEMBER, HR, AUDITOR.

- Sidebar modules are role-filtered
- Privileged endpoints require roles or permissions
- Local fallback auth is for dev only
- Production path is JWT bearer

Evidence: `tests/role_module_matrix.py`, `tests/test_ui_role_navigation_playwright.py`.

---

## 4. Delivery Workflow

Projects and Kanban are linked to sprint execution.

- Demo seed creates departments, users, projects, sprints, members, and tasks
- Kanban filters by project, sprint, assignee, status, overdue, keyword, deadline
- Task detail captures assignee, difficulty, story points, deadline, comments

Evidence: `scripts/seed_full_demo.py`, `tests/test_task_filters.py`, `tests/test_task_detail.py`.

---

## 5. KPI And Reports

KPI is deterministic and documented.

- On-time done: `+10 * multiplier`
- Late done: `+5 * multiplier`
- Unfinished in month: `-5 * multiplier`
- Manual adjustment requires reason and audit trail
- Exports: KPI CSV/XLSX/PDF, portfolio, project progress, sprint review

Evidence: `app/kpi.py`, `docs/KPI_VALIDATION_RULES.md`, `tests/test_kpi.py`.

---

## 6. AI With Human Approval

AI suggests work; it does not silently change the plan.

- Text or `.docx` input creates an AI draft
- Manager/admin reviews and edits suggested items
- Import creates real Kanban tasks
- No API key required for local demo because heuristic fallback exists

Evidence: `app/routers/ai.py`, `docs/AI_TASK_GENERATION_SPEC.md`, `tests/test_ai_task_breakdown.py`.

---

## 7. RAG For Project Context

Local RAG is reliable without external services.

- Project-scoped documents
- ACL-aware listing and querying
- Lexical fallback by default
- pgvector embeddings optional for PostgreSQL deployments

Evidence: `app/routers/rag.py`, `app/rag.py`, `tests/test_rbac_rag.py`, `tests/test_rag_pgvector.py`.

---

## 8. Teams-ready Simulation

TeamsWork demos Teams workflows locally without Graph, Teams Admin Center, or sideloading.

- Web simulator at `/admin/integrations/teams-simulator`
- `/task-list`, `/kpi-me`, `/help`
- Adaptive Card JSON and Teams-like preview
- Deadline reminder queue, process, retry, health

Evidence: `docs/TEAMS_SIMULATION_MODE.md`, `app/routers/teams.py`, `tests/test_teams_simulation.py`.

---

## 9. Evidence And CI

The demo is reproducible.

- `python scripts/seed_full_demo.py --reset-demo`
- `pytest -q`
- `python -m compileall app scripts`
- `python scripts/smoke_check.py --base-url http://127.0.0.1:8000 --user-id 1 --expect-production-auth`
- `python scripts/benchmark_smoke.py --json`
- `python scripts/capture_demo_evidence.py --base-url http://127.0.0.1:8000`

Evidence files: `docs/TEST_EVIDENCE.md`, `docs/TRACEABILITY_MATRIX.md`.

---

## 10. Phase 6 Release Controls

Admin, compliance, maintenance, and QA evidence are explicit.

- Admin search, recent activity, config flags, and system notification broadcast
- GDPR/PDPA request/export/manual-review workflow
- Maintenance windows, retention metadata, and cleanup dry-run
- Release gate includes synthetic journey and QA evidence status

Evidence: `app/routers/phase6.py`, `tests/test_phase6_admin_compliance_maintenance.py`, `docs/PHASE6_UAT_EVIDENCE_TEMPLATE.md`.

---

## 11. Q&A Anchors

- RBAC: tested role matrix and guarded endpoints
- KPI: formula lives in code and docs; AI cannot change it
- AI/RAG: fallback-first local demo, optional providers for richer behavior
- Teams: local tab/queue/callback demo, real posting needs configured tenant
- Compliance: no hard delete automation; requests produce export and manual review evidence
- CI/test: GitHub Actions runs pytest on Python 3.11 and 3.12 plus compile check

Close: TeamsWork is controlled delivery operations with evidence, not a one-off demo.

---

## Timing Plan

| Segment | Time |
| --- | ---: |
| Product and architecture | 1:15 |
| RBAC | 1:15 |
| Project/Kanban | 1:15 |
| KPI/reports | 1:15 |
| AI/RAG | 1:30 |
| Teams | 1:00 |
| Ops/evidence/CI | 1:00 |
| Q&A buffer | 1:00 |
