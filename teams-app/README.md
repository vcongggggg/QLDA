# Teams App Package

## Contents
- `manifest.json`: Microsoft Teams app manifest for TeamsWork tab integration.

## Before sideloading
1. Keep placeholders in `manifest.json`; the packaging script fills them from `.env`.
2. Set `.env`:
   - `APP_BASE_URL=https://example.ngrok-free.dev`
   - `TEAMS_CLIENT_ID=<Azure client ID>`
3. Ensure Azure Expose an API matches `api://HOST/CLIENT_ID`.
4. Keep `color.png` (192x192) and `outline.png` (32x32) in this folder.
5. Run `python scripts/package_teams_app.py --source teams-app --out teams-app-package.zip`.
6. Upload package in Teams Admin Center or Teams sideload.

## Backend dependency
The tab points to:
- `/teams/tab`
- `/teams/tab/prod`
- `/integrations/teams/aad/me`
- `/integrations/teams/aad/sync`

Ensure backend is publicly reachable with HTTPS.
