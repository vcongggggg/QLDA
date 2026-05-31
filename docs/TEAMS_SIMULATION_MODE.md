# Teams-ready Simulation Mode

## Why MVP does not use real Teams

TeamsWork runs the Microsoft Teams workflow in `simulation` mode for the MVP. The demo does not call Microsoft Graph, does not require Teams Admin Center, and does not require sideloading a custom Teams app.

This is intentional because student Microsoft Teams accounts normally do not have tenant admin rights to:

- Upload or approve a custom Teams app for an organization.
- Configure Azure AD / Entra ID SSO for a tab or bot.
- Grant Microsoft Graph application permissions.
- Register and trust Bot Framework callbacks for production use.

The MVP therefore proves the business flow locally: bot commands, Adaptive Card payloads, task actions, notification queue processing, retry, and readiness monitoring.

## Environment defaults

```env
TEAMS_INTEGRATION_MODE=simulation
TEAMS_REAL_GRAPH_ENABLED=false
```

In this mode, queue processing marks Teams simulation notifications as sent without external HTTP calls. A test payload can set `simulate_failure=true` to exercise retry behavior up to three attempts.

## Architecture

- Web demo page: `/admin/integrations/teams-simulator`
- Simulator command API: `POST /integrations/teams/simulator/command`
- Card preview API: `GET /integrations/teams/cards/preview`
- Queue API: `POST /integrations/teams/notifications/queue`
- Process API: `POST /integrations/teams/notifications/process`
- Retry API: `POST /integrations/teams/notifications/retry/{id}`
- Health API: `GET /integrations/teams/health`

The simulator reuses existing TeamsWork modules:

- `notification_queue` for queued/sent/failed status and retry count.
- Task repository for `/task-list`, Complete, Extend, and Comment actions.
- KPI ledger for `/kpi-me`.
- Audit log for queue, process, retry, and card actions.

## Demo script

1. Open `/admin/integrations/teams-simulator`.
2. Confirm the `Simulation Mode` badge and health panel show real Graph disabled.
3. Run `/task-list` to show current visible tasks as Adaptive Card JSON and preview HTML.
4. Run `/kpi-me` to show monthly KPI score, on-time tasks, late tasks, and overdue unfinished tasks.
5. Click `Queue deadline cards` to create `deadline_reminder` card payloads for tasks due within 24 hours.
6. Click `Process queue`; queued cards move to `sent` without a Microsoft Graph call.
7. For retry evidence, queue a test payload with `simulate_failure=true` through API tests; failed rows can be retried from the simulator.

## Upgrade path to real Teams

When a Microsoft 365 Developer or E5 tenant is available:

1. Register an Entra ID application for TeamsWork.
2. Configure tab SSO and valid domains in the Teams app manifest.
3. Register the bot and callback URL with Bot Framework.
4. Grant the required Microsoft Graph permissions with tenant admin consent.
5. Set `TEAMS_INTEGRATION_MODE` to a real delivery mode and set `TEAMS_REAL_GRAPH_ENABLED=true`.
6. Configure `TEAMS_CLIENT_ID`, `TEAMS_TENANT_ID`, `TEAMS_CLIENT_SECRET`, team/channel ids, and bot credentials.
7. Re-run Graph mock tests first, then tenant smoke tests.

Until those conditions are met, TeamsWork must be described as Teams-ready simulation, not production Microsoft Teams integration.
