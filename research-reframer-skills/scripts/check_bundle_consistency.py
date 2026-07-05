#!/usr/bin/env python
"""Check that bundled reframe-workshop validation assets match root assets."""
from __future__ import print_function

import filecmp
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSHOP = ROOT / "skills" / "reframe-workshop"


def compare_file(left, right, errors):
    if not left.is_file():
        errors.append("missing: {}".format(left))
        return
    if not right.is_file():
        errors.append("missing: {}".format(right))
        return
    if not filecmp.cmp(str(left), str(right), shallow=False):
        errors.append("drift: {} != {}".format(left, right))


def main():
    errors = []
    compare_file(
        ROOT / "scripts" / "validate_outputs.py",
        WORKSHOP / "scripts" / "validate_outputs.py",
        errors,
    )
    compare_file(
        ROOT / "scripts" / "contract.py",
        WORKSHOP / "scripts" / "contract.py",
        errors,
    )
    for schema in sorted((ROOT / "schemas").glob("*.schema.json")):
        compare_file(schema, WORKSHOP / "references" / schema.name, errors)

    if errors:
        for error in errors:
            print("[FAIL] {}".format(error))
        return 1

    print("[OK] bundled validator and schemas match root assets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
