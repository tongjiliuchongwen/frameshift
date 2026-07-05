---
name: reframe-workshop
description: "Run the full Codex-ready, human-in-the-loop Research Reframer workflow (v0.7 diagnostic three-gate) for rough research ideas, paper gaps, proposals, project notes, or early concepts. Use when Codex should orchestrate diagnosis -> system-map -> leverage-scan -> Gate 1 -> lateral-generate -> Gate 2 -> vertical-audit -> Gate 3 -> idea-card into traceable artifacts with browser-button gate selections, auditable system relations, pseudo-innovation classifications, and final idea change logs."
---

# Reframe Workshop (Codex v0.7)

Use this skill to guide an early-stage research input through the full Research Reframer workflow.
The goal is not to auto-pick an idea; it is to expose where the frame can change and let the human
control three selection gates through the browser-button sidecar.

## Global Quality Contract

The final objective is a research idea that has a structural increment over the original idea,
a plausible scientific mechanism, a minimal verification path, and a plain-language explanation of
why the idea is genuinely different rather than a terminology swap.

## Language and Encoding Rules

- Default user-facing language is Simplified Chinese. Keep technical terms such as `agent`, `artifact`,
  `benchmark`, `oracle`, and id fields such as `LP-001` in English only when useful.
- Natural-language fields in generated `.md` files and in gate-facing JSON fields must be Chinese:
  `old_frame`, `new_frame`, `scheme`, `why_interesting`, `bad_use_to_avoid`, audit reasons, idea-card
  explanations, and final report prose.
- Use a two-layer output model:
  - **Reader layer:** default page/report/Gate text. Write for a related-field researcher who is not
    in this exact subfield. Use plain Simplified Chinese, short sentences, and explain what the idea
    means before showing provenance. Do not show schema field names, operator names, raw scores, or
    dense English terminology by default.
  - **Technical layer:** trace, ids, schema fields, operators, judge scores, source quotes, and dense
    paper terminology. Keep this layer in JSON, appendices, or collapsed details.
- In the reader layer, English terms are allowed only for paper titles, model/dataset names, stable
  ids, and necessary technical nouns. The first necessary technical noun must use
  `中文解释（English term）`; later mentions should prefer the Chinese explanation.
- Before finalizing Gate cards, idea cards, or reports, run a short readability cleanup: remove
  unnecessary English, split long sentences, replace jargon stacks with "action + result + condition",
  and keep technical trace in the detail layer.
- Windows UTF-8 rule: never pipe non-ASCII content through PowerShell to an external process, for example
  `@'...'@ | python -` or `@'...'@ | node`. Windows PowerShell can encode that pipe as ASCII/OEM and
  replace Chinese with literal `?`.
- Do not use default `Set-Content` or `Out-File` for Chinese artifacts. Use `apply_patch`, or a file
  writer with explicit `encoding="utf-8"` whose source was not passed through a PowerShell text pipe.
- After writing artifacts, run the validator and inspect for runs of question marks, Unicode replacement
  characters, or common mojibake byte-decoding artifacts. These are hard failures, not cosmetic display issues.

```text
input
  -> diagnosis         00_diagnosis.json
  -> system-map        01_system_map.json
  -> leverage-scan     02_leverage_points.json
  -- Gate 1: sidecar button selects leverage points
  -> lateral-generate  03_lateral_reframes.json
  -- Gate 2: sidecar button selects lateral schemes
  -> vertical-audit    04_vertical_audits.json
  -- Gate 3: sidecar button selects audited schemes
  -> idea-card         06_idea_cards.json
  -> reframe_report.md + decision_log.md + 05_human_selection.md/json + 05_gate_cards.json
```

## Workflow

1. **Ingest.** Read the input and preserve its source. Ask at most one clarifying question only when
   domain, audience, or constraints are missing and materially affect selection.
2. **Diagnosis.** Write `00_diagnosis.json`: one-sentence original idea summary, dissatisfaction
   types, primary bottleneck, core value to preserve, most promising change target, and downstream
   focus. This is not the answer; it names what later stages must improve.
3. **System map.** Run `system-map` -> `01_system_map.json` (+ `.md` when useful). Key relation
   objects must include `relation_type`, `evidence_source`, `mechanism`, and `if_wrong_impact`.
4. **Leverage scan.** Run `leverage-scan` -> `02_leverage_points.json` (+ `.md`). Use 8-15 leverage
   points in full runs, or 3-5 for compact demos.
5. **Gate 1.** Stop after writing `02_leverage_points.json`. Gate 1 selection must come from the
   Codex App Server sidecar as a `<codex_gate_selection>` event. The sidecar records
   `05_human_selection.json` and `05_gate_cards.json`; append the readable decision log and continue.
6. **Lateral generate.** Run `lateral-generate` on the selected LPs -> `03_lateral_reframes.json`.
   Operators are internal; do not score or audit schemes here.
7. **Gate 2.** Stop after writing `03_lateral_reframes.json`. Gate 2 selection must come from the
   sidecar as a `<codex_gate_selection>` event. Do not ask the user to type ids.
