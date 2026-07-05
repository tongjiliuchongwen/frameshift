#!/usr/bin/env python
"""Validate Research Reframer v0.5 output artifacts (schema_version 2.0).

Stdlib-only, no third-party dependencies. Enforces the v0.5 three-gate contract
and the input -> system_node -> LP -> LR -> VA -> IC trace chain. All vocabulary
and id patterns come from contract.py (the single source of truth).

Hard failures (exit 1, [ERROR]) cover structure, enums, id formats, coverage
arithmetic, dual-judge consistency, audit-score means, cross-artifact trace
equality, and the human-gate audit trail. Non-fatal [WARN]s flag diversity /
groundedness risks and never change the exit code.

This is a clean break from the v0.2/v0.3 validator; it does not accept legacy
(schema_version 1.0) artifacts.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract as C  # noqa: E402

SCHEMA_VERSION = C.SCHEMA_VERSION
LATERAL_OPERATORS = set(C.LATERAL_OPERATORS)
LEVERAGE_TYPES = set(C.LEVERAGE_TYPES)
VERDICTS = set(C.VERDICTS)
AUDITORS = set(C.AUDITORS)
AUDIT_SCORE_KEYS = list(C.AUDIT_SCORE_KEYS)
TOL = C.TOLERANCE
VERDICT_RANK = {"reject": 0, "revise": 1, "keep": 2}  # for conservative resolution

LP_RE = re.compile(C.ID_PATTERNS["leverage_point"])
LR_RE = re.compile(C.ID_PATTERNS["lateral_scheme"])
VA_RE = re.compile(C.ID_PATTERNS["vertical_audit"])
IC_RE = re.compile(C.ID_PATTERNS["idea_card"])

ARTIFACTS = dict(C.ARTIFACTS)
REQUIRED_TRAIL = ["05_human_selection.md", "decision_log.md"]
OPTIONAL_TRAIL = ["reframe_report.md"]

GENERIC_RATIONALE_PHRASES = [
    "this is an interesting reframe",
    "this could lead to new research",
    "this changes the perspective",
    "this is a novel idea",
    "this opens up new directions",
    "this is worth exploring",
]


class Ctx:
    """Accumulates errors / warnings for one validation run."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def load_json(path, ctx):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        ctx.err("missing file: {}".format(path))
    except ValueError as exc:
        ctx.err("invalid JSON in {}: {}".format(path, exc))
    return None


def need(obj, keys, ctx, where):
    ok = True
    if not isinstance(obj, dict):
        ctx.err("{}: expected an object".format(where))
        return False
    for k in keys:
        if k not in obj:
            ctx.err("{}: missing required field '{}'".format(where, k))
            ok = False
    return ok


def check_version(obj, ctx, where):
    if isinstance(obj, dict) and obj.get("schema_version") != SCHEMA_VERSION:
        ctx.err("{}: schema_version must be '{}' (got {!r})".format(
            where, SCHEMA_VERSION, obj.get("schema_version")))


def nonempty_str(val):
    return isinstance(val, str) and val.strip() != ""


def tokens(text):
    """Tokenize for the specificity heuristic, CJK- and id-aware.

    Counts ASCII words (>=4 chars), id-like tokens (LP-001, RL04, A03...), and
    individual CJK characters, so grounded Chinese / id-referenced rationales are
    not falsely flagged as vague (a known v0.4 false-positive source).
    """
    if not isinstance(text, str):
        return set()
    out = set(re.findall(r"[A-Za-z][A-Za-z0-9_]{3,}", text))
    out |= set(re.findall(r"[A-Z]{1,4}-?[0-9]{1,3}", text))
    out |= set(re.findall(r"[一-鿿]", text))
    return out


def mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


# ---------------------------------------------------------------------------
# per-artifact validators
# ---------------------------------------------------------------------------
def validate_system_map(data, ctx):
    where = "system_map"
    check_version(data, ctx, where)
    node_arrays = [
        "actors", "goals", "stocks", "flows", "feedback_loops", "rules",
        "information_flows", "delays", "boundaries", "failure_modes", "uncertainties",
    ]
    need(data, C.REQUIRED_FIELDS["system_map"], ctx, where)
    ids = set()
    if isinstance(data, dict):
        for arr in node_arrays:
            items = data.get(arr) or []
            if not isinstance(items, list) or not items:
                ctx.err("{}: '{}' must be a non-empty array".format(where, arr))
                continue
            for it in items:
                if isinstance(it, dict) and nonempty_str(it.get("id")):
                    ids.add(it["id"])
    return ids


