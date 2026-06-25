---
name: frameshift
description: Use when Codex should run the frameshift research-direction workflow on a paper, paper path, domain description, or research/product ideation prompt by locating clamped degrees of freedom, diverging with lateral-thinking operators, appraising candidates through a falsifiability floor, and assembling an interactive value map.
---

# frameshift Codex Entry Point

This is a repo-scoped Codex wrapper for the canonical frameshift skill.

Before doing frameshift work, read `../../../SKILL.md` completely and treat it as the source of truth. Resolve its relative paths from the repository root, not from this wrapper directory.

When the root skill references role cards, read them from:

- `../../../roles/locate.md`
- `../../../roles/diverge.md`
- `../../../roles/appraise.md`
- `../../../roles/value_map.md`

Run deterministic engine commands from the repository root:

- `python -m engine.cli assemble --run <run_id>`
- `python -m engine.cli serve --port 8420`

Do not duplicate or override the root skill here. Keep this file as a thin Codex discovery layer so Claude Code and Codex share the same canonical workflow.
