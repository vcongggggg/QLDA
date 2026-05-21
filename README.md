# QLDA - TeamsWork

TeamsWork la ung dung quan ly cong viec, KPI va du an noi bo, co API FastAPI, giao dien web tinh, bao cao CSV/XLSX/PDF, tich hop Microsoft Teams va module AI phan ra yeu cau thanh task.

## Tinh nang chinh

- Quan ly user, phong ban, du an, sprint va task.
- Kanban voi trang thai `todo`, `doing`, `done`.
- RBAC theo vai tro `admin`, `manager`, `staff`, `hr` va bang permission co the cau hinh.
- KPI hang thang voi diem theo deadline va do kho.
- Bao cao KPI, tien do du an, sprint review va portfolio.
- Hang doi thong bao Teams proactive, retry va requeue.
- AI task breakdown tu text hoac file `.docx`.
- Kho tri thuc RAG de bo sung ngu canh khi AI phan tich yeu cau.
- Import task AI da chon vao Kanban.
- SQLite cho dev local, PostgreSQL cho docker/production-like.

## Quy uoc phat trien

- UI thay doi theo `DESIGN.md`.
- Backend, RBAC, KPI, Teams, AI import va security thay doi theo `AGENTS.md`.
- Quality gate mac dinh la `pytest -q`; `pytest.ini` chi collect test trong `tests/`.

## Stack

- Python 3.12+
- FastAPI, Uvicorn
- Pydantic v2
- SQLite / PostgreSQL
- Pytest
- python-docx, openpyxl, reportlab
- AI local OpenAI-compatible qua Ollama/Qwen

## Cai dat local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Mo ung dung:

- UI: http://127.0.0.1:8000/ui/
- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## Cau hinh AI local Qwen

Mac dinh `.env.example` dung Ollama local:

```env
AI_PROVIDER=openai_compatible
AI_API_KEY=ollama
AI_BASE_URL=http://localhost:11434/v1
AI_MODEL=qwen3:8b
AI_FALLBACK_MODEL=qwen2.5:7b
AI_TASK_BREAKDOWN_TIMEOUT_SECONDS=20
```

Chay model bang Ollama:

```bash
ollama pull qwen3:8b
ollama pull qwen2.5:7b
ollama serve
```

Backend goi API theo chuan OpenAI-compatible `/chat/completions`. Neu model chinh loi, he thong thu model fallback; neu AI local khong san sang, module se dung heuristic local de demo khong bi dung luong.

## Luong AI review va import task

AI chi de xuat task. Task that trong Kanban chi duoc tao sau khi manager/admin review va import draft.

1. Mo tab AI tren UI.
2. Dan requirements hoac upload file `.docx`.
3. Bam tao task de he thong luu mot AI draft o trang thai `draft`.
4. Manager/admin mo bang `AI drafts`, review/chinh task de xuat va ghi note/reason neu can.
5. Sau review, draft chuyen sang `reviewed`.
6. Chon assignee va project neu co, bam import de tao task that trong Kanban.
7. Draft da `imported` khong duoc import lai.

Endpoint lien quan:

- `POST /ai/task-breakdown`
- `POST /ai/task-breakdown/docx`
- `GET /ai/task-breakdown/drafts`
- `GET /ai/task-breakdown/drafts/{draft_id}`
- `PATCH /ai/task-breakdown/drafts/{draft_id}/review`
- `POST /ai/task-breakdown/import`

Neu bat `use_rag`, backend se truy van kho RAG bang `rag_query` neu co, hoac dung noi dung requirements lam truy van. Ket qua tra ve them `retrieved_context_count` va `retrieved_sources` de UI/API biet AI da dung nguon nao.

## Kho tri thuc RAG

RAG dung cho viec luu spec, bien ban hop, checklist hoac yeu cau nghiep vu de bo sung ngu canh khi tao task bang AI. Tai lieu duoc chia thanh cac chunk nho va truy van bang matching tu khoa noi bo, khong can dich vu vector database trong moi truong local.

Endpoint lien quan:

