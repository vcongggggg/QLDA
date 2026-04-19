# Teams App Publish Checklist

## 1. Azure AD App Registration
- Create app registration in Azure AD.
- Add redirect URI if required by your Teams auth flow.
- Set application (client) ID into TEAMS_CLIENT_ID.
- Grant permissions and admin consent.

## 2. Backend Environment
- Configure `.env` values:
  - `APP_BASE_URL`
  - `TEAMS_CLIENT_ID`
  - `TEAMS_TENANT_ID`
  - `TEAMS_INCOMING_WEBHOOK_URL` (if using reminders)
- Deploy backend using HTTPS.

## 3. Manifest Preparation
- Update `teams-app/manifest.json`:
  - Replace `REPLACE_WITH_PUBLIC_HOST` in URLs and validDomains.
- Add icons:
  - `teams-app/color.png` (192x192)
  - `teams-app/outline.png` (32x32)

## 4. Package
Run:

```bash
python scripts/package_teams_app.py --source teams-app --out teams-app-package.zip
```

## 5. Sideload / Publish
- Upload zip package to Teams client (sideload) or Teams Admin Center.
- Pin app to personal scope for pilot users.

## 6. Validate
- Open Teams tab and verify token call to `/integrations/teams/aad/me`.
- Sync user with `/integrations/teams/aad/sync`.
- Trigger reminders using `/integrations/teams/reminders/run`.
- Validate bot command callback `/integrations/teams/bot/messages`.