def validate_leverage_points(data, ctx, system_ids):
    where = "leverage_points"
    check_version(data, ctx, where)
    need(data, C.REQUIRED_FIELDS["leverage_points"], ctx, where)
    lp_map = {}
    items = data.get("leverage_points") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        ctx.err("{}: 'leverage_points' must be a non-empty array".format(where))
        return lp_map
    for lp in items:
        lid = lp.get("id") if isinstance(lp, dict) else None
        if not (isinstance(lid, str) and LP_RE.match(lid)):
            ctx.err("{}: bad leverage point id {!r} (want LP-###)".format(where, lid))
            continue
        tag = "{} {}".format(where, lid)
        if lid in lp_map:
            ctx.err("{}: duplicate leverage point id {}".format(where, lid))
        need(lp, C.REQUIRED_FIELDS["leverage_point_item"], ctx, tag)
        if lp.get("type") not in LEVERAGE_TYPES:
            ctx.err("{}: {} type {!r} not in {}".format(where, lid, lp.get("type"), sorted(LEVERAGE_TYPES)))
        trace = lp.get("source_trace") or {}
        need(trace, C.REQUIRED_FIELDS["leverage_point_source_trace"], ctx, tag + " source_trace")
        node_ids = trace.get("system_node_ids") or []
        if system_ids:
            for nid in node_ids:
                if nid not in system_ids:
                    ctx.err("{}: {} source_trace references unknown system node {}".format(where, lid, nid))
        lp_map[lid] = {"type": lp.get("type"), "system_node_ids": list(node_ids)}
    return lp_map


def validate_lateral_reframes(data, ctx, lp_map):
    where = "lateral_reframes"
    check_version(data, ctx, where)
    need(data, C.REQUIRED_FIELDS["lateral_reframes"], ctx, where)
    lr_map = {}
    selected = data.get("source_leverage_points") or []
    for lpid in selected:
        if lp_map and lpid not in lp_map:
            ctx.err("{}: source_leverage_points references unknown {}".format(where, lpid))
    schemes = data.get("lateral_schemes") or []
    if not isinstance(schemes, list) or not schemes:
        ctx.err("{}: 'lateral_schemes' must be a non-empty array".format(where))
        return lr_map
    req = C.REQUIRED_FIELDS["lateral_scheme_item"]
    new_frames, changed = [], []
    occupied = set()
    for s in schemes:
        sid = s.get("lateral_id") if isinstance(s, dict) else None
        tag = "{} {}".format(where, sid or "?")
        if not (isinstance(sid, str) and LR_RE.match(sid)):
            ctx.err("{}: bad lateral id {!r} (want LR-###)".format(where, sid))
            continue
        if sid in lr_map:
            ctx.err("{}: duplicate lateral id {}".format(where, sid))
        need(s, req, ctx, tag)
        op = s.get("operator")
        if op not in LATERAL_OPERATORS:
            ctx.err("{}: operator {!r} not in v0.5 set".format(tag, op))
        splp = s.get("source_leverage_point")
        if lp_map and splp not in lp_map:
            ctx.err("{}: source_leverage_point {} unknown".format(tag, splp))
        if selected and splp not in selected:
            ctx.err("{}: source_leverage_point {} not in the Gate-1 selection".format(tag, splp))
        if s.get("not_yet_audited") is not True:
            ctx.err("{}: not_yet_audited must be true at this stage".format(tag))
        new_frames.append(s.get("new_frame"))
        changed.append(s.get("changed_assumption"))
        occupied.add((splp, op))
        lr_map[sid] = {
            "operator": op, "source_leverage_point": splp,
            "old_frame": s.get("old_frame"), "new_frame": s.get("new_frame"),
            "changed_assumption": s.get("changed_assumption"),
        }
    _check_ledger(data.get("coverage_ledger"), ctx, where, selected, occupied, lr_map)
    _warn_duplicates(ctx, where, "new_frame", new_frames)
    _warn_duplicates(ctx, where, "changed_assumption", changed)
    return lr_map


