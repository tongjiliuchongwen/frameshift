#!/usr/bin/env python
"""Research Reframer — canonical data contract (single source of truth), v0.5.

This module is the ONE authoritative definition of the v0.5 ("2.0" schema) data
contract: the unified lateral-operator vocabulary, leverage-type metadata, the
adversarial audit verdict enum, id patterns, artifact filenames, and the trace
chain. The JSON Schemas' enums, the validator's constants, the static renderer's
lists, and the reframe-ui contract are all meant to be generated FROM / checked
AGAINST this module so the vocabulary lives in exactly one place.

Stdlib-only, no third-party deps (matches validate_outputs.py). Run with
`python contract.py --dump` to (re)write contract.json for non-Python consumers
(the reframe-ui front end, schema generation).

Status: live. validate_outputs.py imports this module, the JSON Schemas mirror it,
the static renderer and reframe-ui read its vocabulary, and REQUIRED_FIELDS below
is the canonical required-field contract the validator enforces — checked against
the actual schemas by scripts/check_contract_schema_sync.py so the two cannot drift.
"""
from __future__ import print_function

import argparse
import json
from pathlib import Path


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
# Contract-breaking bump from v0.4.1's "1.0". v0.2/v0.3 artifacts do NOT validate
# under "2.0"; main (tag v0.4.1) remains the last v0.4 release.
SCHEMA_VERSION = "2.0"
PACK_VERSION = "0.5.0"


# ---------------------------------------------------------------------------
# Lateral-thinking operators (UNIFIED)
# ---------------------------------------------------------------------------
# v0.5 resolves the v0.2/v0.3 split by adopting the v0.3 set and DROPPING the
# three v0.2-only operators (function_abstraction, boundary_shift, goal_inversion).
# These operators are an INTERNAL generation mechanism in lateral-generate, not a
# user-facing axis (the human selects leverage points at Gate 1, not method cells).
LATERAL_OPERATORS = [
    "assumption_challenge",
    "reversal",
    "decomposition",
    "analogy",
    "random_stimulus",
    "PO_provocation",
    "entry_point_shift",
    "concept_abstraction",
]

# Operators retired from the active contract in v0.5 (kept here only to document
# the migration; artifacts may NOT use them).
RETIRED_V02_OPERATORS = [
    "function_abstraction",
    "boundary_shift",
    "goal_inversion",
]


# ---------------------------------------------------------------------------
# Leverage types (Meadows-style) — METADATA on each leverage point
# ---------------------------------------------------------------------------
# Carried forward unchanged from v0.4.1's leverage_points contract. In v0.5 this
# is metadata on each LP (it is no longer a grid ROW axis; the grid is demoted to
# an internal LP x operator coverage ledger).
LEVERAGE_TYPES = [
    "parameter",
    "buffer",
    "structure",
    "delay",
    "feedback_loop",
    "information_flow",
    "rule",
    "self_organization",
    "goal",
    "paradigm",
]

# Optional coarse family grouping for the internal coverage ledger (the old v0.3
# 6 grid-row types). NOT a required field and NOT a user-facing axis in v0.5.
LEVERAGE_FAMILIES = [
    "parameter_metric",
    "stock_flow_delay",
    "feedback_information",
    "rule_incentive",
    "self_organization_structure",
    "goal_paradigm",
]

REFRAMING_POTENTIAL = ["high", "medium", "low"]


# ---------------------------------------------------------------------------
# Lateral schemes (Stage: lateral-generate) — JUDGMENT DEFERRED
# ---------------------------------------------------------------------------
# A lateral scheme carries no quality score; it is explicitly not_yet_audited.
LATERAL_FIELDS = [
    "lateral_id",
    "source_leverage_point",
    "operator",
    "old_frame",
    "lateral_move",
    "new_frame",
    "scheme",
    "why_interesting",
    "changed_assumption",
    "bad_use_to_avoid",
    "not_yet_audited",
]


