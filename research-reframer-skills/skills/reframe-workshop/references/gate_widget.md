# Interactive gate panel — reusable template

This is the **default** way to run the three human gates: an inline, clickable panel rendered with
the built-in `mcp__visualize__show_widget` tool. A click calls the global `sendPrompt(...)` so the
selection lands **straight in the conversation** and drives the next stage. No server, no launch flag,
no per-use setup — it ships inside the pack as instructions and works for anyone who installed it.

If `show_widget` is unavailable in the current client, **fall back to `AskUserQuestion`** (a core tool;
see the fallback note at the bottom). Never fall back to "read a static list and type ids back".

## How to use it per gate

1. Read the gate's artifact (`02_leverage_points.json` for Gate 1, `03_lateral_reframes.json` for
   Gate 2, `04_vertical_audits.json` for Gate 3).
2. Build the `ITEMS` array from it (one entry per candidate). Pre-select (`rec:true`) a diverse
   recommended set per the Selection heuristics.
3. Set the `GATE` block for that gate (number, id prefix, the directive each button sends).
4. Pass the body below as `show_widget`'s `widget_code`. Put your prose (what the gate is) in the
   response text, not inside the widget.
5. When the click arrives as a normal message, run **only** that gate's downstream stage.

Per-gate config:

| Gate | source artifact | id prefix | rows are | continue runs |
| --- | --- | --- | --- | --- |
| 1 | `02_leverage_points.json` | `LP-` | leverage points | `lateral-generate` → `03` |
| 2 | `03_lateral_reframes.json` | `LR-` | lateral schemes | `vertical-audit` → `04` |
| 3 | `04_vertical_audits.json` | `VA-` | audited schemes; both-judges-rejected go in a read-only drawer (`selectable:false`) | `idea-card` → `06` + validate |

## widget_code template (adapt `GATE` and `ITEMS`, then render)

```html
<h2 style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">闸门:点选候选项,点"继续"把选择送回对话。</h2>
<style>
.lp{display:flex;gap:12px;align-items:flex-start;width:100%;text-align:left;background:var(--surface-2);border:0.5px solid var(--border);border-radius:12px;padding:12px 14px;margin:0 0 8px;cursor:pointer}
.lp:hover{border-color:var(--border-strong)}
.lp.sel{border:2px solid var(--border-accent);background:var(--bg-accent)}
.lp.ro{cursor:default;opacity:0.6}
.ck{flex:0 0 18px;width:18px;height:18px;border-radius:5px;border:1.5px solid var(--border-strong);display:flex;align-items:center;justify-content:center;margin-top:2px}
.lp.sel .ck{background:var(--text-accent);border-color:var(--text-accent)}
.ck i{font-size:13px;color:#fff;opacity:0}
.lp.sel .ck i{opacity:1}
.pill{font-size:12px;padding:1px 8px;border-radius:var(--radius);background:var(--surface-1);color:var(--text-secondary)}
.id{font-family:var(--font-mono);font-size:13px;font-weight:500;color:var(--text-primary)}
.dsc{font-size:14px;color:var(--text-secondary);line-height:1.6}
</style>
<div id="gate" style="padding:0.5rem 0"></div>
<div style="display:flex;align-items:center;gap:12px;margin-top:14px;flex-wrap:wrap">
<span id="cnt" style="font-size:14px;color:var(--text-secondary)"></span>
<span style="flex:1"></span>
<button onclick="_dele()" style="font-size:14px">让 Claude 替我选 ↗</button>
<button onclick="_go()" style="font-size:14px;background:var(--bg-accent);color:var(--text-accent);border:0.5px solid var(--border-accent)" id="gobtn"></button>
</div>
<script>
(function(){
  var GATE={ n:1, verb:"进入 Gate 2",
    go:function(ids){return "Gate 1:我选定杠杆点 "+ids+"。记录到 05_human_selection.md 与 decision_log.md,只对这些杠杆点运行 lateral-generate 生成 03_lateral_reframes,进入 Gate 2。";},
    dele:"Gate 1:你来替我选杠杆点(按多样性挑 2-4 个互不重叠的高杠杆点),说明理由、记录,然后跑 lateral-generate 进入 Gate 2。" };
  var ITEMS=[
    { id:"LP-001", tags:["paradigm","high"], desc:"可评分性 = 有效问题的定义", rec:true, selectable:true },
    { id:"LP-002", tags:["goal","high"], desc:"argmax M ↔ 审问 M", rec:false, selectable:true }
  ];
  var sel=new Set(ITEMS.filter(function(i){return i.rec;}).map(function(i){return i.id;}));
  var box=document.getElementById("gate");
  ITEMS.forEach(function(it){
    var row=document.createElement("div");
    row.className="lp"+(it.selectable?"":" ro")+(sel.has(it.id)?" sel":"");
    row.dataset.id=it.id;
    var tags=it.tags.map(function(t){return '<span class="pill">'+t+'</span>';}).join("");
    row.innerHTML='<span class="ck"><i class="ti ti-check"></i></span><div style="flex:1"><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px"><span class="id">'+it.id+'</span>'+tags+'</div><div class="dsc">'+it.desc+'</div></div>';
    if(it.selectable){ row.onclick=function(){ if(sel.has(it.id)){sel.delete(it.id);}else{sel.add(it.id);} paint(); }; }
    box.appendChild(row);
  });
  function paint(){
    document.querySelectorAll('.lp').forEach(function(el){ el.classList.toggle('sel', sel.has(el.dataset.id)); });
    document.getElementById('cnt').textContent='已选 '+sel.size+' 个';
  }
  document.getElementById('gobtn').textContent='用选中的'+GATE.verb+' ↗';
  window._go=function(){ if(sel.size===0){document.getElementById('cnt').textContent='先选至少 1 个';return;} sendPrompt(GATE.go(Array.from(sel).sort().join(', '))); };
  window._dele=function(){ sendPrompt(GATE.dele); };
  paint();
})();
</script>
```

Replace `GATE` and `ITEMS` per gate. For **Gate 2** set `GATE.n=2`, `verb="进入 Gate 3"`, the `go`
directive to "对所选 LR 跑 vertical-audit(Codex+Claude 双裁、默认驳回)生成 04,进入 Gate 3", and build
`ITEMS` from `03_lateral_reframes.json` (id prefix `LR-`, tags = operator + source LP). For **Gate 3**
set `verb="出 idea 卡"`, the `go` directive to "对所选 VA 跑 idea-card 生成 06、跑校验器到 exit 0", build
`ITEMS` from `04_vertical_audits.json`, and add the both-judges-rejected audits as `selectable:false`
rows (read-only "rejected drawer").

## Fallback — `AskUserQuestion` (when `show_widget` is unavailable)

Render one `AskUserQuestion` (multiSelect) whose options are the recommended candidates plus a
distinct "让 Claude 按启发式替我选" option; the auto "Other" lets the human name different ids. The
chosen labels arrive in the conversation exactly like a panel click. This is a core tool with zero
setup, so it always works even when the rich panel can't render. Never degrade to "type the ids into
a box yourself" — always give clickable options.
