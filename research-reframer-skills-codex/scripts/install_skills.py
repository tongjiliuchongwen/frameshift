#!/usr/bin/env python
"""Install Codex Research Reframer skills into Codex or optional cross-engine folders."""
from __future__ import print_function

import argparse
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


TARGET_ALIASES = {
    "claude": ["claude-user"],
    "codex": ["codex-user"],
    "both": ["claude-user", "codex-user"],
    "both-user": ["claude-user", "codex-user"],
    "both-repo": ["claude-repo", "codex-repo"],
}


def default_target(kind, repo_root=None):
    home = Path.home()
    repo_root = Path(repo_root or Path.cwd()).resolve()
    if kind == "claude-user":
        return home / ".claude" / "skills"
    if kind == "codex-user":
        return home / ".agents" / "skills"
    if kind == "legacy-codex":
        return home / ".codex" / "skills"
    if kind == "claude-repo":
        return repo_root / ".claude" / "skills"
    if kind == "codex-repo":
        return repo_root / ".agents" / "skills"
    raise ValueError(kind)


def read_skill_name(path):
    skill_md = path / "SKILL.md"
    if not skill_md.is_file():
        return None
    text = skill_md.read_text(encoding="utf-8")
    match = re.search(r"(?m)^name:\s*['\"]?([^'\"\r\n]+)['\"]?\s*$", text)
    if not match:
        return None
    return match.group(1).strip()


def copy_skill(src, dst, force=False, dry_run=False):
    target = dst / src.name
    if dry_run:
        print("[DRY] copy {} -> {}".format(src, target))
        return
    if target.exists():
        if not force:
            raise SystemExit(
                "target already exists: {}. Re-run with --force to overwrite.".format(target)
            )
        if target.is_symlink():
            raise SystemExit("refusing to overwrite symlinked target: {}".format(target))
        src_name = read_skill_name(src)
        target_name = read_skill_name(target)
        if src_name != target_name:
            raise SystemExit(
                "refusing to overwrite {}: installed skill name {!r} does not match source {!r}".format(
                    target, target_name, src_name
                )
            )
        shutil.rmtree(str(target))
    shutil.copytree(
        str(src),
        str(target),
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    print("[OK] installed {}".format(target))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install Codex Research Reframer skills.")
    parser.add_argument(
        "--target",
        choices=[
            "claude",
            "codex",
            "both",
            "claude-user",
            "codex-user",
            "both-user",
            "claude-repo",
            "codex-repo",
            "both-repo",
            "legacy-codex",
        ],
        default="codex",
        help=(
            "Install target. The default codex/codex-user uses the official ~/.agents/skills "
            "location. Claude targets remain only for cross-engine testing."
        ),
    )
    parser.add_argument(
        "--path",
        help="Deprecated alias for --target-dir. Overrides --target and installs into one directory.",
    )
    parser.add_argument(
        "--target-dir",
        help="Override target skill directory. Overrides --target and installs into one directory.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root for *-repo targets. Required for repo-scoped installs.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing installed skills.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not SKILLS.is_dir():
        raise SystemExit("skills directory not found: {}".format(SKILLS))

    targets = []
    override_dir = args.target_dir or args.path
    if args.target_dir and args.path:
        raise SystemExit("use only one of --target-dir or deprecated --path")
    if override_dir:
        targets.append(Path(override_dir).expanduser())
    else:
        target_names = TARGET_ALIASES.get(args.target, [args.target])
        if any(name.endswith("-repo") for name in target_names) and args.repo_root is None:
            raise SystemExit("repo-scoped targets require an explicit --repo-root")
        for name in target_names:
            targets.append(default_target(name, repo_root=args.repo_root))

    for target in targets:
        if args.dry_run:
            print("[DRY] ensure {}".format(target))
        else:
            target.mkdir(parents=True, exist_ok=True)
        for src in sorted(SKILLS.iterdir()):
            if src.is_dir() and (src / "SKILL.md").is_file():
                copy_skill(src, target, force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
