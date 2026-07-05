# Reframe report — PHYSMASTER (v0.7 antigravity-run)

**Input:** PHYSMASTER 自主 AI 物理学家 (paper-gap). **Contract:** v0.7 / schema_version 2.1.

## What the three gates produced
0. **Diagnosis:** named the primary bottleneck: discovery was framed as solving/validating a given problem, while novelty/value judgment could collapse into ordinary hypothesis generation plus retrieval filtering.
1. **Gate 1 (systems):** picked 4 leverage points — who judges value (LP-002), information signal (LP-003), feedback loop bias (LP-004), and human role (LP-006).
2. **Gate 2 (lateral):** 7 divergent schemes generated (judgment deferred); 2 selected as "interesting" for audit.
3. **Gate 3 (vertical):** adversarial judge (Claude). 2 escalated → 1 final idea card selected by human.

## Idea cards
- **IC-001 — 决策边界纠偏的MCTS自适应探索** (from LP-004 · reversal · VA-002, revise): reward MCTS exploration on boundaries of historically rejected space to bypass LLM critic bias.

## Why this beats the v0.4 two-gate flow here
- Gate 1 asks "where in the system" (a leverage point), not an abstract `type × operator` cell.
- Stage 0 gives the run a diagnostic target before the system map starts.
- System-map relations now carry relation type, evidence source, mechanism, and wrong-edge impact.
- Lateral generation stayed generative (no premature scoring); the audit is a *separate*, adversarial, default-reject stage. The audit now also classifies pseudo-innovation patterns as machine-readable `clear` / `repairable` / `fatal` blocks.
- Idea cards descend from *audited* schemes, with a machine-checked diagnosis→LP→LR→VA→IC lineage and a `change_log` explaining how each card differs from the original frame.

## Honest caveats
Heuristic scores; coverage ratio is an inspection signal, not a quality proof; the validator checks the contract and the trace, not novelty or correctness.
