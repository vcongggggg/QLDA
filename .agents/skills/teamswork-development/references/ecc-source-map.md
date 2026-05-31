# ECC Source Map

This skill intentionally distills only the ECC guidance that applies to TeamsWork. Do not copy broad ECC examples into the project skill unless they are needed for a concrete TeamsWork workflow.

## Sources

- `ECC/skills/coding-standards/SKILL.md`
  - Extracted: readability, KISS, DRY, YAGNI, descriptive names, small scoped changes, clear error handling.
  - Omitted: generic TypeScript/React examples not used by the current FastAPI/static UI app.

- `ECC/skills/fastapi-patterns/SKILL.md`
  - Extracted: thin routers, Pydantic request/response models, dependency/auth boundaries, safe response models, tests around dependency and auth behavior.
  - Adapted: repository style to match the existing `app/repository.py` pattern instead of introducing a new service layout.

- `ECC/skills/frontend-patterns/SKILL.md`
  - Extracted: role-aware UI, predictable state updates, clear loading/error/empty states, accessible controls.
  - Omitted: React/Next.js-specific hooks and component architecture because TeamsWork currently uses static HTML/CSS/JS.

- `ECC/skills/verification-loop/SKILL.md`
  - Extracted: verify after significant changes, run focused checks first, then full tests, inspect diff, report residual risk.
  - Adapted: TeamsWork commands use `pytest`, Playwright tests, and `python -m compileall app scripts`.

- `DESIGN.md`
  - Extracted into `references/design-baseline.md` for UI and Microsoft Teams tab rules.
