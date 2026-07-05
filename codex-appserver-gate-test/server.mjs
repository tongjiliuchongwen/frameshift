import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { access, mkdir, readFile, stat, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const THREAD_ID = process.env.CODEX_THREAD_ID;
const WORKSPACE = process.env.GATE_WORKSPACE || resolve(HERE, "..");
const HTTP_PORT = Number(process.env.GATE_HTTP_PORT || 8787);
const APP_PORT = Number(process.env.CODEX_APPSERVER_PORT || 4517);
const APP_URL = `ws://127.0.0.1:${APP_PORT}`;
const READY_URL = `http://127.0.0.1:${APP_PORT}/readyz`;
const DEFAULT_RUN_DIR = resolve(HERE, "..", "research-reframer-skills-codex-v0.7-diagnostic-feedback-search", "examples", "physmaster-three-gate");
const RUN_DIR = process.env.REFRAME_RUN_DIR || DEFAULT_RUN_DIR;
const OUTPUTS_DIR = join(RUN_DIR, "outputs");
const STATUS_PATH = join(OUTPUTS_DIR, ".gate_status.json");
const CURRENT_TURN_TIMEOUT_MS = Number(process.env.GATE_CURRENT_TURN_TIMEOUT_MS || 10 * 60 * 1000);
const BUSY_STATES = new Set([
  "connecting",
  "reading_thread",
  "resuming_thread",
  "starting_turn",
  "recording_selection",
  "agent_running",
]);
const ACTIVE_TURN_STATES = new Set([
  "active",
  "inProgress",
  "pending",
  "queued",
  "running",
]);

const RECOMMENDED_BY_GATE = {
  1: ["LP-003", "LP-004", "LP-006", "LP-002"],
  2: ["LR-001", "LR-005", "LR-009", "LR-013"],
  3: ["VA-002", "VA-003"],
};

if (!THREAD_ID) {
  console.error("CODEX_THREAD_ID is required.");
  process.exit(1);
}

let appServerProc = null;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchOk(url) {
  try {
    const res = await fetch(url);
    return res.ok;
  } catch {
    return false;
  }
}

async function fileExists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function readJson(path) {
  return JSON.parse(await readFile(path, "utf8"));
}

async function readJsonIfExists(path, fallback) {
  try {
    return await readJson(path);
  } catch {
    return fallback;
  }
}

async function writeJson(path, value) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function fileInfo(path) {
  try {
    const info = await stat(path);
    return {
      exists: true,
      size: info.size,
      mtime: info.mtime.toISOString(),
    };
  } catch {
    return {
      exists: false,
      size: null,
      mtime: null,
    };
  }
}

function runId() {
  return RUN_DIR.split(/[\\/]/).filter(Boolean).at(-1) || "research-reframer-run";
}

function artifactName(path) {
  return String(path || "").split(/[\\/]/).filter(Boolean).at(-1) || "";
}

async function readGateStatus() {
  return await readJsonIfExists(STATUS_PATH, null);
}

async function writeGateStatus(patch) {
  const previous = (await readGateStatus()) || {};
  const now = new Date().toISOString();
  const next = {
    schema_version: "1.0",
    run_id: runId(),
    updated_at: now,
    ...previous,
    ...patch,
    updated_at: now,
  };
  await writeJson(STATUS_PATH, next);
  return next;
}

async function ensureAppServer() {
  if (await fetchOk(READY_URL)) return;

  if (!appServerProc) {
    const command = `codex app-server --listen ws://127.0.0.1:${APP_PORT}`;
    appServerProc = spawn("cmd.exe", ["/d", "/s", "/c", command], {
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });
    appServerProc.stdout.on("data", (chunk) => console.log(`[app-server] ${chunk}`.trim()));
    appServerProc.stderr.on("data", (chunk) => console.error(`[app-server] ${chunk}`.trim()));
    appServerProc.on("exit", (code, signal) => {
      console.log(`[app-server] exited code=${code} signal=${signal}`);
      appServerProc = null;
    });
  }

  const started = Date.now();
  while (Date.now() - started < 15000) {
    if (await fetchOk(READY_URL)) return;
    await sleep(250);
  }
  throw new Error(`app-server did not become ready at ${READY_URL}`);
}

function rpcClient() {
  const ws = new WebSocket(APP_URL);
  let nextId = 1;
  const pending = new Map();
  const notifications = [];

  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(`${msg.error.code || ""} ${msg.error.message || JSON.stringify(msg.error)}`));
      else resolve(msg.result);
      return;
    }
    if (msg.method) notifications.push(msg);
  });

  function request(method, params, timeoutMs = 60000) {
    const id = nextId++;
    ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
      setTimeout(() => {
        if (pending.has(id)) {
          pending.delete(id);
          reject(new Error(`timeout waiting for ${method}`));
        }
      }, timeoutMs);
    });
  }

  function notify(method, params = {}) {
    ws.send(JSON.stringify({ method, params }));
  }

  return new Promise((resolve, reject) => {
    ws.addEventListener("open", () => resolve({ ws, request, notify, notifications }));
    ws.addEventListener("error", () => reject(new Error("WebSocket connection failed")));
  });
}

async function openRpcClient(name) {
  await ensureAppServer();
  const client = await rpcClient();
  const init = await client.request("initialize", {
    clientInfo: {
      name,
      title: "Research Reframer Gate",
      version: "0.3.0",
    },
    capabilities: { experimentalApi: true },
  });
  client.notify("initialized");
  return { ...client, init };
}

function selectionPrompt(ids, gateNumber) {
  const selected = ids.join(", ");
  if (gateNumber === 1) {
    return [
      "<codex_gate_selection>",
      "  <workflow>research-reframer</workflow>",
      "  <gate>1</gate>",
      `  <run_dir>${RUN_DIR}</run_dir>`,
      `  <selected_ids>${selected}</selected_ids>`,
      "  <source>codex-appserver-gate-test</source>",
      "</codex_gate_selection>",
      "",
      "继续 Research Reframer Codex workflow：",
      `- 使用 run_dir: ${RUN_DIR}`,
      `- Gate 1 用户在网页中选择了: ${selected}`,
      "- 不要重跑 01_system_map.json 或 02_leverage_points.json。",
      "- 记录 Gate 1 到 outputs\\05_human_selection.md、outputs\\05_human_selection.json 和 outputs\\decision_log.md。",
      "- 保留 sidecar 已写入的 outputs\\05_gate_cards.json；不要删除卡片快照。",
      "- 只生成 03_lateral_reframes.json 和 03_lateral_reframes.md。",
      "- 后续面向用户的 Gate 展示必须用中文轻量选择卡：短标题 + 旧→新/方案/风险，不要原样摊开 JSON 字段。",
      "- Windows UTF-8 约束：不要用 PowerShell here-string 管道写中文，例如 @'...'@ | python - 或 @'...'@ | node；也不要用默认 Set-Content/Out-File。它会把中文替换成问号。用 apply_patch 或明确 UTF-8 的文件写入方式，写完必须检查没有连续问号、Unicode replacement character 或 mojibake。",
      "- 生成完成后停在 Gate 2，并使用 App Server 网页 Gate。",
    ].join("\n");
  }

  if (gateNumber === 2) {
    return [
      "<codex_gate_selection>",
      "  <workflow>research-reframer</workflow>",
      "  <gate>2</gate>",
      `  <run_dir>${RUN_DIR}</run_dir>`,
      `  <selected_ids>${selected}</selected_ids>`,
      "  <source>codex-appserver-gate-test</source>",
      "</codex_gate_selection>",
      "",
      "继续 Research Reframer Codex workflow：",
      `- 使用 run_dir: ${RUN_DIR}`,
      `- Gate 2 用户在网页中选择了: ${selected}`,
      "- 不要重跑 01_system_map.json、02_leverage_points.json 或 03_lateral_reframes.json。",
      "- 记录 Gate 2 到 outputs\\05_human_selection.md、outputs\\05_human_selection.json 和 outputs\\decision_log.md。",
      "- 保留 sidecar 已写入的 outputs\\05_gate_cards.json；不要删除卡片快照。",
      "- 只生成 04_vertical_audits.json 和 04_vertical_audits.md。",
      "- 后续面向用户的 Gate 展示必须用中文轻量选择卡：保留下来的核心 / 最小实验 / 最大风险，不要展示完整 audit。",
      "- Windows UTF-8 约束：不要用 PowerShell here-string 管道写中文，例如 @'...'@ | python - 或 @'...'@ | node；也不要用默认 Set-Content/Out-File。它会把中文替换成问号。用 apply_patch 或明确 UTF-8 的文件写入方式，写完必须检查没有连续问号、Unicode replacement character 或 mojibake。",
      "- 生成完成后停在 Gate 3，并使用 App Server 网页 Gate。",
    ].join("\n");
  }

  if (gateNumber === 3) {
    return [
      "<codex_gate_selection>",
      "  <workflow>research-reframer</workflow>",
      "  <gate>3</gate>",
      `  <run_dir>${RUN_DIR}</run_dir>`,
      `  <selected_ids>${selected}</selected_ids>`,
      "  <source>codex-appserver-gate-test</source>",
      "</codex_gate_selection>",
      "",
      "继续 Research Reframer Codex workflow：",
      `- 使用 run_dir: ${RUN_DIR}`,
      `- Gate 3 用户在网页中选择了: ${selected}`,
      "- 不要重跑前序 artifacts。",
      "- 记录 Gate 3 到 outputs\\05_human_selection.md、outputs\\05_human_selection.json 和 outputs\\decision_log.md。",
      "- 保留 sidecar 已写入的 outputs\\05_gate_cards.json；不要删除卡片快照。",
      "- 生成 06_idea_cards.json、06_idea_cards.md、reframe_report.md，并运行 validator。",
      "- 最终报告可以保留必要英文术语，但解释性文字应优先中文。",
      "- Windows UTF-8 约束：不要用 PowerShell here-string 管道写中文，例如 @'...'@ | python - 或 @'...'@ | node；也不要用默认 Set-Content/Out-File。它会把中文替换成问号。用 apply_patch 或明确 UTF-8 的文件写入方式，写完必须检查没有连续问号、Unicode replacement character 或 mojibake。",
    ].join("\n");
  }

  throw new Error(`unsupported gate number: ${gateNumber}`);
}

