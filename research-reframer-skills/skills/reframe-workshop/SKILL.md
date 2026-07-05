---
name: reframe-workshop
description: "Run the full human-in-the-loop Research Reframer workflow (v0.5 three-gate) for rough research ideas, paper gaps, proposals, project notes, or early concepts. Use when an agent should orchestrate system-map → leverage-scan → (Gate 1) → lateral-generate → (Gate 2) → vertical-audit → (Gate 3) → idea-card into a traceable reframing workflow with three human selection gates, an adversarial dual-judge audit, and auditable artifacts."
---

# Reframe Workshop (v0.5 three-gate)

Use this skill to guide an early-stage research input through the full Research Reframer workflow.
The goal is not to auto-pick an idea; it is to make problem reframing structured, searchable,
inspectable, and preference-driven, split across the three cognitive modes:

```
input
  → system-map        01_system_map.json
  → leverage-scan     02_leverage_points.json
  ── Gate 1: human selects LEVERAGE POINTS (systems thinking: where to cut) ──
  → lateral-generate  03_lateral_reframes.json   (diverge; operators internal; judgment deferred)
  ── Gate 2: human selects LATERAL SCHEMES (lateral thinking: what's interesting) ──
  → vertical-audit    04_vertical_audits.json    (converge; adversarial dual-judge, default-reject)
  ── Gate 3: human selects AUDITED SCHEMES (vertical thinking: what survives) ──
  → idea-card         06_idea_cards.json
  → reframe_report.md + decision_log.md + 05_human_selection.md
```

## Workflow

1. **Ingest.** Read the input; preserve / summarize its source. Ask at most one clarifying question
   only if domain, audience, or constraints are missing and materially affect selection.
2. **System map.** Run `system-map` → `01_system_map.json` (+ `.md`).
3. **Leverage scan.** Run `leverage-scan` → `02_leverage_points.json` (+ `.md`). 8–15 leverage points
   in full runs, 3–5 in compact demos, each with `id` (`LP-###`), `type`, `system_location`,
   `current_assumption`, `why_it_matters`, `risk`, `human_selectable`.
4. **Gate 1 — select leverage points.** Present the interactive gate (clickable panel — see **Gates — how to present them** below); the human picks `LP-###` ids (where in the system to
   cut), or delegates. Record in `05_human_selection.md` + `decision_log.md`.
5. **Lateral generate.** Run `lateral-generate` on the selected LPs → `03_lateral_reframes.json`
   (+ `.md`). Operators are internal; **defer judgment** (no scores); keep the `coverage_ledger` and
   the anti-collapse discipline. Every scheme is `not_yet_audited: true`.
6. **Gate 2 — select lateral schemes.** Present the interactive gate (clickable panel — see **Gates — how to present them** below); the human picks the *interesting* `LR-###` ids to
   audit (this protects unproven-but-interesting ideas; it is NOT "make a card"). Append to the trail.
7. **Vertical audit.** Run `vertical-audit` on the selected schemes → `04_vertical_audits.json`
   (+ `.md`). **Adversarial, default-reject, dual-judge** (Codex external + Claude). Expect real
   rejections; preserve rejected `VA` records with reasons; flag `needs_human` on judge disagreement.
8. **Gate 3 — select audited schemes.** Present the interactive gate (clickable panel — see **Gates — how to present them** below); the human picks which surviving / escalated `VA-###`
   become cards (resolving `needs_human` audits to keep/revise). Append to the trail.
9. **Idea cards.** Run `idea-card` on the Gate-3 selection → `06_idea_cards.json` (+ `.md`). Each card
   carries a `method_trace` with the full `LP → LR → VA` lineage.
10. **Report + validate.** Produce `reframe_report.md`. Run the bundled validator (below) before
    finalizing when file-system access is available.

## Gates — how to present them (DEFAULT: inline clickable panel, zero-setup)

At every gate give the human **clickable options that flow straight into the conversation** — never a
static list they must read and type ids back from. This is the default; it ships inside the pack and
needs **no server, no launch flag, no per-use setup**:

