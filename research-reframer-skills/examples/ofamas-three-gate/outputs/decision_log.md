# Decision log — ofamas v0.5

Pipeline: `system-map → leverage-scan → [Gate1] → lateral-generate → [Gate2] → vertical-audit → [Gate3] → idea-card`.
Schema contract: v0.5 (`schema_version: 2.0`). Trace chain: input → system_node → LP → LR → VA → IC.

## Stage 1 — lateral-generate (judgment deferred)
- 7 lateral schemes across LP-001/002/004, operators internal (reversal, assumption_challenge,
  decomposition, PO_provocation, analogy, concept_abstraction).
- Coverage ledger: 7/24 cells occupied (ratio 0.29), 17 underexplored.
- No scoring at this stage; all schemes `not_yet_audited: true`.

## Stage 2 — vertical-audit (adversarial, dual-judge)
Judges: **Codex** (external `codex exec`, read-only, schema-forced) + **Claude**, same default-reject rubric, independently.

| VA | source | codex | claude | agreement | resolved | note |
|----|--------|-------|--------|-----------|----------|------|
| VA-001 | LR-001 不确定性路由 | reject | reject | yes | reject | rejected drawer |
| VA-002 | LR-003 结构vs内容消融 | reject | revise | no | reject* | escalated → Gate 3 |
| VA-003 | LR-004 固定拓扑证伪基线 | reject | revise | no | reject* | escalated → Gate 3 |
| VA-004 | LR-006 噪声合成标签 | reject | reject | yes | reject | rejected drawer |

\*conservative placeholder on disagreement; `needs_human=true` hands it to Gate 3.

Codex rejected all four on `discriminable_from_prior=false` (LR-001 ≈ MoE/OOD routing; LR-006 ≈ noisy-label
training). Claude disagreed on the two empirical-audit reframes (LR-003/LR-004): once narrowed to
budget-matched / non-inferiority tests they directly falsify the paper's topology-first premise, which is a
real (if not mechanism-novel) contribution. Two agreement-rejects fill the rejected drawer.

## Stage 3 — idea-card (Gate-3 human resolution)
Human rescued VA-002 + VA-003 (`revise`) → IC-001 (结构 vs 内容预算匹配审计),
IC-002 (固定拓扑证伪基线). Each card's `method_trace` re-points to its VA with full LP→LR→VA lineage
(machine-checked field equality). IC-001 / IC-002 cross-reference each other (the baseline is a cell of the ablation).

## Honest limits
Heuristic audit scores; coverage ledger is an inspection signal; both judges are LLMs (external ≠ ground truth).
Validator checks contract + trace, not novelty.
