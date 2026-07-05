# Decision log — physmaster v0.7

Pipeline: `diagnosis → system-map → leverage-scan → [Gate1] → lateral-generate → [Gate2] → vertical-audit → [Gate3] → idea-card`.
Schema contract: v0.7 (`schema_version: 2.1`). Trace chain: diagnosis → input → system_node → LP → LR → VA → IC.

## Stage 1 — lateral-generate (judgment deferred)
- 7 lateral schemes across LP-001/002/005, operators internal (reversal, assumption_challenge,
  decomposition, PO_provocation, analogy, concept_abstraction).
- Coverage ledger: 7/24 cells occupied (ratio 0.29), 17 underexplored — empty cells recorded, not hidden.
- No scoring at this stage (de Bono: stay generative). All schemes `not_yet_audited: true`.

## Stage 2 — vertical-audit (adversarial, dual-judge)
Judges: **Codex** (external engine, `codex exec`, read-only, schema-forced verdict) + **Claude** (this agent),
same default-reject rubric, independently.

| VA | source | codex | claude | agreement | resolved | note |
|----|--------|-------|--------|-----------|----------|------|
| VA-001 | LR-001 | reject | revise | no | reject* | escalated → Gate 3 |
| VA-002 | LR-003 | reject | reject | yes | reject | rejected drawer |
| VA-003 | LR-004 | reject | reject | yes | reject | rejected drawer |
| VA-004 | LR-006 | reject | revise | no | reject* | escalated → Gate 3 |

\*resolved verdict on disagreement is the conservative (reject) placeholder; `needs_human=true` hands it to Gate 3.

Codex rejected all four on `discriminable_from_prior=false` (a hard, fair gate — the same adversarial
posture that the sibling `frameshift` project needed three rounds to reach). Two agreement-rejects fill
the "rejected drawer" with real, reasoned true-negatives. Two disagreements were escalated.

## Stage 3 — idea-card (Gate-3 human resolution)
Human rescued the two escalated audits (`revise`) → IC-001 (缺席证明锚定的问题发现),
IC-002 (条件感知的失败重激活记忆). Each card inherits its audit's refined scheme + minimal experiment;
`method_trace` re-points to the VA with full LP→LR→VA lineage (machine-checked field equality).

## Honest limits
Heuristic audit scores; QD-lite-style coverage ledger is an inspection signal, not a quality guarantee;
Codex/Claude are both LLMs (external ≠ ground truth). Validator checks contract + trace, not novelty.
