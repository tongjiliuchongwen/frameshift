#!/usr/bin/env node
/*
 * reframe-ui — a Claude Code "channel" that turns the THREE Research Reframer human
 * gates into a clickable localhost UI:
 *   Gate 1 · pick leverage points (LP-###)   → agent runs lateral-generate → 03
 *   Gate 2 · pick lateral schemes (LR-###)    → agent runs vertical-audit   → 04
 *   Gate 3 · pick audited schemes (VA-###)    → agent runs idea-card        → 06
 *
 * ONE process is BOTH:
 *   (a) an MCP server over stdio  -> talks to Claude Code (the channel)
 *   (b) an HTTP + SSE server      -> talks to the browser UI (127.0.0.1)
 *
 * A browser click POSTs /select -> we push notifications/claude/channel -> the
 * selection lands in the RUNNING Claude Code session as a <channel> tag. Claude
 * continues the pipeline, then calls the `reply` tool -> we SSE the status to the
 * browser so it advances to the next gate.
 *
 * Gate detection keys on contract VALIDITY (schema_version 2.0 + a non-empty
 * artifact array), not raw file existence, so a half-written / invalid artifact
 * does not advance the UI past a gate the validator would reject.
 *
 * CRITICAL: stdout is the MCP JSON-RPC transport. Never write to stdout
 * (no console.log). All logging goes to stderr via log().
 *
 * See CONTRACT.md for the exact wire shapes.
 */
import http from 'node:http';
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { join, dirname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { ListToolsRequestSchema, CallToolRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.REFRAME_PORT || 8765);

const log = (...a) => console.error('[reframe-ui]', ...a);

// gate → explicit-id prefix
const GATE_PREFIX = { 1: 'LP-', 2: 'LR-', 3: 'VA-' };

// Where runs live; each run is <BASE>/<name>/outputs/.
function probeBase() {
  for (const rel of ['../test-runs', '../examples', '../../test-runs', '../../examples']) {
    const p = join(__dirname, ...rel.split('/'));
    if (existsSync(p)) return p;
  }
  return join(__dirname, '..', 'test-runs');
}
let RUN_DIR = process.env.REFRAME_RUN_DIR || null;
const BASE = process.env.REFRAME_BASE || (RUN_DIR ? join(RUN_DIR, '..', '..') : probeBase());
if (!RUN_DIR) RUN_DIR = autoLatestRun();

// ---------------------------------------------------------------- run discovery
function autoLatestRun() {
  try {
    const runs = readdirSync(BASE)
      .map((n) => join(BASE, n, 'outputs'))
      .filter((p) => existsSync(p));
    if (!runs.length) return null;
    runs.sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs);
    return runs[0];
  } catch {
    return null;
  }
}
const runName = (dir) => (dir ? basename(join(dir, '..')) : null);
const readJSON = (p) => {
  try { return JSON.parse(readFileSync(p, 'utf8')); } catch { return null; }
};
// a v0.5 artifact counts as "reached" only if it declares schema_version 2.0 and
// carries a non-empty array under its key — not merely that the file exists.
const validV05 = (obj, key) => !!(obj && obj.schema_version === '2.0' && Array.isArray(obj[key]) && obj[key].length);

