---
name: lateral-generate
description: "Generate divergent lateral reframes from human-selected leverage points (v0.7 Stage 1, between Gate 1 and Gate 2). Judgment is deferred: produce grounded but unproven schemes by sweeping lateral-thinking operators internally, keep them diverse with an LP x operator coverage ledger, and do not score or audit them here. Use after the sidecar sends the Gate 1 leverage-point selection; vertical-audit judges selected schemes next."
---

# Lateral Generate

Use this skill after Gate 1, when the Codex App Server sidecar has sent selected leverage points from
`02_leverage_points.json` as a `<codex_gate_selection>` event.

```text
leverage-scan -> Gate 1 sidecar selection -> lateral-generate -> Gate 2 sidecar selection -> vertical-audit
```

Stay generative and defer judgment. A lateral scheme may be unproven or bold; it must be marked
`not_yet_audited: true`.

## Language and Encoding Rules

- Write all natural-language artifact fields in Simplified Chinese by default. Keep stable ids and
  technical terms such as `agent`, `artifact`, `oracle`, `benchmark`, and `PL-agnostic` in English
  when they are the paper's terms.
- Gate 2 reads `old_frame`, `new_frame`, `scheme`, `why_interesting`, and `bad_use_to_avoid` directly,
  so these fields must be readable Chinese, not English-only notes and not placeholder text.
- Write Gate-facing fields as the reader layer: short, plain Chinese for a researcher adjacent to
  the field. Keep operator names, source ids, and dense terminology in trace/detail fields rather
  than making them carry the default meaning.
- If a paper term must remain in English, explain it once in Chinese first. Example:
  `安全参照行为（safe baseline）`; later mentions should prefer the Chinese phrase.
- On Windows, do not generate this JSON by piping a PowerShell here-string into Python or Node, such as
  `@'...'@ | python -`. That path can replace every Chinese character with `?` before the program sees
  it. Use `apply_patch` or an explicit UTF-8 file-writing path, then run the validator.

## Input

- `01_system_map.json`
- `02_leverage_points.json`
- `00_diagnosis.json` when available, to keep schemes focused on the primary bottleneck
- Gate-1 selection: `LP-###` ids from `<codex_gate_selection>`.

## Operators Are Internal

For each selected leverage point, internally sweep the 8 lateral operators and keep genuinely distinct
reframes:

`assumption_challenge, reversal, decomposition, analogy, random_stimulus, PO_provocation, entry_point_shift, concept_abstraction`

The human chose where in the system to intervene; do not ask them to choose operators.

## Anti-Collapse Discipline

1. Every scheme must have a distinct `new_frame` and `changed_assumption`.
2. Each scheme must include `bad_use_to_avoid`.
3. Prefer local `input_evidence` and system nodes instead of reusing the same evidence everywhere.
4. Maintain the `coverage_ledger` over selected LP x operator cells.

## Anti-Glue Self Check

Before keeping an `LR-###`, ask whether it truly changes at least one of these:

1. Who judges value.
2. What counts as evidence.
3. Where the system boundary sits.
4. Who or what is being measured.
5. When information is revealed.
6. What the objective function is.
7. Whether the old assumption is reversed, decomposed, replaced, or shifted.
8. Which Stage 0 diagnosis bottleneck the scheme tries to relieve.

If the answer is "none" and the scheme only adds a metric, calibration pass, ablation, evaluator,
control group, or extra module, rewrite it. If it is still worth keeping as a method improvement,
say so honestly in `bad_use_to_avoid`.

## Workflow

1. Load the system map, leverage points, and Gate-1 selection.
2. For each selected `LP-###`, sweep operators and draft schemes.
3. For each scheme run the anti-glue self check, then write `old_frame`, `lateral_move`, `new_frame`,
   `scheme`, `why_interesting`, `changed_assumption`, `bad_use_to_avoid`, and `not_yet_audited: true`.
4. Drop near-duplicates.
5. Build the `coverage_ledger`.
6. Write `03_lateral_reframes.json`, optional `.md`, and optional `.html`.
7. Stop. Gate 2 must be selected through the sidecar.

## Output Contract

Return JSON matching `schemas/lateral_reframes.schema.json`:

```json
{
  "schema_version": "2.1",
  "source_leverage_points": ["LP-007", "LP-012"],
  "lateral_schemes": [
    {
      "lateral_id": "LR-001",
      "source_leverage_point": "LP-007",
      "operator": "reversal",
      "old_frame": "Trace is an after-the-fact log explaining what the agent did.",
      "lateral_move": "Reverse trace from explanation to intervention.",
      "new_frame": "Trace becomes a feedback signal that shapes the agent's next reframing step.",
      "scheme": "Feed the trace of rejected reframes into the next search round so the agent avoids repeating shallow variations.",
      "why_interesting": "Turns passive observability into active control of the search.",
      "changed_assumption": "Trace is for humans to read, not for the agent to act on.",
      "bad_use_to_avoid": "Do not stop at the slogan 'trace as feedback' with no concrete update rule.",
      "not_yet_audited": true
    }
  ],
  "coverage_ledger": {
    "operators": ["assumption_challenge", "reversal", "decomposition", "analogy", "random_stimulus", "PO_provocation", "entry_point_shift", "concept_abstraction"],
    "cells": [
      { "leverage_point": "LP-007", "operator": "reversal", "scheme_count": 1, "scheme_ids": ["LR-001"] }
    ],
    "occupied_count": 1,
    "total_cells": 16,
    "coverage_ratio": 0.06,
    "underexplored": [ { "leverage_point": "LP-007", "operator": "decomposition" } ]
  }
}
```

`total_cells` = number of selected leverage points times 8. `coverage_ratio` = `occupied_count` /
`total_cells`. The validator checks this arithmetic.

## Handoff: Gate 2

Stop after writing `03_lateral_reframes.json`. Gate 2 is selected only through the Codex App Server
sidecar in `../codex-appserver-gate-test`; do not ask the user to type ids into chat. The sidecar
renders lightweight Chinese cards and records the exact snapshot. When the next turn arrives with
`<codex_gate_selection><gate>2</gate>...`, run `vertical-audit` only on those selected `LR-###` ids.
