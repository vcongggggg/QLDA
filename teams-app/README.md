# Teams App Package

## Contents
- `manifest.json`: Microsoft Teams app manifest for TeamsWork tab integration.

## Before sideloading
1. Replace `REPLACE_WITH_PUBLIC_HOST` in `manifest.json` with your public HTTPS domain (no protocol in `validDomains`, with protocol in URLs).
2. Create `color.png` (192x192) and `outline.png` (32x32) in this folder.
3. Zip `manifest.json`, `color.png`, `outline.png`.
4. Upload package in Teams Admin Center or Teams sideload.

## Backend dependency
The tab points to:
- `/teams/tab`
- `/integrations/teams/aad/me`

Ensure backend is publicly reachable with HTTPS.