// ---------------------------------------------------------------- state for UI
function buildState() {
  const dir = RUN_DIR;
  if (!dir || !existsSync(dir)) return { ok: false, error: 'no run dir', base: BASE };

  const lpsRaw = readJSON(join(dir, '02_leverage_points.json'));
  const latRaw = readJSON(join(dir, '03_lateral_reframes.json'));
  const audRaw = readJSON(join(dir, '04_vertical_audits.json'));
  const cardRaw = readJSON(join(dir, '06_idea_cards.json'));

  const lpsOk = validV05(lpsRaw, 'leverage_points');
  const latOk = validV05(latRaw, 'lateral_schemes');
  const audOk = validV05(audRaw, 'audits');
  const cardOk = validV05(cardRaw, 'idea_cards');

  let gate = 'not_ready';
  if (cardOk) gate = 'done';
  else if (audOk) gate = 3;
  else if (latOk) gate = 2;
  else if (lpsOk) gate = 1;

  // Gate 1 context: the leverage points to choose from.
  const leverage = lpsOk
    ? lpsRaw.leverage_points.map((l) => ({
        id: l.id, type: l.type, system_location: l.system_location,
        why_it_matters: l.why_it_matters, current_assumption: l.current_assumption,
        reframing_potential: l.reframing_potential,
      }))
    : null;

  // Gate 2 context: the lateral schemes (judgment deferred) + the coverage ledger.
  const lateral = latOk
    ? {
        source_leverage_points: latRaw.source_leverage_points || [],
        coverage_ledger: latRaw.coverage_ledger
          ? {
              occupied_count: latRaw.coverage_ledger.occupied_count,
              total_cells: latRaw.coverage_ledger.total_cells,
              coverage_ratio: latRaw.coverage_ledger.coverage_ratio,
              underexplored: (latRaw.coverage_ledger.underexplored || []).length,
            }
          : null,
        schemes: latRaw.lateral_schemes.map((s) => ({
          lateral_id: s.lateral_id, source_leverage_point: s.source_leverage_point, operator: s.operator,
          old_frame: s.old_frame, new_frame: s.new_frame, scheme: s.scheme,
          why_interesting: s.why_interesting, changed_assumption: s.changed_assumption,
          bad_use_to_avoid: s.bad_use_to_avoid,
        })),
      }
    : null;

  // Gate 3 context: the audits. `eligible` = can become a card (keep/revise survivor,
  // or an escalated needs_human audit the human may rescue). Both-judges-reject is not.
  const audits = audOk
    ? audRaw.audits.map((a) => ({
        audit_id: a.audit_id, source_lateral_id: a.source_lateral_id, verdict: a.verdict,
        codex_verdict: a.codex_verdict, claude_verdict: a.claude_verdict,
        agreement: a.agreement, needs_human: a.needs_human,
        minimal_experiment_exists: a.minimal_experiment_exists,
        discriminable_from_prior: a.discriminable_from_prior, so_what_passes: a.so_what_passes,
        refined_scheme: a.refined_scheme, core_claim: a.core_claim, novelty_risk: a.novelty_risk,
        minimal_experiment: a.minimal_experiment, failure_modes: a.failure_modes || [],
        overall: a.audit_score?.overall, reasons: a.reasons || [],
        eligible: a.verdict === 'keep' || a.verdict === 'revise' || !!a.needs_human,
      }))
    : null;

  const cards = cardOk
    ? cardRaw.idea_cards.map((c) => ({ id: c.id, title: c.title, one_sentence: c.one_sentence }))
    : null;

  return { ok: true, run_id: runName(dir), gate, leverage, lateral, audits, cards, last_status: lastStatus };
}

// the set of valid explicit ids for a gate, from current state
function knownIds(st, gate) {
  if (gate === 1) return new Set((st.leverage || []).map((l) => l.id));
  if (gate === 2) return new Set((st.lateral?.schemes || []).map((s) => s.lateral_id));
  if (gate === 3) return new Set((st.audits || []).filter((a) => a.eligible).map((a) => a.audit_id));
  return new Set();
}

// ---------------------------------------------------------------- MCP channel
const mcp = new Server(
  { name: 'reframe-ui', version: '0.5.0' },
  {
    capabilities: { tools: {}, experimental: { 'claude/channel': {} } },
    instructions:
      `reframe-ui 是 Research Reframer 三道人工关卡的本地 UI 通道。用户在浏览器里的选择会以 ` +
      `<channel source="reframe-ui" gate="1|2|3" mode="explicit|nl|delegate" run_id="..." ids="..."> ` +
      `事件到达,tag 正文(content)是给你的明确中文指令。收到后严格照 content 执行,绝不重跑前序阶段:` +
      `Gate 1 = 用户选杠杆点(LP-###),你对所选杠杆点运行 lateral-generate 生成 03_lateral_reframes;` +
      `Gate 2 = 用户选横向方案(LR-###),你对其运行 vertical-audit(Codex+Claude 双裁、默认驳回)生成 04_vertical_audits;` +
      `Gate 3 = 用户选审计方案(VA-###),你对其运行 idea-card 生成 06_idea_cards(method_trace 与 VA/LR 逐字一致),跑校验器到退出码 0。` +
      `每个 gate 都要记录到 05_human_selection.md 与 decision_log.md。每次完成后必须调用 reply 工具回一句简短中文状态,否则 UI 不会推进。UI 地址 http://localhost:${PORT}。`,
  },
);

mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'reply',
      description: '把一句状态推送回 reframe-ui 浏览器面板(用户在浏览器看到),并让面板刷新到下一步。每完成一个 gate 必须调用。',
      inputSchema: {
        type: 'object',
        properties: { text: { type: 'string', description: '给用户看的简短中文状态' } },
        required: ['text'],
      },
    },
  ],
}));

mcp.setRequestHandler(CallToolRequestSchema, async (req) => {
  if (req.params.name === 'reply') {
    pushStatus(String(req.params.arguments?.text ?? ''));
    return { content: [{ type: 'text', text: 'sent' }] };
  }
  throw new Error('unknown tool: ' + req.params.name);
});

// push a human selection from the browser INTO the running Claude session
async function deliver(sel) {
  if (!RUN_DIR) { log('deliver skipped: no run dir'); return false; }
  const meta = { gate: String(sel.gate), mode: sel.mode, run_id: runName(RUN_DIR) };
  if (sel.ids?.length) meta.ids = sel.ids.join(',');
  try {
    await mcp.notification({
      method: 'notifications/claude/channel',
      params: { content: composeDirective(sel), meta },
    });
    log('delivered', JSON.stringify(meta));
    return true;
  } catch (e) {
    log('deliver failed:', e?.message || e);
    return false;
  }
}

function composeDirective(sel) {
  const where = `run=${runName(RUN_DIR)}`;
  const ids = (sel.ids || []).join(', ');
  if (sel.gate === 1) {
    if (sel.mode === 'explicit')
      return `[reframe-ui Gate 1 / ${where}] 用户在 UI 选定杠杆点:${ids}。请记录到 05_human_selection.md 与 decision_log.md,然后只对这些杠杆点运行 lateral-generate 生成 03_lateral_reframes.{json,md}(算子内化、判断延迟、保留 coverage_ledger),完成后调用 reply 工具回一句状态。不要重跑 system-map / leverage-scan。`;
    if (sel.mode === 'nl')
      return `[reframe-ui Gate 1 / ${where}] 用户用自然语言表达杠杆点选择意图:「${sel.intent}」。请从 02_leverage_points.json 里挑选合适的杠杆点(解释理由),记录选择,只对所选杠杆点跑 lateral-generate,完成后 reply 回状态。`;
    return `[reframe-ui Gate 1 / ${where}] 用户托管杠杆点选择:「${sel.intent || '按多样性代选 2-4 个互不重叠的高杠杆点'}」。请按 reframe-workshop 选择启发式挑选(说明理由),记录选择,跑 lateral-generate,完成后 reply 回状态。`;
  }
  if (sel.gate === 2) {
    if (sel.mode === 'explicit')
      return `[reframe-ui Gate 2 / ${where}] 用户选定要审计的横向方案:${ids}。请对这些方案运行 vertical-audit(Codex 外审 + Claude 自审,双裁、默认驳回)生成 04_vertical_audits.{json,md},追加记录到 05_human_selection.md 与 decision_log.md,完成后 reply 回状态。不要重跑前序阶段。`;
    if (sel.mode === 'nl')
      return `[reframe-ui Gate 2 / ${where}] 用户用自然语言表达横向方案选择意图:「${sel.intent}」。请从 03_lateral_reframes.json 里映射出对应方案(解释理由),对其跑 vertical-audit 双裁,完成后 reply 回状态。`;
    return `[reframe-ui Gate 2 / ${where}] 用户托管横向方案选择:「${sel.intent || '按多样性挑有意思的几个、跨不同杠杆点'}」。请代选并说明,跑 vertical-audit 双裁,完成后 reply 回状态。`;
  }
  if (sel.mode === 'explicit')
    return `[reframe-ui Gate 3 / ${where}] 用户选定要成卡的审计方案:${ids}。请对这些 VA 运行 idea-card 生成 06_idea_cards.{json,md}(method_trace 与 VA/LR 逐字一致;needs_human 的按人工 keep/revise 解决),追加记录,跑校验器到退出码 0,完成后 reply 回状态。不要重跑前序阶段。`;
  if (sel.mode === 'nl')
    return `[reframe-ui Gate 3 / ${where}] 用户用自然语言表达成卡意图:「${sel.intent}」。请从 04_vertical_audits.json 的存活/可救回审计里映射出对应 VA(解释理由),生成 idea 卡,跑校验,完成后 reply 回状态。`;
  return `[reframe-ui Gate 3 / ${where}] 用户托管成卡选择:「${sel.intent || '保留存活与可救回的、最可判别的几个'}」。请代选 VA 并说明,生成 idea 卡,跑校验,完成后 reply 回状态。`;
}