function expectedArtifactForGate(gateNumber) {
  if (gateNumber === 1) return `${OUTPUTS_DIR}\\03_lateral_reframes.json`;
  if (gateNumber === 2) return `${OUTPUTS_DIR}\\04_vertical_audits.json`;
  if (gateNumber === 3) return `${OUTPUTS_DIR}\\06_idea_cards.json`;
  return null;
}

function isBusyState(state) {
  return BUSY_STATES.has(String(state || ""));
}

function findTurnStatus(thread, turnId) {
  if (!turnId) return null;
  const turns = Array.isArray(thread?.turns) ? thread.turns : [];
  const turn = turns.find((item) => item?.id === turnId);
  return turn?.status || null;
}

function findActiveTurns(thread) {
  const turns = Array.isArray(thread?.turns) ? thread.turns : [];
  return turns
    .filter((turn) => ACTIVE_TURN_STATES.has(String(turn?.status || "")))
    .map((turn) => ({
      id: turn?.id || null,
      status: turn?.status || null,
    }));
}

async function waitForTurnVisible(request, threadId, turnId, timeoutMs = 10000) {
  if (!turnId) return { visible: false, status: null };
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const read = await request("thread/read", { threadId, includeTurns: true }, 15000);
    const status = findTurnStatus(read.thread, turnId);
    if (status) return { visible: true, status };
    await sleep(500);
  }
  return { visible: false, status: null };
}

async function waitForGateCompletion(gateNumber, notifications, timeoutMs, onTick = null, turnInfo = {}) {
  const expected = expectedArtifactForGate(gateNumber);
  const started = Date.now();
  let lastTick = 0;
  let lastThreadPoll = 0;
  let artifactReady = false;
  while (Date.now() - started < timeoutMs) {
    if (onTick && Date.now() - lastTick > 2000) {
      lastTick = Date.now();
      await onTick({
        elapsed_ms: Date.now() - started,
        expected_artifact: expected,
        artifact_ready: artifactReady,
      });
    }
    const failed = notifications.find((n) =>
      ["turn/failed", "turn/failure", "task_failed", "task/failed", "error"].includes(n.method)
    );
    if (failed) return { completed: false, failed, timedOut: false, artifactReady: false };
    if (expected && !artifactReady && (await fileExists(expected))) artifactReady = true;
    const completed = notifications.find((n) =>
      ["turn/completed", "turn/complete", "task_complete", "task/completed"].includes(n.method)
    );
    if (completed) {
      if (artifactReady) return { completed: true, failed: null, timedOut: false, artifactReady: true };
      return {
        completed: false,
        failed: { method: "artifact/missing_after_turn_complete", expected },
        timedOut: false,
        artifactReady: false,
      };
    }
    if (turnInfo.request && turnInfo.threadId && turnInfo.turnId && Date.now() - lastThreadPoll > 2500) {
      lastThreadPoll = Date.now();
      try {
        const read = await turnInfo.request(
          "thread/read",
          { threadId: turnInfo.threadId, includeTurns: true },
          15000
        );
        const turnStatus = findTurnStatus(read.thread, turnInfo.turnId);
        if (turnStatus === "completed") {
          if (artifactReady) return { completed: true, failed: null, timedOut: false, artifactReady: true };
          return {
            completed: false,
            failed: { method: "artifact/missing_after_turn_complete", expected },
            timedOut: false,
            artifactReady: false,
          };
        }
        if (["failed", "failure", "cancelled", "canceled"].includes(String(turnStatus))) {
          return {
            completed: false,
            failed: { method: "turn/status", status: turnStatus },
            timedOut: false,
            artifactReady,
          };
        }
      } catch {
        // Keep polling filesystem and notifications; transient app-server reads should not fail the gate turn.
      }
    }
    await sleep(750);
  }
  return { completed: false, failed: null, timedOut: true, artifactReady };
}

function textFromItem(item) {
  if (!item) return null;
  if (typeof item.text === "string") return item.text;
  if (Array.isArray(item.content)) return item.content.map((part) => part?.text || "").join("");
  return null;
}

function lastAgentMessage(thread) {
  const turns = Array.isArray(thread?.turns) ? thread.turns : [];
  for (let i = turns.length - 1; i >= 0; i--) {
    const items = Array.isArray(turns[i]?.items) ? turns[i].items : [];
    for (let j = items.length - 1; j >= 0; j--) {
      const item = items[j];
      if (item?.type === "agentMessage") return textFromItem(item);
    }
  }
  return null;
}

async function probeCurrentThread() {
  const client = await openRpcClient("gate-probe");
  const { ws, request, init } = client;
  try {
    const read = await request("thread/read", { threadId: THREAD_ID, includeTurns: true });
    const gate = await loadGateOptions();
    return {
      ok: true,
      appServer: init.userAgent,
      threadId: read.thread?.id || THREAD_ID,
      turns: read.thread?.turns?.length ?? null,
      title: read.thread?.title ?? null,
      gate: gate.gate,
      optionCount: gate.options.length,
    };
  } finally {
    ws.close();
  }
}

