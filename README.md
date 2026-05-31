# TeamsWork / QLDA

![Ngôn ngữ: Tiếng Việt](https://img.shields.io/badge/Ngon_ngu-Tieng_Viet-2B579A?style=for-the-badge)![Language: English](https://img.shields.io/badge/Language-English-555555?style=for-the-badge)**TeamsWork** là nền tảng quản lý dự án, công việc, KPI, báo cáo, Microsoft Teams và AI task breakdown cho vận hành nội bộ.

---

## Tiếng Việt

> Chọn nhanh ngôn ngữ: [Tiếng Việt](#ti%E1%BA%BFng-vi%E1%BB%87t) | [English](#english)

### Tổng Quan

TeamsWork là ứng dụng quản lý công việc và dự án nội bộ, tập trung vào các luồng vận hành hằng ngày của đội dự án:

- Quản lý người dùng, phòng ban, vai trò, quyền hạn và thành viên dự án.
- Quản lý dự án, sprint, task Kanban, workload và cảnh báo quá tải.
- Theo dõi KPI hằng tháng theo deadline, độ khó, story point và điều chỉnh thủ công có audit.
- Xuất báo cáo CSV, XLSX và PDF cho KPI, tiến độ dự án và portfolio.
- Tích hợp Microsoft Teams cho tab nội bộ, nhắc việc, hàng đợi proactive notification và đồng bộ AAD.
- Dùng AI để phân tích yêu cầu từ text hoặc file `.docx`, tạo draft task để manager/admin review trước khi import.
- Dùng RAG để lưu tri thức dự án, truy vấn ngữ cảnh và hỗ trợ AI task breakdown chính xác hơn.
- Hỗ trợ SQLite cho local/dev và PostgreSQL cho Docker hoặc môi trường production-like.

Ứng dụng ưu tiên tính thực dụng: giao diện gọn, mật độ thông tin cao, phân quyền rõ ràng, phù hợp cho quản trị dự án và vận hành nội bộ hơn là landing page marketing.

### Tính Năng Chính

| Nhóm | Chức năng |
| --- | --- |
| Identity & RBAC | Đăng nhập JWT, header fallback cho dev, role `admin`, `manager`, `staff`, `hr`, bảng permission có thể cấu hình. |
| Organization | Quản lý users, departments, project members và quyền truy cập theo project. |
| Delivery | Projects, sprints, Kanban tasks, task comments, story points, deadline, status và workload warnings. |
| KPI | KPI tháng tính từ task hoàn thành đúng hạn/trễ hạn, độ khó, story point và điều chỉnh KPI. |
| Reports | Export KPI, project progress, sprint review và portfolio ở CSV/XLSX/PDF. |
| AI | Tạo AI task draft từ requirement text hoặc `.docx`, review/chỉnh sửa trước khi import vào Kanban. |
| RAG | Ingest tài liệu dự án, chunking, lexical search mặc định, pgvector optional, ACL theo project. |
| Microsoft Teams | Teams tab, AAD sync, reminder runner, bot callback, proactive queue, retry/requeue. |
| Audit & Ops | Audit logs, notification queue status, overdue spike dashboard và readiness/metrics endpoints. |

### Kiến Trúc Ngắn Gọn

```text
Browser / Teams Tab
        |
        v
FastAPI app
  |-- Auth / RBAC
  |-- Projects / Sprints / Tasks
  |-- KPI / Reports
  |-- AI Task Breakdown
  |-- RAG Documents / Query
  |-- Teams Integrations
  |-- Audit / Monitoring
        |
        v
SQLite local/dev hoặc PostgreSQL Docker/production-like
        |
        +-- Ollama/OpenAI-compatible chat completions cho AI
        +-- Optional pgvector + embeddings cho semantic RAG
```

### Tech Stack

- Python 3.12+
- FastAPI, Uvicorn
- Pydantic v2
- SQLite cho local/dev
- PostgreSQL 16 cho Docker/production-like
- Pytest
- `python-docx` cho requirement `.docx`
- `openpyxl` và `reportlab` cho báo cáo
- OpenAI-compatible local AI qua Ollama/Qwen
- Optional PostgreSQL `pgvector` cho RAG semantic search

### Cấu Trúc Thư Mục

```text
.
|-- app/                         # FastAPI application, routers, repository, DB, AI/RAG logic
|-- docs/                        # Tài liệu triển khai, RAG, RBAC, seed, quality gate
|-- scripts/                     # Seed, smoke check, backup, migration, package Teams app
|-- teams-app/                   # Microsoft Teams app manifest/assets/checklist
|-- tests/                       # Pytest suite
|-- DESIGN.md                    # Quy chuẩn UI
|-- DEPLOYMENT_RUNBOOK.md        # Checklist triển khai
|-- SEED_AND_RAG_PLAN.md         # Kế hoạch seed full demo và RAG
|-- docker-compose.yml           # API + PostgreSQL local stack
|-- requirements.txt             # Python dependencies
`-- README.md                    # Tài liệu này
```

### Cài Đặt Local

Tạo môi trường Python và cài dependency:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Chạy API:

```bash
uvicorn app.main:app --reload
```

Mở ứng dụng:

- UI: <http://127.0.0.1:8000/ui/>
- API docs: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

### Chạy Bằng Docker

```bash
docker compose up --build
```

Docker Compose sẽ chạy:

- `api`: FastAPI app ở cổng `8000`
- `postgres`: PostgreSQL 16 ở cổng `5432`

Biến `DATABASE_URL_DOCKER` trong `.env.example` đã trỏ tới service `postgres` trong Compose network.

### Cấu Hình Môi Trường

File mẫu:

- `.env.example`: local/dev
- `.env.staging.example`: staging
- `.env.production.example`: production

Các nhóm biến quan trọng:

```env
APP_BASE_URL=http://localhost:8000
APP_ENV=development
DATABASE_URL=postgresql://teamswork:teamswork@localhost:5432/teamswork
AUTH_JWT_SECRET=dev-secret-change-me
AUTH_DISABLE_JWT_VALIDATION=true
AUTH_ALLOW_HEADER_FALLBACK=true
```

Khuyến nghị production:

- Đặt `APP_ENV=production`.
- Đặt `AUTH_DISABLE_JWT_VALIDATION=false`.
- Đặt `AUTH_ALLOW_HEADER_FALLBACK=false`.
- Thay `AUTH_JWT_SECRET` bằng secret mạnh.
- Không commit secret, token, webhook URL hoặc service URL thật vào repo.

### Authentication Và RBAC

Production mode dùng JWT bearer:

```env
AUTH_DISABLE_JWT_VALIDATION=false
AUTH_ALLOW_HEADER_FALLBACK=false
AUTH_JWT_SECRET=change-me-with-a-strong-secret
```

Local/dev có thể dùng header fallback:

```http
X-User-Id: 1
```

Vai trò mặc định:

| Role | Mục đích |
| --- | --- |
| `admin` | Quản trị hệ thống, seed, audit, RBAC, báo cáo và dữ liệu toàn cục. |
| `manager` | Quản lý project, sprint, task, KPI team, AI review/import và RAG theo project. |
| `staff` | Xem và cập nhật task/KPI của chính mình theo quyền được cấp. |
| `hr` | Xem user, department, KPI và báo cáo liên quan nhân sự. |

RBAC được seed bằng các bảng `roles`, `permissions` và `role_permissions`. Router mới nên ưu tiên `require_permission(...)` để có thể đổi quyền theo role mà không sửa code.

Endpoint RBAC:

- `GET /rbac/roles`
- `GET /rbac/permissions`
- `GET /rbac/roles/{role_slug}/permissions`
- `PUT /rbac/roles/{role_slug}/permissions`

Permission đáng chú ý:

- `roles.view`, `roles.manage`
- `users.create`, `users.view`
- `tasks.create`, `tasks.update_any`, `tasks.update_own`
- `projects.manage`, `projects.view`
- `sprints.manage`, `sprints.view`
- `kpi.view`, `kpi.adjust`
- `reports.export`
- `ai.preview`, `ai.import`
- `rag.manage`, `rag.query`
- `teams.view`, `teams.manage`
- `monitoring.view`, `monitoring.admin`

### AI Task Breakdown

AI chỉ tạo task đề xuất. Task thật trong Kanban chỉ được tạo sau khi manager/admin review và import draft.

Luồng sử dụng:

1. Mở tab AI trên UI.
2. Dán requirement hoặc upload file `.docx`.
3. Bấm tạo task để hệ thống lưu một AI draft ở trạng thái `draft`.
4. Manager/admin mở danh sách `AI drafts`.
5. Review, chỉnh task đề xuất và ghi note/reason nếu cần.
6. Draft chuyển sang trạng thái `reviewed`.
7. Chọn assignee/project nếu cần, sau đó import vào Kanban.
8. Draft đã `imported` không được import lại.

Endpoint liên quan:

- `POST /ai/task-breakdown`
- `POST /ai/task-breakdown/docx`
- `GET /ai/task-breakdown/drafts`
- `GET /ai/task-breakdown/drafts/{draft_id}`
- `PATCH /ai/task-breakdown/drafts/{draft_id}/review`
- `POST /ai/task-breakdown/import`

### Cấu Hình AI Local Với Ollama/Qwen

Mặc định `.env.example` dùng OpenAI-compatible API qua Ollama:

```env
AI_PROVIDER=openai_compatible
AI_API_KEY=ollama
AI_BASE_URL=http://localhost:11434/v1
AI_MODEL=qwen3:8b
AI_FALLBACK_MODEL=qwen2.5:7b
AI_TASK_BREAKDOWN_TIMEOUT_SECONDS=20
```

Chạy model:

```bash
ollama pull qwen3:8b
ollama pull qwen2.5:7b
ollama serve
```

Backend gọi API theo chuẩn OpenAI-compatible `/chat/completions`. Nếu model chính lỗi, hệ thống thử model fallback. Nếu AI local không sẵn sàng, module dùng heuristic local để demo không bị chặn.

### RAG Knowledge Base

RAG dùng để lưu spec, biên bản họp, checklist hoặc yêu cầu nghiệp vụ theo project. Khi AI task breakdown bật `use_rag`, backend truy vấn kho RAG để bổ sung ngữ cảnh.

Đặc điểm chính:

- Tài liệu bắt buộc gắn `project_id`.
- Nội dung được chia chunk có overlap.
- Local/dev có thể chạy lexical/BM25 + TF-IDF fallback, không cần pgvector.
- PostgreSQL production-like có thể bật `RAG_VECTOR_BACKEND=pgvector` và `RAG_EMBEDDING_ENABLED=true`.
- ACL RAG theo project access, project members, manager và permission.

Biến môi trường:

```env
RAG_VECTOR_BACKEND=pgvector
RAG_EMBEDDING_ENABLED=false
RAG_EMBEDDING_PROVIDER=openai_compatible
RAG_EMBEDDING_MODEL=text-embedding-3-small
RAG_EMBEDDING_DIM=1536
RAG_SCORE_THRESHOLD=0.45
RAG_SEARCH_LIMIT=5
RAG_STORAGE_ROOT=.data/rag_uploads
RAG_PDF_ENABLED=false
```

Endpoint liên quan:

- `POST /rag/documents`
- `GET /rag/documents`
- `DELETE /rag/documents/{document_id}`
- `POST /rag/query`

Permission liên quan:

- `rag.manage`: thêm và xóa tài liệu RAG.
- `rag.query`: xem danh sách tài liệu và truy vấn RAG.

Giới hạn hiện tại:

- PDF optional và đang tắt mặc định.
- OCR chưa được bật như một luồng chính.
- Embeddings optional; lexical fallback là mặc định cho local/dev.

### Seed Demo Data

Cần có user admin trước khi seed qua API:

```http
POST /seed/init
X-User-Id: 1
```

Dữ liệu mẫu gồm user, phòng ban, dự án, sprint, task, capacity, risk, weekly status, AI draft và RAG document.

Full demo seed idempotent cho local/dev/demo:

```bash
python scripts/seed_full_demo.py --upsert
python scripts/seed_full_demo.py --rag-only
python scripts/seed_full_demo.py --reset-demo
```

Final demo evidence capture:

```bash
uvicorn app.main:app --reload
python scripts/smoke_check.py --base-url http://127.0.0.1:8000 --user-id 1 --expect-production-auth
python scripts/capture_demo_evidence.py --base-url http://127.0.0.1:8000
```

Artifacts are written to `.tmp/demo-evidence/<timestamp>/`.

Xem thêm:

- `docs/DEMO_SEED.md`
- `SEED_AND_RAG_PLAN.md`

Lưu ý: `--reset-demo` chỉ dành cho local/dev/demo. Không seed secret, token, webhook hoặc service URL thật.

### Task API Và Bộ Lọc

Endpoint chính cho task:

- `POST /tasks`
- `GET /tasks`
- `PATCH /tasks/{task_id}/status`

`GET /tasks` hỗ trợ:

- `project_id`
- `sprint_id`
- `assignee_id`
- `status`: `todo`, `doing`, `done`
- `overdue`: `true` để lấy task quá hạn chưa done, `false` để loại task quá hạn
- `keyword`: tìm trong `title` và `description`
- `deadline_from`, `deadline_to`: ISO datetime

Role `staff` chỉ thấy task được gán cho chính mình. Hiện tại task chưa có field `priority`, nên API chưa hỗ trợ filter theo priority.

### Workload Và Capacity Theo Sprint

Endpoint:

- `GET /sprints/{sprint_id}/workload-warnings`

Response tổng hợp workload theo từng assignee:

- `workload_points`: tổng `story_points` của task chưa `done` trong sprint.
- `capacity_points`: MVP tạm dùng `sprint_capacity_plans.capacity_hours` làm proxy.
- `overloaded`: `true` khi workload vượt capacity.
- `overdue_task_count`: số task chưa `done` đã quá deadline.
- `risk_level`: `high`, `medium` hoặc `low`.

RBAC:

- `admin`, `manager`, `hr` xem dữ liệu sprint/project có quyền truy cập.
- `staff` chỉ thấy workload của chính mình.

### Microsoft Teams

Teams integration đã có scaffold:

- Teams tab: `GET /teams/tab`
- Production tab: `GET /teams/tab/prod`
- AAD identity: `GET /integrations/teams/aad/me`
- AAD sync: `POST /integrations/teams/aad/sync`
- Reminder runner: `POST /integrations/teams/reminders/run`
- Bot callback: `POST /integrations/teams/bot/messages`
- Adaptive Card action callback: `POST /integrations/teams/card/actions`
- Proactive queue: `POST /integrations/teams/proactive/queue`
- Teams tab summary: `GET /integrations/teams/summary?month=YYYY-MM`
- Queue processor: `POST /integrations/teams/proactive/process`
- Requeue failed item: `POST /integrations/teams/proactive/requeue/{notification_id}`

Teams app assets nằm trong `teams-app/`. Script đóng gói:

```bash
python scripts/package_teams_app.py
```

Checklist publish nằm ở `teams-app/PUBLISH_CHECKLIST.md`.

Phase 4 Teams release behavior:

- Bot commands are local-testable: `/help`, `/task-list`, `/team-kpi`, `/my-deadlines`, `/top-kpi`, `/search`, `/new-task`, `/assign`, `/status`, `/report`.
- Data-changing bot commands and Adaptive Card actions require a mapped Teams `aadObjectId` and existing TeamsWork RBAC permissions.
- Proactive queue payloads support `dedup_key` and `target` metadata for user, webhook, channel, and project-channel routing.
- Microsoft Graph channel posting is disabled by default. It only runs when `TEAMS_PROACTIVE_MODE=graph` and `TEAMS_CLIENT_ID`, `TEAMS_CLIENT_SECRET`, `TEAMS_TENANT_ID`, `TEAMS_GRAPH_TEAM_ID`, and `TEAMS_GRAPH_CHANNEL_ID` are configured.
- Tests mock Graph calls; local demo and default config do not send real Teams messages.

### Audit & Ops Dashboard

Audit & Ops là dashboard vận hành tối thiểu cho:

- Audit logs
- Teams notification queue
- Overdue spike
- Monitoring readiness/metrics

Endpoint:

- `GET /monitoring/ops`
- `GET /audit/logs`
- `GET /monitoring/readiness`
- `GET /monitoring/metrics`

Filter audit:

- `actor_id`
- `action`
- `entity_type`
- `date_from`, `date_to`
- `keyword`
- `limit`

Dashboard không trả webhook URL, bearer token, client secret, raw provider stack trace hoặc raw queue payload.

### Endpoint Chính

| Nhóm | Endpoint |
| --- | --- |
| Users | `POST /users`, `GET /users` |
| Auth | `POST /auth/token` |
| RBAC | `GET /rbac/roles`, `GET /rbac/permissions`, `PUT /rbac/roles/{role_slug}/permissions` |
| Departments | `POST /departments`, `GET /departments` |
| Projects | `POST /projects`, `GET /projects`, `POST /projects/{project_id}/members` |
| Sprints | `POST /projects/{project_id}/sprints`, `PATCH /sprints/{sprint_id}/status`, `GET /sprints/{sprint_id}/workload-warnings` |
| Tasks | `POST /tasks`, `GET /tasks`, `PATCH /tasks/{task_id}/status` |
| KPI | `GET /kpi/monthly?month=YYYY-MM`, `POST /kpi/adjustments` |
| Dashboard | `GET /dashboard/summary?month=YYYY-MM` |
| Reports | `GET /reports/kpi.csv`, `GET /reports/kpi.xlsx`, `GET /reports/kpi.pdf`, `GET /reports/projects/progress.csv`, `GET /reports/projects/progress.xlsx` |
| RAG | `POST /rag/documents`, `GET /rag/documents`, `DELETE /rag/documents/{document_id}`, `POST /rag/query` |
| Portfolio | `GET /portfolio/summary` |
| Monitoring | `GET /monitoring/readiness`, `GET /monitoring/metrics`, `GET /monitoring/ops` |
| Audit | `GET /audit/logs` |

### Test Và Quality Gate

Chạy toàn bộ test:

```bash
pytest -q
```

Chạy riêng luồng API, AI và RBAC/RAG:

```bash
pytest tests/test_api_flow.py tests/test_ai_task_breakdown.py tests/test_rbac_rag.py
```

Quality gate mặc định:

- Test phải chạy qua `pytest -q`.
- `pytest.ini` chỉ collect test trong `tests/`.
- UI thay đổi theo `DESIGN.md`.
- Backend, RBAC, KPI, Teams, AI import và security thay đổi theo `AGENTS.md`.

### Migration, Backup Và Smoke Check

Migrate SQLite sang PostgreSQL:

```bash
python scripts/migrate_sqlite_to_postgres.py --sqlite teamswork.db --postgres-dsn "postgresql://teamswork:teamswork@localhost:5432/teamswork"
```

Backup PostgreSQL:

```powershell
./scripts/backup_postgres.ps1 -PostgresDsn "postgresql://teamswork:teamswork@localhost:5432/teamswork" -OutputDir "backups"
```

Smoke check sau deploy:

```bash
python scripts/smoke_check.py --base-url https://teamswork.example.com --user-id 1 --expect-production-auth
```

### Tài Liệu Liên Quan

- `DESIGN.md`: baseline thiết kế UI.
- `DEPLOYMENT_RUNBOOK.md`: checklist triển khai.
- `SEED_AND_RAG_PLAN.md`: kế hoạch seed full data và RAG.
- `docs/PHASE_5_RAG_PGVECTOR.md`: chi tiết RAG/pgvector.
- `docs/DEMO_SEED.md`: dữ liệu demo.
- `docs/AUTH_RBAC_DEPARTMENT_IMPLEMENTATION_REPORT.md`: auth/RBAC/department.
- `docs/QUALITY_GATE.md`: quality gate.
- `teams-app/PUBLISH_CHECKLIST.md`: checklist publish Teams app.

### Quy Ước Phát Triển

- Giữ giao diện compact, dễ scan, phù hợp công cụ vận hành nội bộ.
- Không hiển thị bearer token, webhook URL, client secret hoặc raw provider error trên UI.
- Các endpoint thay đổi dữ liệu cần RBAC rõ ràng.
- Task AI chỉ được import sau khi đã review.
- Seed destructive chỉ dùng cho local/dev/demo.
- Không hardcode secret; dùng biến môi trường.
- Review `git diff` trước khi push.

---

## English

> Quick language switch: [Tiếng Việt](#ti%E1%BA%BFng-vi%E1%BB%87t) | [English](#english)

### Overview

TeamsWork is an internal project operations platform for work management, KPI tracking, reporting, Microsoft Teams workflows, and AI-assisted task breakdown.

It is designed for daily project delivery and internal operations:

- Manage users, departments, roles, permissions, and project members.
- Manage projects, sprints, Kanban tasks, workload, and overload warnings.
- Track monthly KPI from deadlines, difficulty, story points, and audited manual adjustments.
- Export CSV, XLSX, and PDF reports for KPI, project progress, and portfolio views.
- Integrate with Microsoft Teams tabs, reminders, proactive notification queues, and AAD sync.
- Use AI to turn text or `.docx` requirements into reviewed task drafts.
- Use RAG to store project knowledge and retrieve context for AI task breakdown.
- Run with SQLite for local/dev or PostgreSQL for Docker and production-like environments.

The product is intentionally practical: dense, readable, role-aware, and optimized for internal teams rather than marketing presentation.

### Core Features

| Area | Capability |
| --- | --- |
| Identity & RBAC | JWT auth, dev header fallback, roles `admin`, `manager`, `staff`, `hr`, configurable permissions. |
| Organization | Users, departments, project members, and project-scoped access control. |
| Delivery | Projects, sprints, Kanban tasks, comments, story points, deadlines, statuses, and workload warnings. |
| KPI | Monthly KPI from on-time/late task completion, difficulty, story points, and manual adjustments. |
| Reports | KPI, project progress, sprint review, and portfolio exports in CSV/XLSX/PDF. |
| AI | Task draft generation from text or `.docx`, with review/edit before Kanban import. |
| RAG | Project document ingestion, chunking, default lexical search, optional pgvector, and project ACL. |
| Microsoft Teams | Teams tab, AAD sync, reminder runner, bot callback, proactive queue, retry/requeue. |
| Audit & Ops | Audit logs, notification queue status, overdue spike dashboard, readiness and metrics endpoints. |

### Architecture

```text
Browser / Teams Tab
        |
        v
FastAPI app
  |-- Auth / RBAC
  |-- Projects / Sprints / Tasks
  |-- KPI / Reports
  |-- AI Task Breakdown
  |-- RAG Documents / Query
  |-- Teams Integrations
  |-- Audit / Monitoring
        |
        v
SQLite local/dev or PostgreSQL Docker/production-like
        |
        +-- Ollama/OpenAI-compatible chat completions for AI
        +-- Optional pgvector + embeddings for semantic RAG
```

### Tech Stack

- Python 3.12+
- FastAPI, Uvicorn
- Pydantic v2
- SQLite for local/dev
- PostgreSQL 16 for Docker/production-like
- Pytest
- `python-docx` for `.docx` requirements
- `openpyxl` and `reportlab` for reporting
- OpenAI-compatible local AI through Ollama/Qwen
- Optional PostgreSQL `pgvector` for semantic RAG search

### Repository Layout

```text
.
|-- app/                         # FastAPI application, routers, repository, DB, AI/RAG logic
|-- docs/                        # Deployment, RAG, RBAC, seed, quality gate docs
|-- scripts/                     # Seed, smoke check, backup, migration, Teams package scripts
|-- teams-app/                   # Microsoft Teams app manifest/assets/checklist
|-- tests/                       # Pytest suite
|-- DESIGN.md                    # UI design baseline
|-- DEPLOYMENT_RUNBOOK.md        # Deployment checklist
|-- SEED_AND_RAG_PLAN.md         # Full demo seed and RAG plan
|-- docker-compose.yml           # API + PostgreSQL local stack
|-- requirements.txt             # Python dependencies
`-- README.md                    # This document
```

### Local Setup

Create a Python environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Open the app:

- UI: <http://127.0.0.1:8000/ui/>
- API docs: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

### Docker

```bash
docker compose up --build
```

Docker Compose starts:

- `api`: FastAPI app on port `8000`
- `postgres`: PostgreSQL 16 on port `5432`

`DATABASE_URL_DOCKER` in `.env.example` already points to the `postgres` service inside the Compose network.

### Environment Configuration

Template files:

- `.env.example`: local/dev
- `.env.staging.example`: staging
- `.env.production.example`: production

Important variables:

```env
APP_BASE_URL=http://localhost:8000
APP_ENV=development
DATABASE_URL=postgresql://teamswork:teamswork@localhost:5432/teamswork
AUTH_JWT_SECRET=dev-secret-change-me
AUTH_DISABLE_JWT_VALIDATION=true
AUTH_ALLOW_HEADER_FALLBACK=true
```

Production recommendations:

- Set `APP_ENV=production`.
- Set `AUTH_DISABLE_JWT_VALIDATION=false`.
- Set `AUTH_ALLOW_HEADER_FALLBACK=false`.
- Replace `AUTH_JWT_SECRET` with a strong secret.
- Never commit real secrets, tokens, webhook URLs, or service URLs.

### Authentication And RBAC

Production mode uses JWT bearer auth:

```env
AUTH_DISABLE_JWT_VALIDATION=false
AUTH_ALLOW_HEADER_FALLBACK=false
AUTH_JWT_SECRET=change-me-with-a-strong-secret
```

Local/dev can use header fallback:

```http
X-User-Id: 1
```

Default roles:

| Role | Purpose |
| --- | --- |
| `admin` | System administration, seed, audit, RBAC, reports, and global data. |
| `manager` | Project, sprint, task, team KPI, AI review/import, and project RAG management. |
| `staff` | View and update own tasks/KPI according to assigned permissions. |
| `hr` | View users, departments, KPI, and HR-related reports. |

RBAC is seeded through `roles`, `permissions`, and `role_permissions`. New routers should prefer `require_permission(...)` so role permissions can change without code changes.

RBAC endpoints:

- `GET /rbac/roles`
- `GET /rbac/permissions`
- `GET /rbac/roles/{role_slug}/permissions`
- `PUT /rbac/roles/{role_slug}/permissions`

Notable permissions:

- `roles.view`, `roles.manage`
- `users.create`, `users.view`
- `tasks.create`, `tasks.update_any`, `tasks.update_own`
- `projects.manage`, `projects.view`
- `sprints.manage`, `sprints.view`
- `kpi.view`, `kpi.adjust`
- `reports.export`
- `ai.preview`, `ai.import`
- `rag.manage`, `rag.query`
- `teams.view`, `teams.manage`
- `monitoring.view`, `monitoring.admin`

### AI Task Breakdown

AI only proposes tasks. Real Kanban tasks are created only after a manager/admin reviews and imports the draft.

Workflow:

1. Open the AI tab in the UI.
2. Paste requirements or upload a `.docx` file.
3. Generate tasks; the system stores an AI draft with status `draft`.
4. A manager/admin opens `AI drafts`.
5. Review, edit proposed tasks, and add notes/reasons if needed.
6. The draft moves to `reviewed`.
7. Choose assignee/project if needed, then import into Kanban.
8. A draft with status `imported` cannot be imported again.

Related endpoints:

- `POST /ai/task-breakdown`
- `POST /ai/task-breakdown/docx`
- `GET /ai/task-breakdown/drafts`
- `GET /ai/task-breakdown/drafts/{draft_id}`
- `PATCH /ai/task-breakdown/drafts/{draft_id}/review`
- `POST /ai/task-breakdown/import`

### Local AI With Ollama/Qwen

`.env.example` defaults to an OpenAI-compatible API through Ollama:

```env
AI_PROVIDER=openai_compatible
AI_API_KEY=ollama
AI_BASE_URL=http://localhost:11434/v1
AI_MODEL=qwen3:8b
AI_FALLBACK_MODEL=qwen2.5:7b
AI_TASK_BREAKDOWN_TIMEOUT_SECONDS=20
```

Run the models:

```bash
ollama pull qwen3:8b
ollama pull qwen2.5:7b
ollama serve
```

The backend calls the OpenAI-compatible `/chat/completions` API. If the primary model fails, it tries the fallback model. If local AI is unavailable, the module uses a local heuristic so demos do not block.

### RAG Knowledge Base

RAG stores project specs, meeting notes, checklists, or business requirements. When AI task breakdown uses `use_rag`, the backend retrieves project context before generating task drafts.

Key behavior:

- Documents must be attached to `project_id`.
- Content is split into overlapping chunks.
- Local/dev can run lexical/BM25 + TF-IDF fallback without pgvector.
- PostgreSQL production-like environments can enable `RAG_VECTOR_BACKEND=pgvector` and `RAG_EMBEDDING_ENABLED=true`.
- RAG ACL follows project access, project members, managers, and permissions.

Environment variables:

```env
RAG_VECTOR_BACKEND=pgvector
RAG_EMBEDDING_ENABLED=false
RAG_EMBEDDING_PROVIDER=openai_compatible
RAG_EMBEDDING_MODEL=text-embedding-3-small
RAG_EMBEDDING_DIM=1536
RAG_SCORE_THRESHOLD=0.45
RAG_SEARCH_LIMIT=5
RAG_STORAGE_ROOT=.data/rag_uploads
RAG_PDF_ENABLED=false
```

Related endpoints:

- `POST /rag/documents`
- `GET /rag/documents`
- `DELETE /rag/documents/{document_id}`
- `POST /rag/query`

Related permissions:

- `rag.manage`: add and delete RAG documents.
- `rag.query`: list documents and query RAG.

Current limits:

- PDF support is optional and disabled by default.
- OCR is not part of the main flow yet.
- Embeddings are optional; lexical fallback is the default for local/dev.

### Demo Seed Data

An admin user is required before API seed:

```http
POST /seed/init
X-User-Id: 1
```

Demo data includes users, departments, projects, sprints, tasks, capacity, risks, weekly status, AI drafts, and RAG documents.

Idempotent full demo seed for local/dev/demo:

```bash
python scripts/seed_full_demo.py --upsert
python scripts/seed_full_demo.py --rag-only
python scripts/seed_full_demo.py --reset-demo
```

Final demo evidence capture:

```bash
uvicorn app.main:app --reload
python scripts/smoke_check.py --base-url http://127.0.0.1:8000 --user-id 1 --expect-production-auth
python scripts/capture_demo_evidence.py --base-url http://127.0.0.1:8000
```

Artifacts are written to `.tmp/demo-evidence/<timestamp>/`.

See also:

- `docs/DEMO_SEED.md`
- `SEED_AND_RAG_PLAN.md`

Note: `--reset-demo` is only for local/dev/demo. Do not seed real secrets, tokens, webhooks, or service URLs.

### Task API And Filters

Primary task endpoints:

- `POST /tasks`
- `GET /tasks`
- `PATCH /tasks/{task_id}/status`

`GET /tasks` supports:

- `project_id`
- `sprint_id`
- `assignee_id`
- `status`: `todo`, `doing`, `done`
- `overdue`: `true` for unfinished overdue tasks, `false` to exclude overdue tasks
- `keyword`: search in `title` and `description`
- `deadline_from`, `deadline_to`: ISO datetime

The `staff` role only sees tasks assigned to the current user. Tasks do not currently have a `priority` field, so priority filtering is not supported yet.

### Sprint Workload And Capacity

Endpoint:

- `GET /sprints/{sprint_id}/workload-warnings`

The response summarizes workload per assignee:

- `workload_points`: sum of `story_points` for unfinished tasks in the sprint.
- `capacity_points`: MVP proxy from `sprint_capacity_plans.capacity_hours`.
- `overloaded`: `true` when workload exceeds capacity.
- `overdue_task_count`: unfinished overdue tasks in the sprint.
- `risk_level`: `high`, `medium`, or `low`.

RBAC:

- `admin`, `manager`, and `hr` can view sprint/project data they can access.
- `staff` only sees their own workload.

### Microsoft Teams

Teams integration scaffold:

- Teams tab: `GET /teams/tab`
- Production tab: `GET /teams/tab/prod`
- AAD identity: `GET /integrations/teams/aad/me`
- AAD sync: `POST /integrations/teams/aad/sync`
- Reminder runner: `POST /integrations/teams/reminders/run`
- Bot callback: `POST /integrations/teams/bot/messages`
- Adaptive Card action callback: `POST /integrations/teams/card/actions`
- Proactive queue: `POST /integrations/teams/proactive/queue`
- Teams tab summary: `GET /integrations/teams/summary?month=YYYY-MM`
- Queue processor: `POST /integrations/teams/proactive/process`
- Requeue failed item: `POST /integrations/teams/proactive/requeue/{notification_id}`

Teams app assets live in `teams-app/`. Package script:

```bash
python scripts/package_teams_app.py
```

Publishing checklist: `teams-app/PUBLISH_CHECKLIST.md`.

Phase 4 Teams release behavior:

- Bot commands are local-testable: `/help`, `/task-list`, `/team-kpi`, `/my-deadlines`, `/top-kpi`, `/search`, `/new-task`, `/assign`, `/status`, `/report`.
- Data-changing bot commands and Adaptive Card actions require a mapped Teams `aadObjectId` and existing TeamsWork RBAC permissions.
- Proactive queue payloads support `dedup_key` and `target` metadata for user, webhook, channel, and project-channel routing.
- Microsoft Graph channel posting is disabled by default. It only runs when `TEAMS_PROACTIVE_MODE=graph` and `TEAMS_CLIENT_ID`, `TEAMS_CLIENT_SECRET`, `TEAMS_TENANT_ID`, `TEAMS_GRAPH_TEAM_ID`, and `TEAMS_GRAPH_CHANNEL_ID` are configured.
- Tests mock Graph calls; local demo and default config do not send real Teams messages.

### Audit & Ops Dashboard

Audit & Ops is a minimal operations dashboard for:

- Audit logs
- Teams notification queue
- Overdue spike
- Monitoring readiness/metrics

Endpoints:

- `GET /monitoring/ops`
- `GET /audit/logs`
- `GET /monitoring/readiness`
- `GET /monitoring/metrics`

Audit filters:

- `actor_id`
- `action`
- `entity_type`
- `date_from`, `date_to`
- `keyword`
- `limit`

The dashboard must not return webhook URLs, bearer tokens, client secrets, raw provider stack traces, or raw queue payloads.

### Main Endpoints

| Area | Endpoint |
| --- | --- |
| Users | `POST /users`, `GET /users` |
| Auth | `POST /auth/token` |
| RBAC | `GET /rbac/roles`, `GET /rbac/permissions`, `PUT /rbac/roles/{role_slug}/permissions` |
| Departments | `POST /departments`, `GET /departments` |
| Projects | `POST /projects`, `GET /projects`, `POST /projects/{project_id}/members` |
| Sprints | `POST /projects/{project_id}/sprints`, `PATCH /sprints/{sprint_id}/status`, `GET /sprints/{sprint_id}/workload-warnings` |
| Tasks | `POST /tasks`, `GET /tasks`, `PATCH /tasks/{task_id}/status` |
| KPI | `GET /kpi/monthly?month=YYYY-MM`, `POST /kpi/adjustments` |
| Dashboard | `GET /dashboard/summary?month=YYYY-MM` |
| Reports | `GET /reports/kpi.csv`, `GET /reports/kpi.xlsx`, `GET /reports/kpi.pdf`, `GET /reports/projects/progress.csv`, `GET /reports/projects/progress.xlsx` |
| RAG | `POST /rag/documents`, `GET /rag/documents`, `DELETE /rag/documents/{document_id}`, `POST /rag/query` |
| Portfolio | `GET /portfolio/summary` |
| Monitoring | `GET /monitoring/readiness`, `GET /monitoring/metrics`, `GET /monitoring/ops` |
| Audit | `GET /audit/logs` |

### Tests And Quality Gate

Run the full test suite:

```bash
pytest -q
```

Run API, AI, and RBAC/RAG flows:

```bash
pytest tests/test_api_flow.py tests/test_ai_task_breakdown.py tests/test_rbac_rag.py
```

Final demo evidence docs and scripts:

- `docs/FINAL_DEMO_SCRIPT.md`
- `docs/TRACEABILITY_MATRIX.md`
- `docs/TEST_EVIDENCE.md`
- `docs/FINAL_DEMO_SLIDES.md`
- `scripts/capture_demo_evidence.py`

Final demo evidence docs and scripts:

- `docs/FINAL_DEMO_SCRIPT.md`
- `docs/TRACEABILITY_MATRIX.md`
- `docs/TEST_EVIDENCE.md`
- `docs/FINAL_DEMO_SLIDES.md`
- `scripts/capture_demo_evidence.py`

Default quality gate:

- Tests should pass with `pytest -q`.
- `pytest.ini` only collects tests from `tests/`.
- UI changes must follow `DESIGN.md`.
- Backend, RBAC, KPI, Teams, AI import, and security changes must follow `AGENTS.md`.

### Migration, Backup, And Smoke Check

Migrate SQLite to PostgreSQL:

```bash
python scripts/migrate_sqlite_to_postgres.py --sqlite teamswork.db --postgres-dsn "postgresql://teamswork:teamswork@localhost:5432/teamswork"
```

Back up PostgreSQL:

```powershell
./scripts/backup_postgres.ps1 -PostgresDsn "postgresql://teamswork:teamswork@localhost:5432/teamswork" -OutputDir "backups"
```

Post-deploy smoke check:

```bash
python scripts/smoke_check.py --base-url https://teamswork.example.com --user-id 1 --expect-production-auth
```

### Related Docs

- `DESIGN.md`: UI design baseline.
- `DEPLOYMENT_RUNBOOK.md`: deployment checklist.
- `SEED_AND_RAG_PLAN.md`: full data seed and RAG plan.
- `docs/PHASE_5_RAG_PGVECTOR.md`: RAG/pgvector details.
- `docs/DEMO_SEED.md`: demo dataset.
- `docs/AUTH_RBAC_DEPARTMENT_IMPLEMENTATION_REPORT.md`: auth/RBAC/department.
- `docs/QUALITY_GATE.md`: quality gate.
- `teams-app/PUBLISH_CHECKLIST.md`: Teams app publishing checklist.

### Development Conventions

- Keep the UI compact, scannable, and suitable for internal operations.
- Do not expose bearer tokens, webhook URLs, client secrets, or raw provider errors in the UI.
- Data-changing endpoints need clear RBAC.
- AI-generated tasks must be reviewed before import.
- Destructive seed operations are only for local/dev/demo.
- Never hardcode secrets; use environment variables.
- Review `git diff` before pushing.

### Role Browser Audit

Install Chromium before running the Playwright role/navigation audit:

```bash
python -m playwright install chromium
pytest tests/test_ui_role_navigation_playwright.py
```

For a headed full-button demo run, slow Playwright down and use the temporary seeded database:

```powershell
$env:PLAYWRIGHT_HEADED='1'
$env:PLAYWRIGHT_SLOW_MO_MS='650'
$env:PLAYWRIGHT_DEMO_STEP_MS='450'
$env:PLAYWRIGHT_DEMO_NOTE_MS='800'
$env:PLAYWRIGHT_DEMO_AFTER_ACTION_MS='350'
.\.venv\Scripts\python.exe -m pytest tests\test_ui_full_button_audit_playwright.py -q
```

The full-button audit shifts temporary demo task deadlines and KPI adjustments into the current month so the KPI screens have visible demo data without touching the local `teamswork.db`. In headed mode it also shows a small `Running: role / module / action` note; set `PLAYWRIGHT_DEMO_NOTES='0'` to hide it.