def _check_ledger(ledger, ctx, where, selected, occupied, lr_map):
    if not isinstance(ledger, dict):
        ctx.err("{}: coverage_ledger must be an object".format(where))
        return
    ops = ledger.get("operators") or []
    if set(ops) != LATERAL_OPERATORS or len(ops) != len(LATERAL_OPERATORS):
        ctx.err("{}: coverage_ledger.operators must be exactly the 8 v0.5 operators".format(where))
    total = len(selected) * len(LATERAL_OPERATORS)
    if ledger.get("total_cells") != total:
        ctx.err("{}: total_cells must be {} (selected LP × 8)".format(where, total))
    if ledger.get("occupied_count") != len(occupied):
        ctx.err("{}: occupied_count must equal distinct occupied (LP,operator) cells ({})".format(where, len(occupied)))
    ratio = ledger.get("coverage_ratio")
    if total and (not isinstance(ratio, (int, float)) or abs(ratio - len(occupied) / total) > TOL):
        ctx.err("{}: coverage_ratio must equal occupied/total".format(where))
    # underexplored must be exactly the complement
    full = set((lp, op) for lp in selected for op in LATERAL_OPERATORS)
    want_under = full - occupied
    got_under = set((c.get("leverage_point"), c.get("operator")) for c in (ledger.get("underexplored") or []))
    if want_under != got_under:
        ctx.err("{}: underexplored must be exactly the unoccupied (LP,operator) cells".format(where))
    # ledger cells' scheme_ids must reference real schemes
    for cell in ledger.get("cells") or []:
        for rid in cell.get("scheme_ids") or []:
            if rid not in lr_map:
                ctx.err("{}: coverage_ledger references unknown scheme {}".format(where, rid))


def validate_vertical_audits(data, ctx, lr_map):
    where = "vertical_audits"
    check_version(data, ctx, where)
    need(data, C.REQUIRED_FIELDS["vertical_audits"], ctx, where)
    va_map = {}
    audited = data.get("audited_lateral_ids") or []
    for rid in audited:
        if lr_map and rid not in lr_map:
            ctx.err("{}: audited_lateral_ids references unknown {}".format(where, rid))
    audits = data.get("audits") or []
    if not isinstance(audits, list) or not audits:
        ctx.err("{}: 'audits' must be a non-empty array".format(where))
        return va_map
    req = C.REQUIRED_FIELDS["vertical_audit_item"]
    for a in audits:
        aid = a.get("audit_id") if isinstance(a, dict) else None
        tag = "{} {}".format(where, aid or "?")
        if not (isinstance(aid, str) and VA_RE.match(aid)):
            ctx.err("{}: bad audit id {!r} (want VA-###)".format(where, aid))
            continue
        if aid in va_map:
            ctx.err("{}: duplicate audit id {}".format(where, aid))
        need(a, req, ctx, tag)
        slr = a.get("source_lateral_id")
        if lr_map and slr not in lr_map:
            ctx.err("{}: source_lateral_id {} unknown".format(tag, slr))
        if audited and slr not in audited:
            ctx.err("{}: source_lateral_id {} not in the Gate-2 selection".format(tag, slr))
        if a.get("auditor") not in AUDITORS:
            ctx.err("{}: auditor {!r} invalid".format(tag, a.get("auditor")))
        cv, clv, v = a.get("codex_verdict"), a.get("claude_verdict"), a.get("verdict")
        for label, val in (("codex_verdict", cv), ("claude_verdict", clv)):
            if val is not None and val not in VERDICTS:
                ctx.err("{}: {} {!r} invalid".format(tag, label, val))
        if v not in VERDICTS:
            ctx.err("{}: verdict {!r} invalid".format(tag, v))
        _check_dual(ctx, tag, a, cv, clv, v)
        _check_gates(ctx, tag, a, v, bool(a.get("needs_human")))
        _check_audit_score(ctx, tag, a.get("audit_score"))
        if not (isinstance(a.get("reasons"), list) and a.get("reasons")):
            ctx.err("{}: reasons must be a non-empty array".format(tag))
        for m in a.get("merge_suggestions") or []:
            if lr_map and m.get("with") not in lr_map:
                ctx.err("{}: merge_suggestions.with {} unknown".format(tag, m.get("with")))
        va_map[aid] = {
            "source_lateral_id": slr, "verdict": v,
            "audit_score": a.get("audit_score"),
            "needs_human": bool(a.get("needs_human")),
        }
    return va_map