async function sendToCurrentThread(ids, gateNumber) {
  const expected = expectedArtifactForGate(gateNumber);
  await writeGateStatus({
    gate: gateNumber,
    state: "connecting",
    selected_ids: ids,
    expected_artifact: expected,
    expected_artifact_name: artifactName(expected),
    started_at: new Date().toISOString(),
    message: `正在连接 Codex app-server，准备发送 Gate ${gateNumber} 选择。`,
  });
  const client = await openRpcClient("gate-current-thread");
  const { ws, request, notifications, init } = client;
  try {
    await writeGateStatus({
      gate: gateNumber,
      state: "reading_thread",
      selected_ids: ids,
      expected_artifact: expected,
      expected_artifact_name: artifactName(expected),
      message: "app-server 已连接，正在读取目标 Codex thread。",
    });
    const read = await request("thread/read", { threadId: THREAD_ID, includeTurns: true });
    const activeTurns = findActiveTurns(read.thread);
    if (activeTurns.length) {
      const summary = activeTurns.map((turn) => `${turn.id || "unknown"}:${turn.status || "unknown"}`).join(", ");
      await writeGateStatus({
        gate: gateNumber,
        state: "failed",
        selected_ids: ids,
        expected_artifact: expected,
        expected_artifact_name: artifactName(expected),
        turns_before_start: read.thread?.turns?.length ?? null,
        failed: { method: "thread/active_turns", active_turns: activeTurns },
        message: `目标 Codex thread 仍有未完成 turn：${summary}。不要重复点击；先处理或等待该 turn 结束。`,
      });
      throw new Error(`target Codex thread has active turn(s): ${summary}`);
    }
    try {
      await writeGateStatus({
        gate: gateNumber,
        state: "resuming_thread",
        selected_ids: ids,
        expected_artifact: expected,
        expected_artifact_name: artifactName(expected),
        turns_before_start: read.thread?.turns?.length ?? null,
        message: "目标 thread 可读取，正在 resume 当前 Codex 线程。",
      });
      await request("thread/resume", { threadId: THREAD_ID, cwd: WORKSPACE }, 15000);
    } catch (err) {
      await writeGateStatus({
        gate: gateNumber,
        state: "failed",
        selected_ids: ids,
        expected_artifact: expected,
        expected_artifact_name: artifactName(expected),
        message: `无法 resume 当前 Codex 线程：${err.message || err}`,
      });
      throw new Error(
        `current Desktop thread is readable but could not be resumed within 15s; wait until the active Codex turn is idle, then click again. Detail: ${err.message || err}`
      );
    }

    await writeGateStatus({
      gate: gateNumber,
      state: "starting_turn",
      selected_ids: ids,
      expected_artifact: expected,
      expected_artifact_name: artifactName(expected),
      message: "正在向当前 Codex 线程发送 Gate selection prompt。",
    });
    const start = await request("turn/start", {
      threadId: THREAD_ID,
      input: [{ type: "text", text: selectionPrompt(ids, gateNumber) }],
      cwd: WORKSPACE,
    });
    const startTurnId = start.turn?.id || null;
    if (!startTurnId) {
      await writeGateStatus({
        gate: gateNumber,
        state: "failed",
        selected_ids: ids,
        expected_artifact: expected,
        expected_artifact_name: artifactName(expected),
        failed: { method: "turn/start", reason: "missing_turn_id", result: start || null },
        message: "turn/start 没有返回 turn id，未启动可追踪的 Codex turn。",
      });
      throw new Error("turn/start did not return a turn id");
    }
    const visible = await waitForTurnVisible(request, THREAD_ID, startTurnId, 10000);
    if (!visible.visible) {
      await writeGateStatus({
        gate: gateNumber,
        state: "failed",
        selected_ids: ids,
        expected_artifact: expected,
        expected_artifact_name: artifactName(expected),
        turn_id: startTurnId,
        failed: { method: "turn/not_visible_after_start", turn_id: startTurnId },
        message: `turn/start 返回了 ${startTurnId}，但 thread/read 中看不到该 turn。已停止等待，避免空等 artifact。`,
      });
      throw new Error(`turn/start returned ${startTurnId}, but thread/read did not show that turn`);
    }
    if (["failed", "failure", "cancelled", "canceled"].includes(String(visible.status))) {
      await writeGateStatus({
        gate: gateNumber,
        state: "failed",
        selected_ids: ids,
        expected_artifact: expected,
        expected_artifact_name: artifactName(expected),
        turn_id: startTurnId,
        failed: { method: "turn/status_after_start", status: visible.status },
        message: `Codex turn 启动后立即进入 ${visible.status} 状态。`,
      });
      throw new Error(`turn ${startTurnId} entered ${visible.status} immediately after start`);
    }
    await writeGateStatus({
      gate: gateNumber,
      state: "agent_running",
      selected_ids: ids,
      expected_artifact: expected,
      expected_artifact_name: artifactName(expected),
      turn_id: startTurnId,
      message: `Codex 正在生成 ${artifactName(expected)}，可以刷新页面查看状态。`,
    });
    const status = await waitForGateCompletion(gateNumber, notifications, CURRENT_TURN_TIMEOUT_MS, async (tick) => {
      await writeGateStatus({
        gate: gateNumber,
        state: "agent_running",
        selected_ids: ids,
        expected_artifact: expected,
        expected_artifact_name: artifactName(expected),
        turn_id: startTurnId,
        elapsed_ms: tick.elapsed_ms,
        last_heartbeat: new Date().toISOString(),
        artifact_ready: Boolean(tick.artifact_ready),
        message: tick.artifact_ready
          ? `${artifactName(expected)} 已出现，正在等待 Codex turn 完成。`
          : `Codex 正在生成 ${artifactName(expected)}，已等待 ${Math.round(tick.elapsed_ms / 1000)} 秒。`,
      });
    }, { request, threadId: THREAD_ID, turnId: startTurnId });
    await writeGateStatus({
      gate: gateNumber,
      state: status.completed ? "artifact_ready" : status.timedOut ? "timed_out" : "failed",
      selected_ids: ids,
      expected_artifact: expected,
      expected_artifact_name: artifactName(expected),
      turn_id: startTurnId,
      completed: status.completed,
      timed_out: status.timedOut,
      failed: status.failed || null,
      message: status.completed
        ? `${artifactName(expected)} 已生成，刷新后进入下一 Gate。`
        : status.timedOut
          ? `等待 ${artifactName(expected)} 超时。不要重复点击，先检查线程是否仍在运行。`
          : `Codex turn 失败，未生成 ${artifactName(expected)}。`,
    });
    const readAfter = status.completed
      ? await request("thread/read", { threadId: THREAD_ID, includeTurns: true }, 60000)
      : null;

    return {
      ok: true,
      mode: "current",
      gate: gateNumber,
      appServer: init.userAgent,
      threadId: THREAD_ID,
      turnsBeforeStart: read.thread?.turns?.length ?? null,
      turnId: startTurnId,
      completed: status.completed,
      timedOut: status.timedOut,
      failed: status.failed,
      agentMessage: lastAgentMessage(readAfter?.thread),
      note: status.completed
        ? "Turn completed in the current Codex Desktop thread."
        : "Turn started but did not complete before timeout. Do not send a manual chat message while a gate turn is running.",
      notifications: notifications.map((n) => n.method).slice(-20),
    };
  } finally {
    ws.close();
  }
}

function safeIds(value) {
  if (!Array.isArray(value)) return [];
  return value.map(String).map((s) => s.trim()).filter(Boolean).slice(0, 20);
}

async function detectGateNumber() {
  if (await fileExists(`${OUTPUTS_DIR}\\06_idea_cards.json`)) return 4;
  if (await fileExists(`${OUTPUTS_DIR}\\04_vertical_audits.json`)) return 3;
  if (await fileExists(`${OUTPUTS_DIR}\\03_lateral_reframes.json`)) return 2;
  return 1;
}

function recommendedFor(gateNumber, availableIds) {
  const fromEnv = process.env[`GATE${gateNumber}_RECOMMENDED_IDS`];
  const ids = (fromEnv ? fromEnv.split(",") : RECOMMENDED_BY_GATE[gateNumber] || [])
    .map((id) => id.trim())
    .filter(Boolean);
  const available = new Set(availableIds);
  return ids.filter((id) => available.has(id));
}

function compactText(value, max = 180) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
}

function rows(...entries) {
  return entries
    .filter((entry) => entry && entry.text)
    .map((entry) => ({ label: entry.label, text: compactText(entry.text, entry.max || 180) }));
}

function cardSnapshot(option) {
  return {
    id: option.id,
    title: option.title,
    meta: option.meta || "",
    recommended: Boolean(option.recommended),
    summary_rows: option.summaryRows || [],
    detail_rows: option.detailRows || [],
  };
}

function gate3SelectionEntry(gate, id) {
  const option = (gate.options || []).find((item) => item.id === id) || {};
  return {
    audit_id: id,
    resolution: option.resolution || "selected_for_card",
  };
}

async function recordGateSelection(gate, ids) {
  const now = new Date().toISOString();
  const key = `gate${gate.gate}`;

  const cardsPath = `${OUTPUTS_DIR}\\05_gate_cards.json`;
  const cardsDoc = await readJsonIfExists(cardsPath, {
    schema_version: "2.0",
    run_id: RUN_DIR.split(/[\\/]/).filter(Boolean).at(-1) || "research-reframer-run",
    recorded_by: "codex-appserver-gate-test",
    gates: {},
  });
  cardsDoc.gates[key] = {
    display_language: "zh-CN",
    source_artifact: gate.optionsPath,
    task: gate.task,
    selection_guidance: gate.selectionGuidance,
    recommended_ids: gate.recommendedIds || [],
    selected_ids: ids,
    recorded_at: now,
    cards: (gate.options || []).map(cardSnapshot),
  };
  await writeJson(cardsPath, cardsDoc);

  const selectionPath = `${OUTPUTS_DIR}\\05_human_selection.json`;
  const selectionDoc = await readJsonIfExists(selectionPath, {
    schema_version: "2.0",
    run_id: RUN_DIR.split(/[\\/]/).filter(Boolean).at(-1) || "research-reframer-run",
    recorded_by: "codex-appserver-gate-test",
    gates: {},
  });
  const common = {
    mode: "explicit",
    recommended_ids: gate.recommendedIds || [],
    recorded_at: now,
    source: "codex-appserver-gate-test",
  };
  if (gate.gate === 1) {
    selectionDoc.gates[key] = {
      ...common,
      selected: ids,
      not_selected_recommended: (gate.recommendedIds || []).filter((id) => !ids.includes(id)),
    };
  } else if (gate.gate === 2) {
    selectionDoc.gates[key] = {
      ...common,
      selected: ids,
      not_selected_recommended: (gate.recommendedIds || []).filter((id) => !ids.includes(id)),
      wildcard_prompt_shown: Boolean(gate.wildcardPromptShown),
      wildcard_added: Boolean(gate.wildcardAdded),
    };
  } else if (gate.gate === 3) {
    selectionDoc.gates[key] = {
      ...common,
      selected: ids.map((id) => gate3SelectionEntry(gate, id)),
      rejected_drawer_locked: gate.rejectedIds || [],
    };
  }
  await writeJson(selectionPath, selectionDoc);
}

