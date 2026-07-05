---
name: leverage-scan
description: "Find high-leverage reframing points in a structured system map. Use after system-map, or whenever an agent has actors, goals, rules, information flows, boundaries, delays, feedback loops, assumptions, or failure modes and needs to identify human-selectable places where a research problem can be reframed."
---

# Leverage Scan

Use this skill to turn a system map into a ranked list of reframing leverage points. The output is not a list of ideas. It is a list of places where changing the frame could create better research questions.

## Input

Use a `system_map.json` or equivalent structured notes containing:

- Actors and incentives
- Goals and evaluation rules
- Stocks, flows, and feedback loops
- Information flows and delays
- Boundaries, assumptions, uncertainties, and failure modes

If the input is prose, first normalize it into the relevant fields from `$system-map`.

## Leverage Types

Use these research-oriented leverage types:

- `parameter`: a threshold, metric, hyperparameter, sample size, or constant
- `buffer`: a stock, reserve, slack, or robustness margin
- `structure`: a system architecture, modular boundary, causal path, or aggregation level
- `delay`: a timing gap between signal, action, and consequence
- `feedback_loop`: a reinforcing or balancing loop that shapes behavior
- `information_flow`: who sees what, when, with what fidelity
- `rule`: incentive, policy, access rule, benchmark, or constraint
- `self_organization`: how the system can create new structure or roles
- `goal`: what the system optimizes for
- `paradigm`: the deep assumption that defines what counts as a valid problem

Prefer `information_flow`, `rule`, `goal`, and `paradigm` when they are grounded in the input; they usually create stronger reframes than parameter tweaks.

## Workflow

1. Scan each system-map section for assumptions that lock the current problem frame.
2. Convert each lock into a leverage point with an explicit system location.
3. Rank by reframing potential, not by immediate feasibility.
4. Mark which points are suitable for human selection.
5. Include enough trace data that a later idea card can point back to the source.

## Output Contract

Return JSON with this shape:

```json
{
  "schema_version": "2.0",
  "source_system": "system name",
  "leverage_points": [
    {
      "id": "LP-001",
      "type": "information_flow",
      "system_location": "where in the system map this point lives",
      "source_trace": {
        "system_node_ids": ["I01", "R02"],
        "input_evidence": "short exact source phrase when available, otherwise a system-map statement"
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

- Target 8-15 leverage points for rich workshop runs. For compact demos or very short inputs, 3-5 representative leverage points are acceptable if they are diverse and traceable.
- Do not turn every limitation into a leverage point. A leverage point must identify what can be changed in the frame.
- Avoid vague locations such as "the method" or "the system". Point to a rule, boundary, feedback loop, information path, or goal.
- Prefer exact source phrases in `source_trace.input_evidence`. Use a system-map statement only when the original input is unavailable.
- Include at least one high-level point involving a rule, goal, paradigm, or information flow when supported by the input.
- Keep `human_selectable` true only when a researcher can make a meaningful preference choice about the point.

## Handoff — Gate 1 (default: inline clickable panel)

Present **Gate 1** as a clickable panel, never a static list the user types ids back from: render the
leverage points with the `mcp__visualize__show_widget` tool (toggle rows + a "let Claude decide" button
that `sendPrompt`s the selection), and fall back to `AskUserQuestion` if `show_widget` is unavailable.
This is zero-setup and ships in the pack — see `reframe-workshop/references/gate_widget.md`. The human
picks 2-4 leverage points (*where in the system to cut*); on the selection, run the installed
`lateral-generate` skill on the chosen points. The optional `reframe-ui` browser channel is an advanced
alternative, not required.
