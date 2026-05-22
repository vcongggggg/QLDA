# Auth RBAC Department Implementation Report

## Hien Trang Ban Dau

- TeamsWork da co FastAPI backend, SQLite/PostgreSQL adapter, static frontend trong `app/static`.
- Auth cu dung `X-User-Id` de gia lap dang nhap va co endpoint admin `/auth/token`.
- RBAC cu da co `roles`, `permissions`, `role_permissions` voi role legacy `admin`, `manager`, `hr`, `staff`.
- `users.id` dang duoc task, KPI, project, audit va notification tham chieu, nen khong tao bang user moi.

## Entity/Bang Da Them Hoac Chinh

- `users`: bo sung `password_hash`, `role_id`, `department_id`, `position`, `avatar_url`, `is_active`, `created_at`, `updated_at`.
- `roles`: giu `slug` lam khoa tuong thich, bo sung `code`, `is_system_role`.
- `permissions`: giu `key` lam khoa tuong thich, bo sung `code`, `module`.
- `departments`: bo sung `description`, `manager_user_id`, `is_active`.
- `role_permissions`: giu quan he hien co, seed them permission code moi.
- Migration moi: `auth_rbac_department_schema`, idempotent va khong xoa du lieu cu.

## Roles, Permissions, Mapping

- Role moi: `ADMIN`, `MANAGER`, `LEADER`, `MEMBER`, `HR`, `AUDITOR`.
- Role legacy van duoc giu: `admin`, `manager`, `staff`, `hr`; backend map chung qua canonical role code de khong pha flow cu.
- Permission moi theo module: dashboard, kanban, project, KPI, report, AI task, team, user, role, department, audit, ops.
- Permission legacy van duoc giu de test/API cu tiep tuc hoat dong: `users.view`, `roles.manage`, `tasks.update_own`, `reports.export`, `monitoring.admin`, ...
- `ADMIN` co toan bo permission. `AUDITOR` co quyen xem audit/ops/report nhung khong co permission mutate nghiep vu. `MEMBER` chi co own task/KPI va view lien quan.

## API Da Them/Chinh

- `POST /auth/login`: dang nhap bang email/password, tra `accessToken` va user profile co role, department, permissions.
- `GET /auth/me`: reload user hien tai tu bearer token.
- `POST /auth/logout`: endpoint logout stateless cho FE.
- `GET /users`, `POST /users`, `PUT /users/{id}`, `PATCH /users/{id}/active`, `POST /users/{id}/reset-password`.
- `GET /departments`, `POST /departments`, `PUT /departments/{id}`, `DELETE /departments/{id}`, `GET /departments/{id}/members`.
- RBAC endpoints cu duoc giu, tra them metadata `code/module` khi co.

## Frontend Da Chinh

- `app/static/index.html`: them login screen, an app shell cho den khi co session, bo user switcher khoi production.
- `app/static/app.js`: them auth state, luu `tw_access_token`, goi `/auth/me` khi reload, gan `Authorization: Bearer`, logout, permission-gated navigation.
- `app/static/styles.css`: them style login/logout.
- Sidebar hien ten, role, department, avatar chu cai dau va logout.
- Admin hien them bang nhan vien/phong ban toi thieu, van giu RBAC permission matrix hien co.

## Cap Nhat Permission-Gated Sidebar Va Route Guard

- Sidebar hien menu theo permission VIEW tu `/auth/me`, khong hardcode role cho menu:
  - `hasPermission(code)`
  - `hasAnyPermission(codes)`
  - `canViewModule(module)`
- Mapping module view hien tai nam trong `MODULE_VIEW_PERMISSIONS`:
  - MEMBER thay dashboard/kanban/project/KPI/AI/teams neu co permission tuong ung; khong thay `Quan tri` hoac `Audit & Ops`.
  - AUDITOR thay `Audit & Ops` va report/audit-oriented surfaces; khong thay `Quan tri`.
  - ADMIN thay tat ca menu.
- Route guard doc URL truc tiep qua query/hash (`?section=admin`, `#admin`, `#/admin`). Neu user khong co VIEW permission, UI hien `Access Denied` thay vi load module.
- Cac nut thao tac duoc gate bang permission action:
  - report export can `REPORT_EXPORT`/`reports.export`.
  - AI generate/review/import can `AI_TASK_GENERATE`/`AI_TASK_REVIEW`/`AI_TASK_IMPORT` hoac legacy permission tuong ung.
  - task status/drag drop can permission update task.
  - RAG manage, seed init, RBAC save deu co guard rieng.
- Backend van giu permission checks tren API. Vi du `/users`, `/departments`, `/rbac`, `/monitoring/ops`, `/audit/logs` van tra 403 neu token/header user khong co permission phu hop.

## Migration/Seed

- Migration chay qua `init_db()` nhu hien tai.
- Demo auth accounts duoc seed idempotent trong `init_db()`:
  - `admin@teamswork.local / Admin@123`
  - `manager@teamswork.local / Manager@123`
  - `leader@teamswork.local / Leader@123`
  - `member@teamswork.local / Member@123`
  - `hr@teamswork.local / Hr@123`
  - `auditor@teamswork.local / Auditor@123`
- `seed_data()` demo lon van reset business data nhu cu va khong them 6 account auth de giu compatibility voi dataset/test hien co.

## Cap Nhat Seed Permission Theo UX Moi

- `MEMBER` khong co `USER_VIEW`, `ROLE_VIEW`, `DEPARTMENT_VIEW`, `AUDIT_VIEW`, `OPS_VIEW`.
- `AUDITOR` chi giu nhom xem dashboard/report/audit/ops va legacy permission doc ops; khong co permission sua user/task/project/RBAC.
- `HR` co `USER_VIEW`, `USER_CREATE`, `USER_UPDATE`, `USER_RESET_PASSWORD`, `DEPARTMENT_VIEW`; khong co `ROLE_MANAGE`.
- `MANAGER`/`LEADER` tap trung team/task/project/KPI/report/AI; khong co `USER_VIEW`, `ROLE_VIEW`, `DEPARTMENT_VIEW`, `AUDIT_VIEW`, `OPS_VIEW` nen khong thay module quan tri he thong hoac Audit & Ops tren sidebar.

## Checklist Test Da Chay

- `pytest tests/test_auth_rbac_department.py -q`
- `pytest tests/test_auth_rbac_department.py tests/test_ops_dashboard.py tests/test_api_flow.py tests/test_rbac_rag.py -q`
- `pytest tests/test_auth_rbac_department.py tests/test_api_flow.py tests/test_rbac_rag.py tests/test_kpi.py tests/test_demo_seed.py -q`
- `pytest -q`
- HTTP smoke tren server local: `POST /auth/login` va `GET /auth/me` voi `admin@teamswork.local`.

Ket qua: pass.

## TODO / Gioi Han

- Scope `LEADER`/`MANAGER` theo team nho hien moi dua vao project membership, manager project va department; neu co bang team rieng sau nay can tach ro hon.
- Frontend admin hien table toi thieu; create/edit/reset password co API san sang nhung UI form day du co the lam tiep.
- Refresh token chua them vi kien truc hien tai chua co refresh-token store; access token stateless la mac dinh.
