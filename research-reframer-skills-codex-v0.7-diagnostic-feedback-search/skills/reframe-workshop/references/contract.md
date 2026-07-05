# Research Reframer Contract (v0.7 / schema_version 2.1)

The machine-readable source of truth is `scripts/contract.py`, bundled next to the validator. The
JSON Schemas in `references/` mirror its vocabulary. This file is the human summary.

## Three-Gate Pipeline And Artifacts

```text
outputs/
  00_diagnosis.json                       # original bottleneck and preserved value
  01_system_map.json (+ .md)
  02_leverage_points.json (+ .md)        # LP-###
  -- Gate 1: human selects leverage points
  03_lateral_reframes.json (+ .md, .html)# LR-###; judgment deferred
  -- Gate 2: human selects lateral schemes
  04_vertical_audits.json (+ .md, .html) # VA-###; external/local audit; default-reject
  -- Gate 3: human selects audited schemes
  06_idea_cards.json (+ .md)             # IC-###
  05_human_selection.md
  decision_log.md
  reframe_report.md
```

## Trace Chain

```text
diagnosis -> input_evidence -> system_node -> LP-### -> LR-### -> VA-### -> IC-###
```

## Vocabulary

- **dissatisfaction_types:** novelty_gap, unclear_mechanism, weak_testability, jargon_or_opacity,
  loose_structure, unclear_prior_difference, too_broad_to_execute, too_conservative.
- **system_relation_types:** fact, inference, analogy, low_confidence.
- **lateral_operators:** assumption_challenge, reversal, decomposition, analogy, random_stimulus,
  PO_provocation, entry_point_shift, concept_abstraction.
- **verdict:** reject | revise | keep.
- **auditor:** dual | codex | self.
- **pseudo_innovation.status:** clear | repairable | fatal.
- **audit_score keys:** coherence, testability, novelty_potential, research_value, risk.
- **id patterns:** `LP-### / LR-### / VA-### / IC-###`.
- **schema_version:** `2.1`.

## Validator Hard Errors

The validator enforces required fields, enums, id formats, relation audit metadata, coverage-ledger
arithmetic, dual-judge consistency, pseudo-innovation blocks, audit-score means, trace equality,
idea-card change logs, and the existence of `05_human_selection.md` and `decision_log.md`.

Warnings are non-fatal and flag diversity collapse or ungrounded/generic rationales. The validator
checks structure and trace, not novelty or research quality.

## Codex Edition Note

The v0.7 schema retains the historical `claude_verdict` field. In this Codex edition, that field means
the local/orchestrating judge verdict. `codex_verdict` means the separate external `codex exec` pass
when available.
