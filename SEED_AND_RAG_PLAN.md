# Seed Full Data and RAG Plan

## 1. Scope

Audit nay danh gia codebase hien tai de lap ke hoach seed full demo data va seed RAG. Tai lieu nay chi la ke hoach; khong thay doi code ung dung, schema, migration, seeder hay test.

Nguon da audit:

- `app/database.py`: schema SQLite/PostgreSQL, `init_db()`, seed RBAC va auth demo account mac dinh.
- `app/migrations.py`: migration bo sung cot/index, RAG pgvector, auth/RBAC/department.
- `app/repository.py`: data access, quan he nghiep vu, ACL RAG.
- `app/seed.py`: seeder demo hien co.
- `app/rag.py`, `app/routers/rag.py`, `app/routers/ai.py`: RAG ingestion/query va AI task breakdown dung RAG context.
- `tests/test_demo_seed.py`, `tests/test_rag_pgvector.py`, `tests/test_rbac_rag.py`: ky vong hien tai cua seed/RAG.
- `README.md`, `docs/PHASE_5_RAG_PGVECTOR.md`, `docs/AUTH_RBAC_DEPARTMENT_IMPLEMENTATION_REPORT.md`: mo ta van hanh.

## 2. DB Models / Schema Hien Tai

Codebase khong dung ORM. Schema duoc khai bao bang SQL thu cong trong `app/database.py`, sau do duoc bo sung qua migrations.

### Core identity and RBAC

| Table | Vai tro | Cot chinh | Rang buoc / ghi chu |
|---|---|---|---|
| `users` | Nhan su / tai khoan | `id`, `full_name`, `email`, `aad_object_id`, `role`, `department`, `password_hash`, `role_id`, `department_id`, `position`, `avatar_url`, `is_active`, `created_at`, `updated_at` | `email` unique, `aad_object_id` unique. Vua giu legacy `role`/`department` dang text, vua co `role_id`/`department_id`. |
| `roles` | Vai tro RBAC | `slug`, `name`, `description`, `is_system`, `code`, `is_system_role` | `slug` primary key. Co ca legacy lowercase va canonical uppercase roles. |
| `permissions` | Quyen | `key`, `name`, `description`, `category`, `code`, `module` | `key` primary key. |
| `role_permissions` | Role-permission mapping | `role_slug`, `permission_key` | Primary key gom 2 cot. |
| `departments` | Phong ban | `id`, `name`, `code`, `description`, `manager_user_id`, `is_active`, `created_at` | `name` unique, `code` unique. `manager_user_id` chua co FK trong migration add-column. |

### Project delivery

| Table | Vai tro | Cot chinh | Rang buoc / ghi chu |
|---|---|---|---|
| `projects` | Du an | `id`, `name`, `description`, `department_id`, `manager_id`, `start_date`, `end_date`, `status`, `created_at` | `status`: `active`, `on_hold`, `done`, `archived`. FK den departments/users trong schema moi. |
| `project_members` | Thanh vien du an | `id`, `project_id`, `user_id`, `role`, `joined_at` | Unique `(project_id, user_id)`. |
| `sprints` | Sprint cua project | `id`, `project_id`, `name`, `goal`, `start_date`, `end_date`, `status`, `created_at` | `status`: `planned`, `active`, `completed`. |
| `tasks` | Cong viec Kanban | `id`, `title`, `description`, `assignee_id`, `project_id`, `sprint_id`, `story_points`, `difficulty`, `status`, `deadline`, `completed_at`, `created_at`, `updated_at` | `difficulty`: `easy`, `medium`, `hard`; `status`: `todo`, `doing`, `done`. |
| `task_comments` | Binh luan task | `id`, `task_id`, `author_user_id`, `body`, `created_at` | Dung cho detail, notification va RAG-like noi dung demo. |
| `sprint_capacity_plans` | Capacity theo sprint/user | `id`, `sprint_id`, `user_id`, `capacity_hours`, `allocated_hours`, `created_at` | Unique `(sprint_id, user_id)`. Hien duoc dung nhu proxy capacity points. |

