# Changelog

All notable changes to the Research Reframer skill pack.

## [0.7.0-codex] - 2026-07-01

### Added

- Added `00_diagnosis.json` as the Stage 0 artifact for original-idea dissatisfaction diagnosis.
- Added v0.7 `schema_version: 2.1` contract fields for auditable system relations:
  `relation_type`, `evidence_source`, `mechanism`, and `if_wrong_impact`.
- Added `pseudo_innovation` blocks to vertical audits with explicit failure types and repair/fatal status.
- Added `escalation_reason` and `human_resolution` to make judge disagreement and human rescue readable.
- Added `change_log` to idea cards so final ideas state the structural change and real increment over the input.
- Added the v0.7 diagnostic feedback-search design note.

### Changed

- Updated the bundled validator, schemas, and contract copy in `reframe-workshop`.
- Updated the core examples to validate under `schema_version: 2.1`.
- Updated static vertical-audit HTML rendering to show pseudo-innovation and human-resolution fields.

## [0.5.1-codex] - 2026-06-28

### Added

- Added `05_gate_cards.json` to preserve the exact lightweight Chinese card text shown at each human gate.
- Added `05_human_selection.json` as a machine-readable selection contract for Gate 1/2/3.
- Added schemas for both gate audit-trail files and validator checks that Gate selections match downstream artifacts.

### Changed

- Codex gates now use one path only: the Codex App Server sidecar in `../codex-appserver-gate-test`.
- Browser buttons select Gate 1/2/3 options. The sidecar records `05_gate_cards.json` and
  `05_human_selection.json`, then starts the next Codex turn through `codex app-server`.
- The sidecar does not type into the chat composer, and the skills must not ask the user to type gate ids.
- Static HTML renders default to selection-card rows (`旧->新`, `人话方案`, `看点`, `风险`) with raw fields behind details.
- `lateral-generate` includes a lightweight anti-glue self check to flag ordinary method add-ons that are not real reframes.

### Removed

- Removed the obsolete non-sidecar gate instructions from the Codex edition.
- Removed the old prompt-reference file for the obsolete gate path.

## [0.5.0-codex] - 2026-06-28

### Changed

- Added a Codex-first edition of the Research Reframer skill pack.
- Human gates are represented in the artifact contract as Gate 1/2/3 selections and audit trails.
- Packaging and smoke tests exclude generated smoke/live/private test runs.

## [0.5.0] - 2026-06-27

Major, contract-breaking redesign: the two-gate method-grid / QD flow became a three-gate cognitive
pipeline: systems -> lateral -> vertical. `schema_version` bumped from `1.0` to `2.0`; v0.2/v0.3
artifacts do not validate under 2.0.

### Added

- Three human gates: Gate 1 selects leverage points (`LP-###`), Gate 2 selects lateral schemes
  (`LR-###`), and Gate 3 selects audited schemes (`VA-###`).
- `lateral-generate`: divergence stage with judgment deferred.
- `vertical-audit`: adversarial, default-reject convergence with external and local judge provenance.
- `scripts/contract.py`: single source of truth for vocabulary, verdict enum, id patterns, artifact
  filenames, and `schema_version`.
- End-to-end example artifacts under `examples/`.

### Removed

- Retired the v0.2 `lateral-reframe` path and the v0.3 `method-grid` / `method-qd-search` skills.