async function loadGateOptions() {
  const gateNumber = await detectGateNumber();
  if (gateNumber === 4) return loadCompleteState();
  if (gateNumber === 1) return loadGate1Options();
  if (gateNumber === 2) return loadGate2Options();
  return loadGate3Options();
}

async function loadHumanSelection() {
  return await readJsonIfExists(`${OUTPUTS_DIR}\\05_human_selection.json`, { gates: {} });
}

async function buildProgressState(gate) {
  const status = await readGateStatus();
  const selection = await loadHumanSelection();
  const gateFromStatus = Number(status?.gate || 0);
  const expectedFromStatus = status?.expected_artifact || expectedArtifactForGate(gate.gate);
  const expectedInfo = expectedFromStatus ? await fileInfo(expectedFromStatus) : { exists: false };
  const activeStatusApplies = gateFromStatus === gate.gate || (gateFromStatus && gateFromStatus < gate.gate && status?.state);
  let state = activeStatusApplies ? status.state : "idle";
  let message = activeStatusApplies ? status.message : `当前是 Gate ${gate.gate}：${gate.task}`;
  if (
    gateFromStatus &&
    gateFromStatus < gate.gate &&
    ["artifact_ready", "timed_out", "failed"].includes(String(status?.state))
  ) {
    state = "idle";
    message = `上一次 Gate ${gateFromStatus} 已完成，现在进入 Gate ${gate.gate}。`;
  } else if (status?.state === "agent_running" && expectedInfo.exists) {
    state = "agent_running";
    message = `${artifactName(expectedFromStatus)} 已出现，正在等待 Codex turn 完成。`;
  }

  const files = {
    source: await fileInfo(join(RUN_DIR, "source_extracted.txt")),
    diagnosis: await fileInfo(`${OUTPUTS_DIR}\\00_diagnosis.json`),
    systemMap: await fileInfo(`${OUTPUTS_DIR}\\01_system_map.json`),
    leverage: await fileInfo(`${OUTPUTS_DIR}\\02_leverage_points.json`),
    lateral: await fileInfo(`${OUTPUTS_DIR}\\03_lateral_reframes.json`),
    audits: await fileInfo(`${OUTPUTS_DIR}\\04_vertical_audits.json`),
    ideas: await fileInfo(`${OUTPUTS_DIR}\\06_idea_cards.json`),
  };
  if (gate.gate === 4 && files.ideas.exists) {
    state = "complete";
    message = "流程已完成。最终 Idea Cards 已生成并在下方展开。";
  }
  const gates = selection.gates || {};
  const stages = [
    { key: "source", label: "PDF 解析", detail: "source_extracted.txt", status: files.source.exists ? "done" : "pending" },
    { key: "diagnosis", label: "00 诊断", detail: "00_diagnosis.json", status: files.diagnosis.exists ? "done" : "pending" },
    { key: "system", label: "01 系统图", detail: "01_system_map.json", status: files.systemMap.exists ? "done" : "pending" },
    { key: "leverage", label: "02 杠杆点", detail: "02_leverage_points.json", status: files.leverage.exists ? "done" : "pending" },
    { key: "gate1", label: "Gate 1", detail: (gates.gate1?.selected || []).join(", ") || "选择 LP", status: gates.gate1 ? "done" : gate.gate === 1 ? "current" : "pending" },
    { key: "lateral", label: "03 横向方案", detail: "03_lateral_reframes.json", status: files.lateral.exists ? "done" : "pending" },
    { key: "gate2", label: "Gate 2", detail: (gates.gate2?.selected || []).join(", ") || "选择 LR", status: gates.gate2 ? "done" : gate.gate === 2 ? "current" : "pending" },
    { key: "audits", label: "04 垂直审计", detail: "04_vertical_audits.json", status: files.audits.exists ? "done" : state === "agent_running" && gate.gate === 2 ? "running" : "pending" },
    { key: "gate3", label: "Gate 3", detail: "选择 VA", status: gates.gate3 ? "done" : gate.gate === 3 ? "current" : "pending" },
    { key: "ideas", label: "06 Idea Cards", detail: "06_idea_cards.json", status: files.ideas.exists ? "done" : state === "agent_running" && gate.gate === 3 ? "running" : "pending" },
  ];
  const doneCount = stages.filter((item) => item.status === "done").length;
  let percent = Math.round((doneCount / stages.length) * 100);
  if (state === "recording_selection") percent = Math.max(percent, 48);
  if (state === "agent_running") percent = Math.max(percent, gate.gate === 2 ? 68 : 82);
  if (state === "artifact_ready") percent = Math.max(percent, 92);
  if (gate.gate === 4) percent = 100;

  return {
    gate: gate.gate,
    task: gate.task,
    state,
    message,
    percent,
    selected_ids: status?.selected_ids || [],
    expected_artifact: expectedFromStatus,
    expected_artifact_name: artifactName(expectedFromStatus),
    expected_artifact_exists: expectedInfo.exists,
    started_at: status?.started_at || null,
    updated_at: status?.updated_at || null,
    last_heartbeat: status?.last_heartbeat || null,
    elapsed_ms: status?.elapsed_ms || null,
    stages,
  };
}

async function loadCompleteState() {
  return {
    gate: 4,
    heading: "Research Reframer 已完成",
    task: "流程已完成",
    runDir: RUN_DIR,
    optionsPath: `${OUTPUTS_DIR}\\06_idea_cards.json`,
    recommendedIds: [],
    selectionGuidance: "三道 Gate 已完成。最终文件已经写入 outputs 目录，不需要继续选择。",
    options: [],
  };
}

async function loadIdeaCards() {
  const doc = await readJsonIfExists(`${OUTPUTS_DIR}\\06_idea_cards.json`, {});
  if (Array.isArray(doc.idea_cards)) return doc.idea_cards;
  if (Array.isArray(doc.cards)) return doc.cards;
  return [];
}

async function loadGate1Options() {
  const path = `${OUTPUTS_DIR}\\02_leverage_points.json`;
  const doc = await readJson(path);
  const options = (doc.leverage_points || []).map((lp) => ({
    id: lp.id,
    meta: `${lp.type} / ${lp.reframing_potential}`,
    title: compactText(lp.system_location, 44),
    summaryRows: rows(
      { label: "旧假设", text: lp.current_assumption, max: 90 },
      { label: "卡在哪里", text: lp.system_location, max: 110 },
      { label: "选它后会生成", text: lp.why_it_matters, max: 120 }
    ),
    detailRows: rows(
      { label: "证据", text: lp.source_trace?.input_evidence, max: 160 },
      { label: "风险", text: lp.risk, max: 160 }
    ),
  }));
  const recommendedIds = recommendedFor(1, options.map((o) => o.id));
  return {
    gate: 1,
    heading: "Gate 1：选系统切口",
    task: "选系统切口",
    runDir: RUN_DIR,
    optionsPath: path,
    recommendedIds,
    selectionGuidance: "选择后，系统只会围绕这些切口生成横向方案。这里不是选最终 idea。",
    options: options.map((o) => ({ ...o, recommended: recommendedIds.includes(o.id) })),
  };
}

async function loadGate2Options() {
  const path = `${OUTPUTS_DIR}\\03_lateral_reframes.json`;
  const doc = await readJson(path);
  const options = (doc.lateral_schemes || []).map((scheme) => ({
    id: scheme.lateral_id,
    meta: `${scheme.source_leverage_point}`,
    title: compactText(scheme.new_frame, 44),
    summaryRows: rows(
      { label: "旧→新", text: `${scheme.old_frame} → ${scheme.new_frame}`, max: 110 },
      { label: "人话方案", text: scheme.scheme, max: 110 },
      { label: "看点", text: scheme.why_interesting, max: 110 },
      { label: "风险", text: scheme.bad_use_to_avoid, max: 100 }
    ),
    detailRows: rows(
      { label: "来源切口", text: scheme.source_leverage_point, max: 80 },
      { label: "内部生成方式", text: scheme.operator, max: 80 },
      { label: "改变的假设", text: scheme.changed_assumption, max: 160 },
      { label: "lateral move", text: scheme.lateral_move, max: 160 }
    ),
  }));
  const recommendedIds = recommendedFor(2, options.map((o) => o.id));
  return {
    gate: 2,
    heading: "Gate 2：选横向方案",
    task: "选要审计的横向方案",
    runDir: RUN_DIR,
    optionsPath: path,
    recommendedIds,
    selectionGuidance: "这里选“值得审计”的方案，不是在证明它正确。优先选看点清楚、风险也说得清楚的方案。",
    options: options.map((o) => ({ ...o, recommended: recommendedIds.includes(o.id) })),
  };
}