### KPI, reports, ops

| Table | Vai tro | Cot chinh | Rang buoc / ghi chu |
|---|---|---|---|
| `kpi_adjustments` | Dieu chinh diem KPI | `id`, `user_id`, `month`, `points`, `reason`, `created_by`, `created_at` | KPI thang tinh tu tasks + adjustments. |
| `project_risks` | Risk register | `id`, `project_id`, `title`, `description`, `probability`, `impact`, `mitigation_plan`, `owner_user_id`, `status`, `created_at` | `probability`/`impact`: `low`, `medium`, `high`; `status`: `open`, `mitigated`, `closed`. |
| `weekly_status_updates` | Bao cao weekly / RAG status | `id`, `project_id`, `sprint_id`, `week_label`, `progress_percent`, `rag_status`, `summary`, `next_steps`, `blocker`, `created_by`, `created_at` | `rag_status`: `red`, `amber`, `green`; day la R/A/G status, khong phai module Retrieval-Augmented Generation. |
| `audit_logs` | Audit trail | `id`, `actor_user_id`, `action`, `entity`, `entity_id`, `detail`, `created_at` | Dung cho ops dashboard va audit endpoint. |
| `app_notifications` | In-app notifications | `id`, `user_id`, `type`, `title`, `message`, `entity_type`, `entity_id`, `is_read`, `created_at`, `read_at` | `type`: `task_due_soon`, `task_overdue`, `task_comment`, `task_status_changed`. |
| `notification_queue` | Teams proactive queue | `id`, `user_id`, `channel`, `payload`, `status`, `attempts`, `max_attempts`, `last_error`, `next_retry_at`, `created_at`, `sent_at` | `status`: `queued`, `sent`, `failed`. |
| `teams_conversation_refs` | Teams conversation ref | `id`, `user_id`, `aad_object_id`, `conversation_id`, `service_url`, `tenant_id`, `channel_id`, `created_at` | `conversation_id` unique. Seed demo hien tai reset bang nay nhung khong tao ref mau. |

### AI and RAG

| Table | Vai tro | Cot chinh | Rang buoc / ghi chu |
|---|---|---|---|
| `ai_task_drafts` | AI-generated task draft | `id`, `source_type`, `source_summary`, `source_name`, `generated_tasks`, `status`, `reviewer_id`, `reviewed_at`, `imported_at`, `review_note`, `edit_reason`, `created_by`, `created_at` | `generated_tasks` la JSON text. `status`: `draft`, `reviewed`, `imported`. |
| `rag_documents` | Tai lieu RAG | `id`, `title`, `source_label`, `project_id`, `storage_path`, `created_by`, `created_at` | Bat buoc gan `project_id` o API/schema hien tai. |
| `rag_chunks` | Chunk cua document | `id`, `document_id`, `content`, `source_label`, `chunk_index`, `char_count`, `token_estimate`, `created_at` | Chunk size target 1000 chars, overlap 150 chars. |
| `rag_chunk_embeddings` | Embedding per chunk | `id`, `chunk_id`, `provider`, `model`, `dim`, `version`, `embedding_json` hoac `embedding vector(1536)`, `created_at` | Unique `(chunk_id, provider, model, version)`. SQLite dung JSON; Postgres co the dung pgvector. |
| `rag_document_permissions` | ACL RAG | `id`, `document_id`, `project_id`, `user_id`, `role_slug`, `access_level`, `created_at` | Unique `(document_id, project_id, user_id, role_slug)`. Access default `query`. |
| `schema_migrations` | Migration tracking | `version`, `name`, `applied_at` | Tao trong `app/migrations.py`. |

## 3. Seeders Hien Co

### `init_db()` trong `app/database.py`

Chay khi FastAPI startup va trong tests. Thu tu:

1. Tao schema theo dialect SQLite/PostgreSQL.
2. Chay migrations 1-6.
3. `_seed_rbac_defaults(conn)`: upsert roles, permissions, role_permissions.
4. `_seed_auth_demo_accounts(conn)`: upsert departments auth co ban va 6 account demo.

Tinh chat:

