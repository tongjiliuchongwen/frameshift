#!/usr/bin/env python
"""Render static HTML views of v0.5 Research Reframer artifacts.

Stdlib-only. Given a run's outputs directory, writes a self-contained
`03_lateral_reframes.html` (the divergence: schemes grouped by leverage point +
the coverage ledger) and/or `04_vertical_audits.html` (the convergence: dual-judge
verdicts, the survivors, and the rejected drawer) for whichever artifacts exist.

This is the offline counterpart to the reframe-ui channel — no server needed.

    python scripts/render_outputs.py path/to/outputs
"""
import argparse
import html
import json
import sys
from pathlib import Path

CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1f;--muted:#6b6b70;--line:#e6e6e3;
--accent:#2f6f4f;--chip:#f0f0ee;--chip-ink:#414146;--warn:#b8860b;--err:#8a2b22;--ok:#2f6f4f}
@media(prefers-color-scheme:dark){:root{--bg:#161617;--card:#1f1f21;--ink:#ededef;--muted:#9a9aa0;
--line:#2c2c2f;--accent:#4f9c72;--chip:#28282b;--chip-ink:#c8c8cc;--warn:#d8b048;--err:#f0a89e;--ok:#4f9c72}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);line-height:1.55;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",Roboto,Arial,sans-serif;font-size:14px}
.wrap{max-width:980px;margin:0 auto;padding:24px 20px 60px}
h1{font-size:18px;margin:0 0 2px}.sub{color:var(--muted);font-size:12.5px;margin:0 0 18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:14px}
h2{font-size:13px;margin:0 0 10px}.muted{color:var(--muted)}
.cov{display:flex;gap:18px;flex-wrap:wrap;font-size:12.5px}.cov b{font-variant-numeric:tabular-nums}
.grp{font-size:12px;font-weight:600;color:var(--muted);margin:14px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--line)}
.item{border:1px solid var(--line);border-radius:9px;padding:11px 13px;margin-bottom:9px}
.pid{font-weight:600;font-variant-numeric:tabular-nums}
.tag{font-size:11px;background:var(--chip);color:var(--chip-ink);padding:1px 8px;border-radius:20px;margin-left:6px}
.tag.op{background:#f1e9f4;color:#5a3a6b}@media(prefers-color-scheme:dark){.tag.op{background:#2a1f30;color:#caa8d8}}
.desc{margin-top:5px}.meta{margin-top:6px;font-size:12px;color:var(--muted)}
.kv{margin-top:6px;font-size:12.5px}.kv .k{color:var(--muted);margin-right:6px}
.verdict{font-size:11px;padding:1px 9px;border-radius:20px;font-weight:600;margin-left:6px}
.verdict.keep{background:#eaf3ee;color:var(--ok)}.verdict.revise{background:#fbf3df;color:var(--warn)}
.verdict.reject{background:#fdecea;color:var(--err)}.verdict.escalate{background:#eaf0fb;color:#3a5a9b}
@media(prefers-color-scheme:dark){.verdict.keep{background:#1c2a22}.verdict.revise{background:#2a2415}
.verdict.reject{background:#2a1715}.verdict.escalate{background:#19233a;color:#9db8ec}}
.gates .y{color:var(--ok)}.gates .n{color:var(--err)}
.rej{border:1px solid var(--line);border-left:3px solid #f0c4bd;border-radius:8px;padding:9px 11px;margin:8px 0}
details>summary{cursor:pointer;color:var(--muted);font-size:12px;padding:4px 0}
"""

def esc(x):
    return html.escape("" if x is None else str(x))

def page(title, body):
    return ("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>%s</title><style>%s</style></head><body><div class=\"wrap\">%s</div></body></html>"
            % (esc(title), CSS, body))

def kvrows(pairs):
    out = []
    for k, v in pairs:
        if v is None or str(v).strip() == "":
            continue
        out.append('<div class="kv"><span class="k">%s</span>%s</div>' % (esc(k), esc(v)))
    return "".join(out)


def render_lateral(data, run):
    schemes = data.get("lateral_schemes", [])
    led = data.get("coverage_ledger") or {}
    cov = ('<div class="card"><h2>发散覆盖（LP × 算子 台账）</h2><div class="cov">'
           '<div>已占用 <b>%s / %s</b></div><div>覆盖率 <b>%s%%</b></div>'
           '<div>欠探索 <b>%s</b></div><div>方案 <b>%s</b></div><div>来源杠杆点 <b>%s</b></div></div></div>'
           % (esc(led.get("occupied_count")), esc(led.get("total_cells")),
              esc(round((led.get("coverage_ratio") or 0) * 1000) / 10),
              esc(len(led.get("underexplored", []))), esc(len(schemes)),
              esc(len(data.get("source_leverage_points", [])))))
    groups = {}
    for s in schemes:
        groups.setdefault(s.get("source_leverage_point"), []).append(s)
    blocks = []
    for lp, items in groups.items():
        rows = ['<div class="grp">%s （%s）</div>' % (esc(lp), len(items))]
        for s in items:
            rows.append(
                '<div class="item"><div><span class="pid">%s</span>'
                '<span class="tag op">%s</span></div><div class="desc">%s</div>'
                '<div class="meta">为何有意思：%s</div>%s</div>'
                % (esc(s.get("lateral_id")), esc(s.get("operator")), esc(s.get("new_frame")),
                   esc(s.get("why_interesting")),
                   kvrows([("旧框架", s.get("old_frame")), ("改变的假设", s.get("changed_assumption")),
                           ("方案", s.get("scheme")), ("要避免的退化", s.get("bad_use_to_avoid"))])))
        blocks.append('<div class="card">%s</div>' % "".join(rows))
    body = ('<h1>横向方案 · %s</h1><div class="sub">水平发散（判断延迟，未审计）。共 %s 个方案。</div>%s%s'
            % (esc(run), len(schemes), cov, "".join(blocks)))
    return page("横向方案 · %s" % run, body)


def render_audits(data, run):
    audits = data.get("audits", [])
    def eligible(a):
        return a.get("verdict") in ("keep", "revise") or a.get("needs_human")
    surv = [a for a in audits if eligible(a)]
    rej = [a for a in audits if not eligible(a)]

    def gate(b):
        return '<span class="y">✓</span>' if b else '<span class="n">✗</span>'

    cards = []
    for a in surv:
        nh = a.get("needs_human")
        vclass = "escalate" if nh else a.get("verdict")
        vtext = "需人工" if nh else {"keep": "保留", "revise": "修订", "reject": "驳回"}.get(a.get("verdict"), a.get("verdict"))
        sc = a.get("audit_score") or {}
        cards.append(
            '<div class="item"><div><span class="pid">%s</span>'
            '<span class="verdict %s">%s</span><span class="tag">源 %s</span></div>'
            '<div class="desc">%s</div>'
            '<div class="meta gates">综合分 %s · 可证伪 %s · 可判别 %s · so-what %s%s</div>%s</div>'
            % (esc(a.get("audit_id")), esc(vclass), esc(vtext), esc(a.get("source_lateral_id")),
               esc(a.get("refined_scheme") or a.get("core_claim")), esc(sc.get("overall")),
               gate(a.get("minimal_experiment_exists")), gate(a.get("discriminable_from_prior")),
               gate(a.get("so_what_passes")),
               (" · codex %s / claude %s" % (esc(a.get("codex_verdict")), esc(a.get("claude_verdict")))) if nh else "",
               kvrows([("核心主张", a.get("core_claim")), ("最小实验", a.get("minimal_experiment")),
                       ("新颖性风险", a.get("novelty_risk")),
                       ("失败模式", "；".join(a.get("failure_modes", []))),
                       ("裁判理由", "  ".join(a.get("reasons", [])))])))
    rejrows = []
    for a in rej:
        rejrows.append('<div class="rej"><span class="pid">%s</span>'
                       '<span class="verdict reject">双裁驳回</span>'
                       '<span class="tag">源 %s</span><div class="meta">%s</div></div>'
                       % (esc(a.get("audit_id")), esc(a.get("source_lateral_id")),
                          esc("；".join(a.get("reasons", [])) or a.get("novelty_risk"))))
    drawer = ('<details class="card"><summary>被驳回抽屉 · %s 个（只读，带理由的 true-negative）</summary>%s</details>'
              % (len(rej), "".join(rejrows))) if rej else ""
    body = ('<h1>垂直审计 · %s</h1><div class="sub">对抗式双裁（Codex + Claude，默认驳回）。'
            '可成卡 %s / 共 %s。</div><div class="card">%s</div>%s'
            % (esc(run), len(surv), len(audits), "".join(cards) or '<div class="muted">无可成卡审计。</div>', drawer))
    return page("垂直审计 · %s" % run, body)


def main(argv=None):
    p = argparse.ArgumentParser(description="Render static HTML for v0.5 Research Reframer artifacts")
    p.add_argument("output_dir", help="a run's outputs directory")
    args = p.parse_args(argv)
    d = Path(args.output_dir)
    if not d.is_dir():
        print("[ERROR] not a directory: %s" % d, file=sys.stderr)
        return 1
    run = d.parent.name
    wrote = []
    lat = d / "03_lateral_reframes.json"
    aud = d / "04_vertical_audits.json"
    if lat.is_file():
        out = d / "03_lateral_reframes.html"
        out.write_text(render_lateral(json.loads(lat.read_text(encoding="utf-8")), run), encoding="utf-8")
        wrote.append(out.name)
    if aud.is_file():
        out = d / "04_vertical_audits.html"
        out.write_text(render_audits(json.loads(aud.read_text(encoding="utf-8")), run), encoding="utf-8")
        wrote.append(out.name)
    if not wrote:
        print("[WARN] no 03/04 artifacts found in %s" % d, file=sys.stderr)
        return 0
    print("[OK] wrote %s in %s" % (", ".join(wrote), d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
