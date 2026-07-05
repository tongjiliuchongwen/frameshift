# Research Reframer Skills for Codex

Codex-first edition of Research Reframer, a skill pack for early-stage research ideation and problem reframing.

Version: 0.7.0-codex. The core v0.7 artifact contract uses `schema_version: 2.1`; this edition adds Stage 0 diagnosis, auditable system relations, pseudo-innovation audit blocks, and final idea change logs.

## Gate Policy

Human gates use the local Codex App Server gate sidecar in `../codex-appserver-gate-test`.

Gate selections are made with browser buttons. The button records the gate artifacts and starts the next Codex turn through `codex app-server`; it does not type into the chat composer.

There is no manual chat-input fallback for gate ids. If the sidecar is not running, start or fix the sidecar instead of asking the user to type ids.

## Pipeline

```text
input (rough idea / paper gap / project note)
  -> diagnosis         00_diagnosis.json
  -> system-map        01_system_map.json
  -> leverage-scan     02_leverage_points.json        (LP-###)
  -- Gate 1: sidecar button selects leverage points
  -> lateral-generate  03_lateral_reframes.json       (LR-###)
  -- Gate 2: sidecar button selects lateral schemes
  -> vertical-audit    04_vertical_audits.json        (VA-###)
  -- Gate 3: sidecar button selects audited schemes
  -> idea-card         06_idea_cards.json             (IC-###)
```

Every card is traceable end to end: diagnosis -> input evidence -> system node -> LP -> LR -> VA -> IC. The validator checks that chain and also checks that Gate selections match downstream artifacts.

## Install

Dry run first:

```powershell
python scripts/install_skills.py --target codex-user --dry-run
```

Install into Codex:

```powershell
python scripts/install_skills.py --target codex-user --force
```

Restart Codex so the new skills load.

Repo-scoped install is also supported:

```powershell
python scripts/install_skills.py --target codex-repo --repo-root . --force
```

## Quickstart

Run the workflow until `02_leverage_points.json` exists in your current run directory, then start the button sidecar from the sibling directory:

```powershell
cd ..\codex-appserver-gate-test
  $env:CODEX_THREAD_ID="<current-codex-thread-id>"
$env:REFRAME_RUN_DIR="<absolute-path-to-current-run-directory>"
node server.mjs
```

Open <http://127.0.0.1:8787> and use the browser buttons:

```text
选择推荐项
使用选中项继续
```

The sidecar writes `05_gate_cards.json` and `05_human_selection.json`, then sends a `<codex_gate_selection>` event to the current Codex thread. The agent must continue from that event and must not ask the user to type ids into the chat box.

## Expected Artifacts

```text
outputs/
  00_diagnosis.json
  01_system_map.json
  02_leverage_points.json
  03_lateral_reframes.json
  04_vertical_audits.json
  05_gate_cards.json
  05_human_selection.json
  05_human_selection.md
  06_idea_cards.json
  decision_log.md
  reframe_report.md
```

Optional readable `.md` companions and static `.html` views may also be generated.

## Skills

- `system-map`: convert rough research text into actors, goals, flows, feedback loops, rules, information flows, boundaries, failure modes, and uncertainties.
- `leverage-scan`: identify high-leverage places (`LP-###`) where the research frame can change.
- `lateral-generate`: generate divergent schemes (`LR-###`) from selected leverage points while deferring judgment.
- `vertical-audit`: adversarially audit selected schemes (`VA-###`) with external and local judge passes when available, plus machine-readable pseudo-innovation classifications.
- `idea-card`: convert selected audits into traceable, testable research cards (`IC-###`) with compact change logs.
- `reframe-workshop`: orchestrate the full three-gate workflow.

## Vertical Audit Provenance

The JSON schema keeps historical field names:

- `codex_verdict`: verdict from a separate `codex exec` run, when available.
- `claude_verdict`: local/orchestrating judge verdict in this Codex edition.
- `auditor`: `dual` when both passes ran, `codex` when only the external pass ran, or `self` when only the local pass ran.

Both passes are LLM judgments, not ground truth. Use them to expose disagreements and weak ideas, not to prove novelty.

## Validate

```powershell
python scripts/validate_outputs.py examples/physmaster-three-gate/outputs
```

Before publishing a Codex pack:

```powershell
python scripts/check_bundle_consistency.py
python scripts/package_zip.py
python scripts/smoke_test_zip.py dist/research-reframer-skills-codex-pack.zip
```

## Distribution

`scripts/package_zip.py` excludes generated smoke/live/private test-run folders and build artifacts so the ZIP contains only portable Codex skill-pack content.

## Project Shape

```text
research-reframer-skills-codex/
  skills/        # Codex-ready skills
  schemas/       # JSON Schemas mirroring scripts/contract.py
  scripts/       # install, validate, package, smoke, bundle consistency
  examples/      # validated example outputs
  docs/          # historical design notes from the upstream workflow
```

`scripts/contract.py` remains the single source of truth for vocabulary and validation behavior.