- `POST /rag/documents`
- `GET /rag/documents`
- `DELETE /rag/documents/{document_id}`
- `POST /rag/query`

Permission lien quan:

- `rag.manage`: them va xoa tai lieu RAG.
- `rag.query`: xem danh sach tai lieu va truy van RAG.

## Authentication va RBAC

Production mode dung JWT bearer:

```env
AUTH_DISABLE_JWT_VALIDATION=false
AUTH_ALLOW_HEADER_FALLBACK=false
AUTH_JWT_SECRET=<strong-secret>
```

Local/dev co the dung header fallback:

```http
X-User-Id: 1
```

Vai tro mac dinh:

- `admin`: quan tri user, seed, audit, bao cao.
- `manager`: quan ly du an, sprint, task, KPI, AI import.
- `staff`: xem va cap nhat task/KPI cua minh.
- `hr`: xem user, KPI va bao cao lien quan.

He thong seed san bang `roles`, `permissions` va `role_permissions`. Cac router moi uu tien `require_permission(...)` de cho phep thay doi quyen theo vai tro ma khong can sua code.

Endpoint RBAC:

- `GET /rbac/roles`
- `GET /rbac/permissions`
- `GET /rbac/roles/{role_slug}/permissions`
- `PUT /rbac/roles/{role_slug}/permissions`

Permission quan trong:

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

## Seed data

Can co user admin truoc khi seed. Sau do goi:

```http
POST /seed/init
X-User-Id: <admin_id>
```

Du lieu mau gom user, phong ban, du an, sprint, task, capacity, risk va weekly status.

## Endpoint chinh

- `POST /users`, `GET /users`
- `POST /auth/token`
- `GET /rbac/roles`, `GET /rbac/permissions`
- `GET /rbac/roles/{role_slug}/permissions`
- `PUT /rbac/roles/{role_slug}/permissions`
- `POST /departments`, `GET /departments`
- `POST /projects`, `GET /projects`
- `POST /projects/{project_id}/members`
- `POST /projects/{project_id}/sprints`
- `PATCH /sprints/{sprint_id}/status`
- `GET /sprints/{sprint_id}/workload-warnings`
- `POST /tasks`, `GET /tasks`
- `PATCH /tasks/{task_id}/status`
- `GET /kpi/monthly?month=YYYY-MM`
- `POST /kpi/adjustments`
- `GET /dashboard/summary?month=YYYY-MM`
- `GET /reports/kpi.csv?month=YYYY-MM`
- `GET /reports/kpi.xlsx?month=YYYY-MM`
- `GET /reports/kpi.pdf?month=YYYY-MM`
- `GET /reports/projects/progress.csv`
- `GET /reports/projects/progress.xlsx`
- `POST /rag/documents`, `GET /rag/documents`
- `DELETE /rag/documents/{document_id}`
- `POST /rag/query`
- `GET /portfolio/summary`
- `GET /monitoring/readiness`
- `GET /monitoring/metrics`
- `GET /monitoring/ops`
- `GET /audit/logs`

### Query params cho `GET /tasks`

`GET /tasks` ho tro loc nang cao nhung van giu response `TaskOut[]` nhu cu:

- `project_id`, `sprint_id`, `assignee_id`
- `status`: `todo`, `doing`, `done`
- `overdue`: `true` de lay task qua han chua done, `false` de loai task dang qua han
- `keyword`: tim trong `title` va `description`
- `deadline_from`, `deadline_to`: ISO datetime, loc theo deadline

Vai tro `staff` van chi nhin thay task duoc gan cho chinh minh. Hien tai task chua co field `priority`, nen API chua ho tro filter theo priority.

## Canh bao workload/capacity theo sprint

Endpoint `GET /sprints/{sprint_id}/workload-warnings` tra ve workload theo tung assignee trong sprint:

