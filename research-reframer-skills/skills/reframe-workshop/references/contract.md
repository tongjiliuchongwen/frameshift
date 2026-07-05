# Research Reframer contract (v0.5 / schema_version 2.0)

The machine-readable single source of truth is `scripts/contract.py` (bundled next to the validator);
the JSON Schemas in `references/` mirror its vocabulary. This file is the human summary. The workflow
produces paired Markdown and JSON artifacts — Markdown for human reading, JSON for validation.

## Three-gate pipeline + artifacts

```text
outputs/
  01_system_map.json (+ .md)
  02_leverage_points.json (+ .md)        # LP-### (3-digit), 10 Meadows-style leverage types
  ── Gate 1: human selects LEVERAGE POINTS ──
  03_lateral_reframes.json (+ .md, .html)# LR-###; operators internal; not_yet_audited; coverage_ledger
  ── Gate 2: human selects LATERAL SCHEMES ──
  04_vertical_audits.json (+ .md, .html) # VA-###; adversarial dual-judge (Codex + Claude); default-reject
  ── Gate 3: human selects AUDITED SCHEMES ──
  06_idea_cards.json (+ .md)             # IC-###; method_trace re-points to VA
  05_human_selection.md
  decision_log.md
  reframe_report.md
```

## Trace chain (machine-checked)

```text
input_evidence → system_node → LP-### → LR-### → VA-### → IC-###
```

## Vocabulary (from contract.py)

- **lateral_operators (8):** assumption_challenge, reversal, decomposition, analogy, random_stimulus,
  PO_provocation, entry_point_shift, concept_abstraction. (The v0.2-only function_abstraction /
  boundary_shift / goal_inversion are retired.)
- **verdict:** reject | revise | keep (audit posture is default-reject).
- **auditor:** dual | codex | self.
- **audit_score keys:** coherence, testability, novelty_potential, research_value, risk (overall = mean).
- **id patterns:** `LP-### / LR-### / VA-### / IC-###` (3-digit; no v0.4 99-cap).
- **schema_version:** `2.0`.

## What the validator enforces (hard errors)

Required fields, enums, id formats; coverage-ledger arithmetic (`total_cells = selectedLP × 8`,
`occupied`, `underexplored` complement); dual-judge consistency (`agreement = codex==claude`,
conservative verdict + `needs_human` on disagreement); `audit_score.overall == mean`; the
`LP → LR → VA → IC` field-equality (a card's `method_trace` must match its source VA + LR); and the
existence of the human-gate audit trail (`05_human_selection.md`, `decision_log.md`).

Warnings (non-fatal) flag diversity collapse and ungrounded / generic rationales. The validator checks
the **contract and the trace**, not novelty or research quality.

## Honesty

Coverage and scores are heuristic inspection signals. Codex and Claude are both LLMs — an external
judge is more defensible than self-judgment but is not ground truth. This is not full MAP-Elites and
does not replace the researcher.
