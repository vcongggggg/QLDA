# Full Demo Seed and RAG Seed

Use the full demo seed for local, dev, and demo environments. It creates linked QLDA/TeamsWork data for departments, users, projects, sprints, tasks, KPI, reports, notifications, AI drafts, and project-scoped RAG documents.

## Commands

Run from the repository root:

```bash
python scripts/seed_full_demo.py --upsert
```

Seed or refresh only the RAG demo documents:

```bash
python scripts/seed_full_demo.py --rag-only
```

Reset demo-scoped data and reseed it:

```bash
python scripts/seed_full_demo.py --reset-demo
```

`--reset-demo` is guarded and should only be used in local/dev/demo/test. `--force` overrides the guard and must not be used against production data unless that reset has been explicitly approved.

## Demo Accounts

The auth demo accounts are local/demo credentials, not production secrets:

| Email | Password | Canonical role |
|---|---|---|
| `admin@teamswork.local` | `Admin@123` | `ADMIN` |
| `manager@teamswork.local` | `Manager@123` | `MANAGER` |
| `leader@teamswork.local` | `Leader@123` | `LEADER` |
| `member@teamswork.local` | `Member@123` | `MEMBER` |
| `hr@teamswork.local` | `Hr@123` | `HR` |
| `auditor@teamswork.local` | `Auditor@123` | `AUDITOR` |

Additional full-demo users use `Demo@123`.

## RAG Behavior

Local/dev defaults to lexical fallback because `RAG_EMBEDDING_ENABLED=false`. The seed still creates `rag_documents`, `rag_chunks`, placeholder embedding rows, and project-scoped permissions so queries can be tested without a real embedding provider.

If `RAG_EMBEDDING_ENABLED=true`, pgvector is active, and an embedding provider/API key is configured, the seeder attempts to embed the new chunks. Embedding failures are returned as warnings and do not fail the seed.

Useful demo queries:

- `Member có thể xem những chức năng nào?`
- `Manager theo dõi tiến độ task của team như thế nào?`
- `Admin quản lý người dùng và phòng ban như thế nào?`
- `KPI được tính như thế nào?`
- `Dự án demo hiện tại có những sprint/task nào?`
- `Khi task bị quá hạn thì xử lý thế nào?`
- `Auditor có quyền xem gì?`
- `HR có thể xem KPI nhân sự không?`
