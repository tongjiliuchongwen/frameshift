---
name: vertical-audit
description: "Adversarially audit human-selected lateral reframes (v0.7 Stage 2, between Gate 2 and Gate 3). Default verdict is reject; a scheme survives only by passing three gates: a falsifiable minimal experiment exists, it is discriminable from prior work, and it answers so-what. Also classify pseudo-innovation failure types and record escalation/human-rescue semantics. Use after the sidecar sends the Gate 2 lateral-scheme selection; idea-card converts selected survivors next."
---

# Vertical Audit

Use this skill after Gate 2, when the Codex App Server sidecar has sent selected lateral schemes from
`03_lateral_reframes.json` as a `<codex_gate_selection>` event.

```text
lateral-generate -> Gate 2 sidecar selection -> vertical-audit -> Gate 3 sidecar selection -> idea-card
```

This is the convergence stage. The posture is adversarial and default-reject. A scheme is presumed
`reject` until it passes all three gates:

1. `minimal_experiment_exists`: a concrete, falsifiable minimal experiment is describable.
2. `discriminable_from_prior`: the idea is distinguishable from obvious prior work.
3. `so_what_passes`: a real researcher would care about the answer.

Treat `discriminable_from_prior` as an apparent prior-overlap risk based on the judge's available
memory and reasoning, not as a completed literature review. When rejecting on this gate, write
`novelty_risk` in cautious language such as "may collapse to..." and keep final idea-card status as
`needs_literature_check` unless a real literature search was performed.

## Language and Encoding Rules

- Write audit explanations, reasons, risks, and Markdown summaries in Simplified Chinese by default.
  Keep ids and technical terms in English only when they are necessary.
- Treat audit JSON as the technical layer and Gate 3 summaries as the reader layer. The reader layer
  should say what survived, how to test it, and what can go wrong in plain Chinese. Put raw boolean
  gates, pseudo-innovation labels, judge provenance, and score dimensions behind details.
- When writing reader-facing audit text, avoid letting English labels such as `minimal_experiment`,
  `discriminable_from_prior`, `pseudo_innovation`, or operator names become the explanation. Translate
  the meaning first; keep the raw label only in trace/detail fields.
- On Windows, never write Chinese artifacts by piping a PowerShell here-string into Python or Node
  (`@'...'@ | python -`, `@'...'@ | node`) or by using default `Set-Content` / `Out-File`. Use
  `apply_patch` or explicit UTF-8 file writes, then run the validator and reject any `????` or mojibake.

## Judge Provenance

Run two passes when possible:

- **External Codex judge.** Use a separate headless `codex exec` run with read-only access and the
  single-judge schema:

  ```sh
  codex exec --skip-git-repo-check -s read-only \
    --output-schema references/verdict.schema.json \
    -o <tmp>/va_<LR>.json - < <tmp>/prompt_<LR>.txt
  ```

  The prompt is `references/audit_rubric.md` plus the scheme fields.
- **Local judge.** The current orchestrating agent runs the same rubric independently.

Schema compatibility:

- Store the external result in `codex_verdict`.
- Store the local/orchestrating result in `claude_verdict`. The field name is historical and is kept
  so existing downstream readers can still recognize the field.
- Use `auditor: "dual"` when both passes ran, `auditor: "codex"` when only the external pass ran, and
  `auditor: "self"` when only the local pass ran.

If `codex` is not on PATH or is unauthenticated, skip the external pass, set `codex_verdict: null`,
fill `claude_verdict` with the local verdict, and record `auditor: "self"`.

## Resolution

`agreement = (codex_verdict == claude_verdict)` when both are present. If they agree, `verdict` equals
that value and `needs_human = false`. If they disagree, set `needs_human = true`, choose the more
conservative `verdict` (`reject` < `revise` < `keep`), and record both reasons for Gate 3.

When only one judge ran, that judge decides and `needs_human = false` unless the audit itself requires
human judgment.

## Workflow

1. Load `01_system_map.json`, `02_leverage_points.json`, `03_lateral_reframes.json`, and the Gate-2
   selected `LR-###` ids.
2. For each selected scheme, build the audit prompt and run available judges.
3. Resolve the verdict and fill the full `VA` record: `core_claim`, `causal_mechanism`,
   `critical_assumptions`, `novelty_risk`, `minimal_experiment`, `failure_modes`,
   `pseudo_innovation`, `merge_suggestions`, `escalation_reason`, `human_resolution`,
   `audit_score`, and `reasons`.
4. On `revise`, write a tightened `refined_scheme`; on `keep`, restate it; on `reject`, still record
   the attempted refinement and why it failed.
5. Fill `pseudo_innovation`:
   - `clear` when no pseudo-innovation pattern is visible.
   - `repairable` when the idea has a real kernel but currently looks like a terminology swap,
     glue splice, grand narrative, template fill, jargon mask, unverifiable divergence, or
     over-conservative repair.
   - `fatal` when the failure type is central and no useful narrowed claim remains.
6. Set `escalation_reason` to a non-empty explanation when `needs_human=true`; otherwise use `null`.
   `human_resolution` is `null` until Gate 3 records a rescue/selection resolution.
7. Set `audit_score.overall` to the mean of the five sub-scores to within 0.01.
8. Preserve real rejections. If every scheme passes, reread the rubric and tighten judgment.
9. Write `04_vertical_audits.json`, optional `.md`, and optional `.html`. Record judge provenance and
   disagreements in `decision_log.md`.
10. Stop. Gate 3 must be selected through the sidecar.

## Output Contract

Return JSON matching `schemas/vertical_audits.schema.json`.

Each audit must include `audit_id`, `source_lateral_id`, `auditor`, `codex_verdict`,
`claude_verdict`, `agreement`, `needs_human`, `verdict`, the three boolean audit gates,
`refined_scheme`, `core_claim`, `causal_mechanism`, `critical_assumptions`, `novelty_risk`,
`minimal_experiment`, `failure_modes`, `pseudo_innovation`, `merge_suggestions`,
`escalation_reason`, `human_resolution`, `audit_score`, and `reasons`.

`pseudo_innovation.status` is `clear|repairable|fatal`; `failure_types` may include
`terminology_swap`, `glue_splice`, `grand_narrative`, `template_fill`, `jargon_masking`,
`unverifiable_divergence`, and `over_conservative_repair`.

## Handoff: Gate 3

Stop after writing `04_vertical_audits.json`. Gate 3 is selected only through the Codex App Server
sidecar in `../codex-appserver-gate-test`; do not ask the user to type ids into chat. The sidecar
renders eligible `VA-###` audits and locks both-judge rejects out of selection. When the next turn
arrives with `<codex_gate_selection><gate>3</gate>...`, run `idea-card` and the validator.
