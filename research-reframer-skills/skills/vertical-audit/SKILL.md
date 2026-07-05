---
name: vertical-audit
description: "Adversarially audit human-selected lateral reframes (v0.5 Stage 2, between Gate 2 and Gate 3). Default verdict is REJECT; a scheme survives only by passing three gates (a falsifiable minimal experiment exists, it is discriminable from prior work, it answers so-what). Two independent judges run — Codex (external engine) and Claude — and disagreement is escalated to the human at Gate 3. Use after the human selects lateral schemes; idea-card converts survivors next."
---

# Vertical Audit

Use this skill after **Gate 2** (the human picked the *interesting* lateral schemes from
`03_lateral_reframes.json`). It is the **convergence** stage of the v0.5 three-gate flow:

```
lateral-generate -> [Gate 2: select LR] -> vertical-audit -> [Gate 3: select VA] -> idea-card
```

This is the vertical half of de Bono's split: **now judge, deepen, and select.** The posture is
**adversarial and default-reject** — the lesson from the sibling `frameshift` project was that a
gentle "revise and keep" gate rejects nothing and is indefensible. A scheme is presumed `reject`
and must actively pass all three gates:

1. `minimal_experiment_exists` — a concrete, falsifiable minimal experiment is actually describable.
2. `discriminable_from_prior` — it is distinguishable from obvious prior work, not a renamed known
   idea.
3. `so_what_passes` — a real researcher would care about the answer.

## Dual judges (Codex + Claude)

Each Gate-2 scheme is audited **independently by two engines** so the judge is not just the model
that generated the scheme:

- **Codex (external).** Validated headless invocation (read-only sandbox, schema-forced verdict):

  ```sh
  codex exec --skip-git-repo-check -s read-only \
    --output-schema references/verdict.schema.json \
    -o <tmp>/va_<LR>.json - < <tmp>/prompt_<LR>.txt
  ```

  The prompt = `references/audit_rubric.md` + the scheme's fields. Codex returns a `verdict` plus the
  three gate booleans and `reasons`. If `codex` is not on PATH or unauthenticated, skip it and set
  `auditor: "self"` (honest provenance).
- **Claude (this agent).** Run the *same* `references/audit_rubric.md` yourself on the same scheme.

**Resolution.** `agreement = (codex_verdict == claude_verdict)`. If they agree, `verdict` = that
value and `needs_human = false`. If they disagree, set `needs_human = true`, take the **more
conservative** `verdict` (`reject` < `revise` < `keep`), and record both so the human resolves it at
Gate 3. When only one judge ran, `auditor` is `codex` or `self` and that judge decides.

## Workflow

1. Load `01_system_map.json`, `02_leverage_points.json`, `03_lateral_reframes.json`, and the Gate-2
   selection (`LR-###` ids).
2. For each selected scheme, build the audit prompt and run **both** judges.
3. Resolve each verdict (agreement / conservative-on-disagreement) and fill the full `VA` record:
   `core_claim`, `causal_mechanism`, `critical_assumptions`, `novelty_risk`, `minimal_experiment`,
   `failure_modes`, optional `merge_suggestions` (point at another `LR-###`), `audit_score`, and
   `reasons`. On `revise`, write a tightened `refined_scheme`; on `keep`, restate it; on `reject`,
   still record the refined-as-attempted scheme and why it failed.
4. `audit_score.overall` = mean of the five sub-scores (coherence, testability, novelty_potential,
   research_value, risk), to within 0.01 — the validator checks this.
5. **Expect real rejections.** If every scheme passes, you are being too generous — re-read the
   rubric. Preserve rejected `VA` records with reasons (the "rejected drawer" that v0.3 never filled).
6. Write `04_vertical_audits.json`, `04_vertical_audits.md`, and (when a renderer is available)
   `04_vertical_audits.html`. Record judge provenance + any disagreements in `decision_log.md`.
7. Stop. The human selects survivors at **Gate 3**; only `keep`/`revise` audits are eligible for a
   card.

## Output Contract

Return JSON matching `schemas/vertical_audits.schema.json`:

```json
{
  "schema_version": "2.0",
  "audited_lateral_ids": ["LR-001", "LR-004"],
  "audits": [
    {
      "audit_id": "VA-001",
      "source_lateral_id": "LR-001",
      "auditor": "dual",
      "codex_verdict": "reject",
      "claude_verdict": "revise",
      "agreement": false,
      "needs_human": true,
      "verdict": "reject",
      "minimal_experiment_exists": true,
      "discriminable_from_prior": false,
      "so_what_passes": false,
      "refined_scheme": "Narrow to: does rejected-trace feedback reduce repeated shallow reframes vs a no-feedback baseline?",
      "core_claim": "A trace-feedback loop reduces shallow repeats and increases grounded frame shifts.",
      "causal_mechanism": ["Agent emits reframes", "Trace exposes frame moves + failures", "Feedback constrains next search", "Future candidates diversify"],
      "critical_assumptions": ["Trace is structured enough to guide behavior", "Agent can tell shallow variation from real frame shift"],
      "novelty_risk": "Overlaps reflection / self-critique memory / negative-example feedback.",
      "minimal_experiment": "A/B reframe search with vs without rejected-trace feedback; measure duplicate-rate and accepted-idea quality.",
      "failure_modes": ["Overfits to evaluator preferences", "Agent games the trace instead of improving reframes"],
      "merge_suggestions": [{ "with": "LR-004", "reason": "Rejected-reframe branch memory could be the persistence mechanism." }],
      "audit_score": { "coherence": 4, "testability": 5, "novelty_potential": 2, "research_value": 3, "risk": 3, "overall": 3.4 },
      "reasons": ["Codex: not discriminable from reflection/negative-example feedback; so-what weak.", "Claude: salvageable if narrowed to the duplicate-rate ablation."]
    }
  ]
}
```

## Gates (default: inline clickable panel)

The Gate-2 selection that triggers this skill arrives from the default inline gate panel (or the
`AskUserQuestion` fallback). After auditing, **present Gate 3 the same way**: render the audits with
`mcp__visualize__show_widget` — eligible (`keep`/`revise` or `needs_human`) schemes as toggle rows plus
a "let Claude decide" button that `sendPrompt`s the choice, and both-judges-rejected audits in a
read-only "rejected drawer" — falling back to `AskUserQuestion`; never make the human type ids.
Zero-setup, ships in the pack (`reframe-workshop/references/gate_widget.md`). On the Gate-3 selection,
run `idea-card` and the validator.

Optional advanced path — the `reframe-ui` browser channel: a `<channel source="reframe-ui" gate="2" …>`
event delivers the selection; run the audit, then call `reply` so the UI advances to Gate 3 (with
`needs_human` flagged). Not required.