- RBAC defaults idempotent bang `ON CONFLICT`.
- Auth demo accounts idempotent theo `LOWER(email)`, co update profile va set active.
- Email trong migration co logic normalize reserved domain tu `@teamswork.local` sang `@teamswork.example.com`, nhung `_seed_auth_demo_accounts` van khai bao email `@teamswork.local`. Can canh giac neu chay migration truoc seed va seed lai sau do.

### `seed_auth_demo_accounts()` trong `app/seed.py`

Seeder public cho auth demo accounts, duoc tests goi truc tiep. Tuong tu `_seed_auth_demo_accounts`, nhung:

- Co set `password_hash = COALESCE(password_hash, new_hash)` khi user ton tai.
- Tao 5 departments mac dinh: `ADM`, `PMO`, `ENG`, `HR`, `AUD`.
- Tao/cap nhat 6 account: Admin, Manager, Leader, Member, HR, Auditor.

### `seed_data()` trong `app/seed.py`

Seeder demo rong, dang duoc expose qua `POST /seed/init` va test bang `tests/test_demo_seed.py`.

Thu tu hien tai:

1. `reset_demo_data(conn)`: DELETE cac bang trong `DEMO_TABLES`.
2. `seed_departments`: tao 7 department demo.
3. `seed_users`: tao 20 user demo.
4. `seed_projects`: tao 3 project.
5. `seed_sprints`: tao 7 sprint moi project, tong 21.
6. `seed_members`: tao project membership.
7. `seed_tasks`: tao 100 tasks.
8. `seed_capacity`: tao sprint capacity.
9. `seed_risks`: tao project risks.
10. `seed_weekly_updates`: tao weekly status.
11. `seed_kpi_adjustments`: tao 5 KPI adjustments.
12. `seed_notifications_comments_audit`: tao task comments, app notifications, notification queue, audit logs.
13. `seed_ai_and_rag`: tao AI drafts, RAG docs/chunks/placeholder embeddings/permissions.
14. Tra ve summary counts.

Counts ky vong tu tests:

- `users`: 20
- `departments`: 7
- `projects`: 3
- `sprints`: 21
- `tasks`: 100
- `project_risks`: >= 6
- `weekly_status_updates`: >= 12
- `kpi_adjustments`: 5
- `task_comments`: 250
- `app_notifications`: 7
- `notification_queue`: 4
- `ai_task_drafts`: 4
- `rag_documents`: 4
- `rag_chunks`: 8

Rui ro lon: `seed_data()` hien tai destructive, xoa ca `users`, `departments`, projects, tasks, RAG, audit, queue. No giu RBAC tables vi `roles`, `permissions`, `role_permissions` khong nam trong `DEMO_TABLES`, nhung se xoa auth demo accounts do `init_db()`.

## 4. Bang Can Seed Cho Full Demo

### Bat buoc

1. `departments`
2. `users`
3. `project_members`
4. `projects`
5. `sprints`
6. `tasks`
7. `task_comments`
8. `sprint_capacity_plans`
9. `kpi_adjustments`
10. `project_risks`
11. `weekly_status_updates`
12. `ai_task_drafts`
13. `rag_documents`
14. `rag_chunks`
15. `rag_chunk_embeddings`
16. `rag_document_permissions`
17. `audit_logs`
18. `app_notifications`
19. `notification_queue`

### Nen de `init_db()` quan ly

1. `roles`
2. `permissions`
3. `role_permissions`
4. `schema_migrations`

Khong nen seed lai 3 bang RBAC trong full demo seed, tru khi la buoc upsert idempotent rieng co test bao ve.

### Tuy chon

1. `teams_conversation_refs`: chi nen seed neu can demo Teams proactive voi conversation ref gia lap. Khong nen dua `service_url`/tenant real vao seed.
2. `storage_path` cho `rag_documents`: chi seed metadata neu co file mau trong repo, khong tro toi duong dan production.

## 5. Quan He Du Lieu Nghiep Vu

### Users, roles, departments