8. **Vertical audit.** Run `vertical-audit` -> `04_vertical_audits.json`. Use an external headless
   `codex exec` pass when available, plus the local/orchestrating judge. Keep historical field names:
   the local verdict is stored in `claude_verdict`. Each audit must also include `pseudo_innovation`,
   `escalation_reason`, and `human_resolution`.
9. **Gate 3.** Stop after writing `04_vertical_audits.json`. Gate 3 selection must come from the
   sidecar as a `<codex_gate_selection>` event. The sidecar records selected audit ids and resolutions.
10. **Idea cards.** Run `idea-card` on the Gate-3 selection -> `06_idea_cards.json`. Each card must
    include `change_log` explaining the source diagnosis, structural change, new mechanism, preserved
    value, removed/weakened content, real increment, and remaining fragility.
11. **Report and validate.** Produce `reframe_report.md`. Run the bundled validator before finalizing
    when file-system access is available.

## Button Gates

Human gate selection is not a chat-input step. Use the local sidecar:

```powershell
cd ..\codex-appserver-gate-test
$env:CODEX_THREAD_ID="<current-codex-thread-id>"
$env:REFRAME_RUN_DIR="<run directory containing outputs>"
node server.mjs
```

The user selects cards at <http://127.0.0.1:8787>. The `使用选中项继续` button writes
`outputs/05_gate_cards.json` and `outputs/05_human_selection.json`, then starts the next Codex turn by
sending a `<codex_gate_selection>` event through `codex app-server`. The button does not type into the
chat composer.

If the sidecar is unavailable, fix or start the sidecar. Do not fall back to asking the user to type
ids, natural-language selections, or `delegate` in the chat composer.

Gate card rules:

- Keep each option compact enough to scan. Do not show full internal fields by default.
- Default display language is Simplified Chinese. Technical English terms may appear only when the
  Chinese line explains what they mean.
- Use these exact reader-layer labels, and ignore any legacy mojibake labels in older docs:
  - Gate 1: `原来的默认想法`, `问题卡在哪里`, `选它后会生成什么`.
  - Gate 2: `原来怎么想 -> 现在怎么想`, `人话方案`, `看点`, `风险`.
  - Gate 3: `保留下来的核心`, `最小实验`, `最大风险`.
- Gate 1 cards show: `旧假设`, `卡在问题哪里`, `选它后会生成`.
- Gate 2 cards show: `旧->新`, `人话方案`, `看点`, `风险`.
- Gate 3 cards show: `保留下来的核心`, `最小实验`, `最大风险`.
- Do not add innovation-type labels or forced four-way grouping. Put degeneration concerns in the
  `风险` line instead.
- Include a recommended set in the sidecar data, but do not proceed until a `<codex_gate_selection>`
  event arrives.
- After each gate, run only the downstream stage for that gate. Do not rerun earlier artifacts unless
  the user explicitly asks.

For every gate, the sidecar saves the actual displayed cards to `05_gate_cards.json`. This file should
preserve the option id, title, 3-4 default rows, detail rows, recommended ids, and selected ids.

## Selection Heuristics

- **Gate 1:** choose 2-4 leverage points from different leverage families, preferably goal/paradigm,
  rule/incentive, and feedback/information when grounded in the input.
- **Gate 2:** choose schemes that are diverse across leverage points and operators. Favor bold,
  structurally distinct reframes; judgment is deliberately deferred until vertical audit.
- **Gate 3:** choose `keep`/`revise` audits and rescue `needs_human` audits only when the optimistic
  narrowing is genuinely testable and discriminable. Never make cards from audits both judges rejected.

## Artifact Layout

```text
outputs/
  00_diagnosis.json
  01_system_map.json (+ .md)
  02_leverage_points.json (+ .md)
  03_lateral_reframes.json (+ .md, .html)
  04_vertical_audits.json (+ .md, .html)
  05_gate_cards.json
  05_human_selection.json
  05_human_selection.md
  06_idea_cards.json (+ .md)
  decision_log.md
  reframe_report.md
```

## Quality Rules

- Keep generation and appraisal separate: `lateral-generate` diverges; `vertical-audit` judges;
  `idea-card` makes survivors testable.
- Every final idea should answer the diagnosis: which original bottleneck it addresses and what
  structural increment it adds.
- System maps are auditable claims, not decorative diagrams. Key relations need evidence and a
  short note on what would break if the relation is wrong.
- The audit is default-reject. If nothing is rejected, reread the rubric and tighten judgment.
- Do not add a hard pseudo-innovation gate before Gate 2; pseudo-innovation classification belongs
  in `vertical-audit` so lateral generation remains judgment-deferred.
- Keep rejected audits with reasons; they are part of the evidence trail.
- Treat all LLM judge outputs as heuristic judgments, not proof of novelty or correctness.
- Do not present the workflow as replacing the researcher.
- Do not copy large passages from books, papers, or private reference PDFs.

## Validation

Resolve paths relative to this `SKILL.md` when using bundled resources:

```bash
python <installed-skills-dir>/reframe-workshop/scripts/validate_outputs.py path/to/outputs
```

The validator enforces required fields, enums, id formats, coverage-ledger arithmetic, dual-judge
consistency, audit-score means, trace equality, and the human-gate audit trail.