async function loadGate3Options() {
  const path = `${OUTPUTS_DIR}\\04_vertical_audits.json`;
  const doc = await readJson(path);
  const audits = doc.audits || [];
  const rejectedIds = audits
    .filter((audit) => !(audit.needs_human || audit.verdict === "keep" || audit.verdict === "revise"))
    .map((audit) => audit.audit_id);
  const options = audits
    .filter((audit) => audit.needs_human || audit.verdict === "keep" || audit.verdict === "revise")
    .map((audit) => ({
      id: audit.audit_id,
      meta: `${audit.source_lateral_id} / ${audit.verdict}${audit.needs_human ? " / needs_human" : ""}`,
      resolution: audit.needs_human && audit.verdict === "reject" ? "human_rescue_to_revise" : audit.verdict,
      title: compactText(audit.refined_scheme || audit.core_claim, 44),
      summaryRows: rows(
        { label: "保留下来的核心", text: audit.refined_scheme || audit.core_claim, max: 130 },
        { label: "最小实验", text: audit.minimal_experiment, max: 130 },
        { label: "最大风险", text: `${audit.novelty_risk || ""} ${(audit.failure_modes || []).join(" ")}`, max: 120 }
      ),
      detailRows: rows(
        { label: "审计理由", text: Array.isArray(audit.reasons) ? audit.reasons.join(" ") : audit.reasons, max: 220 },
        { label: "因果机制", text: audit.causal_mechanism, max: 180 },
        { label: "分数", text: audit.audit_score ? `overall ${audit.audit_score.overall}` : "", max: 80 }
      ),
    }));
  const recommendedIds = recommendedFor(3, options.map((o) => o.id));
  return {
    gate: 3,
    heading: "Gate 3：选成卡候选",
    task: "选要变成 idea card 的审计后方案",
    runDir: RUN_DIR,
    optionsPath: path,
    recommendedIds,
    rejectedIds,
    selectionGuidance: "这里只看审计后还剩下什么、怎么做最小实验、最大风险是什么。被双重拒绝的方案不会出现在这里。",
    options: options.map((o) => ({ ...o, recommended: recommendedIds.includes(o.id) })),
  };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function stateLabel(state) {
  const labels = {
    idle: "等待选择",
    complete: "已完成",
    recording_selection: "记录选择",
    connecting: "连接中",
    reading_thread: "读取线程",
    resuming_thread: "恢复线程",
    starting_turn: "启动生成",
    agent_running: "后台生成中",
    artifact_ready: "已生成",
    timed_out: "等待超时",
    failed: "失败",
  };
  return labels[state] || state || "等待选择";
}

function statusClass(status) {
  if (status === "done") return "done";
  if (status === "current") return "current";
  if (status === "running") return "running";
  return "pending";
}

function renderStage(stage) {
  const marker = stage.status === "done" ? "✓" : stage.status === "running" ? "…" : stage.status === "current" ? "●" : "○";
  return `
    <div class="stage ${statusClass(stage.status)}">
      <span class="stageDot">${marker}</span>
      <span class="stageText">
        <strong>${escapeHtml(stage.label)}</strong>
        <small>${escapeHtml(stage.detail || "")}</small>
      </span>
    </div>`;
}

function arrayItems(value) {
  if (Array.isArray(value)) return value.filter((item) => item !== null && item !== undefined && String(item).trim());
  if (value === null || value === undefined || String(value).trim() === "") return [];
  return [value];
}

function renderIdeaField(label, value) {
  if (value === null || value === undefined || String(value).trim() === "") return "";
  return `
    <div class="ideaField">
      <span>${escapeHtml(label)}</span>
      <p>${escapeHtml(value)}</p>
    </div>`;
}

function renderIdeaList(label, items) {
  const list = arrayItems(items);
  if (!list.length) return "";
  return `
    <div class="ideaField">
      <span>${escapeHtml(label)}</span>
      <ul class="ideaList">
        ${list.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </div>`;
}

function cleanReaderText(value) {
  if (value === null || value === undefined) return "";
  const replacements = [
    ["expert threshold/safe baseline", "专家设定的事件判定线和安全参照行为"],
    ["baseline-threshold sensitivity atlas", "设定敏感性图谱"],
    ["safe baseline", "安全参照行为"],
    ["event threshold", "事件判定线"],
    ["threshold", "判定线"],
    ["baseline", "参照行为"],
    ["attribution ranking", "贡献排序"],
    ["attribution", "贡献归因"],
    ["high-risk contributor", "高风险来源"],
    ["high-risk contributors", "高风险来源"],
    ["contributors", "贡献来源"],
    ["contributor", "贡献来源"],
    ["safety recommendation", "安全建议"],
    ["recommendation", "建议"],
    ["Kendall tau", "排序一致性分数"],
    ["flip rate", "翻转比例"],
    ["ranking", "排序"],
    ["causal choice", "会影响因果解释的选择"],
    ["baseline-sensitive", "依赖参照设定"],
    ["top-10", "前 10 个"],
    ["top-k", "前 k 个"],
  ];
  let text = String(value);
  for (const [from, to] of replacements) {
    text = text.replaceAll(from, to).replaceAll(from[0].toUpperCase() + from.slice(1), to);
  }
  return text;
}

function readerViewForCard(card) {
  const provided = card.reader_view || {};
  const searchable = `${card.title || ""} ${card.one_sentence || ""} ${card.reframed_problem || ""}`.toLowerCase();
  if (searchable.includes("baseline") && searchable.includes("threshold")) {
    return {
      headline: provided.headline || "先检查解释结果稳不稳，再决定能不能拿它做安全建议",
      summary:
        provided.summary ||
        "原论文把“事件怎么判定”和“被替换成什么安全行为”当成固定前提。这个方向反过来检查：只要合理调整这些前提，高风险对象和安全建议会不会变。",
      original_default:
        provided.original_default ||
        "原来的默认想法是：专家给定的事件判定线和安全参照行为足够可靠，可以直接固定使用。",
      new_question:
        provided.new_question ||
        "新的问题是：这些专家设定本身是否会改变最后解释。如果会改变，就必须把解释标成“依赖参照设定”。",
      minimal_test:
        provided.minimal_test ||
        "在三个多智能体场景里，各准备 3 套合理设定。每套都重新计算高风险对象排序，再看最终安全建议是否翻转。",
      main_risk:
        provided.main_risk ||
        "如果只有很极端的设定才会改变结论，这个方向就会退化成普通稳健性检查，而不是新的研究问题。",
      why_it_matters:
        provided.why_it_matters ||
        "它把论文里隐藏的前提变成了要审计的对象，而不是只换一套说法。",
      glossary: provided.glossary || [
        ["事件判定线", "原文里的 threshold，决定什么时候算极端事件"],
        ["安全参照行为", "原文里的 safe baseline，指被移除动作要替换成什么行为"],
        ["贡献归因", "原文里的 attribution，指把事件责任分到动作或智能体上"],
        ["排序一致性分数", "原文里的 Kendall tau，用来比较两次排序是否一致"],
      ],
    };
  }
  return {
    headline: provided.headline || cleanReaderText(card.title || "未命名研究方向"),
    summary: provided.summary || cleanReaderText(card.one_sentence || ""),
    original_default: provided.original_default || cleanReaderText(card.original_problem || ""),
    new_question: provided.new_question || cleanReaderText(card.reframed_problem || ""),
    minimal_test: provided.minimal_test || cleanReaderText(card.minimal_experiment || ""),
    main_risk: provided.main_risk || cleanReaderText(card.failure_case || ""),
    why_it_matters: provided.why_it_matters || cleanReaderText(card.why_not_obvious || ""),
    glossary: provided.glossary || [],
  };
}

function renderReaderBox(label, value) {
  if (!value) return "";
  return `
    <div class="readerBox">
      <span>${escapeHtml(label)}</span>
      <p>${escapeHtml(value)}</p>
    </div>`;
}

function renderGlossary(items) {
  const rows = arrayItems(items).filter((row) => Array.isArray(row) && row.length >= 2);
  if (!rows.length) return "";
  return `
    <div class="glossary">
      <strong>术语速译</strong>
      <div class="glossaryGrid">
        ${rows
          .map(
            ([term, explanation]) => `
              <span>
                <b>${escapeHtml(term)}</b>
                <small>${escapeHtml(explanation)}</small>
              </span>`
          )
          .join("")}
      </div>
    </div>`;
}

function renderIdeaTrace(card) {
  const trace = card.method_trace || {};
  const score = trace.audit_score || {};
  const rows = [
    ["来源审计", trace.source_vertical_audit || card.system_trace?.reframe],
    ["横向方案", trace.source_lateral_scheme],
    ["杠杆点", trace.source_leverage_point || card.system_trace?.leverage_point],
    ["操作", trace.operator || card.system_trace?.lateral_operation],
    ["审计结论", trace.audit_verdict],
    ["综合分", score.overall],
  ].filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== "");
  if (!rows.length) return "";
  return `
    <div class="traceGrid">
      ${rows
        .map(
          ([label, value]) => `
            <span>
              <small>${escapeHtml(label)}</small>
              <strong>${escapeHtml(value)}</strong>
            </span>`
        )
        .join("")}
    </div>`;
}

