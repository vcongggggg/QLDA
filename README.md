# QLDA - TeamsWork

TeamsWork la ung dung quan ly cong viec, KPI va du an noi bo, co API FastAPI, giao dien web tinh, bao cao CSV/XLSX/PDF, tich hop Microsoft Teams va module AI phan ra yeu cau thanh task.

## Tinh nang chinh

- Quan ly user, phong ban, du an, sprint va task.
- Kanban voi trang thai `todo`, `doing`, `done`.
- RBAC theo vai tro `admin`, `manager`, `staff`, `hr`.
- KPI hang thang voi diem theo deadline va do kho.
- Bao cao KPI, tien do du an, sprint review va portfolio.
- Hang doi thong bao Teams proactive, retry va requeue.
- AI task breakdown tu text hoac file `.docx`.
- Import task AI da chon vao Kanban.
- SQLite cho dev local, PostgreSQL cho docker/production-like.

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

## Luong AI import task

1. Mo tab AI tren UI.
2. Dan requirements hoac upload file `.docx`.
3. Bam tao task de xem danh sach de xuat.
4. Chon task can import, chon assignee va project neu co.
5. Bam import de tao task that trong Kanban.

Endpoint lien quan:

- `POST /ai/task-breakdown`
- `POST /ai/task-breakdown/docx`
- `POST /ai/task-breakdown/import`

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

Quyen co ban:

- `admin`: quan tri user, seed, audit, bao cao.
- `manager`: quan ly du an, sprint, task, KPI, AI import.
- `staff`: xem va cap nhat task/KPI cua minh.
- `hr`: xem user, KPI va bao cao lien quan.

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
- `POST /departments`, `GET /departments`
- `POST /projects`, `GET /projects`
- `POST /projects/{project_id}/members`
- `POST /projects/{project_id}/sprints`
- `PATCH /sprints/{sprint_id}/status`
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
- `GET /portfolio/summary`
- `GET /monitoring/readiness`
- `GET /monitoring/metrics`

## Microsoft Teams

Da co scaffold tich hop Teams:

- Teams tab: `GET /teams/tab`
- Production tab: `GET /teams/tab/prod`
- AAD identity: `GET /integrations/teams/aad/me`
- AAD sync: `POST /integrations/teams/aad/sync`
- Reminder runner: `POST /integrations/teams/reminders/run`
- Bot callback: `POST /integrations/teams/bot/messages`
- Proactive queue: `POST /integrations/teams/proactive/queue`
- Queue processor: `POST /integrations/teams/proactive/process`
- Requeue failed item: `POST /integrations/teams/proactive/requeue/{notification_id}`

Teams app assets nam trong `teams-app/`, script dong goi nam o `scripts/package_teams_app.py`.

## Test

```bash
pytest -q
```

Chay rieng luong API va AI:

```bash
pytest tests/test_api_flow.py tests/test_ai_task_breakdown.py
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
