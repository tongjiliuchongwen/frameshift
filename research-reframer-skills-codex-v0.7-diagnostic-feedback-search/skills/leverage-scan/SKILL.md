---
name: leverage-scan
description: "Find high-leverage reframing points in a structured system map. Use after system-map, or whenever Codex has actors, goals, rules, information flows, boundaries, delays, feedback loops, assumptions, or failure modes and needs to identify human-selectable places where a research problem can be reframed."
---

# Leverage Scan

Use this skill to turn a system map into ranked reframing leverage points. The output is not a list of
ideas. It is a list of places where changing the frame could create better research questions.

In v0.7, leverage points should answer the Stage 0 diagnosis: they should target the primary
bottleneck while preserving the original idea's core value.

## Language and Encoding Rules

- Write natural-language leverage-point fields in Simplified Chinese by default. Preserve ids and
  source technical terms in English when needed.
- Write human-selectable fields as the reader layer: concise Chinese, no raw schema labels, and no
  unexplained English terms. Put system node ids, source quotes, and technical trace in detail fields.
- For Gate 1, each leverage point should be understandable from three plain lines: what the current
  default assumption is, where it blocks the problem, and what kind of downstream ideas selecting it
  will generate.
- On Windows, never write Chinese artifacts by piping a PowerShell here-string into Python or Node
  (`@'...'@ | python -`, `@'...'@ | node`) or by using default `Set-Content` / `Out-File`. Use
  `apply_patch` or explicit UTF-8 file writes, then run the validator and reject any `????` or mojibake.

## Input

Use a `system_map.json` or equivalent structured notes containing actors, goals, stocks, flows,
feedback loops, information flows, delays, boundaries, assumptions, uncertainties, and failure modes.
If the input is prose, first normalize it with `system-map`.

When available, also read `00_diagnosis.json` and use `primary_bottleneck`, `core_value_to_preserve`,
and `downstream_focus` to rank leverage points.

## Leverage Types

- `parameter`: threshold, metric, hyperparameter, sample size, or constant.
- `buffer`: stock, reserve, slack, or robustness margin.
- `structure`: architecture, boundary, causal path, or aggregation level.
- `delay`: timing gap between signal, action, and consequence.
- `feedback_loop`: reinforcing or balancing loop.
- `information_flow`: who sees what, when, with what fidelity.
- `rule`: incentive, policy, access rule, benchmark, or constraint.
- `self_organization`: how the system can create new structure or roles.
- `goal`: what the system optimizes for.
- `paradigm`: the deep assumption defining what counts as a valid problem.

Prefer `information_flow`, `rule`, `goal`, and `paradigm` when grounded in the input.

## Workflow

1. Scan each system-map section for assumptions that lock the current problem frame.
2. Convert each lock into a leverage point with an explicit system location.
3. Rank by reframing potential against the Stage 0 diagnosis, not immediate feasibility.
4. Mark which points are suitable for human selection.
5. Include enough trace data that later artifacts can point back to the source.

## Output Contract

Return JSON with this shape:

```json
{
  "schema_version": "2.1",
  "source_system": "system name",
  "leverage_points": [
    {
      "id": "LP-001",
      "type": "information_flow",
      "system_location": "where in the system map this point lives",
      "source_trace": {
        "system_node_ids": ["I01", "R02"],
        "input_evidence": "short exact source phrase when available"
      },
      "why_it_matters": "why this point can change the research frame",
      "current_assumption": "what the current frame assumes",
      "reframing_potential": "high|medium|low",
      "risk": "what could make this point misleading or unproductive",
      "human_selectable": true
    }
  ],
  "selection_guidance": "which 2-4 points a human should consider selecting and why"
}
```

## Quality Rules

- Target 8-15 leverage points for rich runs. Use 3-5 only for compact demos or very short inputs.
- Do not turn every limitation into a leverage point.
- Avoid vague locations such as "the method" or "the system".
- Prefer exact source phrases in `source_trace.input_evidence`.
- Prefer leverage points that directly explain which diagnosis bottleneck they address.
- Include at least one high-level point involving a rule, goal, paradigm, or information flow when supported.
- Keep `human_selectable` true only when a researcher can make a meaningful preference choice.

## Handoff: Gate 1

Stop after writing `02_leverage_points.json`. Gate 1 is selected only through the Codex App Server
sidecar in `../codex-appserver-gate-test`; do not ask the user to type ids into chat. When the next
turn arrives with `<codex_gate_selection><gate>1</gate>...`, run `lateral-generate` only on those
selected `LP-###` ids.