def _check_dual(ctx, tag, a, cv, clv, v):
    both = cv is not None and clv is not None
    agreement = a.get("agreement")
    if both:
        if agreement != (cv == clv):
            ctx.err("{}: agreement must equal (codex_verdict == claude_verdict)".format(tag))
        if cv == clv and v != cv:
            ctx.err("{}: on agreement, verdict must equal both judges".format(tag))
        if cv != clv:
            conservative = cv if VERDICT_RANK[cv] <= VERDICT_RANK[clv] else clv
            if v != conservative:
                ctx.err("{}: on disagreement, verdict must be the more conservative ({})".format(tag, conservative))
            if a.get("needs_human") is not True:
                ctx.err("{}: disagreement must set needs_human=true".format(tag))
        else:
            if a.get("needs_human") is not False:
                ctx.err("{}: agreement must set needs_human=false".format(tag))
    else:
        # single judge: agreement false, needs_human false, verdict == the judge that ran
        ran = cv if cv is not None else clv
        if ran is not None and v != ran:
            ctx.err("{}: single-judge verdict must equal the judge that ran".format(tag))
        if a.get("needs_human") not in (False, None) and a.get("needs_human") is not False:
            ctx.err("{}: single-judge needs_human must be false".format(tag))


def _check_gates(ctx, tag, a, verdict, needs_human):
    gates = [a.get("minimal_experiment_exists"), a.get("discriminable_from_prior"), a.get("so_what_passes")]
    for g in gates:
        if not isinstance(g, bool):
            ctx.err("{}: the three audit gates must be booleans".format(tag))
            return
    # On disagreement the verdict is a conservative placeholder pending the Gate-3
    # human decision, so it need not be consistent with one judge's gate booleans.
    if needs_human:
        return
    # keep requires all three gates true; reject requires at least one false
    if verdict == "keep" and not all(gates):
        ctx.err("{}: verdict 'keep' requires all three gates true".format(tag))
    if verdict == "reject" and all(gates):
        ctx.err("{}: verdict 'reject' but all three gates passed".format(tag))


def _check_audit_score(ctx, tag, score):
    if not isinstance(score, dict):
        ctx.err("{}: audit_score must be an object".format(tag))
        return
    vals = []
    for k in AUDIT_SCORE_KEYS:
        x = score.get(k)
        if not isinstance(x, (int, float)) or not (1 <= x <= 5):
            ctx.err("{}: audit_score.{} must be a number in 1..5".format(tag, k))
        else:
            vals.append(x)
    ov = score.get("overall")
    if vals and len(vals) == len(AUDIT_SCORE_KEYS):
        if not isinstance(ov, (int, float)) or abs(ov - mean(vals)) > TOL:
            ctx.err("{}: audit_score.overall must equal the mean of the five sub-scores".format(tag))


def validate_idea_cards(data, ctx, lp_map, lr_map, va_map):
    where = "idea_cards"
    check_version(data, ctx, where)
    need(data, C.REQUIRED_FIELDS["idea_cards"], ctx, where)
    cards = data.get("idea_cards") or []
    if not isinstance(cards, list) or not cards:
        ctx.err("{}: 'idea_cards' must be a non-empty array".format(where))
        return
    seen = set()
    follow = []
    for card in cards:
        cid = card.get("id") if isinstance(card, dict) else None
        tag = "{} {}".format(where, cid or "?")
        if not (isinstance(cid, str) and IC_RE.match(cid)):
            ctx.err("{}: bad idea card id {!r} (want IC-###)".format(where, cid))
            continue
        if cid in seen:
            ctx.err("{}: duplicate idea card id {}".format(where, cid))
        seen.add(cid)
        need(card, C.REQUIRED_FIELDS["idea_card_item"], ctx, tag)
        _check_card_traces(ctx, tag, card, lp_map, lr_map, va_map)
        _warn_specificity(ctx, tag, card)
        if isinstance(card.get("next_steps"), list):
            follow.extend(card["next_steps"])
    _warn_duplicates(ctx, where, "next_steps", follow)


