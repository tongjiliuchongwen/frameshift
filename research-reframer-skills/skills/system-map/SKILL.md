---
name: system-map
description: "Extract the hidden system structure from a rough research idea, paper abstract, proposal, project note, README, or slide text. Use when an agent needs to turn unstructured early-stage research material into actors, goals, stocks, flows, feedback loops, rules, information flows, delays, boundaries, failure modes, and uncertainties before ideation or reframing."
---

# System Map

Use this skill to convert a rough research input into a structured system map. Do not brainstorm ideas yet. The purpose is to expose the structure that later skills can reframe.

## Input

Accept any text artifact:

- Rough idea or proposal
- Paper abstract plus limitation section
- Project note, README, issue, or slide text
- User-provided domain constraints or preferences

If the source is long, first extract the sections that define the problem, actors, assumptions, limitations, methods, evaluation, and intended users.

## Workflow

1. Identify the current problem frame in one sentence.
2. Extract direct evidence from the input before adding interpretation.
3. Map the system using the output contract below.
4. Keep uncertain inferences explicit in `uncertainties`.
5. Produce both a readable Markdown summary and JSON when the user wants downstream validation.

## Output Contract

Return JSON with this shape:

```json
{
  "schema_version": "2.0",
  "system_name": "short name",
  "source_summary": "what the input is trying to do",
  "original_problem": "the problem frame the input currently assumes",
  "actors": [
    {
      "id": "A01",
      "name": "actor name",
      "role": "what this actor does",
      "incentives": ["what this actor optimizes for"]
    }
  ],
  "goals": [
    {
      "id": "G01",
      "statement": "goal or success definition",
      "owner": "A01 or unknown"
    }
  ],
  "stocks": [
    {
      "id": "S01",
      "name": "accumulated state",
      "description": "what builds up or depletes"
    }
  ],
  "flows": [
    {
      "id": "F01",
      "from": "source node",
      "to": "target node",
      "description": "movement, influence, or conversion"
    }
  ],
  "feedback_loops": [
    {
      "id": "B01",
      "type": "balancing|reinforcing|unknown",
      "description": "loop behavior",
      "nodes": ["node ids or names"]
    }
  ],
  "rules": [
    {
      "id": "RL01",
      "statement": "constraint, norm, policy, metric, or evaluation rule",
      "explicitness": "explicit|implicit|inferred"
    }
  ],
  "information_flows": [
    {
      "id": "I01",
      "sender": "actor or system part",
      "receiver": "actor or system part",
      "content": "what information moves",
      "timing": "when it appears"
    }
  ],
  "delays": [
    {
      "id": "T01",
      "description": "lag between action and consequence",
      "effect": "why the lag matters"
    }
  ],
  "boundaries": [
    {
      "id": "BD01",
      "inside": "what the current frame includes",
      "outside": "what it leaves out"
    }
  ],
  "failure_modes": [
    {
      "id": "FM01",
      "description": "how the system can fail",
      "linked_nodes": ["node ids or names"]
    }
  ],
  "uncertainties": [
    {
      "id": "U01",
      "question": "what is unclear",
      "why_it_matters": "how it affects reframing"
    }
  ]
}
```

## Quality Rules

- Prefer structure over polish. A terse but traceable system map is better than a fluent essay.
- Separate what the input says from what you infer.
- Do not invent literature support. Put missing evidence in `uncertainties`.
- Include at least one `rules`, `information_flows`, `boundaries`, and `failure_modes` item for non-trivial inputs.
- Preserve terms from the source when they are meaningful; normalize only enough to make downstream references stable.

## Handoff

After producing the system map, suggest using the installed leverage-scan skill to find reframing leverage points (`$leverage-scan` in Codex-style prompts, or `/leverage-scan` where slash skill invocation is supported). If the user wants the whole process, suggest reframe-workshop.
