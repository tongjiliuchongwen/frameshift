---
name: lateral-generate
description: "Generate divergent lateral reframes from human-selected leverage points (v0.5 Stage 1, between Gate 1 and Gate 2). Judgment is DEFERRED: produce many grounded but unproven schemes by sweeping lateral-thinking operators internally, keep them diverse via an LP x operator coverage ledger, and do NOT score or audit them here. Use after the human selects leverage points; the vertical-audit skill judges them next."
---

# Lateral Generate

Use this skill after **Gate 1** (the human selected leverage points in `02_leverage_points.json`).
It is the **divergence** stage of the v0.5 three-gate flow:

```
leverage-scan -> [Gate 1: select LP] -> lateral-generate -> [Gate 2: select LR] -> vertical-audit
```

This stage embodies the lateral half of de Bono's split: **stay generative, defer judgment.** Do NOT
score, rank, or audit schemes here — that is the next stage's job. A lateral scheme is allowed to be
unproven, bold, or even slightly unreasonable; it is explicitly `not_yet_audited`.

## Input

- `01_system_map.json`
- `02_leverage_points.json`
- The Gate-1 human selection: a list of `LP-###` ids (or, in delegate mode, select a diverse 2–4
  yourself and record the choice in `decision_log.md`).

## Operators are internal, not user-facing

The human chose *where in the system to cut* (the leverage point). They did NOT choose a lateral
trick. For each selected leverage point, internally sweep the 8 lateral operators and keep whichever
produce a genuinely distinct reframe:

`assumption_challenge, reversal, decomposition, analogy, random_stimulus, PO_provocation, entry_point_shift, concept_abstraction`

You need not fill every `LP × operator` cell — empty cells are information (recorded in the ledger).
Aim for breadth across operators per leverage point, not exhaustiveness.

## Anti-collapse discipline (the project's hardest-won property — keep it)

Lateral generation is exactly where ideas collapse into "one insight wearing N costumes." Enforce:

1. Every scheme must have a **distinct `new_frame` and `changed_assumption`** — no paraphrase twins.
2. Each scheme carries a **`bad_use_to_avoid`**: the specific degenerate version of this reframe to
   avoid (the cosmetic, slogan-only reading).
3. Prefer the most **local** `input_evidence` / system node for each scheme rather than reusing the
   same evidence everywhere.
4. Maintain the **`coverage_ledger`** over `selected LP × operator`: which cells are occupied, how
   many schemes each holds, and which are underexplored.

## Workflow

1. Load the system map, leverage points, and the Gate-1 selection.
2. For each selected `LP-###`, sweep operators and draft schemes. Ground each in a system node and
   the leverage point.
3. For each scheme write `old_frame`, `lateral_move`, `new_frame`, `scheme`, `why_interesting`,
   `changed_assumption`, `bad_use_to_avoid`, and set `not_yet_audited: true`.
4. Drop near-duplicates (same `new_frame`/`changed_assumption`); keep bold-but-coherent ones.
5. Build the `coverage_ledger`.
6. Write `03_lateral_reframes.json`, `03_lateral_reframes.md`, and (when a renderer is available)
   `03_lateral_reframes.html`. Record the Gate-1 rationale in `decision_log.md`.
7. Stop. Do NOT score or pick winners — present the schemes for **Gate 2**.

## Output Contract

Return JSON matching `schemas/lateral_reframes.schema.json`:

```json
{
  "schema_version": "2.0",
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
      "bad_use_to_avoid": "Do not stop at the slogan 'trace as feedback' with no concrete update rule or avoidance criterion.",
      "not_yet_audited": true
    }
  ],
  "coverage_ledger": {
    "operators": ["assumption_challenge","reversal","decomposition","analogy","random_stimulus","PO_provocation","entry_point_shift","concept_abstraction"],
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

`total_cells` = (number of selected leverage points) × 8. `coverage_ratio` = `occupied_count` /
`total_cells`. `underexplored` lists the `LP × operator` cells with no scheme. The validator checks
this arithmetic, so do not fake it.

## Gates (default: inline clickable panel)

The Gate-1 selection that triggers this skill comes from the default inline gate panel (or the
`AskUserQuestion` fallback) — the chosen `LP-###` ids arrive in the conversation; act on them and
generate. After writing `03`, **present Gate 2 the same way**: render the lateral schemes with
`mcp__visualize__show_widget` (toggle rows + a "let Claude decide" button that `sendPrompt`s the
choice), falling back to `AskUserQuestion`; never make the human type ids. Zero-setup, ships in the
pack (`reframe-workshop/references/gate_widget.md`). On the Gate-2 selection, run `vertical-audit`.

Optional advanced path — the `reframe-ui` browser channel: a `<channel source="reframe-ui" gate="1" …>`
event delivers the selection (explicit ids / NL intent / delegate); act on it, generate, then call the
`reply` tool so the UI advances. Not required.