// ---------------------------------------------------------------- HTTP + SSE
const sseClients = new Set();
let lastStatus = null;
function pushStatus(text) {
  lastStatus = text;
  const data = `data: ${JSON.stringify({ type: 'status', text })}\n\n`;
  for (const res of sseClients) { try { res.write(data); } catch { /* client gone */ } }
  log('status ->', text);
}

const sendJSON = (res, obj, code = 200) => {
  const b = Buffer.from(JSON.stringify(obj, null, 2));
  res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': b.length });
  res.end(b);
};
const MAX_BODY = 64 * 1024; // cap /select bodies; free text reaches Claude's context
const readBody = (req) =>
  new Promise((resolve, reject) => {
    let d = '';
    let size = 0;
    let stop = false;
    req.on('data', (c) => {
      if (stop) return;
      size += c.length;
      if (size > MAX_BODY) { stop = true; reject(new Error('body too large')); return; }
      d += c;
    });
    req.on('end', () => { if (!stop) resolve(d); });
    req.on('error', reject);
  });

// Only accept browser requests from this machine (DNS-rebinding / local-page guard).
const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '::1', '[::1]', '']);
function localRequestOk(req) {
  const host = String(req.headers.host || '').replace(/:\d+$/, '').toLowerCase();
  if (!LOCAL_HOSTS.has(host)) return false;
  const origin = req.headers.origin;
  if (origin) {
    try { if (!LOCAL_HOSTS.has(new URL(origin).hostname.toLowerCase())) return false; }
    catch { return false; }
  }
  return true;
}

function serveUI(res) {
  const f = join(__dirname, 'ui.html');
  if (existsSync(f)) {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(readFileSync(f));
  }
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end('<!doctype html><meta charset="utf-8"><h1>reframe-ui</h1><p>ui.html 尚未构建。<code>/state</code> 已可用。</p>');
}

