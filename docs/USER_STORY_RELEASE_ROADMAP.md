# TeamsWork User Story Release Roadmap

Generated: 2026-05-31

This roadmap implements the production-release scope from `docs/USER_STORY_COMPLETION_AUDIT.md`: finish `Must Have` and `Should Have` user stories first. `Could Have` and `Won't Have` stories stay in backlog unless explicitly promoted.

## Release Baseline

| Metric | Count |
| --- | ---: |
| Must Have + Should Have stories | 374 |
| Already Done | 295 |
| Partial, still unfinished | 0 |
| Not started | 79 |
| Remaining release stories | 79 |

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

## Per-Story Must/Should Roadmap

This section expands every unfinished Must Have and Should Have user story from docs/USER_STORY_COMPLETION_AUDIT.md into an execution row. Current remaining count: 139 release-scope stories (64 Must Have, 75 Should Have).

Use these rows as the implementation queue. Promote a row to `Done` only after API/UI behavior, RBAC, focused tests, and audit evidence are updated. For Teams-related rows, the default target remains Teams-ready Simulation Mode; real Microsoft Graph or Teams outbound must stay disabled unless explicitly configured and approved with a real tenant.

| US | Priority | Current | Phase | Workstream | Roadmap action | Verification |
| --- | --- | --- | --- | --- | --- | --- |
| US003 | Must Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / SSO Login | Implement production-safe auth/RBAC workflow for SSO Login with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US006 | Must Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Phân quyền | Implement production-safe auth/RBAC workflow for Phân quyền with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US007 | Must Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Phân quyền | Implement production-safe auth/RBAC workflow for Phân quyền with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US008 | Must Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Phân quyền | Implement production-safe auth/RBAC workflow for Phân quyền with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US013 | Should Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Profile | Implement production-safe auth/RBAC workflow for Profile with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US015 | Should Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Onboarding | Implement production-safe auth/RBAC workflow for Onboarding with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US016 | Should Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Onboarding | Implement production-safe auth/RBAC workflow for Onboarding with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US020 | Should Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Audit | Implement production-safe auth/RBAC workflow for Audit with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US021 | Should Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Auth & Security | Implement production-safe auth/RBAC workflow for Auth & Security with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US024 | Must Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Phân quyền | Implement production-safe auth/RBAC workflow for Phân quyền with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US025 | Must Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / SSO Login | Implement production-safe auth/RBAC workflow for SSO Login with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US027 | Should Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Phân quyền | Implement production-safe auth/RBAC workflow for Phân quyền with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US031 | Must Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Auth & Security | Implement production-safe auth/RBAC workflow for Auth & Security with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US032 | Must Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Auth & Security | Implement production-safe auth/RBAC workflow for Auth & Security with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US034 | Should Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Onboarding | Implement production-safe auth/RBAC workflow for Onboarding with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US036 | Should Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Notification Settings | Implement production-safe auth/RBAC workflow for Notification Settings with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US038 | Must Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / SSO Login | Implement production-safe auth/RBAC workflow for SSO Login with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US042 | Should Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Phân quyền | Implement production-safe auth/RBAC workflow for Phân quyền with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US043 | Should Have | Done | Phase 1 - Production Foundation, Auth, RBAC, Security | E1: Auth & User Mgmt / Onboarding | Implement production-safe auth/RBAC workflow for Onboarding with audit evidence and local/dev fallback guarded. | tests/test_auth_rbac_department.py; tests/test_auth_security_hardening.py; tests/test_role_module_rbac_matrix.py |
| US053 | Should Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E2: Task Management / Tạo Task | Completed task workflow across API, RBAC, UI state, validation, and audit/activity evidence. | tests/test_task_filters.py; tests/test_task_detail.py; tests/test_api_flow.py; tests/test_ui_role_navigation_playwright.py |
| US073 | Should Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E2: Task Management / Chi tiết Task | Completed task-detail workflow across API, RBAC, UI state, validation, and audit/activity evidence. | tests/test_task_detail.py; tests/test_task_deadline_extension.py; tests/test_ui_role_navigation_playwright.py |
| US080 | Should Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E2: Task Management / Tìm kiếm & Lọc | Completed search/filter workflow with role scope, deadline range, keyword, and UI filter state. | tests/test_task_filters.py; tests/test_ui_role_navigation_playwright.py |
| US091 | Should Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E2: Task Management / Tạo Task | Completed task creation persistence, validation, audit, and Kanban refresh behavior. | tests/test_api_flow.py; tests/test_ui_role_navigation_playwright.py |
| US094 | Should Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E2: Task Management / Deadline | Completed deadline-extension workflow with manager/admin RBAC, required reason, notification, and activity evidence. | tests/test_task_deadline_extension.py; tests/test_ui_role_navigation_playwright.py |
| US098 | Should Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E2: Task Management / Tìm kiếm & Lọc | Completed staff self-scope behavior for task filters. | tests/test_task_filters.py |
| US110 | Should Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E2: Task Management / Chi tiết Task | Completed task detail permission boundary for staff/member users and privileged reviewers. | tests/test_task_detail.py |
| US113 | Should Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E2: Task Management / Tìm kiếm & Lọc | Completed invalid-filter validation and UI empty/error state evidence. | tests/test_task_filters.py |
| US297 | Should Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Tạo Project | Completed project creation API/UI with creator ownership default and audit evidence. | tests/test_phase2_project_workflow.py; tests/test_api_flow.py; tests/test_ui_role_navigation_playwright.py |
| US298 | Should Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Tạo Project | Completed project creation validation and `projects.manage` permission enforcement. | tests/test_phase2_project_workflow.py; tests/test_api_flow.py |
| US305 | Should Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Backlog | Completed project backlog listing with staff self-scope and project-detail UI links. | tests/test_task_filters.py; tests/test_phase2_project_workflow.py |
| US306 | Should Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Backlog | Completed backlog move-to-sprint workflow with same-project validation and audit evidence. | tests/test_task_bulk_backlog.py; tests/test_phase2_project_workflow.py; tests/test_api_flow.py |
| US309 | Should Have | Not started | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Milestones | Finish project/sprint workflow for Milestones with project access checks and staff scope preserved. | tests/test_project_*.py or nearest sprint/backlog focused tests; tests/test_api_flow.py |
| US310 | Should Have | Not started | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Milestones | Finish project/sprint workflow for Milestones with project access checks and staff scope preserved. | tests/test_project_*.py or nearest sprint/backlog focused tests; tests/test_api_flow.py |
| US322 | Should Have | Not started | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Backlog | Finish project/sprint workflow for Backlog with project access checks and staff scope preserved. | tests/test_project_*.py or nearest sprint/backlog focused tests; tests/test_api_flow.py |
| US323 | Should Have | Not started | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Milestones | Finish project/sprint workflow for Milestones with project access checks and staff scope preserved. | tests/test_project_*.py or nearest sprint/backlog focused tests; tests/test_api_flow.py |
| US324 | Should Have | Not started | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Team | Finish project/sprint workflow for Team with project access checks and staff scope preserved. | tests/test_project_*.py or nearest sprint/backlog focused tests; tests/test_api_flow.py |
| US325 | Should Have | Not started | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Sprint | Finish project/sprint workflow for Sprint with project access checks and staff scope preserved. | tests/test_project_*.py or nearest sprint/backlog focused tests; tests/test_api_flow.py |
| US331 | Should Have | Not started | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Team | Finish project/sprint workflow for Team with project access checks and staff scope preserved. | tests/test_project_*.py or nearest sprint/backlog focused tests; tests/test_api_flow.py |
| US333 | Must Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Tạo Project | Completed project detail UI for progress, members, sprints, backlog, and scoped project mutation evidence. | tests/test_phase2_project_workflow.py; tests/test_ui_role_navigation_playwright.py |
| US335 | Should Have | Not started | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Backlog | Finish project/sprint workflow for Backlog with project access checks and staff scope preserved. | tests/test_project_*.py or nearest sprint/backlog focused tests; tests/test_api_flow.py |
| US336 | Should Have | Not started | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Team | Finish project/sprint workflow for Team with project access checks and staff scope preserved. | tests/test_project_*.py or nearest sprint/backlog focused tests; tests/test_api_flow.py |
| US337 | Must Have | Done | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Tạo Project | Completed project access checks for outside-manager membership and sprint mutation denial. | tests/test_phase2_project_workflow.py |
| US342 | Should Have | Not started | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Tạo Project | Finish project/sprint workflow for Tạo Project with project access checks and staff scope preserved. | tests/test_project_*.py or nearest sprint/backlog focused tests; tests/test_api_flow.py |
| US347 | Should Have | Not started | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Tạo Project | Finish project/sprint workflow for Tạo Project with project access checks and staff scope preserved. | tests/test_project_*.py or nearest sprint/backlog focused tests; tests/test_api_flow.py |
| US348 | Should Have | Not started | Phase 2 - Core Task, Kanban, Deadline, Backlog | E6: Project Management / Sprint | Finish project/sprint workflow for Sprint with project access checks and staff scope preserved. | tests/test_project_*.py or nearest sprint/backlog focused tests; tests/test_api_flow.py |
| US121 | Should Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Cấu hình KPI | Completed KPI config API with required change reason, audit evidence, RBAC, and default formula compatibility. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US122 | Should Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Cấu hình KPI | Completed KPI config validation for policy shape, fallback difficulty, manager permissions, and staff denial. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US140 | Must Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Xem KPI | Completed ledger-backed monthly KPI read workflow with member self-scope and target progress fields. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US142 | Should Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Mục tiêu KPI | Completed KPI target create/list/progress workflow for user-month targets. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US144 | Should Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Mục tiêu KPI | Completed KPI target update and progress gap calculation without changing the default score formula. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US145 | Should Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Mục tiêu KPI | Completed KPI target CSV/XLSX import validation and audit-backed upsert workflow. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US151 | Should Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Thông báo KPI | Completed KPI target warning runner for users below target. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US152 | Should Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Thông báo KPI | Completed daily duplicate prevention for KPI target warning notifications. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US153 | Should Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Thông báo KPI | Completed audited, role-gated KPI warning generation without external delivery side effects. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US157 | Should Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Xem KPI | Completed KPI history, team summary, and department breakdown read endpoints. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US159 | Must Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Tính điểm KPI | Completed transaction-ledger rebuild with active/reversed events and idempotency. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US165 | Must Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Tính điểm KPI | Completed manual KPI adjustment workflow requiring stored reason and approval before score impact. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US166 | Should Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Xem KPI | Completed staff/member KPI read scoping and report export permission behavior. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US171 | Should Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Cấu hình KPI | Completed persisted KPI policy retrieval/update evidence while preserving tested defaults. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US174 | Must Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Tính điểm KPI | Completed ledger-backed KPI aggregation from task and approved adjustment transactions. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US177 | Must Have | Done | Phase 3 - KPI Configuration, Targets, Transactions | E3: KPI Management / Tính điểm KPI | Completed rollback-safe KPI transaction behavior for changed task outcomes. | tests/test_kpi.py; tests/test_kpi_phase3.py; tests/test_api_flow.py |
| US184 | Must Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Bot Commands | Local simulator accepts `/help`, `/task-list`, `/team-kpi`, `/kpi-me`, `/my-deadlines`, `/top-kpi`, `/search`, `/new-task`, `/assign`, `/status`, and `/report` using `X-User-Id`; real outbound remains disabled by default. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US185 | Should Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Bot Commands | Local simulator accepts `/help`, `/task-list`, `/team-kpi`, `/kpi-me`, `/my-deadlines`, `/top-kpi`, `/search`, `/new-task`, `/assign`, `/status`, and `/report` using `X-User-Id`; real outbound remains disabled by default. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US187 | Should Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Bot Commands | Local simulator accepts `/help`, `/task-list`, `/team-kpi`, `/kpi-me`, `/my-deadlines`, `/top-kpi`, `/search`, `/new-task`, `/assign`, `/status`, and `/report` using `X-User-Id`; real outbound remains disabled by default. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US190 | Should Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Adaptive Cards | Local card preview/action APIs cover task list, deadline, task action, KPI personal, and KPI summary cards with RBAC and no real Teams outbound. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US194 | Must Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Adaptive Cards | Local card preview/action APIs cover task list, deadline, task action, KPI personal, and KPI summary cards with RBAC and no real Teams outbound. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US195 | Should Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Adaptive Cards | Local card preview/action APIs cover task list, deadline, task action, KPI personal, and KPI summary cards with RBAC and no real Teams outbound. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US201 | Must Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Bot Commands | Local simulator accepts command catalog and reuses existing task/KPI/RBAC handlers; mutating commands are permission-checked and tested without Teams tenant dependency. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US202 | Should Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Bot Commands | Local simulator accepts command catalog and reuses existing task/KPI/RBAC handlers; mutating commands are permission-checked and tested without Teams tenant dependency. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US203 | Should Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Bot Commands | Local simulator accepts command catalog and reuses existing task/KPI/RBAC handlers; mutating commands are permission-checked and tested without Teams tenant dependency. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US205 | Should Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Bot Commands | Local simulator accepts command catalog and reuses existing task/KPI/RBAC handlers; mutating commands are permission-checked and tested without Teams tenant dependency. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US207 | Must Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Adaptive Cards | Local card preview/action APIs cover task list, deadline, task action, KPI personal, and KPI summary cards with RBAC and no real Teams outbound. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US208 | Should Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Bot Commands | Local simulator accepts command catalog and reuses existing task/KPI/RBAC handlers; mutating commands are permission-checked and tested without Teams tenant dependency. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US216 | Must Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Adaptive Cards | Local card preview/action APIs cover task list, deadline, task action, KPI personal, and KPI summary cards with RBAC and no real Teams outbound. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US217 | Should Have | Partial | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Channel Notifications | Complete local Teams-ready simulation acceptance for Channel Notifications; keep real outbound disabled by default. Current slice validates channel/project-channel targets and project access before queue writes. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US219 | Must Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Adaptive Cards | Local card preview/action APIs cover task list, deadline, task action, KPI personal, and KPI summary cards with RBAC and no real Teams outbound. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US222 | Should Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Bot Commands | Local simulator accepts command catalog and reuses existing task/KPI/RBAC handlers; mutating commands are permission-checked and tested without Teams tenant dependency. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US225 | Must Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Bot Commands | Local simulator accepts command catalog and reuses existing task/KPI/RBAC handlers; mutating commands are permission-checked and tested without Teams tenant dependency. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US228 | Should Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Adaptive Cards | Local card preview/action APIs cover task list, deadline, task action, KPI personal, and KPI summary cards with RBAC and no real Teams outbound. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US230 | Must Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Adaptive Cards | Local card preview/action APIs cover task list, deadline, task action, KPI personal, and KPI summary cards with RBAC and no real Teams outbound. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US232 | Should Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Bot Commands | Local simulator accepts command catalog and reuses existing task/KPI/RBAC handlers; mutating commands are permission-checked and tested without Teams tenant dependency. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US233 | Must Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Bot Commands | Local simulator accepts command catalog and reuses existing task/KPI/RBAC handlers; mutating commands are permission-checked and tested without Teams tenant dependency. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US235 | Must Have | Done | Phase 4 - Teams-ready Simulation, Bot, Adaptive Cards | E4: Bot & Notifications / Adaptive Cards | Local card preview/action APIs cover task list, deadline, task action, KPI personal, and KPI summary cards with RBAC and no real Teams outbound. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; tests/test_notifications.py |
| US357 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Teams Tab | Deliver mockable/platform-ready Teams Tab path; document tenant/admin dependency and keep production Graph/Teams outbound opt-in. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US360 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Azure AD | Deliver mockable/platform-ready Azure AD path; document tenant/admin dependency and keep production Graph/Teams outbound opt-in. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US361 | Should Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Azure AD | Deliver mockable/platform-ready Azure AD path; document tenant/admin dependency and keep production Graph/Teams outbound opt-in. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US362 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Azure AD | Deliver mockable/platform-ready Azure AD path; document tenant/admin dependency and keep production Graph/Teams outbound opt-in. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US365 | Must Have | Partial | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Microsoft Graph | Deliver mockable/platform-ready Microsoft Graph path; document tenant/admin dependency and keep production Graph/Teams outbound opt-in. Current slice keeps Graph channel targets explicit and validated before queue processing. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US367 | Should Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / SharePoint | Define SharePoint-ready contract and mocked tests; defer real tenant connection until admin permissions exist. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US368 | Should Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / SharePoint | Define SharePoint-ready contract and mocked tests; defer real tenant connection until admin permissions exist. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US372 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Fluent UI | Finish Fluent UI acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US373 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Fluent UI | Finish Fluent UI acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US374 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Fluent UI | Finish Fluent UI acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US375 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Performance | Finish Performance acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US376 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Performance | Finish Performance acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US377 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Performance | Finish Performance acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US379 | Must Have | Partial | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Security | Finish Security acceptance with API/UI/RBAC/tests/docs evidence. Current slice enforces Teams proactive queue target validation, project access checks, and user existence checks. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US380 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Security | Finish Security acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US383 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / DevOps | Finish DevOps acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US384 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Performance | Finish Performance acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US386 | Should Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Microsoft Graph | Deliver mockable/platform-ready Microsoft Graph path; document tenant/admin dependency and keep production Graph/Teams outbound opt-in. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US387 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Fluent UI | Finish Fluent UI acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US388 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Security | Finish Security acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US391 | Should Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Azure AD | Deliver mockable/platform-ready Azure AD path; document tenant/admin dependency and keep production Graph/Teams outbound opt-in. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US392 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Performance | Finish Performance acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US394 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Security | Finish Security acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US395 | Should Have | Partial | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / API | Finish API acceptance with API/UI/RBAC/tests/docs evidence. Current slice adds API validation coverage for proactive Teams channel and project-channel queue requests. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US397 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Performance | Finish Performance acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US398 | Should Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / DevOps | Finish DevOps acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US399 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Security | Finish Security acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US400 | Should Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / DevOps | Finish DevOps acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US403 | Must Have | Not started | Phase 4 - Teams-ready Simulation and Platform Readiness | E7: Integration & Platform / Performance | Finish Performance acceptance with API/UI/RBAC/tests/docs evidence. | tests/test_teams_mvp.py; tests/test_teams_simulation.py; platform readiness docs/checks |
| US241 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Dashboard | `GET /reports/dashboard/insights` returns role-scoped dashboard cards, alerts, chart catalog, export links, and empty/error states for local/demo use. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US243 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Báo cáo | Local report/export endpoints cover KPI, tasks, portfolio, project progress, sprint review, analytics JSON/CSV/XLSX, and schedule logs with RBAC. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US244 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Báo cáo | Local report/export endpoints cover KPI, tasks, portfolio, project progress, sprint review, analytics JSON/CSV/XLSX, and schedule logs with RBAC. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US245 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Báo cáo | Local report/export endpoints cover KPI, tasks, portfolio, project progress, sprint review, analytics JSON/CSV/XLSX, and schedule logs with RBAC. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US246 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Báo cáo | Local report/export endpoints cover KPI, tasks, portfolio, project progress, sprint review, analytics JSON/CSV/XLSX, and schedule logs with RBAC. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US253 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Biểu đồ | Dashboard insights and Reports UI expose local chart catalog/data for task status, workload, velocity, project effort, and dependency summary. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US262 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Analytics | Analytics summary and dashboard insights compute local productivity, backlog, cycle time, workload, utilization, velocity, project effort, and dependency metrics. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US270 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Báo cáo | Local report/export endpoints cover KPI, tasks, portfolio, project progress, sprint review, analytics JSON/CSV/XLSX, and schedule logs with RBAC. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US272 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Dashboard | Role-scoped dashboard insights are available for staff/member, manager, HR, admin, and auditor-style report users without external BI dependencies. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US273 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Scheduled Reports | Scheduled reports create/list/manual-run/run-due locally and log skipped email delivery when outbound email is not configured. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US274 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Biểu đồ | Dashboard insights and Reports UI expose local chart catalog/data for task status, workload, velocity, project effort, and dependency summary. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US277 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Dashboard | Role-scoped dashboard insights are available for staff/member, manager, HR, admin, and auditor-style report users without external BI dependencies. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US279 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Báo cáo | Local report/export endpoints cover KPI, tasks, portfolio, project progress, sprint review, analytics JSON/CSV/XLSX, and schedule logs with RBAC. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US282 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Dashboard | Dashboard insights include stable loading/empty/error state fields and warning/info alerts for empty months, overdue backlog, and unassigned backlog. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US283 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Export | Dashboard insights expose export links for users with `reports.export`; analytics JSON/CSV/XLSX exports reuse the tested summary shape. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US286 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Dashboard | Dashboard insights include cards, alerts, analytics payload, KPI rows, chart catalog, and export links in a stable local API shape. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US288 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E5: Reporting & Analytics / Analytics | Analytics summary and dashboard insights compute local productivity, backlog, cycle time, workload, utilization, velocity, project effort, and dependency metrics. | tests/test_reports_analytics.py; Playwright UI smoke where UI changes |
| US445 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / Mobile | Responsive mobile shell includes role-aware bottom navigation, off-canvas sidebar close behavior, and no horizontal overflow in Playwright mobile viewport. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US446 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / Mobile | Responsive mobile shell includes role-aware bottom navigation, off-canvas sidebar close behavior, and no horizontal overflow in Playwright mobile viewport. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US448 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / UX | UX shell keeps active navigation state, skip-to-content flow, keyboard shortcuts, and stable page titles across route changes. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US450 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / UX | UX shell keeps active navigation state, skip-to-content flow, keyboard shortcuts, and stable page titles across route changes. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US454 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / UX | UX shell keeps active navigation state, skip-to-content flow, keyboard shortcuts, and stable page titles across route changes. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US457 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / Accessibility | Accessibility hooks include skip link, focus-visible outline, aria-current navigation state, labeled mobile nav, and reduced-motion CSS. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US458 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / Accessibility | Accessibility hooks include skip link, focus-visible outline, aria-current navigation state, labeled mobile nav, and reduced-motion CSS. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US460 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / i18n | Core navigation/topbar supports persisted VI/EN language toggle with document lang updates. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US463 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / UX | UX shell keeps active navigation state, skip-to-content flow, keyboard shortcuts, and stable page titles across route changes. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US466 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / UX | UX shell keeps active navigation state, skip-to-content flow, keyboard shortcuts, and stable page titles across route changes. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US468 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / Performance | Performance pass adds reduced-motion support, lightweight mobile nav rendering, CSS-only responsiveness, and navigation performance marks. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US469 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / UX | UX shell keeps active navigation state, skip-to-content flow, keyboard shortcuts, and stable page titles across route changes. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US470 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / Accessibility | Accessibility hooks include skip link, focus-visible outline, aria-current navigation state, labeled mobile nav, and reduced-motion CSS. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US471 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / i18n | Core navigation/topbar supports persisted VI/EN language toggle with document lang updates. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US478 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / Mobile | Responsive mobile shell includes role-aware bottom navigation, off-canvas sidebar close behavior, and no horizontal overflow in Playwright mobile viewport. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US479 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / Accessibility | Accessibility hooks include skip link, focus-visible outline, aria-current navigation state, labeled mobile nav, and reduced-motion CSS. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US480 | Must Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / UX | UX shell keeps active navigation state, skip-to-content flow, keyboard shortcuts, and stable page titles across route changes. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US481 | Should Have | Done | Phase 5 - Reporting, Analytics, Dashboards, UX | E9: Mobile & UX / UX | UX shell keeps active navigation state, skip-to-content flow, keyboard shortcuts, and stable page titles across route changes. | tests/test_phase5_mobile_ux_static.py; tests/test_ui_role_navigation_playwright.py |
| US406 | Must Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Cấu hình hệ thống | system config overview exposes safe settings, redacts secrets, and records local change policy. | tests/test_phase6_admin_compliance_maintenance.py |
| US407 | Must Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Cấu hình hệ thống | system config overview exposes safe settings, redacts secrets, and records local change policy. | tests/test_phase6_admin_compliance_maintenance.py |
| US408 | Should Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Cấu hình hệ thống | system config overview exposes safe settings, redacts secrets, and records local change policy. | tests/test_phase6_admin_compliance_maintenance.py |
| US410 | Should Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Cấu hình hệ thống | system config overview exposes auth/Teams/AI configuration categories without leaking secret values. | tests/test_phase6_admin_compliance_maintenance.py |
| US411 | Should Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Cấu hình hệ thống | system config overview exposes auth/Teams/AI configuration categories without leaking secret values. | tests/test_phase6_admin_compliance_maintenance.py |
| US418 | Must Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Phòng ban | department ops evidence summarizes active/inactive departments, manager assignment, and user distribution behind admin/HR permissions. | tests/test_phase6_admin_compliance_maintenance.py |
| US419 | Should Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Phòng ban | department ops evidence summarizes active/inactive departments, manager assignment, and user distribution behind admin/HR permissions. | tests/test_phase6_admin_compliance_maintenance.py |
| US421 | Must Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Thông báo hệ thống | system notification broadcast and evidence endpoints support privileged release/admin communication review. | tests/test_phase6_admin_compliance_maintenance.py |
| US422 | Should Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Thông báo hệ thống | system notification broadcast and evidence endpoints support privileged release/admin communication review. | tests/test_phase6_admin_compliance_maintenance.py |
| US423 | Should Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / License | license status endpoint reports local demo license mode, active users, usage counts, and external integration deferral. | tests/test_phase6_admin_compliance_maintenance.py |
| US424 | Must Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / License | license status endpoint reports local demo license mode, active users, usage counts, and external integration deferral. | tests/test_phase6_admin_compliance_maintenance.py |
| US426 | Must Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Cấu hình hệ thống | system config overview exposes safe settings, redacts secrets, and records local change policy. | tests/test_phase6_admin_compliance_maintenance.py |
| US427 | Must Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Cấu hình hệ thống | system config overview exposes safe settings, redacts secrets, and records local change policy. | tests/test_phase6_admin_compliance_maintenance.py |
| US429 | Must Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Audit & Compliance | compliance evidence summarizes request backlog, lineage domains, export endpoint, and manual-review no-hard-delete policy. | tests/test_phase6_admin_compliance_maintenance.py |
| US431 | Must Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Admin Panel | admin release panel summarizes available admin, config, license, compliance, maintenance, QA, and release-gate surfaces. | tests/test_phase6_admin_compliance_maintenance.py |
| US437 | Should Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Admin Panel | admin release panel summarizes available admin, config, license, compliance, maintenance, QA, and release-gate surfaces. | tests/test_phase6_admin_compliance_maintenance.py |
| US441 | Should Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Thông báo hệ thống | system notification broadcast and evidence endpoints support privileged release/admin communication review. | tests/test_phase6_admin_compliance_maintenance.py |
| US443 | Should Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E8: Admin & Config / Audit & Compliance | compliance evidence summarizes request backlog, lineage domains, export endpoint, and manual-review no-hard-delete policy. | tests/test_phase6_admin_compliance_maintenance.py |
| US494 | Should Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E10: Testing & QA / Performance Testing | QA release evidence documents local synthetic performance smoke through benchmark command and release-gate journeys. | tests/test_phase6_admin_compliance_maintenance.py |
| US497 | Must Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E10: Testing & QA / UAT | QA release evidence links the UAT template and marks stakeholder signoff as a tracked release evidence item. | tests/test_phase6_admin_compliance_maintenance.py |
| US502 | Must Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E10: Testing & QA / Test Data | QA test-data inventory reports seeded/test bootstrap counts, seed/reset policy, and demo account documentation. | tests/test_phase6_admin_compliance_maintenance.py |
| US507 | Should Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E10: Testing & QA / Performance Testing | QA release evidence documents local synthetic performance smoke through benchmark command and release-gate journeys. | tests/test_phase6_admin_compliance_maintenance.py |
| US509 | Should Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E10: Testing & QA / Monitoring | QA release evidence and release gate expose monitoring health/readiness/metrics/release-gate endpoints and queue counts. | tests/test_phase6_admin_compliance_maintenance.py; tests/test_ops_dashboard.py |
| US510 | Must Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E10: Testing & QA / Security Testing | QA release evidence records security-header, login-lockout, audit-export, redaction, and production-auth safety checks. | tests/test_phase6_admin_compliance_maintenance.py; tests/test_auth_security_hardening.py |
| US513 | Should Have | Done | Phase 6 - Admin, Compliance, Operations, QA Release Gate | E10: Testing & QA / Monitoring | QA release evidence and release gate expose monitoring health/readiness/metrics/release-gate endpoints and queue counts. | tests/test_phase6_admin_compliance_maintenance.py; tests/test_ops_dashboard.py |

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

- Default the MVP to Teams-ready Simulation Mode because the current student Teams account cannot provide tenant/admin approval for production app upload, SSO, or Graph permissions.
- Do not claim production Teams integration in release evidence until a Microsoft 365 Developer/E5 tenant is available.
- Harden Teams-ready behavior through the web simulator, local tab preview, Adaptive Card JSON, queue retry, and readiness endpoints.
- Keep Graph-backed channel posting behind environment-controlled configuration with mocked test path only.
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
