# reframe-ui

Research Reframer 三道人工关卡的本地点击式 UI,作为 Claude Code 的 **channel**(research preview)。

把浏览器里的鼠标点选(Gate 1 选杠杆点 / Gate 2 选横向方案 / Gate 3 选审计成卡)直接推进**正在运行的 Claude Code 会话**:你在网页上一点,选择就以 `<channel source="reframe-ui">` 事件落进会话上下文,Claude 接着跑后续阶段(lateral-generate / vertical-audit / idea-card),完成后回一句状态,网页随之刷新到下一关。

一个 Node 进程同时是两样东西:

```
浏览器 UI  --HTTP-->  reframe-ui 进程  --MCP 通知-->  Claude Code 会话
浏览器 UI  <--SSE---  reframe-ui 进程  <--reply 工具--  Claude Code 会话
```

- **MCP(stdio)channel**:只跟 Claude Code 对话(通知 + `reply` 工具)。
- **本地 HTTP/SSE 服务器**:只跟浏览器对话,绑定 `127.0.0.1`。

本实现是纯 Node + SSE,**不需要 Bun,也不需要 WebSocket**。

---

## 前置条件

- **Node**:已用 v25 验证。
- **Claude Code v2.1.80+**:channel 能力需要这个版本起。
- **Anthropic 账号鉴权**:claude.ai 登录或 Console API key 均可;**不支持 Bedrock / Vertex / Foundry**。
- **账户类型**:Pro / Max 个人账户默认即可用;Team / Enterprise 需要管理员开启 `channelsEnabled`。

---

## 安装

```bash
cd reframe-ui
npm install
```

---

## 运行

reframe-ui 不是常规 MCP server——它是个 **channel**,必须随会话用 channel 开关启动,不能靠 `claude mcp` 那套拉起。

因为这个 channel 是自定义的(不在 Anthropic 的内置 allowlist 里),要用开发标志加载:

```bash
claude --dangerously-load-development-channels server:reframe-ui
```

- `server:reframe-ui` 中的 `reframe-ui` 对应 `.mcp.json` 里注册的 server 名。
- 启动时会有确认提示;**每次**要用这个自定义 channel 都得带上 `--dangerously-load-development-channels`。

### 先注册(已提供 `.mcp.json`)

仓库已带 `.mcp.json`:

```json
{
  "mcpServers": {
    "reframe-ui": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/server.mjs"]
    }
  }
}
```

`${CLAUDE_PLUGIN_ROOT}` 是 Claude Code 在加载时注入的占位符,指向本插件根目录(即 `server.mjs` 所在目录)。作为插件安装时它会被自动展开;若你在别处手写 `.mcp.json`,把它替换成 `server.mjs` 的绝对路径即可。

### 环境变量

| 变量 | 作用 | 默认值 |
| --- | --- | --- |
| `REFRAME_RUN_DIR` | 直接指定要读取的某个 run 的 `outputs` 目录 | 自动取 `REFRAME_BASE` 下最新(按 mtime)的 run |
| `REFRAME_BASE` | runs 根目录(每个 run 是 `<BASE>/<name>/outputs/`) | `../test-runs`(相对 `server.mjs`) |
| `REFRAME_PORT` | 本地 HTTP/SSE 端口 | `8765` |

示例:

```bash
REFRAME_BASE=/path/to/runs REFRAME_PORT=8765 \
  claude --dangerously-load-development-channels server:reframe-ui
```

---

## 使用流程

1. 启动带 channel 的会话(见上)。
2. 运行 `/reframe-workshop`,让流程跑到 **Gate 1**(生成 `02_leverage_points.json`)。
3. 浏览器打开 <http://localhost:8765>。
4. **Gate 1** 选杠杆点(三种模式见下),点击确认 → 以 `<channel … gate="1" …>` 落进会话 → Claude 只对所选杠杆点跑 `lateral-generate`(生成 `03_lateral_reframes.json`)→ `reply` → UI 进到 **Gate 2**。
5. **Gate 2** 选要审计的横向方案 → Claude 跑 `vertical-audit`(Codex + Claude 双裁、默认驳回,生成 `04_vertical_audits.json`)→ `reply` → 进到 **Gate 3**。
6. **Gate 3** 选要成卡的审计方案(两裁分歧的标「需人工」由你拍板;被双裁驳回的进只读「被驳回抽屉」不可选)→ Claude 跑 `idea-card`(生成 `06_idea_cards.{md,json}`,`method_trace` 与 VA/LR 逐字一致)+ 跑校验器到退出码 0 → `reply` 完成。