- `users.role_id` tro logic den `roles.slug`, nhung schema hien tai khong enforce FK cho cot add sau migration.
- `users.role` la legacy lowercase (`admin`, `manager`, `staff`, `hr`); `users.role_id` la canonical uppercase (`ADMIN`, `MANAGER`, `LEADER`, `MEMBER`, `HR`, `AUDITOR`) hoac legacy tuy du lieu.
- `canonical_role_code()` map `staff/member` thanh `MEMBER`; `legacy_role_slug()` map `MEMBER` thanh `staff`, `LEADER` thanh `manager`, `AUDITOR` thanh `hr`.
- `users.department_id` lien ket den `departments.id`; `users.department` giu ten legacy.
- `departments.manager_user_id` nen tro den user co role `MANAGER`, `LEADER`, `HR` hoac `ADMIN` tuy phong ban.

### Departments, teams, projects

Codebase hien chua co table `teams` rieng. Khai niem team duoc bieu dien bang:

- `departments`: co cau to chuc.
- `project_members`: team theo tung project.
- `project_members.role`: role trong du an (`project_manager`, `business_analyst`, `backend_developer`, `qa_tester`, ...).

Ke hoach seed full data nen xem "teams" la project team unless sau nay them table moi.

### Projects, sprints, tasks

- `projects.department_id` gan project ve phong ban chu quan.
- `projects.manager_id` gan PM/manager.
- `project_members.project_id` + `user_id` cap quyen project access cho non-admin/non-HR.
- `sprints.project_id` bat buoc thuoc project.
- `tasks.project_id` optional nhung demo nen gan day du.
- `tasks.sprint_id` optional nhung demo nen gan phan lon vao sprint de burndown/review/workload co y nghia.
- `tasks.assignee_id` bat buoc den `users.id`.
- `task_comments.task_id` va `author_user_id` tao lich su cong tac.

### KPI and reports

- KPI khong co bang tong hop rieng; `calculate_monthly_kpi()` tinh realtime tu `tasks` theo `deadline`, `completed_at`, `status`, `difficulty`, `story_points`, cong/tru `kpi_adjustments`.
- Reports dung:
  - KPI: `tasks` + `users` + `kpi_adjustments`.
  - Portfolio/project progress: `projects` + `tasks`.
  - Sprint review: `sprints` + `tasks`.
  - Ops dashboard: `audit_logs`, `notification_queue`, overdue tasks.
- Full demo seed phai co tasks phan bo qua nhieu thang (`YYYY-MM`), status done on-time, done late, doing/todo overdue de KPI/report co du lieu.

### RAG and AI

- `rag_documents.project_id` quyet dinh scope chinh.
- `rag_chunks.document_id` la noi dung search.
- `rag_document_permissions` la ACL truy van. `create_rag_document()` hien them row `(document_id, project_id, user_id=NULL, role_slug=NULL, access_level='query')`.
- `_rag_acl_clause()` cho admin/hr xem tat ca documents co `project_id`; user khac xem neu la project manager, project member, duoc grant user-specific, hoac role_slug match.
- `ai_task_drafts.generated_tasks` luu JSON task de xuat; import moi tao `tasks` that.
- `app/routers/ai.py` neu `use_rag=true` se query RAG, build context, truyen vao `breakdown_requirements()`, roi luu draft.

## 6. Module RAG Hoat Dong Nhu The Nao

### Ingestion

1. API `POST /rag/documents` yeu cau permission `rag.manage` va project access.
2. Payload gom `title`, `source_label`, `project_id`, `content`.
3. `chunk_text()` normalize whitespace, cat chunk target 1000 chars, min 900, max 1100, overlap 150.
4. `create_rag_document()` insert document, chunks, va permission mac dinh.
5. `_try_store_embeddings()` chi chay neu `RAG_EMBEDDING_ENABLED=true`, backend pgvector, va provider hop le.

### Query

1. API `POST /rag/query` yeu cau permission `rag.query`.
2. `query_rag()` tokenize query; limit mac dinh tu `RAG_SEARCH_LIMIT`, max 10.
3. Neu embeddings + pgvector san sang:
   - Embed query qua OpenAI-compatible `/embeddings`.
   - Search semantic bang `<=>` trong Postgres vector.
   - Neu loi, fallback lexical.
