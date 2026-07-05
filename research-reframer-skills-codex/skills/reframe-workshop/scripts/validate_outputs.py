#!/usr/bin/env python
"""Validate Research Reframer v0.7 output artifacts (schema_version 2.1).

Stdlib-only, no third-party dependencies. Enforces the v0.7 diagnostic three-gate
contract and the diagnosis -> input -> system_node -> LP -> LR -> VA -> IC trace
chain. All vocabulary and id patterns come from contract.py (the single source of
truth).

Hard failures (exit 1, [ERROR]) cover structure, enums, id formats, coverage
arithmetic, dual-judge consistency, audit-score means, cross-artifact trace
equality, auditable system relations, pseudo-innovation classifications, idea
change logs, the human-gate audit trail, and text-corruption sentinels. Non-fatal
[WARN]s flag diversity / groundedness risks and never change the exit code.

This is a clean break from earlier validators; it does not accept legacy artifacts.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract as C  # noqa: E402

SCHEMA_VERSION = C.SCHEMA_VERSION
DISSATISFACTION_TYPES = set(C.DISSATISFACTION_TYPES)
SYSTEM_RELATION_TYPES = set(C.SYSTEM_RELATION_TYPES)
LATERAL_OPERATORS = set(C.LATERAL_OPERATORS)
LEVERAGE_TYPES = set(C.LEVERAGE_TYPES)
VERDICTS = set(C.VERDICTS)
AUDITORS = set(C.AUDITORS)
AUDIT_SCORE_KEYS = list(C.AUDIT_SCORE_KEYS)
PSEUDO_INNOVATION_STATUS = set(C.PSEUDO_INNOVATION_STATUS)
PSEUDO_INNOVATION_FAILURE_TYPES = set(C.PSEUDO_INNOVATION_FAILURE_TYPES)
HUMAN_RESOLUTIONS = set(C.HUMAN_RESOLUTIONS)
TOL = C.TOLERANCE
VERDICT_RANK = {"reject": 0, "revise": 1, "keep": 2}  # for conservative resolution

LP_RE = re.compile(C.ID_PATTERNS["leverage_point"])
LR_RE = re.compile(C.ID_PATTERNS["lateral_scheme"])
VA_RE = re.compile(C.ID_PATTERNS["vertical_audit"])
IC_RE = re.compile(C.ID_PATTERNS["idea_card"])

ARTIFACTS = dict(C.ARTIFACTS)
REQUIRED_TRAIL = ["05_gate_cards.json", "05_human_selection.json", "05_human_selection.md", "decision_log.md"]
OPTIONAL_TRAIL = ["reframe_report.md"]

GENERIC_RATIONALE_PHRASES = [
    "this is an interesting reframe",
    "this could lead to new research",
    "this changes the perspective",
    "this is a novel idea",
    "this opens up new directions",
    "this is worth exploring",
]
CORRUPTION_PATTERNS = [
    (re.compile(r"\?{4,}"), "runs of replacement question marks"),
    (re.compile(u"\ufffd"), "Unicode replacement character"),
    (re.compile(r"锛|銆|鈥\?|閫|鏃|鐨|缁|浣|绋|闂"), "common mojibake sequence"),
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
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        check_text_integrity(data, ctx, str(path))
        return data
    except FileNotFoundError:
        ctx.err("missing file: {}".format(path))
    except ValueError as exc:
        ctx.err("invalid JSON in {}: {}".format(path, exc))
    return None


def check_text_integrity(value, ctx, where):
    """Fail fast on lossy Windows/encoding artifacts before they reach a gate."""
    if isinstance(value, dict):
        for key, child in value.items():
            check_text_integrity(child, ctx, "{}.{}".format(where, key))
        return
    if isinstance(value, list):
        for idx, child in enumerate(value):
            check_text_integrity(child, ctx, "{}[{}]".format(where, idx))
        return
    if not isinstance(value, str):
        return
    for regex, label in CORRUPTION_PATTERNS:
        if regex.search(value):
            excerpt = value[:100].replace("\n", "\\n")
            ctx.err("{}: possible text encoding corruption ({}): {!r}".format(where, label, excerpt))
            return


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


def same_id_set(left, right):
    return sorted(left or []) == sorted(right or [])


def gate_name(num):
    return "gate{}".format(num)


def gate_selected(selection, num):
    gate = ((selection or {}).get("gates") or {}).get(gate_name(num)) or {}
    selected = gate.get("selected") or []
    if num == 3:
        out = []
        for item in selected:
            if isinstance(item, dict):
                out.append(item.get("audit_id"))
            else:
                out.append(item)
        return [x for x in out if isinstance(x, str)]
    return [x for x in selected if isinstance(x, str)]


def idea_card_source_vas(data):
    out = []
    if not isinstance(data, dict):
        return out
    for card in data.get("idea_cards") or []:
        if isinstance(card, dict):
            va = (card.get("method_trace") or {}).get("source_vertical_audit")
            if isinstance(va, str):
                out.append(va)
    return out


# ---------------------------------------------------------------------------
# per-artifact validators
# ---------------------------------------------------------------------------
def validate_diagnosis(data, ctx):
    where = "diagnosis"
    check_version(data, ctx, where)
    need(data, C.REQUIRED_FIELDS["diagnosis"], ctx, where)
    types = data.get("dissatisfaction_types") if isinstance(data, dict) else None
    if not isinstance(types, list) or not types:
        ctx.err("{}: dissatisfaction_types must be a non-empty array".format(where))
    else:
        for t in types:
            if t not in DISSATISFACTION_TYPES:
                ctx.err("{}: dissatisfaction_type {!r} invalid".format(where, t))
    return data if isinstance(data, dict) else {}


def validate_system_map(data, ctx):
    where = "system_map"
    check_version(data, ctx, where)
    item_required = {
        "actors": "system_map_actor",
        "goals": "system_map_goal",
        "stocks": "system_map_stock",
        "flows": "system_map_flow",
        "feedback_loops": "system_map_feedback_loop",
        "rules": "system_map_rule",
        "information_flows": "system_map_information_flow",
        "delays": "system_map_delay",
        "boundaries": "system_map_boundary",
        "failure_modes": "system_map_failure_mode",
        "uncertainties": "system_map_uncertainty",
    }
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
                if isinstance(it, dict):
                    need(it, C.REQUIRED_FIELDS[item_required[arr]], ctx, "{}.{} item".format(where, arr))
                    _check_system_map_item(ctx, "{}.{} {}".format(where, arr, it.get("id") or "?"), arr, it)
        for arr in ("flows", "feedback_loops", "information_flows"):
            for idx, it in enumerate(data.get(arr) or []):
                tag = "{}.{}[{}]".format(where, arr, idx)
                if not isinstance(it, dict):
                    continue
                need(it, C.REQUIRED_FIELDS["system_map_relation_audit"], ctx, tag)
                if it.get("relation_type") not in SYSTEM_RELATION_TYPES:
                    ctx.err("{}: relation_type {!r} invalid".format(tag, it.get("relation_type")))
    return ids


def _check_system_map_item(ctx, tag, arr, item):
    if arr == "actors":
        if not isinstance(item.get("incentives"), list) or not item.get("incentives"):
            ctx.err("{}: incentives must be a non-empty array".format(tag))
    elif arr == "feedback_loops":
        if item.get("type") not in ("balancing", "reinforcing", "unknown"):
            ctx.err("{}: feedback loop type {!r} invalid".format(tag, item.get("type")))
        if not isinstance(item.get("nodes"), list) or not item.get("nodes"):
            ctx.err("{}: nodes must be a non-empty array".format(tag))
    elif arr == "rules":
        if item.get("explicitness") not in ("explicit", "implicit", "inferred"):
            ctx.err("{}: explicitness {!r} invalid".format(tag, item.get("explicitness")))
    elif arr == "failure_modes":
        if not isinstance(item.get("linked_nodes"), list) or not item.get("linked_nodes"):
            ctx.err("{}: linked_nodes must be a non-empty array".format(tag))


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
            ctx.err("{}: operator {!r} not in canonical lateral-operator set".format(tag, op))
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
    need(ledger, C.REQUIRED_FIELDS["coverage_ledger"], ctx, "{} coverage_ledger".format(where))
    ops = ledger.get("operators") or []
    if set(ops) != LATERAL_OPERATORS or len(ops) != len(LATERAL_OPERATORS):
        ctx.err("{}: coverage_ledger.operators must be exactly the 8 canonical operators".format(where))
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
        need(cell, C.REQUIRED_FIELDS["coverage_ledger_cell"], ctx, "{} coverage_ledger cell".format(where))
        ids = cell.get("scheme_ids") or []
        if cell.get("scheme_count") != len(ids):
            ctx.err("{}: coverage_ledger cell scheme_count must equal len(scheme_ids)".format(where))
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
        _check_pseudo_innovation(ctx, tag, a.get("pseudo_innovation"))
        _check_escalation(ctx, tag, a)
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
            "human_resolution": a.get("human_resolution"),
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


def _check_pseudo_innovation(ctx, tag, block):
    if not isinstance(block, dict):
        ctx.err("{}: pseudo_innovation must be an object".format(tag))
        return
    need(block, C.REQUIRED_FIELDS["pseudo_innovation"], ctx, tag + " pseudo_innovation")
    status = block.get("status")
    if status not in PSEUDO_INNOVATION_STATUS:
        ctx.err("{}: pseudo_innovation.status {!r} invalid".format(tag, status))
    failures = block.get("failure_types")
    if not isinstance(failures, list):
        ctx.err("{}: pseudo_innovation.failure_types must be an array".format(tag))
        return
    for failure in failures:
        if failure not in PSEUDO_INNOVATION_FAILURE_TYPES:
            ctx.err("{}: pseudo_innovation failure_type {!r} invalid".format(tag, failure))
    if status in ("repairable", "fatal") and not failures:
        ctx.err("{}: pseudo_innovation.status {} requires at least one failure_type".format(tag, status))
    if status == "clear" and failures:
        ctx.warn("{}: pseudo_innovation.status clear should usually have no failure_types".format(tag))


def _check_escalation(ctx, tag, a):
    resolution = a.get("human_resolution")
    if resolution is not None and resolution not in HUMAN_RESOLUTIONS:
        ctx.err("{}: human_resolution {!r} invalid".format(tag, resolution))
    if a.get("needs_human") is True and not nonempty_str(a.get("escalation_reason")):
        ctx.err("{}: needs_human=true requires a non-empty escalation_reason".format(tag))
    if a.get("needs_human") is not True and a.get("escalation_reason") not in (None, ""):
        ctx.warn("{}: escalation_reason is usually null unless needs_human=true".format(tag))


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
        return set()
    seen = set()
    source_vas = set()
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
        _check_reader_view(ctx, tag, card)
        _check_change_log(ctx, tag, card)
        va_id = ((card.get("method_trace") or {}).get("source_vertical_audit"))
        if isinstance(va_id, str):
            source_vas.add(va_id)
        _warn_specificity(ctx, tag, card)
        if isinstance(card.get("next_steps"), list):
            follow.extend(card["next_steps"])
    _warn_duplicates(ctx, where, "next_steps", follow)
    return source_vas


def validate_human_selection(data, ctx, loaded, lp_map, lr_map, va_map, idea_vas):
    where = "human_selection"
    check_version(data, ctx, where)
    if not need(data, ["schema_version", "gates"], ctx, where):
        return
    gates = data.get("gates")
    if not isinstance(gates, dict):
        ctx.err("{}: gates must be an object".format(where))
        return

    for num in (1, 2, 3):
        gate = gates.get(gate_name(num))
        if not isinstance(gate, dict):
            ctx.err("{}: missing {}".format(where, gate_name(num)))
            continue
        if "selected" not in gate:
            ctx.err("{} {}: missing selected".format(where, gate_name(num)))
        mode = gate.get("mode")
        if mode not in ("explicit", "delegate", "mapped_natural_language", "example", "unknown"):
            ctx.err("{} {}: invalid mode {!r}".format(where, gate_name(num), mode))
        if num == 3:
            selected = gate.get("selected") or []
            for idx, item in enumerate(selected):
                tag = "{} gate3 selected[{}]".format(where, idx)
                if not isinstance(item, dict):
                    ctx.err("{}: must be an object with audit_id and resolution".format(tag))
                    continue
                need(item, C.REQUIRED_FIELDS["human_selection_gate3_item"], ctx, tag)
                if item.get("resolution") not in HUMAN_RESOLUTIONS:
                    ctx.err("{}: resolution {!r} invalid".format(tag, item.get("resolution")))

    g1 = gate_selected(data, 1)
    g2 = gate_selected(data, 2)
    g3 = gate_selected(data, 3)

    for lpid in g1:
        if not LP_RE.match(lpid):
            ctx.err("{} gate1: bad selected id {}".format(where, lpid))
        elif lp_map and lpid not in lp_map:
            ctx.err("{} gate1: selected id {} not found in 02_leverage_points.json".format(where, lpid))
    for lrid in g2:
        if not LR_RE.match(lrid):
            ctx.err("{} gate2: bad selected id {}".format(where, lrid))
        elif lr_map and lrid not in lr_map:
            ctx.err("{} gate2: selected id {} not found in 03_lateral_reframes.json".format(where, lrid))
    for vaid in g3:
        if not VA_RE.match(vaid):
            ctx.err("{} gate3: bad selected id {}".format(where, vaid))
        elif va_map and vaid not in va_map:
            ctx.err("{} gate3: selected id {} not found in 04_vertical_audits.json".format(where, vaid))
        elif va_map:
            va = va_map[vaid]
            eligible = va["verdict"] in ("keep", "revise") or va.get("needs_human")
            if not eligible:
                ctx.err("{} gate3: selected {} was not eligible for card creation".format(where, vaid))
            selected_obj = next((x for x in ((gates.get("gate3") or {}).get("selected") or []) if isinstance(x, dict) and x.get("audit_id") == vaid), None)
            if selected_obj and va.get("needs_human") and va.get("human_resolution") != selected_obj.get("resolution"):
                ctx.err("{} gate3: selected {} resolution must match vertical_audit.human_resolution".format(where, vaid))

    lateral = loaded.get("lateral_reframes") or {}
    if lateral and not same_id_set(g1, lateral.get("source_leverage_points") or []):
        ctx.err("{} gate1: selected ids must match 03_lateral_reframes.source_leverage_points".format(where))

    audits = loaded.get("vertical_audits") or {}
    if audits and not same_id_set(g2, audits.get("audited_lateral_ids") or []):
        ctx.err("{} gate2: selected ids must match 04_vertical_audits.audited_lateral_ids".format(where))

    if idea_vas and not same_id_set(g3, list(idea_vas)):
        ctx.err("{} gate3: selected audit ids must match 06_idea_cards method_trace source_vertical_audit".format(where))

    gate3 = gates.get("gate3") or {}
    rejected = gate3.get("rejected_drawer_locked") or []
    for vaid in rejected:
        if not isinstance(vaid, str) or not VA_RE.match(vaid):
            ctx.err("{} gate3: bad rejected_drawer_locked id {}".format(where, vaid))
        elif vaid in g3:
            ctx.err("{} gate3: {} cannot be both selected and locked in rejected drawer".format(where, vaid))


def validate_gate_cards(data, ctx, selection):
    where = "gate_cards"
    check_version(data, ctx, where)
    if not need(data, ["schema_version", "gates"], ctx, where):
        return
    gates = data.get("gates")
    if not isinstance(gates, dict):
        ctx.err("{}: gates must be an object".format(where))
        return

    required_labels = {
        1: ["旧假设", "卡在哪里", "选它后会生成"],
        2: ["旧→新", "风险"],
        3: ["保留下来的核心", "最小实验", "最大风险"],
    }
    for num in (1, 2, 3):
        key = gate_name(num)
        gate = gates.get(key)
        if not isinstance(gate, dict):
            ctx.err("{}: missing {}".format(where, key))
            continue
        need(gate, C.REQUIRED_FIELDS["gate_cards_gate"], ctx, "{} {}".format(where, key))
        if gate.get("display_language") != "zh-CN":
            ctx.err("{} {}: display_language must be zh-CN".format(where, key))
        if not nonempty_str(gate.get("source_artifact")):
            ctx.err("{} {}: source_artifact is required".format(where, key))
        if not isinstance(gate.get("selected_ids"), list):
            ctx.err("{} {}: selected_ids must be an array".format(where, key))
        cards = gate.get("cards")
        if not isinstance(cards, list) or not cards:
            ctx.err("{} {}: cards must be a non-empty array".format(where, key))
            continue
        ids = set()
        for card in cards:
            cid = card.get("id") if isinstance(card, dict) else None
            if not isinstance(cid, str):
                ctx.err("{} {}: card id must be a string".format(where, key))
                continue
            need(card, C.REQUIRED_FIELDS["gate_card_item"], ctx, "{} {} {}".format(where, key, cid))
            ids.add(cid)
            if not nonempty_str(card.get("title")):
                ctx.err("{} {} {}: title is required".format(where, key, cid))
            rows = card.get("summary_rows")
            if not isinstance(rows, list) or not rows:
                ctx.err("{} {} {}: summary_rows must be non-empty".format(where, key, cid))
                continue
            labels = [r.get("label") for r in rows if isinstance(r, dict)]
            for label in required_labels[num]:
                if label not in labels:
                    ctx.err("{} {} {}: missing display label {}".format(where, key, cid, label))
            if num == 2 and not ("方案" in labels or "人话方案" in labels):
                ctx.err("{} {} {}: missing display label 方案 or 人话方案".format(where, key, cid))
            for row in rows:
                if isinstance(row, dict):
                    need(row, C.REQUIRED_FIELDS["gate_card_row"], ctx, "{} {} {} summary_row".format(where, key, cid))
                if not isinstance(row, dict) or not nonempty_str(row.get("label")) or not nonempty_str(row.get("text")):
                    ctx.err("{} {} {}: summary rows need non-empty label/text".format(where, key, cid))

        selected = gate.get("selected_ids") or gate_selected(selection, num)
        for sid in selected:
            if sid not in ids:
                ctx.err("{} {}: selected id {} has no saved card".format(where, key, sid))


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
            expected = _resolution_to_card_verdict(va.get("human_resolution"))
            if not expected:
                ctx.err("{}: escalated audit requires a keep/revise human_resolution".format(tag))
            if expected and av != expected:
                ctx.err("{}: audit_verdict must match VA human_resolution ({})".format(tag, expected))
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
        ctx.err("{}: method_trace.operator {!r} not in canonical lateral-operator set".format(tag, mt.get("operator")))
    _check_audit_score(ctx, tag + " method_trace", mt.get("audit_score"))


def _resolution_to_card_verdict(resolution):
    if resolution in ("keep", "human_rescue_to_keep", "selected_for_card"):
        return "keep"
    if resolution in ("revise", "human_rescue_to_revise"):
        return "revise"
    return None


def _check_change_log(ctx, tag, card):
    change = card.get("change_log") or {}
    mt = card.get("method_trace") or {}
    need(change, C.REQUIRED_FIELDS["idea_card_change_log"], ctx, tag + " change_log")
    if change.get("selected_leverage_point") != mt.get("source_leverage_point"):
        ctx.err("{}: change_log.selected_leverage_point must equal method_trace.source_leverage_point".format(tag))


def _check_reader_view(ctx, tag, card):
    reader = card.get("reader_view") or {}
    if not isinstance(reader, dict):
        ctx.err("{}: reader_view must be an object".format(tag))
        return
    need(reader, C.REQUIRED_FIELDS["idea_card_reader_view"], ctx, tag + " reader_view")
    text_parts = []
    for field in C.REQUIRED_FIELDS["idea_card_reader_view"]:
        value = reader.get(field)
        if not nonempty_str(value):
            ctx.err("{}: reader_view.{} must be a non-empty string".format(tag, field))
            continue
        text_parts.append(value)
        if len(value) > 220 and field != "minimal_test":
            ctx.warn("{}: reader_view.{} is long for the default reader layer".format(tag, field))
    glossary = reader.get("glossary")
    if glossary is not None:
        if not isinstance(glossary, list):
            ctx.err("{}: reader_view.glossary must be an array when present".format(tag))
        else:
            for idx, item in enumerate(glossary):
                if not (isinstance(item, list) and len(item) >= 2 and nonempty_str(item[0]) and nonempty_str(item[1])):
                    ctx.err("{}: reader_view.glossary[{}] must be [term, explanation]".format(tag, idx))
    combined = " ".join(text_parts)
    latin_words = re.findall(r"[A-Za-z][A-Za-z0-9_-]*", combined)
    if len(latin_words) > 12:
        ctx.warn("{}: reader_view has {} English-like tokens; consider moving terms to the technical layer".format(tag, len(latin_words)))


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

    validate_diagnosis(loaded["diagnosis"], ctx) if loaded.get("diagnosis") else {}
    system_ids = validate_system_map(loaded["system_map"], ctx) if loaded.get("system_map") else set()
    lp_map = validate_leverage_points(loaded["leverage_points"], ctx, system_ids) if loaded.get("leverage_points") else {}
    lr_map = validate_lateral_reframes(loaded["lateral_reframes"], ctx, lp_map) if loaded.get("lateral_reframes") else {}
    va_map = validate_vertical_audits(loaded["vertical_audits"], ctx, lr_map) if loaded.get("vertical_audits") else {}
    idea_vas = set()
    if loaded.get("idea_cards"):
        idea_vas = validate_idea_cards(loaded["idea_cards"], ctx, lp_map, lr_map, va_map)

    human_selection = None
    selection_path = base / "05_human_selection.json"
    if selection_path.exists():
        human_selection = load_json(selection_path, ctx)
        if human_selection is not None:
            validate_human_selection(human_selection, ctx, loaded, lp_map, lr_map, va_map, idea_vas)
    gate_cards_path = base / "05_gate_cards.json"
    if gate_cards_path.exists():
        gate_cards = load_json(gate_cards_path, ctx)
        if gate_cards is not None:
            validate_gate_cards(gate_cards, ctx, human_selection or {})

    # human-gate audit trail must exist (closes the "gates are decorative" hole)
    for fname in REQUIRED_TRAIL:
        fp = base / fname
        if not fp.exists():
            ctx.err("missing audit-trail file: {} (the human gates must be recorded)".format(fname))
        elif fp.suffix.lower() == ".md":
            check_text_integrity(fp.read_text(encoding="utf-8"), ctx, str(fp))
    for fname in OPTIONAL_TRAIL:
        fp = base / fname
        if not fp.exists():
            ctx.warn("missing {} (recommended)".format(fname))
        elif fp.suffix.lower() == ".md":
            check_text_integrity(fp.read_text(encoding="utf-8"), ctx, str(fp))

    return report(path, ctx)


SINGLE = {
    "00_diagnosis.json": lambda d, c: validate_diagnosis(d, c),
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
    p = argparse.ArgumentParser(description="Validate Research Reframer v0.7 outputs")
    p.add_argument("path", help="an output directory or a single artifact JSON file")
    args = p.parse_args(argv)
    target = Path(args.path)
    if target.is_dir():
        return validate_output_dir(target)
    return validate_single_file(target)


if __name__ == "__main__":
    raise SystemExit(main())
