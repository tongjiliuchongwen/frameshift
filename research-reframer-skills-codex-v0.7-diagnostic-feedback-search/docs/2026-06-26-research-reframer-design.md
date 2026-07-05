# Research Reframer Design

Date: 2026-06-26

Note: this document records the v0.2 baseline design. v0.3 adds
`method-grid` and `method-qd-search`, a fourth curated demo, QD-lite archive
validation, and static method-grid visualization. See
`docs/2026-06-26-v0.3-method-grid-qd-lite-design.md`.

## Goal

Build a directly installable Claude Code / Codex skill pack for early-stage research idea reframing. The deliverable should read as a reusable research workflow, not a chatbot demo or a prompt collection.

## Scope

First portfolio-grade version:

- Five skills: `system-map`, `leverage-scan`, `lateral-reframe`, `idea-card`, `reframe-workshop`
- Root-level JSON schemas for auditability
- No-dependency validation script
- No-dependency install script
- Three demo inputs with curated output artifacts
- README with install, workflow, before/after, and validation

Out of scope for this version:

- Web UI
- PDF ingestion
- Automated literature search
- True CLI command runner beyond install/validation scripts
- Claims of empirical superiority over baseline brainstorming

## Architecture

The installable product is the `skills/` directory. Each skill is self-contained enough to work after being copied into the supported runtime skill folders:

- Codex user scope: `~/.agents/skills`
- Codex repository scope: `.agents/skills`
- Claude Code user scope: `~/.claude/skills`
- Claude Code repository scope: `.claude/skills`

The installer keeps `~/.codex/skills` as a legacy Codex target for older local setups.

The repository root adds engineering credibility:

- `schemas/`: public data contracts for generated artifacts
- `scripts/validate_outputs.py`: checks required fields and cross-artifact traceability
- `examples/`: reproducible before/after demos
- `docs/`: design notes and future planning

## Workflow

```text
Input note
  -> system-map
  -> leverage-scan
  -> human selects leverage points
  -> lateral-reframe
  -> human selects reframes
  -> idea-card
  -> validation
```

The human gates are intentional. Early-stage research interestingness depends on taste, context, resources, and risk tolerance. The agent structures the space; the researcher chooses where to continue.

## Data Contracts

Core artifacts:

- `01_system_map.json`: structured system representation
- `02_leverage_points.json`: high-leverage reframing locations
- `04_reframes.json`: divergent reframed questions
- `05_idea_cards.json`: actionable and testable research cards

Every idea card must trace back to:

```text
input evidence -> system node -> leverage point -> lateral operation -> reframe
```

## Quality Gates

Required fields:

- Every leverage point needs `source_trace`, `current_assumption`, `why_it_matters`, and `risk`.
- Every reframe needs `changed_assumption`, `new_assumption`, `promise`, and `risk`.
- Every idea card needs `changed_assumption`, `system_trace`, `minimal_experiment`, `evaluation_metrics`, `failure_case`, `related_work_queries`, and `next_steps`.

Validation is intentionally local and deterministic. It does not judge research quality, but it prevents the output from collapsing into unstructured brainstorming.

## Demo Strategy

Use three general demos:

- Weak AI research idea: understandable to any interviewer in under a minute.
- Paper gap reframe: shows research-intern relevance.
- Open-source roadmap reframe: shows engineering/product relevance.

Do not use domain-specific PDFs as the primary demo. Keep them as internal proof-of-concept material only.
