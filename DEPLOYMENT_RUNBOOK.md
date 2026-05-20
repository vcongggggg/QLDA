# TeamsWork Go-Live Runbook

## 1. Preflight Checklist
- Prepare `.env.production` from `.env.production.example`.
- Set strong secrets for `AUTH_JWT_SECRET` and `TEAMS_BOT_APP_SECRET`.
- Ensure PostgreSQL is reachable from API runtime.
- Ensure Teams app is registered and bot credentials are valid.

## 2. Start Services
```bash
docker compose up -d --build
```

## 3. Data Migration (SQLite -> PostgreSQL)
```bash
python scripts/migrate_sqlite_to_postgres.py --sqlite teamswork.db --postgres-dsn "postgresql://teamswork:teamswork@localhost:5432/teamswork"
```

## 4. Health and Readiness Verification
```bash
curl http://localhost:8000/health
curl http://localhost:8000/monitoring/readiness
```

Smoke checklist before pilot:

- `GET /health` returns `ok`.
- `GET /monitoring/readiness` returns `ready`.
- Protected endpoints reject missing auth in production mode.
- `GET /teams/tab` and `GET /teams/tab/prod` render HTML.
- `GET /integrations/teams/summary?month=YYYY-MM` returns task/KPI data for the current user.
- `POST /integrations/teams/aad/sync` works from the Teams tab.
- Notification queue can be listed, processed, and failed items can be requeued by `admin`, `manager`, or `hr`.
- `GET /monitoring/ops` returns Audit & Ops data for `admin`, `manager`, or `hr`, and rejects `staff`.
- KPI, project progress, sprint review, and portfolio reports download with the expected content type.

## 5. Authentication Hardening Validation
- Confirm `AUTH_DISABLE_JWT_VALIDATION=false`.
- Confirm `AUTH_ALLOW_HEADER_FALLBACK=false`.
- Confirm `APP_ENV=production`; startup will fail fast if production auth still uses dev fallback or the default JWT secret.
- Verify protected endpoint rejects missing bearer token.
- Run the automated smoke check after deploy:
```bash
python scripts/smoke_check.py --base-url https://teamswork.example.com --user-id <admin_id> --expect-production-auth
```

## 6. Teams Proactive Flow Validation
1. Call bot callback once from Teams to save conversation reference.
2. Queue a proactive notification for that user:
   - `POST /integrations/teams/proactive/queue?message=...&user_id=...&max_attempts=3`
3. Process queue:
   - `POST /integrations/teams/proactive/process`
4. Check queue states:
   - `GET /integrations/teams/proactive/queue?status=queued`
   - `GET /integrations/teams/proactive/queue?status=failed`
5. Requeue failed item if needed:
   - `POST /integrations/teams/proactive/requeue/{notification_id}`

## 7. Backup Procedure
Run PostgreSQL backup script from a machine with `pg_dump` installed:
```powershell
./scripts/backup_postgres.ps1 -PostgresDsn "postgresql://teamswork:teamswork@localhost:5432/teamswork" -OutputDir "backups"
```

## 8. Rollback Procedure
- Keep latest SQLite snapshot and PostgreSQL dump.
- If deployment fails:
  - Stop API containers.
  - Restore last known good PostgreSQL backup.
  - Restart API with previous image tag and env file.

## 9. Post-Deploy Monitoring
- Poll `/monitoring/metrics` on schedule.
- Use `/monitoring/ops` or the `Audit & Ops` UI tab for audit filters, queue counts, latest failed queue items, and overdue spike triage.
- Alert if `failed_notifications` increases continuously.
- Alert if `overdue_tasks` spikes abnormally.
- The MVP overdue spike alert turns on when overdue tasks exceed `overdue_threshold` (default `10`); tune the query param for pilot sensitivity.
- Failed queue rows are sanitized for operators. Use server logs for raw provider diagnostics when needed.