# ---------------------------------------------------------------------------
# Vertical audit (Stage: vertical-audit) — ADVERSARIAL, dual-judge
# ---------------------------------------------------------------------------
VERDICTS = ["reject", "revise", "keep"]          # default posture is "reject"
AUDITORS = ["dual", "codex", "self"]             # dual = Codex + Claude both ran
AUDIT_GATES = [                                  # all three must pass to survive
    "minimal_experiment_exists",
    "discriminable_from_prior",
    "so_what_passes",
]
AUDIT_SCORE_KEYS = [
    "coherence",
    "testability",
    "novelty_potential",
    "research_value",
    "risk",
]  # overall is the mean of these five, checked to TOLERANCE


# ---------------------------------------------------------------------------
# Provenance / grounding (carried forward)
# ---------------------------------------------------------------------------
INTRODUCTION_TYPES = [
    "input_term",
    "system_map_term",
    "leverage_point_term",
    "lateral_stimulus",
    "analogy_source",
    "agent_inference",
]


# ---------------------------------------------------------------------------
# Id patterns — WIDENED to 3 digits (v0.4.1's 2-digit LP-##/IC-## capped at 99)
# ---------------------------------------------------------------------------
ID_PATTERNS = {
    "leverage_point": r"^LP-[0-9]{3}$",
    "lateral_scheme": r"^LR-[0-9]{3}$",
    "vertical_audit": r"^VA-[0-9]{3}$",
    "idea_card": r"^IC-[0-9]{3}$",
}


# ---------------------------------------------------------------------------
# Artifacts + trace chain
# ---------------------------------------------------------------------------
# input_evidence -> system_node -> LP -> LR -> VA -> IC
ARTIFACTS = {
    "system_map": "01_system_map.json",
    "leverage_points": "02_leverage_points.json",
    "lateral_reframes": "03_lateral_reframes.json",
    "vertical_audits": "04_vertical_audits.json",
    "idea_cards": "06_idea_cards.json",
}

# Human-selection / audit-trail artifacts that v0.5 will actually VALIDATE for
# existence + consistency (v0.4.1 checked none of these — "gates" were author
# discipline only).
AUDIT_TRAIL = [
    "05_human_selection.md",
    "decision_log.md",
    "reframe_report.md",
]

# Three human gates and what each SELECTS.
GATES = {
    1: {"selects": "leverage_points", "id": "leverage_point", "mode": "systems"},
    2: {"selects": "lateral_schemes", "id": "lateral_scheme", "mode": "lateral"},
    3: {"selects": "audited_schemes", "id": "vertical_audit", "mode": "vertical"},
}

TRACE_CHAIN = ["input_evidence", "system_node", "LP", "LR", "VA", "IC"]

# Numeric tolerance for derived-value checks (e.g. audit_score.overall == mean).
TOLERANCE = 0.01