function renderChangeLog(card) {
  const labels = {
    source_diagnosis: "原诊断",
    selected_leverage_point: "选择切口",
    structural_change: "结构变化",
    new_mechanism: "新机制",
    preserved_from_original: "保留内容",
    removed_or_weakened: "削弱内容",
    real_increment_over_original: "真实增量",
    remaining_fragility: "剩余脆弱性",
  };
  const rows = Object.entries(card.change_log || {}).filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== "");
  if (!rows.length) return "";
  return `
    <section class="changeLog">
      <h3>相对原论文改了什么</h3>
      ${rows
        .map(([key, value]) => renderIdeaField(labels[key] || key, value))
        .join("")}
    </section>`;
}

function renderTechnicalDetails(card) {
  return `
    <details class="technicalDetails">
      <summary>展开技术详情、trace、评分和原始字段</summary>
      <div class="technicalBody">
        ${renderIdeaTrace(card)}
        <div class="ideaGrid">
          ${renderIdeaField("原问题", card.original_problem)}
          ${renderIdeaField("改写后的问题", card.reframed_problem)}
          ${renderIdeaField("被改变的假设", card.changed_assumption)}
          ${renderIdeaField("为什么不显然", card.why_not_obvious)}
        </div>
        <section class="experimentBlock">
          <h3>技术版最小实验</h3>
          ${renderIdeaField("实验设计", card.minimal_experiment)}
          ${renderIdeaList("评价指标", card.evaluation_metrics)}
          ${renderIdeaField("预期观察", card.expected_observation)}
          ${renderIdeaField("失败情形", card.failure_case)}
        </section>
        <div class="ideaGrid">
          ${renderIdeaList("相关工作检索词", card.related_work_queries)}
          ${renderIdeaList("下一步", card.next_steps)}
        </div>
        ${renderChangeLog(card)}
        <details class="rawJson">
          <summary>原始 JSON 字段</summary>
          <pre>${escapeHtml(JSON.stringify(card, null, 2))}</pre>
        </details>
      </div>
    </details>`;
}

function renderIdeaCard(card, index) {
  const cardId = card.id || card.card_id || `IC-${String(index + 1).padStart(3, "0")}`;
  const reader = readerViewForCard(card);
  return `
    <article class="ideaCard">
      <div class="ideaHead">
        <div>
          <span class="ideaKicker">${escapeHtml(cardId)} · 人话版${card.status ? ` · ${escapeHtml(card.status)}` : ""}</span>
          <h2>${escapeHtml(reader.headline)}</h2>
        </div>
      </div>
      ${reader.summary ? `<p class="ideaLead">${escapeHtml(reader.summary)}</p>` : ""}
      <div class="readerGrid">
        ${renderReaderBox("原来默认", reader.original_default)}
        ${renderReaderBox("现在改问", reader.new_question)}
        ${renderReaderBox("怎么验证", reader.minimal_test)}
        ${renderReaderBox("可能失败", reader.main_risk)}
      </div>
      ${renderReaderBox("为什么值得看", reader.why_it_matters)}
      ${renderGlossary(reader.glossary)}
      ${renderTechnicalDetails(card)}
    </article>`;
}

function renderFinalIdeas(cards) {
  const ideaCards = cards.map(renderIdeaCard).join("");
  const artifactPaths = [
    `${OUTPUTS_DIR}\\06_idea_cards.json`,
    `${OUTPUTS_DIR}\\06_idea_cards.md`,
    `${OUTPUTS_DIR}\\reframe_report.md`,
  ];
  return `
    <section class="finalDeck">
      <div class="finalHeader">
        <span class="completePill">Gate 4 complete</span>
        <h2>最终 Idea Cards</h2>
        <p>你在 Gate 3 选中的审计后方案已经成卡；下面是刷新后直接可读的完整 idea，不需要再做选择。</p>
      </div>
      ${
        ideaCards ||
        `<div class="emptyFinal">没有读取到 idea card。请检查 <code>${escapeHtml(`${OUTPUTS_DIR}\\06_idea_cards.json`)}</code> 是否存在且可解析。</div>`
      }
      <div class="artifactBar">
        <strong>已写入文件</strong>
        ${artifactPaths.map((path) => `<code>${escapeHtml(path)}</code>`).join("")}
      </div>
    </section>`;
}

