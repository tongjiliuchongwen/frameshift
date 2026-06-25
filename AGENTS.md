# frameshift Agent Notes

## Project Shape

- Treat this directory as the repository root. The parent directory is a workspace archive, not the active project.
- The canonical frameshift workflow is in `SKILL.md`; role cards live in `roles/`.
- Codex discovers the repo-scoped skill through `.agents/skills/frameshift/SKILL.md`, which points back to the canonical root `SKILL.md`.

## Commands

- Rebuild a value map deterministically: `python -m engine.cli assemble --run <run_id>`
- Serve the API and built dashboard: `python -m engine.cli serve --port 8420`
- Build the dashboard: `cd dashboard && npm ci && npm run build`
- Use `npm install` only when intentionally updating `dashboard/package-lock.json`.

## Verification

- After changing engine code or card data, run `python -m engine.cli assemble --run einstein_arena_v3`.
- After changing dashboard code, run `cd dashboard && npm ci && npm run build`.
- Do not hand-edit generated `map.json`, `run.json`, or `map_position` fields to change layout. Edit cards and rerun `assemble`.

## Data And Hygiene

- Keep source files and curated run JSON in git.
- Keep dependency/build/cache output ignored: `dashboard/node_modules/`, `dashboard/dist/`, `__pycache__/`, `*.pyc`.
- Write Markdown and JSON as UTF-8.
- Preserve the workflow separation: locate -> diverge -> appraise -> value map. Do not combine generation and appraisal in one step.
