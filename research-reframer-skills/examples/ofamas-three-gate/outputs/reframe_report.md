# Reframe report — OFA-MAS (v0.5 three-gate demo)

**Input:** OFA-MAS 一对多 MAS 拓扑设计 (arXiv:2601.12996v1) paper-gap. **Contract:** v0.5 / schema_version 2.0.

## What the three gates produced
1. **Gate 1 (systems):** picked 3 leverage points — 一对多范式反转 (LP-001), 拓扑 vs 内容 (LP-002),
   合成数据质量 (LP-004).
2. **Gate 2 (lateral):** 7 divergent schemes (judgment deferred); 4 selected as "interesting".
3. **Gate 3 (vertical):** dual adversarial judges (Codex + Claude). 2 agreement-rejects, 2 escalated and
   human-rescued → 2 idea cards.

## Idea cards
- **IC-001 — 结构 vs 内容:拓扑贡献的预算匹配审计** (from LP-002 · decomposition · VA-002, revise): a
  budget-matched 2×2 factorial ablation that tests whether connection topology contributes beyond node
  content — directly auditing the paper's topology-first premise.
- **IC-002 — 固定拓扑证伪基线** (from LP-002 · PO_provocation · VA-003, revise): a strict non-inferiority
  baseline (fixed topology + optimized content vs learned topology under matched budget/token).

The two cards cross-reference: IC-002's fixed-topology baseline is an extreme cell of IC-001's ablation.

## Why the audit bit
Codex (the external judge) rejected all 4 Gate-2 schemes as "renamed known methods". Two were genuinely
incremental (uncertainty routing ≈ MoE/OOD; noisy synthetic labels ≈ noisy-label training) and Claude
agreed → real rejected drawer. Two were sharp empirical falsifications of the paper's core claim once
narrowed; Claude disagreed → escalated → human kept them. Survivors = empirical audits, not slogans.

## Honest caveats
Heuristic scores; coverage is an inspection signal; both judges are LLMs; the validator checks the contract
and the trace, not novelty or correctness.