def _check_card_traces(ctx, tag, card, lp_map, lr_map, va_map):
    st = card.get("system_trace") or {}
    mt = card.get("method_trace") or {}
    need(st, C.REQUIRED_FIELDS["idea_card_system_trace"], ctx, tag + " system_trace")
    need(mt, C.REQUIRED_FIELDS["idea_card_method_trace"], ctx, tag + " method_trace")
    va_id = mt.get("source_vertical_audit")
    lr_id = mt.get("source_lateral_scheme")
    lp_id = mt.get("source_leverage_point")
    # id existence
    if va_map and va_id not in va_map:
        ctx.err("{}: method_trace.source_vertical_audit {} unknown".format(tag, va_id))
    if lr_map and lr_id not in lr_map:
        ctx.err("{}: method_trace.source_lateral_scheme {} unknown".format(tag, lr_id))
    if lp_map and lp_id not in lp_map:
        ctx.err("{}: method_trace.source_leverage_point {} unknown".format(tag, lp_id))
    # system_trace <-> method_trace coherence
    if st.get("reframe") != va_id:
        ctx.err("{}: system_trace.reframe must equal method_trace.source_vertical_audit".format(tag))
    if st.get("leverage_point") != lp_id:
        ctx.err("{}: system_trace.leverage_point must equal method_trace.source_leverage_point".format(tag))
    if st.get("lateral_operation") != mt.get("operator"):
        ctx.err("{}: system_trace.lateral_operation must equal method_trace.operator".format(tag))
    # equality against the referenced VA / LR (provenance is machine-checked)
    va = va_map.get(va_id) if va_map else None
    lr = lr_map.get(lr_id) if lr_map else None
    if va:
        if mt.get("source_lateral_scheme") != va["source_lateral_id"]:
            ctx.err("{}: method_trace.source_lateral_scheme must match the audit's source_lateral_id".format(tag))
        eligible = va["verdict"] in ("keep", "revise") or va.get("needs_human")
        if not eligible:
            ctx.err("{}: card derives from VA {} that both judges rejected (only keep/revise or escalated audits may become cards)".format(tag, va_id))
        av = mt.get("audit_verdict")
        if va.get("needs_human"):
            if av not in ("keep", "revise"):
                ctx.err("{}: escalated audit — card audit_verdict must be the human's keep/revise resolution".format(tag))
        elif av != va["verdict"]:
            ctx.err("{}: method_trace.audit_verdict must equal the audit's resolved verdict".format(tag))
        if mt.get("audit_score") != va["audit_score"]:
            ctx.err("{}: method_trace.audit_score must equal the audit's audit_score".format(tag))
    if lr:
        if mt.get("operator") != lr["operator"]:
            ctx.err("{}: method_trace.operator must equal the lateral scheme's operator".format(tag))
        if mt.get("source_leverage_point") != lr["source_leverage_point"]:
            ctx.err("{}: method_trace.source_leverage_point must equal the lateral scheme's leverage point".format(tag))
        for f in ("old_frame", "new_frame", "changed_assumption"):
            if mt.get(f) != lr[f]:
                ctx.err("{}: method_trace.{} must equal the lateral scheme's {}".format(tag, f, f))
    if mt.get("operator") not in LATERAL_OPERATORS:
        ctx.err("{}: method_trace.operator {!r} not in v0.5 set".format(tag, mt.get("operator")))
    _check_audit_score(ctx, tag + " method_trace", mt.get("audit_score"))


