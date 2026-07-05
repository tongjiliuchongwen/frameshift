---
name: idea-card
description: "Turn Gate-3-selected vertical audits into traceable, testable research idea cards with provenance, minimal experiments, evaluation metrics, expected observations, failure cases, change logs, related-work queries, and next steps. Use after the vertical-audit skill in the v0.7 diagnostic three-gate workflow, once the human has selected which audited schemes survive and deserve a card."
---

# Idea Card (v0.7)

Use this skill to convert **Gate-3-selected vertical audits** into actionable research idea cards.
This is the final convergence step: every card must be traceable, testable, and explicit about
failure. A card may only descend from an audit the human kept/revised, or a `needs_human` audit the
human rescued at Gate 3 — never from an audit both judges rejected.

## Language and Encoding Rules

- Write idea-card prose, experiment descriptions, failure cases, and Markdown summaries in Simplified
  Chinese by default. Keep ids and technical terms in English only when useful.
- Use a two-layer idea-card structure:
  - **Reader layer:** the default UI/report view. Write for a related-field researcher who is not in
    this exact subfield. Use plain Simplified Chinese, short sentences, and the order
    "这是什么意思 -> 为什么重要 -> 怎么验证 -> 可能在哪里失败". Avoid schema field names and dense
    English terminology.
  - **Technical layer:** `system_trace`, `method_trace`, `audit_score`, related-work queries, raw ids,
    operators, and source evidence. Keep this layer in JSON, appendices, or collapsed details.
- For reader-layer prose, use `中文解释（English term）` only on the first necessary occurrence of a
  technical term. Later mentions should use the Chinese explanation. Do not write mixed phrases such
  as "baseline/threshold sensitivity atlas" in the default reader layer unless it is immediately
  explained in Chinese.
- Before finalizing, run a readability cleanup: remove unnecessary English, split long sentences,
  replace jargon stacks with "action + result + condition", and keep all trace details in the
  technical layer. Do not add new scientific claims during this cleanup.
- On Windows, never write Chinese artifacts by piping a PowerShell here-string into Python or Node
  (`@'...'@ | python -`, `@'...'@ | node`) or by using default `Set-Content` / `Out-File`. Use
  `apply_patch` or explicit UTF-8 file writes, then run the validator and reject any `????` or mojibake.

## Input

- `04_vertical_audits.json` and the Gate-3 selection (`VA-###` ids).
- Upstream for the trace chain: `03_lateral_reframes.json`, `02_leverage_points.json`,
  `01_system_map.json`, and `00_diagnosis.json`.

Each card inherits its content from the audit: the `refined_scheme`, the `minimal_experiment`, the
`failure_modes`, the `audit_score`, and the resolved `verdict`. Do not re-invent the experiment —
carry the one the audit already produced (tighten wording only).

## Workflow

1. Convert each selected `VA-###` into one card.
2. Make the title specific enough to distinguish it from nearby ideas.
3. Carry the audit's minimal experiment, evaluation metrics, expected observation, and failure case;
   keep them card-specific (do not reuse one template across cards).
4. Add `related_work_queries` (from the audit's `novelty_risk`) rather than unsupported literature claims.
5. Build `method_trace` so the card traces back through `VA → LR → LP`. The frame fields
   (`old_frame`, `new_frame`, `changed_assumption`) must equal the source **lateral scheme**; the
   `operator` and `source_leverage_point` must equal the lateral scheme; the `audit_score` must equal
   the source **audit**; and `audit_verdict` must be the resolved `keep`/`revise` (for a rescued
   `needs_human` audit, this is the human's resolution).
6. Keep `system_trace.reframe` = the `VA-###` id, `system_trace.leverage_point` =
   `method_trace.source_leverage_point`, and `system_trace.lateral_operation` = `method_trace.operator`.
7. Add `change_log` so the card states which diagnosis bottleneck it addresses, which leverage point
   it uses, what structure changed, what mechanism was added, what original value was preserved,
   what was removed or weakened, what the real increment is, and what remains fragile.

## Output Contract

Return JSON matching `references/idea_cards.schema.json`:

```json
{
  "schema_version": "2.1",
  "idea_cards": [
    {
      "id": "IC-001",
      "title": "specific research direction",
      "one_sentence": "one-sentence summary",
      "original_problem": "old frame",
      "reframed_problem": "audit refined scheme / new frame",
      "changed_assumption": "assumption changed by the reframe",
      "system_trace": {
        "input_evidence": "short exact source phrase when available",
        "system_node": "node id",
        "leverage_point": "LP-007",
        "lateral_operation": "reversal",
        "reframe": "VA-001"
      },
      "method_trace": {
        "source_vertical_audit": "VA-001",
        "source_lateral_scheme": "LR-001",
        "source_leverage_point": "LP-007",
        "operator": "reversal",
        "source_system_nodes": ["I01"],
        "old_frame": "old frame (equals the lateral scheme)",
        "new_frame": "new frame (equals the lateral scheme)",
        "changed_assumption": "changed assumption (equals the lateral scheme)",
        "audit_verdict": "revise",
        "audit_score": { "coherence": 4, "testability": 5, "novelty_potential": 3, "research_value": 4, "risk": 3, "overall": 3.8 }
      },
      "why_not_obvious": "why this is not a simple extension of the input",
      "minimal_experiment": "data, intervention, comparison, and measurement (from the audit)",
      "evaluation_metrics": ["metric 1", "metric 2"],
      "expected_observation": "what would support the idea",
      "failure_case": "what result would weaken or refute it (from the audit's failure modes)",
      "related_work_queries": ["query for closest prior work", "query for novelty check"],
      "next_steps": ["concrete next action"],
      "status": "needs_literature_check",
      "reader_view": {
        "headline": "plain Chinese title for default UI",
        "summary": "one or two plain Chinese sentences",
        "original_default": "what the original paper assumes, in plain Chinese",
        "new_question": "what the card changes, in plain Chinese",
        "minimal_test": "how to test it, in plain Chinese",
        "main_risk": "how it can fail, in plain Chinese"
      },
      "change_log": {
        "source_diagnosis": "primary bottleneck from 00_diagnosis.json addressed by this card",
        "selected_leverage_point": "LP-007",
        "structural_change": "what system structure changed",
        "new_mechanism": "what mechanism makes the idea work",
        "preserved_from_original": "core value preserved from the original idea",
        "removed_or_weakened": "claims, jargon, or broad framing removed during audit",
        "real_increment_over_original": "why this is stronger than the original",
        "remaining_fragility": "the most important unresolved weakness"
      }
    }
  ]
}
```

## Quality rules

- Reject or repair cards without a minimal experiment. No inspiration-only cards.
- Keep `method_trace` byte-consistent with the source audit and lateral scheme — the validator checks
  field equality on operator, leverage point, frames, `audit_score`, and `audit_verdict`. Do not edit
  those values; tighten only the human-facing prose fields.
- Make each card's `failure_case`, `related_work_queries`, and `next_steps` distinct. Repeated text
  usually means the card is still a template, not a research plan.
- Make `change_log` concrete. It should be possible to read it alone and understand what changed
  from the original idea and why the change is better.
- Avoid fake citations. Use `related_work_queries` until actual literature search is performed; mark
  `status: "needs_literature_check"` until then.
- Prefer 2–4 strong cards. Cards descend only from surviving audits, so a default-reject audit may
  legitimately yield few cards — that is the point, not a failure.

## Handoff

Produce `06_idea_cards.json` (+ `06_idea_cards.md`). Run the bundled validator before reporting:

```bash
python <installed-skills-dir>/reframe-workshop/scripts/validate_outputs.py path/to/outputs
```
