#!/usr/bin/env python
"""Check that contract.REQUIRED_FIELDS covers every `required` field the JSON
Schemas declare inline — so the validator can actually enforce them.

Stdlib-only. For each schema we collect every `required` array reachable WITHOUT
descending into `$defs` (those define reusable node sub-objects that the system-map
validator checks structurally, not via the flat required walk), then assert the
union of the matching contract.REQUIRED_FIELDS entries covers them.

This makes schema -> validator drift a hard failure: add a `required` field to a
schema and forget to teach the validator about it, and this check goes [FAIL].
The reverse (contract lists a field the schema does not require) is allowed — the
validator may legitimately enforce more than the schema's minimum.
"""
from __future__ import print_function

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"

# Which REQUIRED_FIELDS entries together cover one schema's inline `required` set.
SCHEMA_KEYS = {
    "system_map.schema.json": ["system_map"],
    "leverage_points.schema.json": [
        "leverage_points", "leverage_point_item", "leverage_point_source_trace",
    ],
    "lateral_reframes.schema.json": [
        "lateral_reframes", "lateral_scheme_item", "coverage_ledger",
        "coverage_ledger_cell", "coverage_ledger_underexplored",
    ],
    "vertical_audits.schema.json": [
        "vertical_audits", "vertical_audit_item", "vertical_audit_merge", "audit_score",
    ],
    "idea_cards.schema.json": [
        "idea_cards", "idea_card_item", "idea_card_system_trace",
        "idea_card_method_trace", "audit_score",
    ],
}


def collect_inline_required(node):
    """All field names under any `required` array, skipping the `$defs` subtree."""
    found = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$defs":
                continue
            if k == "required" and isinstance(v, list):
                found |= {x for x in v if isinstance(x, str)}
            else:
                found |= collect_inline_required(v)
    elif isinstance(node, list):
        for item in node:
            found |= collect_inline_required(item)
    return found


def main():
    errors = []
    for fname, keys in SCHEMA_KEYS.items():
        path = SCHEMAS / fname
        if not path.is_file():
            errors.append("missing schema: {}".format(path))
            continue
        schema = json.loads(path.read_text(encoding="utf-8"))
        required = collect_inline_required(schema)
        covered = set()
        for key in keys:
            covered |= set(C.REQUIRED_FIELDS.get(key, []))
        missing = sorted(required - covered)
        if missing:
            errors.append(
                "{}: schema requires fields the validator contract does not cover {}: {}".format(
                    fname, keys, ", ".join(missing)
                )
            )

    # Also flag REQUIRED_FIELDS entries that no schema maps to (dead contract entries).
    mapped = set()
    for keys in SCHEMA_KEYS.values():
        mapped |= set(keys)
    orphan = sorted(set(C.REQUIRED_FIELDS) - mapped)
    if orphan:
        errors.append("contract.REQUIRED_FIELDS has entries mapped to no schema: {}".format(", ".join(orphan)))

    if errors:
        for error in errors:
            print("[FAIL] {}".format(error))
        return 1

    print("[OK] contract.REQUIRED_FIELDS covers every inline schema `required` field")
    return 0


if __name__ == "__main__":
    sys.exit(main())
