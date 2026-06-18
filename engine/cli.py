"""frameshift engine CLI.

    python -m engine.cli serve [--port 8420]
        Start the local server (API + dashboard) from the repo root.

    python -m engine.cli assemble --run <id>
        Deterministically rebuild runs/<id>/map.json and run.json from the
        cards in runs/<id>/cards/.  No randomness, no LLM: card value_profile
        -> map coordinates by the fixed mapping in engine.mapping.  This is the
        machine half of the loop — the agent writes cards, this lays them out.

All runs live under ./runs/<run_id>/.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import mapping

RUNS = Path("runs")


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _save_json(path, obj):
    Path(path).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_cards(run_dir):
    cdir = run_dir / "cards"
    if not cdir.is_dir():
        return []
    return [_load_json(p) for p in sorted(cdir.glob("*.json"))]


def cmd_assemble(args):
    run_dir = RUNS / args.run
    if not run_dir.is_dir():
        sys.exit(f"run '{args.run}' not found under {RUNS}/")

    cards = _load_cards(run_dir)
    if not cards:
        sys.exit(f"no cards in {run_dir / 'cards'}/")

    graph = {}
    gp = run_dir / "graph.json"
    if gp.is_file():
        graph = _load_json(gp)

    # build_map writes map_position back onto each survivor card.
    map_obj = mapping.build_map(cards)
    run_obj = mapping.build_run(args.run, graph, cards)
    # preserve an existing created timestamp if run.json already had one
    old_run = run_dir / "run.json"
    if old_run.is_file():
        prev = _load_json(old_run)
        if prev.get("created") and not run_obj.get("created"):
            run_obj["created"] = prev["created"]

    # persist recomputed map_position back into each card (deterministic)
    for c in cards:
        dest = run_dir / "cards" / f"{c['id']}.json"
        if dest.is_file():
            _save_json(dest, c)

    _save_json(run_dir / "map.json", map_obj)
    _save_json(run_dir / "run.json", run_obj)

    print(f"assembled runs/{args.run}: "
          f"{run_obj['n_survivors']} survivors, "
          f"{run_obj['n_rejected']} rejected, "
          f"{run_obj['n_dofs']} clamped DOFs")


def cmd_serve(args):
    from . import serve as srv
    srv.serve(port=args.port)


def main(argv=None):
    p = argparse.ArgumentParser(prog="engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("serve", help="start the local API + dashboard server")
    sp.add_argument("--port", type=int, default=8420)
    sp.set_defaults(func=cmd_serve)

    sp = sub.add_parser(
        "assemble", help="rebuild map.json/run.json from cards/ (deterministic)")
    sp.add_argument("--run", required=True)
    sp.set_defaults(func=cmd_assemble)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
