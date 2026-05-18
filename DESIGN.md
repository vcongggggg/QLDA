# TeamsWork Design Guide

This file is the design baseline for TeamsWork UI changes. Apply it together with `AGENTS.md` before changing the web UI or Microsoft Teams tab.

## Product Surface

- TeamsWork is an internal operations app for tasks, projects, sprints, KPI, reports, AI task preview/import, and Microsoft Teams workflows.
- The UI should feel compact, predictable, and work-focused. Prioritize scanability and repeated use over marketing-style presentation.
- The Microsoft Teams tab is a constrained surface: show the smallest useful dashboard first, then tasks, KPI, and notification queue controls for privileged roles.

## Layout

- Keep the main web app shell: fixed sidebar, topbar, content sections, dense grids, tables, Kanban columns, and drawers.
- Use full-width work areas and simple panels. Do not nest cards inside cards.
- Keep cards and panels at `8px` radius unless matching an existing component that already uses a nearby value.
- For Teams tab layouts, use a compact header, four summary stats, a task board, KPI summary, and queue status. It must fit desktop and narrow Teams viewports.

## Visual System

- Primary brand color: `#2B579A`.
- Use status colors consistently:
  - Success/done: green.
  - Warning/doing: amber.
  - Danger/failed/overdue: red.
  - Neutral/todo: gray.
- Avoid one-note palettes. Keep backgrounds quiet (`#F4F6FB` style) with white panels and restrained borders.
- Use stable panel dimensions, fixed grid tracks, and overflow wrapping so Vietnamese and English labels do not overlap.

## Components

- Sidebar navigation uses icon plus short label.
- Tables are for KPI, audit, reports, and compact comparisons.
- Kanban cards must show title, story points, deadline, and status context.
- Drawers are preferred for task detail so the user keeps board context.
- Buttons should be short command labels. Icon buttons need accessible labels when added.
- Use explicit loading, empty, and error states for Teams tab and API-backed panels.

## Microsoft Teams Rules

- The Teams tab must use AAD token sync when available and local `X-User-Id` only as dev fallback.
- Staff users only see their own tasks/KPI. Queue management is hidden unless the user is `admin`, `manager`, or `hr`.
- Do not display bearer tokens, webhook URLs, client secrets, or raw provider errors.
- Queue status should show queued, sent, and failed counts; retry/process controls belong only to privileged roles.

## Change Policy

- Any UI change must preserve the existing operational design: dense, readable, and role-aware.
- Any backend or security behavior change must follow `AGENTS.md` and update tests.
- If this guide conflicts with `AGENTS.md`, `AGENTS.md` wins for security, RBAC, KPI, and AI import policy.
