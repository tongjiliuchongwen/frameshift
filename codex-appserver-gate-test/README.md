# Codex App Server Gate Sidecar

Local sidecar for sending browser-button gate selections to an existing Codex Desktop thread through `codex app-server`.

Run from this directory:

```powershell
$env:CODEX_THREAD_ID="<thread-id>"
$env:REFRAME_RUN_DIR="..\research-reframer-skills-codex-v0.7-diagnostic-feedback-search\examples\physmaster-three-gate"  # optional; defaults to the bundled fixture
node server.mjs
```

Open <http://127.0.0.1:8787>.

- `检查当前 thread` reads the target Desktop thread history without starting a turn.
- `使用选中项继续` resumes the target Desktop thread and starts the next Research Reframer workflow turn with the selected ids.
- Before starting that turn, the sidecar records the current card snapshot in `outputs\05_gate_cards.json`
  and the selected ids in `outputs\05_human_selection.json`.
- The button does not type into the chat composer. It starts a Codex turn in the target thread through the App Server.

The sidecar uses `codex app-server --listen ws://127.0.0.1:4517`. On Windows, this project starts it through `cmd.exe` so npm shims work reliably.