const httpServer = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://127.0.0.1:${PORT}`);
  try {
    if (req.method === 'GET' && url.pathname === '/') return serveUI(res);

    if (req.method === 'GET' && url.pathname === '/state') {
      const runParam = url.searchParams.get('run');
      if (runParam) {
        // Strict whitelist: a run name is a single path segment of safe chars.
        // basename() alone lets "." and ".." through (basename("..") === ".."),
        // so reject those explicitly before joining onto BASE.
        const safe = /^[A-Za-z0-9_-][A-Za-z0-9._-]*$/.test(runParam) &&
          runParam !== '.' && runParam !== '..' && runParam === basename(runParam);
        if (!safe) return sendJSON(res, { ok: false, error: 'invalid run name' }, 400);
        const cand = join(BASE, runParam, 'outputs');
        if (existsSync(cand)) RUN_DIR = cand;
      }
      return sendJSON(res, buildState());
    }

    if (req.method === 'GET' && url.pathname === '/runs') {
      let runs = [];
      try { runs = readdirSync(BASE).filter((n) => existsSync(join(BASE, n, 'outputs'))); } catch { /* none */ }
      return sendJSON(res, { base: BASE, active: runName(RUN_DIR), runs });
    }

    if (req.method === 'POST' && url.pathname === '/select') {
      if (!localRequestOk(req)) return sendJSON(res, { ok: false, error: 'cross-origin or non-local request rejected' }, 403);
      if (!String(req.headers['content-type'] || '').toLowerCase().includes('application/json'))
        return sendJSON(res, { ok: false, error: 'Content-Type must be application/json' }, 415);
      if (Number(req.headers['content-length'] || 0) > MAX_BODY)
        return sendJSON(res, { ok: false, error: 'request body too large (max 64KB)' }, 413);

      let raw;
      try { raw = await readBody(req); }
      catch { return sendJSON(res, { ok: false, error: 'request body too large (max 64KB)' }, 413); }
      let sel;
      try { sel = JSON.parse(raw); } catch { return sendJSON(res, { ok: false, error: 'bad json' }, 400); }

      // shape checks
      if (!sel || ![1, 2, 3].includes(sel.gate)) return sendJSON(res, { ok: false, error: 'gate must be 1, 2 or 3' }, 400);
      if (!['explicit', 'nl', 'delegate'].includes(sel.mode)) return sendJSON(res, { ok: false, error: 'bad mode' }, 400);

      // validate against the CURRENT run state: the run must be at the submitted
      // gate; explicit ids must carry the right prefix AND be valid/eligible;
      // nl/delegate must not carry ids and nl needs a non-empty intent.
      const st = buildState();
      if (st.ok === false) return sendJSON(res, { ok: false, error: 'no run state to select against' }, 409);
      if (st.gate !== sel.gate) return sendJSON(res, { ok: false, error: `run is at gate ${st.gate}, not ${sel.gate}` }, 409);

      if (sel.mode === 'explicit') {
        if (!(sel.ids?.length)) return sendJSON(res, { ok: false, error: 'explicit mode needs ids' }, 400);
        const prefix = GATE_PREFIX[sel.gate];
        const wrongPrefix = sel.ids.filter((id) => !String(id).startsWith(prefix));
        if (wrongPrefix.length) return sendJSON(res, { ok: false, error: `gate ${sel.gate} ids must start with ${prefix}: ${wrongPrefix.join(', ')}` }, 400);
        const known = knownIds(st, sel.gate);
        const unknown = sel.ids.filter((id) => !known.has(id));
        if (unknown.length) {
          const why = sel.gate === 3 ? 'unknown or not card-eligible (both judges rejected)' : 'unknown for this run';
          return sendJSON(res, { ok: false, error: `${why}: ${unknown.join(', ')}` }, 400);
        }
      } else {
        if (sel.ids?.length) return sendJSON(res, { ok: false, error: `${sel.mode} mode must not carry ids` }, 400);
        if (sel.mode === 'nl' && !String(sel.intent || '').trim()) return sendJSON(res, { ok: false, error: 'nl mode needs a non-empty intent' }, 400);
      }

      const ok = await deliver(sel);
      return sendJSON(res, { ok, delivered: ok ? sel : null }, ok ? 200 : 500);
    }

    if (req.method === 'GET' && url.pathname === '/events') {
      res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
      res.write(`data: ${JSON.stringify({ type: 'hello' })}\n\n`);
      sseClients.add(res);
      req.on('close', () => sseClients.delete(res));
      return;
    }

    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('not found');
  } catch (e) {
    log('http error:', e?.message || e);
    if (!res.headersSent) sendJSON(res, { ok: false, error: String(e?.message || e) }, 500);
  }
});

// ---------------------------------------------------------------- boot
await mcp.connect(new StdioServerTransport()).catch((e) => log('mcp connect error:', e?.message || e));
httpServer.on('error', (e) => {
  if (e?.code === 'EADDRINUSE') log(`port ${PORT} is already in use — set REFRAME_PORT to a free port and relaunch.`);
  else log('http server error:', e?.message || e);
  process.exitCode = 1;
});
httpServer.listen(PORT, '127.0.0.1', () => log(`listening http://127.0.0.1:${PORT}  | run=${RUN_DIR || '(none)'} | base=${BASE}`));