async function html() {
  const gate = await loadGateOptions();
  const progress = await buildProgressState(gate);
  const stageRows = progress.stages.map(renderStage).join("");
  const ideaCards = gate.gate === 4 ? await loadIdeaCards() : [];
  const optionRows = gate.options
    .map(
      (option) => `
        <label class="option">
          <input type="checkbox" value="${escapeHtml(option.id)}" ${option.recommended ? "checked" : ""} />
          <span class="optionBody">
            <span class="optionHead">
              <strong>${escapeHtml(option.id)}</strong>
              <span>${escapeHtml(option.meta || "")}</span>
            </span>
            <span class="title">${escapeHtml(option.title)}</span>
            <span class="summaryRows">
              ${(option.summaryRows || [])
                .map((row) => `<span><b>${escapeHtml(row.label)}：</b>${escapeHtml(row.text)}</span>`)
                .join("")}
            </span>
            ${
              option.detailRows?.length
                ? `<details><summary>详情</summary>${option.detailRows
                    .map((row) => `<p><b>${escapeHtml(row.label)}：</b>${escapeHtml(row.text)}</p>`)
                    .join("")}</details>`
                : ""
            }
          </span>
        </label>`
    )
    .join("");
  const finalArtifacts = gate.gate === 4 ? renderFinalIdeas(ideaCards) : "";
  const gatePanel =
    gate.gate === 4
      ? ""
      : `
    <div class="panel">
      <strong>Gate ${gate.gate}: ${escapeHtml(gate.task)}</strong>
      <p>${escapeHtml(gate.selectionGuidance)}</p>
      <p>推荐: <code>${escapeHtml(gate.recommendedIds.join(", ") || "无")}</code></p>
      <div class="optionList">
        ${optionRows || "<p>当前 Gate 没有可选项。</p>"}
      </div>
      <div class="row">
        <button onclick="sendSelected()">使用选中项继续</button><button class="secondary" onclick="selectRecommended()">选择推荐项</button><button class="secondary" onclick="clearSelected()">清空选择</button>
      </div>
    </div>`;

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(gate.heading)}</title>
  <style>
    :root { color-scheme: light; font-family: "Segoe UI", Arial, sans-serif; }
    body { margin: 0; background: #f5f6f7; color: #1f2328; }
    main { max-width: 1120px; margin: 0 auto; padding: 28px 20px; }
    h1 { font-size: 22px; margin: 0 0 8px; }
    p { line-height: 1.55; color: #555; margin: 8px 0; }
    .panel { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 18px; margin-top: 18px; }
    .progressPanel { border-color: #cbd8ce; background: #fbfdfb; }
    .progressTop { display: grid; grid-template-columns: 1fr auto; gap: 14px; align-items: start; }
    .stateBadge { display: inline-flex; align-items: center; gap: 7px; border: 1px solid #b8c8d7; background: #edf4fb; color: #174a7b; border-radius: 999px; padding: 6px 10px; font-size: 13px; font-weight: 700; white-space: nowrap; }
    .stateBadge::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: #245f9f; box-shadow: 0 0 0 0 rgba(36, 95, 159, .35); animation: pulse 1.5s infinite; }
    .stateBadge.complete { border-color: #b6d5bf; background: #eaf7ee; color: #1d6339; }
    .stateBadge.complete::before { background: #247a4a; animation: none; box-shadow: none; }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(36,95,159,.35); } 70% { box-shadow: 0 0 0 8px rgba(36,95,159,0); } 100% { box-shadow: 0 0 0 0 rgba(36,95,159,0); } }
    .meterMeta { display: flex; justify-content: space-between; gap: 12px; color: #667085; font-size: 12px; margin-top: 14px; }
    .meter { height: 14px; border: 1px solid #b9c5bc; border-radius: 999px; overflow: hidden; background: #f5f7f5; margin-top: 6px; }
    .meterFill { height: 100%; width: ${progress.percent}%; background: repeating-linear-gradient(45deg, rgba(255,255,255,.22) 0, rgba(255,255,255,.22) 8px, transparent 8px, transparent 16px), #245f9f; transition: width .35s ease; }
    .meterFill.running { animation: stripe 1.4s linear infinite; }
    @keyframes stripe { from { background-position: 0 0; } to { background-position: 24px 0; } }
    .stageRail { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; margin-top: 14px; }
    .stage { min-height: 56px; border: 1px solid #d8dee4; border-radius: 8px; background: #fff; padding: 8px; display: grid; grid-template-columns: 24px 1fr; gap: 8px; align-items: start; }
    .stage.done { background: #edf7f0; border-color: #cfe3d5; }
    .stage.current { background: #edf4fb; border-color: #bdd0e2; }
    .stage.running { background: #fff6e4; border-color: #e2c47e; }
    .stageDot { width: 24px; height: 24px; border-radius: 50%; display: grid; place-items: center; background: #9aa49d; color: #fff; font-size: 12px; font-weight: 800; }
    .done .stageDot { background: #247a4a; }
    .current .stageDot { background: #245f9f; }
    .running .stageDot { background: #a76d12; }
    .stageText { min-width: 0; display: grid; gap: 2px; }
    .stageText strong { font-size: 13px; line-height: 1.2; }
    .stageText small { color: #667085; font-size: 11px; line-height: 1.25; overflow-wrap: anywhere; }
    .statusFacts { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }
    .fact { border: 1px solid #e0e4e1; background: #fff; border-radius: 8px; padding: 10px; display: grid; gap: 5px; min-height: 66px; }
    .fact span { color: #667085; font-size: 12px; }
    .fact strong { color: #1f2328; font-size: 13px; overflow-wrap: anywhere; }
    .finalDeck { display: grid; gap: 14px; margin-top: 18px; }
    .finalHeader { display: grid; gap: 6px; }
    .finalHeader h2 { margin: 0; font-size: 24px; line-height: 1.2; }
    .finalHeader p { margin: 0; max-width: 760px; }
    .completePill { width: fit-content; border: 1px solid #b6d5bf; background: #eaf7ee; color: #1d6339; border-radius: 999px; padding: 5px 10px; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0; }
    .ideaCard { background: #fff; border: 1px solid #cdd8df; border-radius: 8px; padding: 20px; box-shadow: 0 1px 0 rgba(31,35,40,.04); display: grid; gap: 16px; }
    .ideaHead { display: flex; justify-content: space-between; gap: 16px; align-items: start; }
    .ideaKicker { color: #315f45; font-size: 13px; font-weight: 800; }
    .ideaCard h2 { margin: 4px 0 0; font-size: 22px; line-height: 1.25; }
    .ideaCard h3 { margin: 0 0 10px; font-size: 16px; }
    .ideaLead { margin: 0; color: #24292f; font-size: 18px; line-height: 1.55; }
    .readerGrid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .readerBox { border: 1px solid #dbe4df; background: #fbfdfb; border-radius: 8px; padding: 12px; min-width: 0; }
    .readerBox span { display: block; color: #315f45; font-size: 12px; font-weight: 800; margin-bottom: 6px; }
    .readerBox p { margin: 0; color: #24292f; overflow-wrap: anywhere; }
    .glossary { border-top: 1px solid #e6eaee; padding-top: 12px; display: grid; gap: 10px; }
    .glossary > strong { font-size: 14px; color: #315f45; }
    .glossaryGrid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
    .glossaryGrid span { border: 1px solid #d8dee4; border-radius: 8px; padding: 8px; background: #fff; min-width: 0; }
    .glossaryGrid b { display: block; color: #1f2328; font-size: 13px; margin-bottom: 4px; }
    .glossaryGrid small { display: block; color: #667085; line-height: 1.35; overflow-wrap: anywhere; }
    .technicalDetails { border-top: 1px solid #d8dee4; padding-top: 10px; }
    .technicalDetails > summary { width: fit-content; border: 1px solid #cbd5dd; background: #f6f8fa; border-radius: 7px; padding: 8px 10px; color: #315f45; font-weight: 800; cursor: pointer; }
    .technicalBody { display: grid; gap: 14px; margin-top: 12px; }
    .rawJson { border-top: 1px solid #e6eaee; padding-top: 10px; }
    .rawJson pre { min-height: 80px; max-height: 360px; font-size: 12px; }
    .ideaGrid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 18px; }
    .ideaField { min-width: 0; border-top: 1px solid #e6eaee; padding-top: 10px; }
    .ideaField span { display: block; color: #667085; font-size: 12px; font-weight: 800; margin-bottom: 5px; }
    .ideaField p { margin: 0; color: #30363d; overflow-wrap: anywhere; }
    .ideaList { margin: 0; padding-left: 18px; color: #30363d; line-height: 1.55; }
    .ideaList li + li { margin-top: 5px; }
    .traceGrid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; }
    .traceGrid span { border: 1px solid #e0e4e8; border-radius: 8px; padding: 8px; min-width: 0; background: #fbfcfd; }
    .traceGrid small { display: block; color: #667085; font-size: 11px; margin-bottom: 3px; }
    .traceGrid strong { display: block; color: #1f2328; font-size: 13px; overflow-wrap: anywhere; }
    .experimentBlock, .changeLog { display: grid; gap: 12px; }
    .artifactBar { background: #fff; border: 1px solid #d8dee4; border-radius: 8px; padding: 14px; display: grid; gap: 8px; }
    .artifactBar strong { font-size: 14px; }
    .artifactBar code { overflow-wrap: anywhere; }
    .emptyFinal { background: #fff; border: 1px solid #d8dee4; border-radius: 8px; padding: 16px; }
    .row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    button { border: 1px solid #b8c4b8; background: #edf7ee; color: #14351f; padding: 10px 14px; border-radius: 7px; cursor: pointer; font-weight: 600; }
    button.secondary { background: #f5f5f5; color: #222; border-color: #ccc; }
    pre { white-space: pre-wrap; background: #111; color: #e6ffe6; border-radius: 8px; padding: 12px; min-height: 120px; overflow: auto; }
    code { background: #eee; padding: 2px 4px; border-radius: 4px; }
    .optionList { display: grid; gap: 10px; margin-top: 14px; }
    .option { display: grid; grid-template-columns: 22px 1fr; gap: 10px; align-items: start; padding: 12px; border: 1px solid #d8dee4; border-radius: 8px; background: #fbfbfc; cursor: pointer; }
    .option:has(input:checked) { border-color: #4f8a66; background: #f0f8f2; }
    .option input { margin-top: 4px; }
    .optionBody { display: grid; gap: 5px; }
    .optionHead { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    .optionHead span { font-size: 12px; padding: 2px 7px; border: 1px solid #d0d7de; border-radius: 999px; color: #57606a; background: #fff; }
    .title { font-weight: 600; color: #24292f; }
    .summaryRows { display: grid; gap: 4px; color: #41464d; font-size: 13px; line-height: 1.45; }
    details { color: #536471; font-size: 13px; margin-top: 2px; }
    details summary { cursor: pointer; color: #315f45; font-weight: 600; }
    details p { margin: 6px 0 0; font-size: 13px; color: #536471; }
    .meta { font-size: 13px; color: #667085; }
    @media (max-width: 900px) { .stageRail { grid-template-columns: repeat(2, minmax(0, 1fr)); } .statusFacts, .ideaGrid, .readerGrid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .traceGrid, .glossaryGrid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .progressTop { grid-template-columns: 1fr; } }
    @media (max-width: 720px) { .ideaGrid, .traceGrid, .readerGrid, .glossaryGrid { grid-template-columns: 1fr; } }
    @media (max-width: 520px) { .stageRail, .statusFacts { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>${escapeHtml(gate.heading)}</h1>
    <p>当前目标对话线程: <code>${THREAD_ID}</code></p>
    <p class="meta">运行目录: <code>${escapeHtml(RUN_DIR)}</code></p>

    ${finalArtifacts}

    <div class="panel progressPanel">
      <div class="progressTop">
        <div>
          <strong id="progressTitle">Gate ${gate.gate}：${escapeHtml(gate.task)}</strong>
          <p id="progressMessage">${escapeHtml(progress.message)}</p>
        </div>
        <span class="stateBadge ${progress.state === "complete" ? "complete" : ""}" id="stateBadge">${escapeHtml(stateLabel(progress.state))}</span>
      </div>
      <div class="meterMeta">
        <span id="meterLabel">阶段进度：artifact-aware，不是模型内部百分比</span>
        <span id="meterPercent">${progress.percent}%</span>
      </div>
      <div class="meter"><div class="meterFill ${progress.state === "agent_running" ? "running" : ""}" id="meterFill"></div></div>
      <div class="statusFacts">
        <div class="fact"><span>当前 Gate</span><strong id="factGate">Gate ${gate.gate}</strong></div>
        <div class="fact"><span>目标 artifact</span><strong id="factArtifact">${escapeHtml(progress.expected_artifact_name || "等待选择")}</strong></div>
        <div class="fact"><span>已选 ID</span><strong id="factIds">${escapeHtml((progress.selected_ids || []).join(", ") || "尚未提交")}</strong></div>
        <div class="fact"><span>最近 heartbeat</span><strong id="factHeartbeat">${escapeHtml(progress.last_heartbeat || progress.updated_at || "尚未开始")}</strong></div>
      </div>
      <div class="stageRail" id="stageRail">${stageRows}</div>
    </div>

    <div class="panel">
      <strong>状态检查</strong>
      <p>读取当前 thread 和 Gate 状态，不会启动新 turn。</p>
      <div class="row">
        <button class="secondary" onclick="probe()">检查当前 thread</button>
        <button class="secondary" onclick="location.reload()">刷新 Gate</button>
      </div>
    </div>

    ${gatePanel}

    <div class="panel">
      <strong>结果</strong>
      <pre id="log">${escapeHtml(progress.message)}</pre>
    </div>
  </main>
  <script>
    const activeGate = ${gate.gate};
    const recommendedIds = ${JSON.stringify(gate.recommendedIds)};
    let statusTimer = null;

    async function postJson(url, payload) {
      const res = await fetch(url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload)
      });
      return await res.json();
    }

    async function getJson(url) {
      const res = await fetch(url, { cache: "no-store" });
      return await res.json();
    }

    function stateLabel(state) {
      const labels = {
        idle: "等待选择",
        complete: "已完成",
        recording_selection: "记录选择",
        connecting: "连接中",
        reading_thread: "读取线程",
        resuming_thread: "恢复线程",
        starting_turn: "启动生成",
        agent_running: "后台生成中",
        artifact_ready: "已生成",
        timed_out: "等待超时",
        failed: "失败"
      };
      return labels[state] || state || "等待选择";
    }

    function stageHtml(stage) {
      const marker = stage.status === "done" ? "✓" : stage.status === "running" ? "…" : stage.status === "current" ? "●" : "○";
      const cls = ["stage", stage.status === "done" ? "done" : stage.status === "current" ? "current" : stage.status === "running" ? "running" : "pending"].join(" ");
      return '<div class="' + cls + '"><span class="stageDot">' + marker + '</span><span class="stageText"><strong>' +
        escapeHtml(stage.label) + '</strong><small>' + escapeHtml(stage.detail || "") + '</small></span></div>';
    }

    function escapeHtml(value) {
      return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }

    function renderStatus(status) {
      document.getElementById("progressMessage").textContent = status.message || "";
      document.getElementById("stateBadge").textContent = stateLabel(status.state);
      document.getElementById("stateBadge").classList.toggle("complete", status.state === "complete");
      document.getElementById("meterPercent").textContent = (status.percent || 0) + "%";
      const fill = document.getElementById("meterFill");
      fill.style.width = (status.percent || 0) + "%";
      fill.classList.toggle("running", status.state === "agent_running");
      document.getElementById("factGate").textContent = "Gate " + status.gate;
      document.getElementById("factArtifact").textContent = status.expected_artifact_name || "等待选择";
      document.getElementById("factIds").textContent = (status.selected_ids || []).join(", ") || "尚未提交";
      document.getElementById("factHeartbeat").textContent = status.last_heartbeat || status.updated_at || "尚未开始";
      document.getElementById("stageRail").innerHTML = (status.stages || []).map(stageHtml).join("");
    }

    async function refreshStatus() {
      try {
        const status = await getJson("/status");
        renderStatus(status);
        return status;
      } catch (err) {
        document.getElementById("log").textContent = "状态刷新失败：" + String(err && err.message || err);
        return null;
      }
    }

    function startStatusPolling() {
      if (statusTimer) clearInterval(statusTimer);
      refreshStatus();
      statusTimer = setInterval(refreshStatus, 2000);
    }

    async function probe() {
      const log = document.getElementById("log");
      log.textContent = "正在检查当前 thread...";
      try {
        const json = await postJson("/probe", {});
        log.textContent = JSON.stringify(json, null, 2);
      } catch (err) {
        log.textContent = String(err && err.stack || err);
      }
    }

    async function send(ids) {
      const log = document.getElementById("log");
      if (activeGate === 4) {
        log.textContent = "Workflow 已完成，不需要继续选择。";
        return;
      }
      log.textContent = "已提交 Gate " + activeGate + " 选择：" + ids.join(", ") + "\\n页面会每 2 秒刷新状态；可以刷新浏览器，不要重复点击。";
      startStatusPolling();
      try {
        const json = await postJson("/select", { ids, gate: activeGate });
        log.textContent = JSON.stringify(json, null, 2);
        await refreshStatus();
      } catch (err) {
        log.textContent = String(err && err.stack || err);
        await refreshStatus();
      }
    }

    function checkedIds() {
      return Array.from(document.querySelectorAll(".option input:checked")).map((input) => input.value);
    }

    function sendSelected() {
      const ids = checkedIds();
      if (!ids.length) {
        document.getElementById("log").textContent = "请至少选择一个选项。";
        return;
      }
      send(ids);
    }

    function selectRecommended() {
      const recommended = new Set(recommendedIds);
      for (const input of document.querySelectorAll(".option input")) input.checked = recommended.has(input.value);
    }

    function clearSelected() {
      for (const input of document.querySelectorAll(".option input")) input.checked = false;
    }

    startStatusPolling();
  </script>
</body>
</html>`;
}

function json(res, status, payload) {
  res.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(payload, null, 2));
}

async function readBody(req) {
  let body = "";
  for await (const chunk of req) {
    body += chunk;
    if (body.length > 8192) throw new Error("request body too large");
  }
  return body ? JSON.parse(body) : {};
}

const server = createServer(async (req, res) => {
  try {
    if (req.method === "GET" && req.url === "/") {
      res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
      res.end(await html());
      return;
    }

    if (req.method === "GET" && req.url === "/gate-options") {
      json(res, 200, await loadGateOptions());
      return;
    }

    if (req.method === "GET" && req.url === "/status") {
      const gate = await loadGateOptions();
      json(res, 200, await buildProgressState(gate));
      return;
    }

    if (req.method === "GET" && req.url === "/healthz") {
      const gate = await loadGateOptions();
      const progress = await buildProgressState(gate);
      json(res, 200, {
        ok: true,
        threadId: THREAD_ID,
        workspace: WORKSPACE,
        appServerUrl: APP_URL,
        gate: gate.gate,
        options: gate.options.length,
        state: progress.state,
        message: progress.message,
      });
      return;
    }

    if (req.method === "POST" && req.url === "/probe") {
      try {
        json(res, 200, await probeCurrentThread());
      } catch (err) {
        json(res, 500, { ok: false, error: String((err && err.message) || err) });
      }
      return;
    }

    if (req.method === "POST" && req.url === "/select") {
      try {
        const parsed = await readBody(req);
        const gateNumber = Number(parsed.gate) || (await detectGateNumber());
        if (gateNumber >= 4) throw new Error("workflow is already complete; no further gate selection is needed");
        const ids = safeIds(parsed.ids);
        if (!ids.length) throw new Error("ids is required");
        const gate = await loadGateOptions();
        if (gate.gate !== gateNumber) throw new Error(`submitted gate ${gateNumber} does not match current gate ${gate.gate}`);
        const currentStatus = await readGateStatus();
        const statusGate = Number(currentStatus?.gate || 0);
        if (isBusyState(currentStatus?.state) && statusGate && statusGate <= gateNumber) {
          throw new Error(
            `Gate ${statusGate} turn is still running; wait for it to finish before submitting Gate ${gateNumber}.`
          );
        }
        const available = new Set((gate.options || []).map((option) => option.id));
        const unknown = ids.filter((id) => !available.has(id));
        if (unknown.length) throw new Error(`unknown ids for Gate ${gateNumber}: ${unknown.join(", ")}`);

        const expected = expectedArtifactForGate(gateNumber);
        await writeGateStatus({
          gate: gateNumber,
          state: "recording_selection",
          selected_ids: ids,
          expected_artifact: expected,
          expected_artifact_name: artifactName(expected),
          started_at: new Date().toISOString(),
          message: `正在记录 Gate ${gateNumber} 选择：${ids.join(", ")}。`,
        });
        await recordGateSelection(gate, ids);
        const result = await sendToCurrentThread(ids, gateNumber);
        json(res, 200, result);
      } catch (err) {
        await writeGateStatus({
          state: "failed",
          message: String((err && err.message) || err),
        });
        json(res, 500, { ok: false, error: String((err && err.message) || err) });
      }
      return;
    }

    res.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    res.end("not found");
  } catch (err) {
    res.writeHead(500, { "content-type": "text/plain; charset=utf-8" });
    res.end(String((err && err.stack) || err));
  }
});

server.listen(HTTP_PORT, "127.0.0.1", () => {
  console.log(`Gate UI: http://127.0.0.1:${HTTP_PORT}`);
  console.log(`Target thread: ${THREAD_ID}`);
  console.log(`Workspace: ${WORKSPACE}`);
});

process.on("SIGINT", () => {
  if (appServerProc) appServerProc.kill();
  process.exit(0);
});