- `workload_points`: tong `story_points` cua task chua `done` trong sprint.
- `capacity_points`: MVP tam dung `sprint_capacity_plans.capacity_hours` lam proxy, vi schema chua co cot `capacity_points` rieng.
- `overloaded=true` khi `workload_points > capacity_points`; neu chua co capacity thi `capacity_points=null` va khong tu danh dau overloaded.
- `overdue_task_count`: so task chua `done` da qua deadline trong sprint.
- `risk_level`: `high` khi vua overloaded vua co task qua han, `medium` khi co mot trong hai dieu kien, con lai la `low`.

RBAC: `admin`, `manager`, `hr` xem du lieu sprint/project co quyen truy cap; `staff` chi thay workload cua chinh minh. UI Kanban hien panel `Workload warnings` khi dang loc theo sprint.

## Microsoft Teams

Da co scaffold tich hop Teams:

- Teams tab: `GET /teams/tab`
- Production tab: `GET /teams/tab/prod`
- AAD identity: `GET /integrations/teams/aad/me`
- AAD sync: `POST /integrations/teams/aad/sync`
- Reminder runner: `POST /integrations/teams/reminders/run`
- Bot callback: `POST /integrations/teams/bot/messages`
- Proactive queue: `POST /integrations/teams/proactive/queue`
- Teams tab summary: `GET /integrations/teams/summary?month=YYYY-MM`
- Queue processor: `POST /integrations/teams/proactive/process`
- Requeue failed item: `POST /integrations/teams/proactive/requeue/{notification_id}`

Teams app assets nam trong `teams-app/`, script dong goi nam o `scripts/package_teams_app.py`.

## Audit & Ops dashboard MVP

Audit & Ops la dashboard van hanh toi thieu cho audit log, Teams notification queue va overdue spike. UI nam o tab `Audit & Ops`; API tong hop la:

- `GET /monitoring/ops`
- `GET /audit/logs`

RBAC:

- `admin`, `manager`, `hr` co `monitoring.view` mac dinh va xem duoc dashboard.
- `staff` bi chan khoi `/monitoring/ops`.
- Queue process/requeue van dung endpoint Teams hien co va chi hien nut khi user co quyen privileged.

Filter audit ho tro:

- `actor_id`
- `action`
- `entity_type` (map vao cot `audit_logs.entity`)
- `date_from`, `date_to`
- `keyword`
- `limit`

Dashboard tra ve:

- `audit_logs`: audit da loc, detail duoc rut gon/redact.
- `notification_queue`: `queued_count`, `sent_count`, `failed_count`, `latest_failed_items`.
- `overdue_spike`: tong task qua han hien tai, top project/sprint, `alert=true` neu vuot nguong.

Nguong overdue mac dinh la `10`, co the doi bang `overdue_threshold`. MVP nay khong tao he audit moi, khong realtime websocket, khong APM, khong them chart library moi. Response khong tra webhook URL, bearer token, client secret, raw provider stack trace hoac payload queue raw.

## Test

```bash
pytest -q
```

Chay rieng luong API va AI:

```bash
pytest tests/test_api_flow.py tests/test_ai_task_breakdown.py tests/test_rbac_rag.py
```

## Docker va PostgreSQL

```bash
docker compose up --build
```

Migrate SQLite sang PostgreSQL:

```bash
python scripts/migrate_sqlite_to_postgres.py --sqlite teamswork.db --postgres-dsn "postgresql://teamswork:teamswork@localhost:5432/teamswork"
```

Backup PostgreSQL:

```powershell
./scripts/backup_postgres.ps1 -PostgresDsn "postgresql://teamswork:teamswork@localhost:5432/teamswork" -OutputDir "backups"
```

## Ghi chu van hanh

- `.env.example` cho local/dev.
- `.env.staging.example` va `.env.production.example` cho moi truong trien khai.
- `DEPLOYMENT_RUNBOOK.md` la checklist go-live.
- `teams-app/PUBLISH_CHECKLIST.md` la checklist publish Teams app.
- Production nen dat `APP_ENV=production`; ung dung se chan startup neu van dung JWT secret mac dinh hoac header fallback dev.
- Smoke check sau deploy:

```bash
python scripts/smoke_check.py --base-url https://teamswork.example.com --user-id <admin_id> --expect-production-auth
```
