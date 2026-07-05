# Changelog

All notable changes to the Research Reframer skill pack.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/); this project is pre-1.0 and the contract may still shift between minor versions.

## [0.5.1] — 2026-06-28

### Changed
- **Gates are now click-driven by default, with zero per-use setup.** Each human gate (1/2/3) renders as
  an inline clickable panel (`mcp__visualize__show_widget` + the global `sendPrompt`) with a "let Claude
  decide" button, falling back to `AskUserQuestion`; a click flows straight into the conversation to
  drive the next stage. Gate 3 shows both-judges-rejected audits in a read-only "rejected drawer". This
  ships inside the pack as skill instructions plus a reusable template
  (`skills/reframe-workshop/references/gate_widget.md`), so an installed copy is click-to-continue with
  **no server and no launch flag**. The `reframe-ui` browser channel (which requires
  `--dangerously-load-development-channels` on every launch plus a local server) is demoted to an
  optional, advanced alternative. Updated `reframe-workshop`, `leverage-scan`, `lateral-generate`,
  `vertical-audit`, and the README to reflect the new default.

## [0.5.0] — 2026-06-27

Major, contract-breaking redesign: the two-gate method-grid / QD flow becomes a **three-gate
cognitive pipeline** (systems → lateral → vertical). `schema_version` bumps `1.0` → `2.0`; v0.2/v0.3
artifacts do not validate under 2.0. `main` (tag `v0.4.1`) remains the last v0.4 release. See
`docs/2026-06-27-v0.5-three-gate-redesign.md`.

