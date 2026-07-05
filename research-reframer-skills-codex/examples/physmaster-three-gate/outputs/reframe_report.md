# Reframe report — PHYSMASTER (v0.7 diagnostic three-gate demo)

**Input:** PHYSMASTER 自主 AI 物理学家 (paper-gap). **Contract:** v0.7 / schema_version 2.1.

## What the three gates produced
0. **Diagnosis:** named the primary bottleneck: discovery was framed as solving/validating a given
   problem, while novelty/value judgment could collapse into ordinary hypothesis generation plus
   retrieval filtering.
1. **Gate 1 (systems):** picked 3 leverage points — what counts as discovery (LP-001), who judges
   value (LP-002), failed paths as assets (LP-005).
2. **Gate 2 (lateral):** 7 divergent schemes generated (judgment deferred); 4 selected as "interesting".
3. **Gate 3 (vertical):** dual adversarial judges (Codex + Claude). 2 agreement-rejects, 2 escalated
   and human-rescued → 2 idea cards.

## Idea cards
- **IC-001 — 缺席证明锚定的问题发现** (from LP-001 · reversal · VA-001, revise): falsifiable
  "why-not-asked-before" proofs as a generative constraint on auto-generated research questions.
- **IC-002 — 条件感知的失败重激活记忆** (from LP-005 · reversal · VA-004, revise): reason+condition
  labeled failure memory that reactivates only when context change makes a failure newly valid.

## Why this beats the v0.4 two-gate flow here
- Gate 1 asks "where in the system" (a leverage point), not an abstract `type × operator` cell.
- Stage 0 gives the run a diagnostic target before the system map starts.
- System-map relations now carry relation type, evidence source, mechanism, and wrong-edge impact.
- Lateral generation stayed generative (no premature scoring); the audit is a *separate*, adversarial,
  default-reject stage with an **external** judge. The audit now also classifies pseudo-innovation
  patterns as machine-readable `clear` / `repairable` / `fatal` blocks.
- Idea cards descend from *audited* schemes, with a machine-checked diagnosis→LP→LR→VA→IC lineage and
  a `change_log` explaining how each card differs from the original frame.

## Honest caveats
Heuristic scores; coverage ratio is an inspection signal, not a quality proof; both judges are LLMs;
the validator checks the contract and the trace, not novelty or correctness.