4. Luon lay lexical candidates tu `list_rag_chunks(limit=500, current_user=...)`.
5. Merge semantic + lexical candidates.
6. Score hybrid:
   - Semantic mode: `0.60 semantic + 0.25 lexical + 0.10 tfidf + 0.05 phrase`.
   - Fallback mode: `0.75 lexical + 0.20 tfidf + 0.05 phrase`.
7. Loc theo `RAG_SCORE_THRESHOLD` mac dinh `0.45`, sort score giam dan.

### ACL

- Admin/HR: xem documents co `project_id IS NOT NULL`.
- Manager/staff/leader/member: can la `projects.manager_id`, `project_members`, grant theo `user_id`, hoac grant theo `role_slug`.
- Existing unscoped RAG docs (`project_id NULL`) khong tra ve trong project-scoped query.

### Gioi han

- Local/dev mac dinh `RAG_EMBEDDING_ENABLED=false`, dung lexical fallback.
- PDF/OCR chua implemented/disabled default.
- Seeder hien tai tao placeholder embedding provider `demo`, model `lexical-placeholder`, embedding null. Du lieu nay khong giup semantic pgvector, nhung khong can cho lexical fallback.

## 7. Noi Nen Dat File Seed

Khuyen nghi giu seed code trong `app/seed.py` cho compatibility hien tai, nhung tach thanh cac nhom ro rang:

1. `app/seed.py`
   - Giu public entrypoints hien co: `seed_auth_demo_accounts()`, `seed_data()`.
   - Them entrypoint tuong lai: `seed_full_demo_data(mode="upsert"|"reset")`, `seed_rag_demo_data(mode="upsert"|"reset")`.
   - Giu helper DB dialect/table utilities vi da co pattern.

2. `app/seed_data/` hoac `app/demo_data/`
   - Dat fixture data dang Python constants hoac JSON.
   - Goi y file:
     - `departments.py` / `departments.json`
     - `users.py`
     - `projects.py`
     - `tasks.py`
     - `rag_documents.py`
   - Loi ich: giam `app/seed.py` dang qua dai, de audit duplicate keys.

3. `scripts/seed_full_demo.py`
   - CLI runner cho local/admin ops, goi function trong `app.seed`.
   - Co flag ro: `--reset-demo`, `--upsert`, `--rag-only`.

4. API endpoint
   - Hien co `POST /seed/init` destructive. Nen giu cho test/demo reset.
   - Neu them endpoint moi, nen tao endpoint rieng nhu `POST /seed/full-demo` hoac query `mode=upsert|reset`, chi cho `monitoring.admin`.

Khong nen dat seed trong migrations, vi demo data co tinh van hanh, khong phai schema invariant.

## 8. Rui Ro Duplicate / Pha Du Lieu

### Rui ro destructive

- `reset_demo_data()` DELETE `users`, `departments`, `projects`, `tasks`, RAG, audit, queue... Neu goi tren database co du lieu that se mat du lieu.
- `DEMO_TABLES` co `users` va `departments`, nen goi `/seed/init` se xoa ca auth demo accounts va bat ky user that nao.
- `DELETE` khong co namespace marker, khong phan biet demo vs production/user-created data.

Bien phap:

- Them guard moi truong: chi cho reset khi `APP_ENV != production` hoac co flag explicit.
- Them `demo_namespace`/`source_label` convention de seed theo namespace.
- Default seed moi nen la upsert idempotent, reset chi la option ro rang.

### Rui ro duplicate

- Nhieu bang thieu unique key theo business identity:
  - `projects.name` khong unique.
  - `sprints` khong unique `(project_id, name)`.
  - `tasks` khong unique theo demo key.
  - `rag_documents` khong unique `(project_id, source_label)`.
  - `rag_chunks` khong unique `(document_id, chunk_index)`.
  - `ai_task_drafts` khong unique source/demo key.
  - `audit_logs`, comments, notifications se duplicate neu seed upsert naive.