### Added
- **Three human gates**: Gate 1 selects leverage points (`LP-###`, *where in the system to cut*),
  Gate 2 selects lateral schemes (`LR-###`, *what's interesting*), Gate 3 selects audited schemes
  (`VA-###`, *what survives*). Trace chain `input → system_node → LP → LR → VA → IC`.
- **`lateral-generate` skill** — divergence stage; operators are internal, judgment is deferred
  (schemes carry no score, `not_yet_audited: true`); diversity kept via an `LP × operator` coverage
  ledger (the grid survives only here, as an internal anti-collapse ledger).
- **`vertical-audit` skill** — adversarial, default-reject convergence with **dual judges**: an
  external engine (Codex via `codex exec`, read-only, schema-forced verdict — not the model that
  generated the scheme) and Claude, each under the same rubric. Agreement is taken; disagreement sets
  `needs_human` and escalates to Gate 3. Rejected audits are preserved with reasons.
- **`scripts/contract.py`** — single source of truth for the vocabulary, verdict enum, 3-digit id
  patterns (no v0.4 99-cap), artifact filenames, and `schema_version`; bundled + consistency-checked.
- New schemas `lateral_reframes` / `vertical_audits`; `idea_cards.method_trace` re-points to the audit.
- The validator now also requires the human-gate audit trail (`05_human_selection.md`,
  `decision_log.md`) to exist and hardens the specificity heuristic against CJK / id-based grounding.
- Two end-to-end examples `examples/physmaster-three-gate/` and `examples/ofamas-three-gate/`, each
  with a real Codex + Claude dual-judge audit.
- **`reframe-ui` rewritten for all three gates** — pick `LP-###` / `LR-###` / `VA-###` in the browser;
  gate detection follows v0.5 contract validity; the rejected drawer is shown read-only. New
  `scripts/render_outputs.py` renders the `03`/`04` static HTML (replacing `render_method_grid.py`).
- **`scripts/check_contract_schema_sync.py`** — fails if any schema `required` field is not covered by
  `contract.REQUIRED_FIELDS`, so the validator's required-field enforcement cannot drift from the schemas.

### Changed
- `reframe-workshop` and `idea-card` SKILLs rewritten for the three-gate flow; `leverage-scan` hands
  off to `lateral-generate`.
- Unified the lateral-operator vocabulary to the 8-operator set (dropped the v0.2-only
  `function_abstraction` / `boundary_shift` / `goal_inversion`).

### Removed
- Retired the v0.2 `lateral-reframe` path and the v0.3 `method-grid` / `method-qd-search` skills; the
  `reframes` / `method_grid` / `method_qd_archive` / `quality_scores` schemas; the static
  `render_method_grid.py`; and the four pre-v0.5 examples.

### Notes
- Codex is an external **judge**, not ground truth — both judges are LLMs; `auditor` is recorded
  honestly (`dual` / `codex` / `self`).
- The validator enforces the v0.5 contract and the full trace chain, **not** novelty or correctness;
  it now checks every schema-`required` field (driven by `contract.REQUIRED_FIELDS`).

## [0.4.1] — 2026-06-27

Hardening pass on the `reframe-ui` channel after an external code review (no change to the default
chat-mediated gates).

### Fixed / hardened
- **Gate state no longer leaks across gates.** When the UI advances (Gate 1 → Gate 2 → done) it now
  clears the previous gate's selection, so a Gate-1 `CELL-…` pick can never be submitted as a Gate-2
  `QD-…` candidate.
- **`POST /select` is validated server-side.** The run must actually be at the submitted gate (`409`
  otherwise); explicit ids must carry the right prefix (`CELL-`/`QD-`) and exist in the artifact
  (`400`); `nl`/`delegate` may not carry ids and `nl` requires a non-empty intent.
- **Honest delivery feedback.** Channel notifications are fire-and-forget, so the UI now says
  "已提交到本地通道，等待 Claude 确认…" and recovers after a 45s timeout (with a hint to launch the
  session with `--dangerously-load-development-channels`) instead of overstating "Claude is processing".
- **Local-only request guard.** `/select` rejects cross-origin requests and non-local `Host`
  (`403`), requires `application/json` (`415`), and caps the body at 64 KB (`413`).
- **`GET /state?run=` path-traversal guard** — a run must be a single folder name under the base.
- **Port-conflict handling** — a clear stderr message + clean exit when `REFRAME_PORT` is taken.

### Added
- **Gate-2 candidate detail panel** — an expandable, read-only view of each candidate's
  `old_frame` / `new_frame` / `changed_assumption` / `why_not_obvious` / evidence / score rationale,
  to support better selection without changing the flow.
- `scripts/smoke_test_zip.py` now requires the `reframe-ui/` files, `CHANGELOG.md`, and the v0.4 design
  doc in the pack (regression guard so a build can't silently drop the channel).
- `reframe-ui/smoke-test.mjs` builds its own portable Gate-2 fixture from the bundled example (works
  from a fresh clone / extracted zip) and now covers the new validation, origin, content-type, and
  body-cap paths (15 checks).

## [0.4.0] — 2026-06-27

### Added
- **`reframe-ui` channel** — an optional Claude Code *channel* (research preview) that turns the two
  human selection gates into a clickable localhost UI instead of chat typing. One Node process is both
  an MCP-over-stdio channel and a `127.0.0.1` HTTP/SSE server: a browser click is pushed into the
  running Claude Code session as a `<channel source="reframe-ui" …>` event; the agent acts and calls a
  `reply` tool to advance the UI. Ships in `reframe-ui/` (server.mjs, ui.html, CONTRACT.md, smoke-test.mjs).
  Node + SSE only — no Bun, no WebSocket; single dependency `@modelcontextprotocol/sdk`.
- Three selection modes in the UI mapping to one `POST /select` contract: 精确 (explicit ids),
  人话 (natural-language intent, agent maps to ids), 托管 (delegate to the agent's heuristics).
- `reframe-workshop` SKILL gains a "reframe-ui channel" section plus notes at both gates: when the
  channel is active, act on the `<channel>` event and call `reply` instead of asking in chat.
- `CHANGELOG.md` (this file) and `docs/2026-06-27-v0.4-interactive-channel.md`.

### Changed
- `scripts/package_zip.py` now excludes `node_modules` from the packaged zip.
- The default chat-mediated gates are unchanged; the channel is strictly additive and optional.

### Notes / limits
- Channel is **Claude-only** (Codex has no equivalent; use its App Server / `codex exec` for that engine),
  **research preview** (protocol may change), requires Claude Code v2.1.80+, an Anthropic-authenticated
  session kept open, and `--dangerously-load-development-channels` for the custom channel.

## [0.3.1] — 2026-06-26
- Human-trial protocol: a 20–30 min real-use trial to check whether the method grid surfaces grounded,
  non-obvious reframes (`human_trial_guide.md` + `human_trial_notes_template.md`).

## [0.3.0] — 2026-06-26
- Method-Grid QD-lite: a 6×8 (system leverage type × lateral operator) method grid, a QD-lite archive
  with coverage stats and per-cell elites, `method-grid` + `method-qd-search` skills, the
  `render_method_grid.py` static visualization, and `method_trace` provenance on idea cards.

## [0.2.0] — 2026-06-26
- Traceable linear pipeline (system-map → leverage-scan → lateral-reframe → idea-card), JSON schemas,
  the dependency-free `validate_outputs.py` contract checker, repo-scoped vs user-scoped installs,
  and bundled validator/schemas inside the installed `reframe-workshop` skill.
