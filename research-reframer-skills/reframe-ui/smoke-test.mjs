#!/usr/bin/env node
/*
 * smoke-test.mjs — dependency-free automated smoke test for the reframe-ui server (v0.5).
 *
 * Builds its OWN gate-3 fixture from the bundled example (copies the example
 * outputs into a temp run dir and removes 06_* so the run sits at Gate 3), so the
 * test is portable across clones / extracted zips and does not depend on test-runs/.
 * Set REFRAME_RUN_DIR to point at a real gate-3 run instead (must have a valid
 * 04_vertical_audits.json but no 06_*).
 *
 * It exercises the three-gate HTTP/SSE contract incl. validation: gate-state (409),
 * id prefix / existence / card-eligibility (400), nl/delegate id rules (400),
 * cross-origin (403), content-type (415), body cap (413), plus the happy path.
 *
 * Child stdout is PIPED — it is the MCP transport and must NOT pollute this test's
 * stdout. stderr is inherited so server [reframe-ui] logs are visible. node: builtins only.
 */
import { spawn } from 'node:child_process';
import { dirname, join, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { mkdtempSync, cpSync, rmSync, readdirSync, readFileSync, existsSync } from 'node:fs';
import http from 'node:http';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = 8766;
const BASE = `http://127.0.0.1:${PORT}`;

// ---- build (or reuse) a gate-3 fixture --------------------------------------
let TMP_BASE = null;
let RUN_DIR = process.env.REFRAME_RUN_DIR || null;
let BASE_DIR = process.env.REFRAME_BASE || null;
if (!RUN_DIR) {
  const example = join(__dirname, '..', 'examples', 'physmaster-three-gate', 'outputs');
  if (!existsSync(example)) {
    console.log('[FAIL] bundled example outputs not found at ' + example);
    process.exit(1);
  }
  TMP_BASE = mkdtempSync(join(tmpdir(), 'reframe-smoke-'));
  RUN_DIR = join(TMP_BASE, 'smoke-run', 'outputs');
  cpSync(example, RUN_DIR, { recursive: true });
  // drop 06_* so the run is at Gate 3 (04_* present, 06_* absent)
  for (const f of readdirSync(RUN_DIR)) if (f.startsWith('06_')) rmSync(join(RUN_DIR, f));
  BASE_DIR = TMP_BASE;
}
const RUN_NAME = basename(join(RUN_DIR, '..'));
const audDoc = JSON.parse(readFileSync(join(RUN_DIR, '04_vertical_audits.json'), 'utf8'));
const isEligible = (a) => a.verdict === 'keep' || a.verdict === 'revise' || !!a.needs_human;
const REAL_VA = (audDoc.audits || []).find(isEligible)?.audit_id;        // card-eligible
const REJ_VA = (audDoc.audits || []).find((a) => !isEligible(a))?.audit_id; // both-judges-reject
const REAL_LR = (audDoc.audits || [])[0]?.source_lateral_id;             // an LR id (wrong prefix for gate 3)

let passed = 0;
let failed = 0;
function check(name, ok, detail) {
  if (ok) { passed++; console.log(`[PASS] ${name}`); }
  else { failed++; console.log(`[FAIL] ${name}${detail ? ' — ' + detail : ''}`); }
}

function raw(method, path, body, headers = {}) {
  return new Promise((resolve) => {
    const data = body === undefined ? null : (typeof body === 'string' ? body : JSON.stringify(body));
    const h = { ...headers };
    if (data != null && !Object.keys(h).some((k) => k.toLowerCase() === 'content-type')) h['Content-Type'] = 'application/json';
    if (data != null && !Object.keys(h).some((k) => k.toLowerCase() === 'content-length')) h['Content-Length'] = Buffer.byteLength(data);
    const r = http.request(BASE + path, { method, headers: h, agent: false }, (res) => {
      let buf = ''; res.setEncoding('utf8');
      res.on('data', (c) => (buf += c));
      res.on('end', () => { let j = null; try { j = JSON.parse(buf); } catch { /* not json */ } resolve({ status: res.statusCode, json: j }); });
    });
    r.on('error', () => resolve({ status: 0, json: null }));
    if (data != null) r.write(data);
    r.end();
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function waitForSSE(path, predicate, timeoutMs) {
  return new Promise((resolve) => {
    const r = http.get(BASE + path, (res) => {
      let buf = '';
      const done = (val) => { try { r.destroy(); } catch {} resolve(val); };
      const timer = setTimeout(() => done(false), timeoutMs);
      res.setEncoding('utf8');
      res.on('data', (chunk) => {
        buf += chunk;
        let i;
        while ((i = buf.indexOf('\n')) >= 0) {
          const line = buf.slice(0, i);
          buf = buf.slice(i + 1);
          if (predicate(line)) { clearTimeout(timer); return done(true); }
        }
      });
      res.on('error', () => { clearTimeout(timer); done(false); });
    });
    r.on('error', () => resolve(false));
  });
}

const child = spawn(process.execPath, [join(__dirname, 'server.mjs')], {
  env: { ...process.env, REFRAME_PORT: String(PORT), REFRAME_RUN_DIR: RUN_DIR, ...(BASE_DIR ? { REFRAME_BASE: BASE_DIR } : {}) },
  stdio: ['ignore', 'pipe', 'inherit'],
});
child.stdout.on('data', () => { /* drain MCP transport, never forward */ });
child.on('error', (e) => { console.log('[FAIL] spawn server — ' + (e?.message || e)); cleanup(); process.exit(1); });

function cleanup() { if (TMP_BASE) { try { rmSync(TMP_BASE, { recursive: true, force: true }); } catch {} } }
function shutdown(code) {
  try { child.stdout?.removeAllListeners(); child.stdout?.destroy(); } catch {}
  try { child.kill(); } catch {}
  cleanup();
  setTimeout(() => process.exit(code), 100);
}

(async () => {
  const deadline = Date.now() + 5000;
  let up = false;
  while (Date.now() < deadline) {
    const r = await raw('GET', '/runs');
    if (r.status === 200) { up = true; break; }
    await sleep(150);
  }
  check('server starts and answers GET /runs within 5s', up);
  if (!up) return shutdown(1);

  // 1) GET /runs includes the fixture run
  {
    const r = await raw('GET', '/runs');
    const ok = r.status === 200 && r.json && Array.isArray(r.json.runs) && r.json.runs.includes(RUN_NAME);
    check(`GET /runs returns runs[] including "${RUN_NAME}"`, ok, JSON.stringify(r.json?.runs));
  }

  // 2) GET /state -> ok:true, gate 3, audits with core_claim + eligible flag
  {
    const r = await raw('GET', '/state');
    const s = r.json || {};
    const auds = s.audits || [];
    const a0 = auds[0] || {};
    const ok = r.status === 200 && s.ok === true && s.gate === 3 && auds.length > 0 &&
      typeof a0.core_claim === 'string' && typeof a0.eligible === 'boolean' && 'verdict' in a0;
    check('GET /state ok:true, gate 3, audits with core_claim/verdict/eligible', ok,
      `gate=${s.gate} audits=${auds.length} core_claim=${typeof a0.core_claim} eligible=${typeof a0.eligible}`);
  }

  // 3) POST /select {gate:4} -> 400 (gate must be 1/2/3)
  {
    const r = await raw('POST', '/select', { gate: 4, mode: 'explicit', ids: [REAL_VA] });
    check('POST /select {gate:4} -> HTTP 400', r.status === 400, `status=${r.status}`);
  }

  // 4) POST /select {gate:3, explicit, ids:[]} -> 400 (explicit needs ids)
  {
    const r = await raw('POST', '/select', { gate: 3, mode: 'explicit', ids: [] });
    check('POST /select gate:3 explicit ids:[] -> HTTP 400', r.status === 400, `status=${r.status}`);
  }

  // 5) POST /select {gate:1} while run is at gate 3 -> 409 (gate-state mismatch)
  {
    const r = await raw('POST', '/select', { gate: 1, mode: 'explicit', ids: ['LP-001'] });
    check('POST /select gate:1 while run at gate 3 -> HTTP 409', r.status === 409, `status=${r.status}`);
  }

  // 6) POST /select gate:3 explicit with an LR id -> 400 (wrong prefix)
  {
    const r = await raw('POST', '/select', { gate: 3, mode: 'explicit', ids: [REAL_LR] });
    check('POST /select gate:3 explicit LR id -> HTTP 400 (wrong prefix)', r.status === 400, `status=${r.status} id=${REAL_LR}`);
  }

  // 7) POST /select gate:3 explicit with a non-existent VA id -> 400
  {
    const r = await raw('POST', '/select', { gate: 3, mode: 'explicit', ids: ['VA-99999'] });
    check('POST /select gate:3 explicit unknown VA id -> HTTP 400', r.status === 400, `status=${r.status}`);
  }

  // 8) POST /select gate:3 explicit with a both-judges-rejected VA -> 400 (not card-eligible)
  if (REJ_VA) {
    const r = await raw('POST', '/select', { gate: 3, mode: 'explicit', ids: [REJ_VA] });
    check('POST /select gate:3 explicit rejected VA -> HTTP 400 (not eligible)', r.status === 400, `status=${r.status} id=${REJ_VA}`);
  } else {
    check('fixture has a both-rejected VA to test eligibility', false, 'no rejected audit in fixture');
  }

  // 9) POST /select gate:3 nl carrying ids -> 400
  {
    const r = await raw('POST', '/select', { gate: 3, mode: 'nl', ids: [REAL_VA], intent: 'x' });
    check('POST /select gate:3 nl with ids -> HTTP 400', r.status === 400, `status=${r.status}`);
  }

  // 10) POST /select gate:3 nl with empty intent -> 400
  {
    const r = await raw('POST', '/select', { gate: 3, mode: 'nl', ids: [], intent: '' });
    check('POST /select gate:3 nl empty intent -> HTTP 400', r.status === 400, `status=${r.status}`);
  }

  // 11) cross-origin POST -> 403
  {
    const r = await raw('POST', '/select', { gate: 3, mode: 'explicit', ids: [REAL_VA] }, { Origin: 'http://evil.example' });
    check('POST /select with cross-origin Origin -> HTTP 403', r.status === 403, `status=${r.status}`);
  }

  // 12) non-JSON content-type -> 415
  {
    const r = await raw('POST', '/select', 'gate=3', { 'Content-Type': 'text/plain' });
    check('POST /select non-JSON Content-Type -> HTTP 415', r.status === 415, `status=${r.status}`);
  }

  // 13) oversized body -> 413
  {
    const r = await raw('POST', '/select', { gate: 3, mode: 'delegate', intent: 'x'.repeat(70 * 1024) });
    check('POST /select oversized body -> HTTP 413', r.status === 413, `status=${r.status}`);
  }

  // 14) valid gate-3 explicit body (card-eligible VA) -> {ok:true}
  {
    const r = await raw('POST', '/select', { gate: 3, mode: 'explicit', ids: [REAL_VA], intent: '' });
    const ok = r.status === 200 && r.json && r.json.ok === true;
    check('POST /select valid gate-3 explicit -> {ok:true}', ok, `status=${r.status} ${JSON.stringify(r.json)}`);
  }

  // 15) GET /events emits a hello line within ~2s
  {
    const ok = await waitForSSE('/events', (line) => line.startsWith('data:') && line.includes('hello'), 2000);
    check('GET /events emits data: line containing "hello" within 2s', ok);
  }

  console.log(`\n${passed} passed, ${failed} failed`);
  shutdown(failed > 0 ? 1 : 0);
})().catch((e) => {
  console.log('[FAIL] unexpected error — ' + (e?.message || e));
  shutdown(1);
});
