# reframe-ui wire contract (v0.5, three-gate)

One Node process = (a) a Claude Code **channel** (MCP over stdio) + (b) a localhost **HTTP/SSE** server.
The browser talks ONLY to the HTTP/SSE side; Claude Code talks ONLY to the MCP/stdio side.

```
browser UI  --HTTP-->  reframe-ui process  --MCP notification-->  Claude Code session
browser UI  <--SSE---  reframe-ui process  <--MCP reply tool----  Claude Code session
```

The three gates: **Gate 1** picks leverage points (`LP-###`) → agent runs `lateral-generate` → `03`;
**Gate 2** picks lateral schemes (`LR-###`) → `vertical-audit` → `04`; **Gate 3** picks audited
schemes (`VA-###`) → `idea-card` → `06`.

## HTTP endpoints (browser ↔ process), bound to 127.0.0.1

### GET `/` → the selection UI (`ui.html`)

### GET `/state[?run=<name>]` → current run state (JSON)
`run` optionally switches the active run (a single folder name under the runs base). The `gate` is
decided by contract **validity** (an artifact counts only if `schema_version === "2.0"` and its array
is non-empty), not mere file existence.

```jsonc
{
  "ok": true,
  "run_id": "physmaster-three-gate",
  "gate": 1 | 2 | 3 | "done" | "not_ready",
  // 1 if 02 valid & 03 absent; 2 if 03 valid & 04 absent; 3 if 04 valid & 06 absent; "done" if 06 valid
  "leverage": [   // present at gate 1 (from 02_leverage_points.json), else null
    { "id": "LP-002", "type": "rule", "system_location": "…", "why_it_matters": "…",
      "current_assumption": "…", "reframing_potential": "high" }
  ],
  "lateral": {    // present at gate 2 (from 03_lateral_reframes.json), else null
    "source_leverage_points": ["LP-001","LP-002","LP-005"],
    "coverage_ledger": { "occupied_count": 7, "total_cells": 24, "coverage_ratio": 0.2917, "underexplored": 17 },
    "schemes": [ { "lateral_id": "LR-001", "source_leverage_point": "LP-001", "operator": "reversal",
      "old_frame": "…", "new_frame": "…", "scheme": "…", "why_interesting": "…",
      "changed_assumption": "…", "bad_use_to_avoid": "…" } ]
  },
  "audits": [     // present at gate 3 (from 04_vertical_audits.json), else null
    { "audit_id": "VA-001", "source_lateral_id": "LR-001", "verdict": "reject",
      "codex_verdict": "reject", "claude_verdict": "revise", "agreement": false, "needs_human": true,
      "minimal_experiment_exists": true, "discriminable_from_prior": true, "so_what_passes": true,
      "refined_scheme": "…", "core_claim": "…", "novelty_risk": "…", "minimal_experiment": "…",
      "failure_modes": ["…"], "overall": 3.6, "reasons": ["…"],
      "eligible": true }   // can become a card: keep/revise survivor OR escalated needs_human
  ],
  "cards": [ { "id": "IC-001", "title": "…", "one_sentence": "…" } ],  // present when "done", else null
  "last_status": "string|null"
}
```

### GET `/runs` → `{ "base": "<abs>", "active": "<name>", "runs": ["physmaster-three-gate", …] }`

### POST `/select` → deliver a human selection into the Claude session
Request body:
```jsonc
{
  "gate": 1 | 2 | 3,
  "mode": "explicit" | "nl" | "delegate",
  "ids": ["LP-002", "LP-005"],   // gate 1 = LP- ; gate 2 = LR- ; gate 3 = VA- ; [] for nl/delegate
  "intent": "偏动态反馈、目标函数和 human control"   // free text for nl/delegate; "" otherwise
}
```
Response: `{ "ok": true, "delivered": { … } }`, or `{ "ok": false, "error": "…" }` with a status code.

Validation (checked against the current run state before anything is pushed into the session):

| Condition | Status |
| --- | --- |
| cross-origin request, or non-local `Host` | `403` |
| `Content-Type` is not `application/json` | `415` |
| body larger than 64 KB | `413` |
| malformed JSON / bad `gate` (not 1/2/3) / bad `mode` | `400` |
| the run is not currently at the submitted `gate` | `409` |
| `explicit` ids have the wrong prefix (`LP-`/`LR-`/`VA-` per gate) | `400` |
| `explicit` ids don't exist, or (gate 3) name a both-judges-rejected, non-card-eligible audit | `400` |
| `nl`/`delegate` carry `ids`, or `nl` has an empty `intent` | `400` |

### GET `/events` → Server-Sent Events stream (process → browser push)
Emits `data: {"type":"hello"}` on connect, then `data: {"type":"status","text":"…"}` whenever the
agent calls the `reply` tool. On a status event the UI re-`GET`s `/state` and advances.

## MCP side (process ↔ Claude Code)

- Capability: `capabilities.experimental["claude/channel"] = {}` (+ `tools: {}` for the reply tool).
- **Inbound to Claude** (on `/select`): `notification("notifications/claude/channel", { content, meta })`
  - `content` = a plain-language directive Claude acts on (includes the user's intent for nl/delegate).
  - `meta` = identifier-keyed routing only; values are ids/enums: `{ gate, mode, run_id, ids?: "LP-..,LP-.." }`.
  - Arrives as `<channel source="reframe-ui" gate="1" mode="explicit" run_id="…" ids="LP-002,LP-005">…content…</channel>`.
- **Outbound from Claude** (the `reply` tool): `{ name: "reply", inputSchema: { text: string } }`. Calling it
  pushes an SSE `status` event to every browser client so the UI advances. Returns `sent`.

## Behavioral rules baked into the channel `instructions`
- **Gate 1** → record to `05_human_selection.md` + `decision_log.md`, run `lateral-generate` on the chosen
  leverage points only, then call `reply`. Never re-run `system-map` / `leverage-scan`.
- **Gate 2** → run `vertical-audit` (Codex + Claude dual-judge, default-reject) on the chosen schemes,
  append the selection log, then call `reply`.
- **Gate 3** → run `idea-card` on the chosen audits (`method_trace` verbatim from the VA + LR;
  `needs_human` resolved to the human's keep/revise), run the validator to exit 0, then call `reply`.