1. **Render an inline panel** with the `mcp__visualize__show_widget` tool, built from the gate's
   artifact, using the template in `references/gate_widget.md`. Each candidate is a toggle row;
   pre-select a diverse recommended set; include a **"用选中的继续"** button (sends the chosen ids via
   the global `sendPrompt`) and a **"让 Claude 替我选"** button (sends a delegate directive). The click
   arrives as a normal message.
2. **If `show_widget` is unavailable**, fall back to **`AskUserQuestion`** (a core tool, also zero-setup):
   the recommended candidates as multiSelect options plus a "let Claude decide" option. Still clickable —
   never make the human type ids into a box.
3. On the selection, record it to `05_human_selection.md` + `decision_log.md` and run **only** that
   gate's downstream stage (Gate 1 → lateral-generate; Gate 2 → vertical-audit; Gate 3 → idea-card +
   validate). Never re-run earlier stages.

Net effect: install the pack once, then every gate is one click — no setup per use.

## reframe-ui channel (optional, advanced — NOT required)

`reframe-ui/` is a separate, optional browser channel — **not** the default and **not** needed. Custom
Claude Code channels must be launched with `--dangerously-load-development-channels` *every* time plus a
local server; that per-use setup is exactly what the default panel above avoids. Use it only if you
specifically want the standalone browser UI. When active, a click arrives as
`<channel source="reframe-ui" gate="1|2|3" …>`; treat it as the gate selection, do the downstream work,
then call the `reply` tool so the UI advances.

## Artifact layout

```text
outputs/
  01_system_map.json (+ .md)
  02_leverage_points.json (+ .md)
  03_lateral_reframes.json (+ .md, .html)
  04_vertical_audits.json (+ .md, .html)
  05_human_selection.md
  06_idea_cards.json (+ .md)
  decision_log.md
  reframe_report.md
```

## Selection heuristics (when the human delegates)

- **Gate 1:** pick 2–4 leverage points that hit *different* leverage families (e.g. a goal/paradigm
  one, a rule/incentive one, a feedback/information or self-organization one) and don't overlap.
- **Gate 2:** pick schemes that are diverse across leverage points and operators, favouring the bold
  and the structurally distinct over safe paraphrases — judgment is deferred here, so keep the odd ones.
- **Gate 3:** keep audited schemes that survived (`keep`/`revise`) and rescue `needs_human` ones only
  when the optimistic judge's narrowing is genuinely discriminable. Don't keep an audit both judges
  rejected. Don't pick only the highest score if a lower one reveals a blind spot.

## Quality rules

- Keep generation and appraisal **separate**: lateral-generate diverges (no scoring); vertical-audit
  judges adversarially; idea-card makes survivors testable.
- The audit is **default-reject**. If nothing is rejected you are being too generous. Preserve
  rejected audits with reasons — the "rejected drawer" is part of the value.
- Codex and Claude are both LLMs; an external judge is more defensible than self-judgment but is
  **not ground truth**. Record `auditor` honestly (`dual` / `codex` / `self`).
- Coverage ratio and audit scores are heuristic **inspection signals**, not proofs of novelty or
  correctness. The validator checks the contract and the trace, not research value.
- Do not present the workflow as replacing the researcher; taste and context drive interestingness.
- Do not copy large passages from books, papers, or private reference PDFs.

## Validation

This skill bundles the contract validator (`scripts/validate_outputs.py`), its single-source-of-truth
constants (`scripts/contract.py`), and the JSON schema references (`references/`). Resolve paths
relative to this `SKILL.md`. When the full repository is available, the root-level validator is
equivalent.

```bash
python <installed-skills-dir>/reframe-workshop/scripts/validate_outputs.py path/to/outputs
```

It enforces required fields, enums, `LP-###/LR-###/VA-###/IC-###` id formats, the coverage-ledger
arithmetic, dual-judge consistency, audit-score means, the `LP → LR → VA → IC` trace equality, and
the existence of the human-gate audit trail (`05_human_selection.md`, `decision_log.md`). Fix every
`[ERROR]` before reporting completion; inspect `[WARN]`s (diversity / groundedness risks) before
sharing a demo even when validation exits 0.