- `project_members` va `sprint_capacity_plans` co unique keys nen duplicate se fail neu khong upsert.
- `users.email`, `departments.code`, `roles.slug`, `permissions.key` co unique keys nen phu hop upsert.

Bien phap:

- Dung deterministic demo keys:
  - User: email.
  - Department: code.
  - Project: stable `source_label` khong co trong schema; tam dung exact name + namespace prefix.
  - Sprint: project name + sprint name.
  - Task: can them convention title prefix/code trong title hoac task source map trong fixture.
  - RAG document: `source_label` + `project_id`.
- Truoc khi insert child data, resolve parent IDs bang natural keys.
- Voi child repeatable data, nen delete theo parent/demo source truoc khi reinsert, khong delete toan bang.

### Rui ro encoding

- `app/seed.py` hien co nhieu chuoi tieng Viet bi mojibake. Neu seed full data phuc vu demo UI/RAG, nen thay bang UTF-8 dung trong fixture moi.
- Neu `ensure_ascii=True`, JSON van an toan ASCII nhung text hien thi trong DB/API phu thuoc source string dung encoding.

### Rui ro RBAC role legacy/canonical

- Role co ca legacy lowercase va uppercase. Seed users can set ca:
  - `role`: legacy slug phu hop (`admin`, `manager`, `staff`, `hr`).
  - `role_id`: canonical (`ADMIN`, `MANAGER`, `LEADER`, `MEMBER`, `HR`, `AUDITOR`).
- RAG ACL dang so sanh `current_user["role"]`, co the la legacy. Neu grant `role_slug='manager'` thi manager legacy match; neu grant `MANAGER` co the khong match tuy payload. Nen seed RAG permission dua vao project membership/user access hon la role_slug chung.

### Rui ro RAG semantic

- Placeholder embeddings null khong dung cho pgvector semantic. Neu bat `RAG_EMBEDDING_ENABLED=true`, can embed lai chunks bang provider that.
- Neu Postgres column la vector, insert null placeholder hop le nhung semantic query chi tim rows co embedding; lexical fallback van duoc.
- Score threshold 0.45 co the loai document demo neu query/demo text khong overlap tu khoa. Seed RAG can co keywords lap lai theo cac demo query mong muon.

### Rui ro production/external

- Seed khong nen tao Teams webhook/service URL/token real.
- `notification_queue.payload` phai la demo payload, khong chua secret.
- Audit detail nen ngan va khong chua credential.

## 9. De Xuat Data Demo Can Seed Theo Role

Muc tieu: moi role dang nhap thay duoc man hinh chinh, co du lieu dung quyen, va co hanh vi khac nhau de demo RBAC.

### Admin (`ADMIN` / `admin`)

Nen seed:

- 1 admin active co password demo.
- Du lieu tren tat ca departments/projects.
- Audit logs da co nhieu action: seed, create project, update task, import AI, KPI adjust.
- Ops dashboard: notification queue co `queued`, `sent`, `failed`; overdue spike co top project/sprint.
- RBAC data day du roles/permissions.
- RAG docs tren tat ca projects de admin query all.

Demo scenarios:

- Xem users, roles, permissions.
- Chay seed endpoint trong local/demo.
- Xem audit/ops.
- Xem portfolio va export report all.
- Quan ly RAG documents.

### Manager (`MANAGER` / `manager`)

Nen seed:

- 3 managers, moi nguoi quan ly 1 project.
- Moi project co 7 sprints, task phan bo done/doing/todo, co overdue.
- Project members gom BA, UX, backend, frontend/mobile, QA.
- Weekly status moi project co red/amber/green.
- Project risks co owner va mitigation.
- AI drafts: it nhat 1 draft `draft`, 1 `reviewed`, 1 `imported`.
- RAG docs project-scoped cho project cua manager.

Demo scenarios:

- Manager chi thay project minh quan ly/member.
- Tao task, sprint, risk, weekly status.
- Review/import AI draft.
- Query RAG theo project.
- Xem KPI team va export reports.

### Leader (`LEADER`)

