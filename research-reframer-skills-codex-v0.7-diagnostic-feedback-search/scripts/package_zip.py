#!/usr/bin/env python
"""Package the Codex Research Reframer skill pack with portable ZIP paths."""
from __future__ import print_function

import argparse
import zipfile
from pathlib import Path


DEFAULT_OUT = Path("dist") / "research-reframer-skills-codex-pack.zip"
EXCLUDED_DIRS = set([
    ".git",
    ".pytest_cache",
    "__pycache__",
    "dist",
    "node_modules",
    "reframe-ui",
    "test-runs",
])
EXCLUDED_SUFFIXES = set([
    ".pyc",
    ".pyo",
])

def should_include(path, root):
    rel_parts = path.relative_to(root).parts
    if any(part in EXCLUDED_DIRS for part in rel_parts):
        return False
    if any(part.startswith("_tmp") for part in rel_parts):
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    if path.name in [".DS_Store", "Thumbs.db"]:
        return False
    return path.is_file()


def package_zip(root, out_path):
    root = Path(root).resolve()
    out_path = Path(out_path)
    if not out_path.is_absolute():
        out_path = root / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    files = [
        path
        for path in sorted(root.rglob("*"))
        if should_include(path, root)
    ]
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            arcname = path.relative_to(root).as_posix()
            zf.write(path, arcname)
    return out_path, len(files)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create a portable Codex Research Reframer skill pack ZIP.")
    parser.add_argument("--root", default=".", help="Project root to package. Defaults to current directory.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output ZIP path.")
    args = parser.parse_args(argv)

    out_path, count = package_zip(args.root, args.out)
    print("[OK] wrote {} ({} files)".format(out_path, count))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
