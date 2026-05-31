# TeamsWork Design Baseline

This is the distilled design layer from `DESIGN.md`. Read the root file when changing UI details directly.

## Product Surface

- TeamsWork is an internal operations app for tasks, projects, sprints, KPI, reports, AI task preview/import, and Microsoft Teams workflows.
- The interface should feel compact, predictable, and work-focused.
- Prioritize scanability and repeated use over marketing-style presentation.
- The Teams tab is constrained: show the smallest useful dashboard first, then tasks, KPI, and notification queue controls for privileged roles.

## Layout

- Keep the main app shell: fixed sidebar, topbar, content sections, dense grids, tables, Kanban columns, and drawers.
- Use full-width work areas and simple panels.
- Do not nest cards inside cards.
- Keep cards and panels at about `8px` radius unless matching an existing nearby component.
- Teams tab layouts should use a compact header, four summary stats, a task board, KPI summary, and queue status that fit desktop and narrow Teams viewports.

## Visual System

- Primary brand color: `#2B579A`.
- Status colors:
  - success/done: green
  - warning/doing: amber
  - danger/failed/overdue: red
  - neutral/todo: gray
- Avoid one-note palettes.
- Prefer quiet backgrounds similar to `#F4F6FB`, white panels, restrained borders, and readable contrast.
- Use stable dimensions and overflow wrapping so Vietnamese and English labels do not overlap.

## Components

- Sidebar navigation uses icon plus short label.
- Tables are appropriate for KPI, audit, reports, and compact comparisons.
- Kanban cards must show title, story points, deadline, and status context.
- Drawers are preferred for task detail so users keep board context.
- Buttons should use short command labels.
- Icon buttons need accessible labels.
- API-backed panels need clear loading, empty, and error states.

## Microsoft Teams Tab

- Use AAD token sync when available.
- Local `X-User-Id` is a development fallback only.
- Staff users only see their own tasks and KPI.
- Queue management is hidden unless the user is `admin`, `manager`, or `hr`.
- Do not display bearer tokens, webhook URLs, client secrets, or raw provider errors.
- Queue status should show queued, sent, and failed counts.
- Retry/process controls are privileged-role controls only.
