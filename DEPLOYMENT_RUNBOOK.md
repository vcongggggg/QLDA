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

## 5. Authentication Hardening Validation
- Confirm `AUTH_DISABLE_JWT_VALIDATION=false`.
- Confirm `AUTH_ALLOW_HEADER_FALLBACK=false`.
- Verify protected endpoint rejects missing bearer token.

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
- Alert if `failed_notifications` increases continuously.
- Alert if `overdue_tasks` spikes abnormally.