Gate 由 outputs 里**有效**的 v0.5 产物推断(`schema_version 2.0` + 非空数组,不只是文件存在):`02` 有效 → Gate 1;`03` 有效 → Gate 2;`04` 有效 → Gate 3;`06` 有效 → done。

---

## 三种选择模式

每道关卡都可用以下任一模式提交(对应 `/select` 的 `mode` 字段):

- **explicit(显式)**:你直接勾选具体 id(Gate 1 是 `LP-…`,Gate 2 是 `LR-…`,Gate 3 是 `VA-…`)。必须带 `ids`。
- **nl(自然语言)**:不点具体项,用一句话描述意图(如「偏动态反馈、目标函数和 human control 那几个」),由 Claude 从当前关卡的项里映射出对应 id 并说明理由。
- **delegate(托管)**:把选择交给 Claude,按 reframe-workshop 的启发式(多样性 / 可判别性)代选并说明理由。

`nl` 与 `delegate` 的 `ids` 传 `[]`,意图放在 `intent` 字段。

---

## HTTP 端点

浏览器 ↔ 进程,全部绑定 `127.0.0.1`。权威定义见 [`CONTRACT.md`](./CONTRACT.md)。

| 方法 + 路径 | 作用 |
| --- | --- |
| `GET /` | 返回选择 UI(`ui.html`) |
| `GET /state[?run=<name>]` | 当前 run 状态 JSON(`gate`、`leverage`/`lateral`/`audits`/`cards`、`last_status`);`gate` 按契约**有效性**判定;带 `run` 参数可切换活跃 run |
| `GET /runs` | 列出 `BASE` 下所有 run:`{ base, active, runs }` |
| `POST /select` | 把一次人工选择投递进会话;body 含 `gate / mode / ids / intent`;成功 `{ ok, delivered }`,出错 HTTP 400 |
| `GET /events` | SSE 流;连上先发 `{"type":"hello"}`,之后每当 Claude 调 `reply` 推 `{"type":"status","text":…}`;UI 收到后应重新 `GET /state` 并前进 |

MCP 侧(进程 ↔ Claude):投递选择走 `notifications/claude/channel` 通知,Claude 用 `reply` 工具回推状态。细节见 `CONTRACT.md`。

---

## 安全

- 服务器**仅绑 `127.0.0.1`**,设计为单人本地使用。
- channel content 会**进入 Claude 的上下文并驱动它去执行动作**,存在 prompt-injection 面——**不要把端口暴露到外网或共享网络**。
- 敏感路径 / 标识放在通知的 `meta`(仅 id/枚举值),**不要放进 `content`**。
- `POST /select` 拒绝跨源请求与非本机 `Host`(403)、要求 `application/json`(415)、限制 body ≤ 64 KB(413),并按当前 run 状态校验 gate / id 前缀(`LP-`/`LR-`/`VA-`)/ 存在性,Gate 3 还校验「可成卡资格」(被双裁驳回的 VA 不可提交)(409 / 400),避免本地恶意网页或陈旧前端把选择注入会话。`GET /state?run=` 只接受单层目录名(防路径穿越)。详见 [`CONTRACT.md`](./CONTRACT.md)。

---

## 限制

- **research preview**:channel 协议可能变动。
- **Claude 专属**:这是 Claude Code 的 channel,Codex 等无对应机制。
- **会话必须开着**:浏览器里的点选只有在对应的 Claude Code 会话仍在运行时才生效。
- **每次都要开发标志**:自定义 channel 每次启动都需 `--dangerously-load-development-channels`,且会有确认提示。