Nen seed:

- 2 leaders trong Engineering/QA, la project member va assignee nhieu tasks.
- Gan vai tro project_members nhu `tech_lead`, `qa_lead`.
- Tasks cua team co workload warning va capacity.
- RAG query permission qua project membership.

Demo scenarios:

- Xem kanban/project duoc tham gia.
- Cap nhat task team/own theo permission hien co.
- Xem KPI team neu permission cho phep.
- Query RAG nhung khong manage RAG.

### Member (`MEMBER` / `staff`)

Nen seed:

- 6-10 members thuoc WEB/MOB/QA/BA/UX.
- Moi member co:
  - 2-4 tasks done on time.
  - 1 task done late.
  - 1 task doing.
  - 0-1 overdue task.
  - Comment cua PM/QA tren task.
  - App notification unread.
- Capacity trong sprint active.

Demo scenarios:

- Chi xem task/KPI cua minh.
- Cap nhat own task status.
- Xem notifications.
- Khong xem ops/admin/RBAC.
- Query RAG chi voi project dang la member neu co `rag.query`.

### HR (`HR` / `hr`)

Nen seed:

- 1-2 HR users.
- Departments co `manager_user_id`, member counts ro rang.
- KPI adjustments do HR/admin tao cho mot so users.
- Reports all/team.
- Khong can lam project member nhung HR duoc ACL project access theo `require_project_access`.

Demo scenarios:

- Xem users/departments.
- Tao/deactivate user trong demo.
- Xem KPI all/team va reports.
- Xem ops dashboard neu co `OPS_VIEW`.

### Auditor (`AUDITOR`)

Nen seed:

- 1 auditor active.
- Audit logs da co du lieu da dang.
- Reports va ops read-only.
- Khong seed project membership neu muon demo read-only qua permission, khong qua membership.

Demo scenarios:

- Xem audit logs theo filter.
- Export/read reports all.
- Khong tao/sua task/project/user.

## 10. De Xuat Full Demo Dataset

### Organization

- 7 departments:
  - `ADM` Administration
  - `PMO` Project Management Office
  - `PBA` Product & Business Analysis
  - `UXD` UI/UX Design
  - `WEB` Web Engineering
  - `MOB` Mobile Engineering
  - `QA` Quality Assurance
  - Co the them `OPS` Operations neu can Teams/Ops demo.
- Moi department co manager_user_id hop ly va 2-8 members.

### Users

- 1 Admin
- 3 Managers
- 2 Leaders
- 10-14 Members
- 2 HR
- 1 Auditor

Tong hop ly: 20-24 users. Neu muon giu tests hien tai, `seed_data()` cu van 20 users; dataset moi co the la `full_demo` rieng.

### Projects

- 3-4 projects:
  - Internal PM & KPI platform
  - Mobile commerce app
  - Field service app
  - Optional: Data/reporting modernization
- Moi project:
  - Department owner.
  - Manager.
  - 6-8 project members.
  - 5-7 sprints.
  - 25-40 tasks.
  - 2-4 risks.
  - 4-6 weekly status updates.

### Sprints and tasks

- Sprint statuses:
  - 2 completed
  - 1 active
  - 2 planned
- Task statuses:
  - 45-55% done
  - 25-35% doing
  - 10-20% todo
- KPI coverage:
  - It nhat 3 thang gan nhau.
  - Done on-time, done late, overdue unfinished.
  - Story points/difficulty da dang.
- Workload:
  - It nhat 1 under-capacity user.
  - It nhat 1 overloaded user.
  - It nhat 1 user missing capacity.
  - It nhat 1 sprint co overdue warnings.

### Reports / ops

- `kpi_adjustments`: 5-8 rows, ca positive/negative, do admin/HR/manager tao.
- `audit_logs`: 20-40 rows, gom create/update/import/export/seed/requeue.
- `app_notifications`: 10-20 rows, read/unread.
- `notification_queue`: 5-8 rows, queued/sent/failed/retry.

### AI/RAG