# ---------------------------------------------------------------------------
# warnings (non-fatal)
# ---------------------------------------------------------------------------
def _warn_duplicates(ctx, where, field, values, threshold=0.3):
    vals = [v for v in values if nonempty_str(v)]
    if len(vals) < 3:
        return
    from collections import Counter
    counts = Counter(vals)
    top, n = counts.most_common(1)[0]
    if n / len(vals) > threshold:
        ctx.warn("{}: '{}' repeats {}/{} times — possible diversity collapse".format(where, field, n, len(vals)))


def _warn_specificity(ctx, tag, card):
    wn = card.get("why_not_obvious")
    if nonempty_str(wn):
        low = wn.strip().lower()
        for phrase in GENERIC_RATIONALE_PHRASES:
            if phrase in low:
                ctx.warn("{}: why_not_obvious looks generic ('{}')".format(tag, phrase))
        # must share at least one grounded token with the reframed frame (CJK/id-aware)
        ref = card.get("reframed_problem", "")
        if tokens(wn).isdisjoint(tokens(ref)) and len(tokens(wn)) > 2:
            ctx.warn("{}: why_not_obvious shares no grounded token with reframed_problem".format(tag))


# ---------------------------------------------------------------------------
# drivers
# ---------------------------------------------------------------------------
def validate_output_dir(path):
    base = Path(path)
    ctx = Ctx()
    loaded = {}
    for key, fname in ARTIFACTS.items():
        fp = base / fname
        if not fp.exists():
            ctx.err("missing artifact: {}".format(fname))
            loaded[key] = None
        else:
            loaded[key] = load_json(fp, ctx)

    system_ids = validate_system_map(loaded["system_map"], ctx) if loaded.get("system_map") else set()
    lp_map = validate_leverage_points(loaded["leverage_points"], ctx, system_ids) if loaded.get("leverage_points") else {}
    lr_map = validate_lateral_reframes(loaded["lateral_reframes"], ctx, lp_map) if loaded.get("lateral_reframes") else {}
    va_map = validate_vertical_audits(loaded["vertical_audits"], ctx, lr_map) if loaded.get("vertical_audits") else {}
    if loaded.get("idea_cards"):
        validate_idea_cards(loaded["idea_cards"], ctx, lp_map, lr_map, va_map)

    # human-gate audit trail must exist (closes the "gates are decorative" hole)
    for fname in REQUIRED_TRAIL:
        if not (base / fname).exists():
            ctx.err("missing audit-trail file: {} (the human gates must be recorded)".format(fname))
    for fname in OPTIONAL_TRAIL:
        if not (base / fname).exists():
            ctx.warn("missing {} (recommended)".format(fname))

    return report(path, ctx)


SINGLE = {
    "01_system_map.json": lambda d, c: validate_system_map(d, c),
    "02_leverage_points.json": lambda d, c: validate_leverage_points(d, c, set()),
    "03_lateral_reframes.json": lambda d, c: validate_lateral_reframes(d, c, {}),
    "04_vertical_audits.json": lambda d, c: validate_vertical_audits(d, c, {}),
    "06_idea_cards.json": lambda d, c: validate_idea_cards(d, c, {}, {}, {}),
}


def validate_single_file(path):
    ctx = Ctx()
    name = Path(path).name
    fn = SINGLE.get(name)
    if not fn:
        ctx.err("unrecognized artifact filename: {} (expected one of {})".format(name, ", ".join(SINGLE)))
        return report(path, ctx)
    data = load_json(path, ctx)
    if data is not None:
        fn(data, ctx)
    return report(path, ctx)


def report(path, ctx):
    for w in ctx.warnings:
        print("[WARN] {}".format(w), file=sys.stderr)
    if ctx.errors:
        for e in ctx.errors:
            print("[ERROR] {}".format(e), file=sys.stderr)
        print("[FAIL] {} ({} error(s), {} warning(s))".format(path, len(ctx.errors), len(ctx.warnings)), file=sys.stderr)
        return 1
    print("[OK] {}".format(path))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="Validate Research Reframer v0.5 outputs")
    p.add_argument("path", help="an output directory or a single artifact JSON file")
    args = p.parse_args(argv)
    target = Path(args.path)
    if target.is_dir():
        return validate_output_dir(target)
    return validate_single_file(target)


if __name__ == "__main__":
    raise SystemExit(main())