# ---------------------------------------------------------------------------
# Required fields — the canonical required-field contract the validator enforces
# ---------------------------------------------------------------------------
# One entry per object the validator descends into (top-level artifact + each
# nested object it iterates). These MIRROR the `required` arrays in schemas/*.json;
# scripts/check_contract_schema_sync.py reads the schema files and fails if any
# inline `required` field here is missing, so the two cannot silently drift.
REQUIRED_FIELDS = {
    "system_map": [
        "schema_version", "system_name", "source_summary", "original_problem",
        "actors", "goals", "stocks", "flows", "feedback_loops", "rules",
        "information_flows", "delays", "boundaries", "failure_modes", "uncertainties",
    ],
    "leverage_points": ["schema_version", "source_system", "leverage_points", "selection_guidance"],
    "leverage_point_item": [
        "id", "type", "system_location", "source_trace", "why_it_matters",
        "current_assumption", "reframing_potential", "risk", "human_selectable",
    ],
    "leverage_point_source_trace": ["system_node_ids", "input_evidence"],
    "lateral_reframes": ["schema_version", "source_leverage_points", "lateral_schemes", "coverage_ledger"],
    "lateral_scheme_item": LATERAL_FIELDS,
    "coverage_ledger": ["operators", "cells", "occupied_count", "total_cells", "coverage_ratio", "underexplored"],
    "coverage_ledger_cell": ["leverage_point", "operator", "scheme_count", "scheme_ids"],
    "coverage_ledger_underexplored": ["leverage_point", "operator"],
    "vertical_audits": ["schema_version", "audited_lateral_ids", "audits"],
    "vertical_audit_item": [
        "audit_id", "source_lateral_id", "auditor", "codex_verdict", "claude_verdict",
        "agreement", "needs_human", "verdict", "minimal_experiment_exists",
        "discriminable_from_prior", "so_what_passes", "refined_scheme", "core_claim",
        "causal_mechanism", "critical_assumptions", "novelty_risk", "minimal_experiment",
        "failure_modes", "audit_score", "reasons",
    ],
    "vertical_audit_merge": ["with", "reason"],
    "audit_score": ["coherence", "testability", "novelty_potential", "research_value", "risk", "overall"],
    "idea_cards": ["schema_version", "idea_cards"],
    "idea_card_item": [
        "id", "title", "one_sentence", "original_problem", "reframed_problem",
        "changed_assumption", "system_trace", "method_trace", "why_not_obvious",
        "minimal_experiment", "evaluation_metrics", "expected_observation",
        "failure_case", "related_work_queries", "next_steps", "status",
    ],
    "idea_card_system_trace": ["input_evidence", "system_node", "leverage_point", "lateral_operation", "reframe"],
    "idea_card_method_trace": [
        "source_vertical_audit", "source_lateral_scheme", "source_leverage_point",
        "operator", "source_system_nodes", "old_frame", "new_frame",
        "changed_assumption", "audit_verdict", "audit_score",
    ],
}


def as_dict():
    """Return the full contract as a JSON-serializable dict (for contract.json)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "pack_version": PACK_VERSION,
        "lateral_operators": LATERAL_OPERATORS,
        "retired_v02_operators": RETIRED_V02_OPERATORS,
        "leverage_types": LEVERAGE_TYPES,
        "leverage_families": LEVERAGE_FAMILIES,
        "reframing_potential": REFRAMING_POTENTIAL,
        "lateral_fields": LATERAL_FIELDS,
        "verdicts": VERDICTS,
        "auditors": AUDITORS,
        "audit_gates": AUDIT_GATES,
        "audit_score_keys": AUDIT_SCORE_KEYS,
        "required_fields": REQUIRED_FIELDS,
        "introduction_types": INTRODUCTION_TYPES,
        "id_patterns": ID_PATTERNS,
        "artifacts": ARTIFACTS,
        "audit_trail": AUDIT_TRAIL,
        "gates": {str(k): v for k, v in GATES.items()},
        "trace_chain": TRACE_CHAIN,
        "tolerance": TOLERANCE,
    }


def _dump_json(path):
    path = Path(path)
    path.write_text(json.dumps(as_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Research Reframer v0.5 canonical contract")
    parser.add_argument(
        "--dump",
        nargs="?",
        const="contract.json",
        metavar="PATH",
        help="write the contract as JSON (default: ./contract.json) for non-Python consumers",
    )
    args = parser.parse_args(argv)

    if args.dump:
        out = _dump_json(args.dump)
        print("[OK] wrote %s" % out)
    else:
        c = as_dict()
        print("Research Reframer contract  schema_version=%s  pack=%s" % (SCHEMA_VERSION, PACK_VERSION))
        print("  lateral_operators (%d): %s" % (len(LATERAL_OPERATORS), ", ".join(LATERAL_OPERATORS)))
        print("  verdicts: %s   auditors: %s" % (", ".join(VERDICTS), ", ".join(AUDITORS)))
        print("  trace_chain: %s" % " -> ".join(TRACE_CHAIN))
        print("  artifacts: %s" % ", ".join(ARTIFACTS.values()))
        print("(run with --dump to emit contract.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
