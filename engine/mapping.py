"""Deterministic value-map geometry — the single source of truth for coordinates.

The dashboard plots survivor cards on a 2-D value map. Both the live server and
the `assemble` CLI compute card -> (x, y) the *same* way, with no randomness, so
a map rebuilt from cards/ is byte-identical to one an agent wrote by hand.

Axes (per the data contract):
  x = value_profile.actionable_commercial   (how close to a buyer/decision)
  y = value_profile.conceptual_depth        (how far it moves the idea itself)

Both inputs are categorical {low, mid, high} and snap to fixed positions on
0..1.  The origin (the paper's own incremental-improvement question) sits in the
bottom-left corner at (0.15, 0.15) — every survivor is read as displacement away
from "just turn the existing knobs".

  size  <- value_profile.deliverability   (how shippable: bigger = sooner)
  badge <- prior_art.novelty_level        (how new: the watermark a human scans)
"""
from __future__ import annotations

# categorical level -> position on a 0..1 axis. low hugs the origin corner.
LEVEL_POS = {"low": 0.15, "mid": 0.5, "high": 0.85}

# the paper's original question always lands in the incremental-improvement corner.
ORIGIN = {"x": 0.15, "y": 0.15, "label": "原问题（增量改进）"}

# deliverability -> a relative dot size the dashboard can scale however it likes.
SIZE_POS = {"high": 1.0, "mid": 0.66, "low": 0.36}

# novelty_level -> a stable badge key the dashboard maps to a glyph/colour.
BADGE_POS = {"high": "★", "mid": "◆", "low": "·"}

AXES = {
    "x": {"label": "可落地 / 商业行动性", "low": "离买家远", "high": "贴着决策"},
    "y": {"label": "概念深度", "low": "换皮", "high": "动范式"},
}


def _level(value, default="mid"):
    """Normalise a categorical level; tolerate stray casing / unknown tokens."""
    if not isinstance(value, str):
        return default
    v = value.strip().lower()
    return v if v in LEVEL_POS else default


def card_position(card):
    """Return {x, y} for a card from its value_profile. Pure, deterministic.

    The contract lets a card carry an explicit map_position; we recompute from
    the value_profile so the geometry can never silently drift from the data.
    """
    vp = card.get("value_profile") or {}
    x = LEVEL_POS[_level(vp.get("actionable_commercial"))]
    y = LEVEL_POS[_level(vp.get("conceptual_depth"))]
    return {"x": round(x, 4), "y": round(y, 4)}


def card_size(card):
    """deliverability {high|mid|low} -> relative dot size in 0..1."""
    vp = card.get("value_profile") or {}
    return SIZE_POS[_level(vp.get("deliverability"))]


def card_badge(card):
    """prior_art.novelty_level {high|mid|low} -> badge key."""
    pa = card.get("prior_art") or {}
    return BADGE_POS[_level(pa.get("novelty_level"))]


def is_survivor(card):
    """A card survives if it passed the falsifiability floor and isn't rejected."""
    if card.get("status") == "rejected":
        return False
    floor = card.get("floor") or {}
    return bool(floor.get("passes", False))


def build_map(cards):
    """Assemble map.json deterministically from a list of card dicts.

    Survivors keep document order; positions/size/badge are written back onto
    each card's map_position so the dashboard can read either source and agree.
    """
    survivors, rejected = [], []
    for c in cards:
        if is_survivor(c):
            c["map_position"] = card_position(c)
            survivors.append(c["id"])
        else:
            rejected.append(c["id"])
    return {
        "axes": AXES,
        "size_encodes": "value_profile.deliverability",
        "badge_encodes": "prior_art.novelty_level",
        "origin": ORIGIN,
        "survivors": survivors,
        "rejected": rejected,
    }


def build_run(run_id, graph, cards):
    """Assemble run.json (the at-a-glance header) from graph + cards."""
    n_surv = sum(1 for c in cards if is_survivor(c))
    return {
        "run_id": run_id,
        "paper_title": (graph.get("paper") or {}).get("title", run_id),
        "created": (graph.get("paper") or {}).get("created"),
        "n_dofs": len(graph.get("clamped_dofs") or []),
        "n_survivors": n_surv,
        "n_rejected": len(cards) - n_surv,
    }