- `ai_task_drafts`: 6-10 rows:
  - 2 draft
  - 2 reviewed
  - 2 imported
  - source_type ca `text` va `docx`
- `rag_documents`: 2-4 docs moi project:
  - Project brief
  - Requirements/spec
  - Sprint/UAT notes
  - Risk/decision log
- `rag_chunks`: tuy content, moi doc 1-4 chunks.
- `rag_document_permissions`: nen tao theo project default + optional role/user grants.
- Embeddings:
  - Local/dev: placeholder row optional, lexical la chinh.
  - Postgres embedding mode: chay job embed rieng sau seed, khong hardcode vector mau.

## 11. Ke Hoach Seed RAG Cu The

### Local/dev lexical seed

1. Tao RAG documents bang content text co keywords trung voi demo query:
   - "KPI dashboard", "overdue task", "sprint review", "UAT", "RBAC", "Teams notification".
   - "mobile cart", "voucher", "order tracking", "push notification".
   - "GPS check-in", "offline sync", "photo evidence", "SLA dashboard".
2. Chunk bang `chunk_text()` de char_count/token_estimate dung logic.
3. Insert `rag_documents`, `rag_chunks`, `rag_document_permissions`.
4. Khong can insert `rag_chunk_embeddings`; hoac insert placeholder null nhu hien tai chi de count demo.
5. Test query voi `RAG_EMBEDDING_ENABLED=false`.

### Postgres pgvector seed

1. Seed same documents/chunks.
2. Neu `RAG_EMBEDDING_ENABLED=true` va co `AI_API_KEY`, goi provider embed tung chunk bang `store_rag_chunk_embedding()`.
3. Neu provider fail, log warning va giu lexical fallback.
4. Khong block full demo seed vi embedding service loi.

### ACL seed

Recommended:

- Moi document co default row `user_id=NULL`, `role_slug=NULL`, `access_level='query'` gan `project_id`.
- Project manager/member xem duoc qua project ACL.
- Them user-specific grant chi khi can demo document rieng.
- Tranh role_slug broad grant neu khong can, vi legacy/canonical role slug co the gay mismatch.

## 12. De Xuat Implementation Phases Sau Audit

### Phase 1: Bao ve seeding

- Them mode ro rang: `reset` vs `upsert`.
- Them guard production cho destructive reset.
- Them summary/dry-run counts.
- Giu `seed_data()` hien tai neu tests phu thuoc, nhung document ro la destructive demo reset.

### Phase 2: Tach fixture data

- Chuyen constants lon khoi `app/seed.py` sang `app/demo_data/`.
- Sua encoding tieng Viet bi mojibake.
- Dinh nghia natural keys cho moi entity.

### Phase 3: Idempotent full data seed

- Upsert parent tables theo natural key.
- Reconcile child tables theo namespace/project source thay vi xoa toan DB.
- Them test chay seed 2 lan khong duplicate.

### Phase 4: RAG seed rieng

- Tao `seed_rag_demo_data(project_ids, user_ids, mode)`.
- Them test query lexical theo role/project ACL.
- Optional CLI `scripts/seed_full_demo.py --rag-only`.

### Phase 5: Verification

- Chay:
  - `pytest tests/test_demo_seed.py -q`
  - `pytest tests/test_rag_pgvector.py tests/test_rbac_rag.py -q`
  - `pytest tests/test_api_flow.py -q`
- Neu co seed endpoint moi, them test permission/production guard.

## 13. Checklist Chap Nhan

- Seed full demo chay 2 lan khong duplicate.
- Reset demo khong the chay o production neu khong co override an toan.
- RBAC defaults khong bi xoa/sua ngoai y muon.
- Moi role dang nhap co du lieu demo rieng va bi gioi han dung quyen.
- KPI thang co du lieu cho done on-time, done late, overdue unfinished va adjustments.
- Reports co du lieu cho KPI, project progress, sprint review, portfolio.
- RAG query local lexical tra ket qua dung project scope.
- AI task breakdown voi `use_rag=true` tra `retrieved_context_count > 0` cho query demo.
- No seed secret, webhook URL, bearer token, tenant/service URL that.
