#!/usr/bin/env python
"""Render static HTML views of v0.7 Research Reframer artifacts.

Stdlib-only. Given a run output directory, writes self-contained HTML views for
`03_lateral_reframes.json` and/or `04_vertical_audits.json` when those artifacts exist.
"""
from __future__ import print_function

import argparse
import html
import json
import sys
from pathlib import Path


CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1f;--muted:#6b6b70;--line:#e6e6e3;
--accent:#2f6f4f;--chip:#f0f0ee;--warn:#b8860b;--err:#8a2b22;--ok:#2f6f4f}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);line-height:1.55;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;font-size:14px}
.wrap{max-width:980px;margin:0 auto;padding:24px 20px 60px}
h1{font-size:18px;margin:0 0 4px}.sub{color:var(--muted);font-size:12.5px;margin:0 0 18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px;margin-bottom:14px}
.item{border:1px solid var(--line);border-radius:8px;padding:11px 13px;margin-bottom:9px}
.pid{font-weight:700;font-variant-numeric:tabular-nums}.tag{font-size:11px;background:var(--chip);padding:1px 8px;border-radius:20px;margin-left:6px}
.meta{margin-top:6px;font-size:12px;color:var(--muted)}.kv{margin-top:6px;font-size:12.5px}.k{color:var(--muted);margin-right:6px}
.verdict{font-size:11px;padding:1px 9px;border-radius:20px;font-weight:700;margin-left:6px}
.keep{background:#eaf3ee;color:var(--ok)}.revise{background:#fbf3df;color:var(--warn)}
.reject{background:#fdecea;color:var(--err)}.escalate{background:#eaf0fb;color:#3a5a9b}
details>summary{cursor:pointer;color:var(--muted);font-size:12px;padding:4px 0}
"""


def esc(value):
    return html.escape("" if value is None else str(value))


def page(title, body):
    return (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>{}</title><style>{}</style></head><body><div class="wrap">{}</div></body></html>'
    ).format(esc(title), CSS, body)


def kvrows(pairs):
    rows = []
    for key, value in pairs:
        if value is None or str(value).strip() == "":
            continue
        rows.append('<div class="kv"><span class="k">{}</span>{}</div>'.format(esc(key), esc(value)))
    return "".join(rows)


def render_lateral(data, run):
    schemes = data.get("lateral_schemes", [])
    ledger = data.get("coverage_ledger") or {}
    coverage = ledger.get("coverage_ratio") or 0
    header = (
        '<h1>Lateral Reframes - {}</h1>'
        '<div class="sub">Divergence stage. Judgment is deferred until vertical audit.</div>'
        '<div class="card">Schemes: <b>{}</b> | Occupied cells: <b>{}/{}</b> | Coverage: <b>{}%</b></div>'
    ).format(
        esc(run),
        esc(len(schemes)),
        esc(ledger.get("occupied_count")),
        esc(ledger.get("total_cells")),
        esc(round(coverage * 1000) / 10),
    )
    rows = []
    for scheme in schemes:
        details = kvrows([
            ("来源切口", scheme.get("source_leverage_point")),
            ("内部生成方式", scheme.get("operator")),
            ("旧框架", scheme.get("old_frame")),
            ("改变的假设", scheme.get("changed_assumption")),
            ("lateral move", scheme.get("lateral_move")),
            ("完整方案", scheme.get("scheme")),
            ("完整看点", scheme.get("why_interesting")),
            ("要避免的退化", scheme.get("bad_use_to_avoid")),
        ])
        rows.append(
            '<div class="item"><div><span class="pid">{}</span><span class="tag">{}</span>'
            '</div><div>{}</div>{}<details><summary>完整字段</summary>{}</details></div>'.format(
                esc(scheme.get("lateral_id")),
                esc(scheme.get("source_leverage_point")),
                esc(scheme.get("new_frame")),
                kvrows([
                    ("旧→新", "{} → {}".format(scheme.get("old_frame"), scheme.get("new_frame"))),
                    ("人话方案", scheme.get("scheme")),
                    ("看点", scheme.get("why_interesting")),
                    ("风险", scheme.get("bad_use_to_avoid")),
                ]),
                details,
            )
        )
    return page("Lateral Reframes - {}".format(run), header + '<div class="card">{}</div>'.format("".join(rows)))


def render_audits(data, run):
    audits = data.get("audits", [])

    def eligible(audit):
        return audit.get("verdict") in ("keep", "revise") or audit.get("needs_human")

    eligible_rows = []
    rejected_rows = []
    for audit in audits:
        score = audit.get("audit_score") or {}
        cls = "escalate" if audit.get("needs_human") else audit.get("verdict")
        details = kvrows([
            ("审计理由", " ".join(audit.get("reasons", []))),
            ("因果机制", " ".join(audit.get("causal_mechanism", []))),
            ("关键假设", " ".join(audit.get("critical_assumptions", []))),
            ("先验重叠风险", audit.get("novelty_risk")),
            ("伪创新分类", "{} / {}".format(
                (audit.get("pseudo_innovation") or {}).get("status"),
                ", ".join((audit.get("pseudo_innovation") or {}).get("failure_types") or []),
            )),
            ("救回原因", audit.get("escalation_reason")),
            ("人类决议", audit.get("human_resolution")),
            ("失败模式", " ".join(audit.get("failure_modes", []))),
            ("分数", "overall {}".format(score.get("overall")) if score.get("overall") is not None else None),
            ("Codex verdict", audit.get("codex_verdict")),
            ("Local verdict", audit.get("claude_verdict")),
        ])
        row = (
            '<div class="item"><div><span class="pid">{}</span><span class="verdict {}">{}</span>'
            '<span class="tag">{}</span></div><div>{}</div>{}<details><summary>完整审计</summary>{}</details></div>'
        ).format(
            esc(audit.get("audit_id")),
            esc(cls),
            esc("needs_human" if audit.get("needs_human") else audit.get("verdict")),
            esc(audit.get("source_lateral_id")),
            esc(audit.get("refined_scheme") or audit.get("core_claim")),
            kvrows([
                ("保留下来的核心", audit.get("refined_scheme") or audit.get("core_claim")),
                ("最小实验", audit.get("minimal_experiment")),
                ("最大风险", "{} {}".format(audit.get("novelty_risk") or "", " ".join(audit.get("failure_modes", []))).strip()),
            ]),
            details,
        )
        if eligible(audit):
            eligible_rows.append(row)
        else:
            rejected_rows.append(row)

    body = (
        '<h1>Vertical Audits - {}</h1>'
        '<div class="sub">Adversarial external/local audit. Default verdict is reject.</div>'
        '<div class="card"><b>Eligible for Gate 3:</b> {} / {}</div>'
        '<div class="card">{}</div>'
    ).format(esc(run), esc(len(eligible_rows)), esc(len(audits)), "".join(eligible_rows) or "None")
    if rejected_rows:
        body += '<details class="card"><summary>Rejected audits ({})</summary>{}</details>'.format(
            len(rejected_rows),
            "".join(rejected_rows),
        )
    return page("Vertical Audits - {}".format(run), body)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render static HTML for v0.7 Research Reframer artifacts")
    parser.add_argument("output_dir", help="a run output directory")
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir)
    if not output_dir.is_dir():
        print("[ERROR] not a directory: {}".format(output_dir), file=sys.stderr)
        return 1

    run = output_dir.parent.name
    wrote = []
    lateral = output_dir / "03_lateral_reframes.json"
    audits = output_dir / "04_vertical_audits.json"
    if lateral.is_file():
        out = output_dir / "03_lateral_reframes.html"
        out.write_text(render_lateral(json.loads(lateral.read_text(encoding="utf-8")), run), encoding="utf-8")
        wrote.append(out.name)
    if audits.is_file():
        out = output_dir / "04_vertical_audits.html"
        out.write_text(render_audits(json.loads(audits.read_text(encoding="utf-8")), run), encoding="utf-8")
        wrote.append(out.name)
    if not wrote:
        print("[WARN] no 03/04 artifacts found in {}".format(output_dir), file=sys.stderr)
        return 0
    print("[OK] wrote {} in {}".format(", ".join(wrote), output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
