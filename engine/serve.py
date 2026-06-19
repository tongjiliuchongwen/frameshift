"""frameshift engine server — stdlib http.server, zero dependencies.

Serves the JSON value-map API over runs/ and statically hosts the built
dashboard (dashboard/dist).  Run from the repo root:

    python -m engine.cli serve            # -> http://127.0.0.1:8420

API (CORS open, so the Vite dev server on :5173 can talk to it too):
    GET /api/runs                 -> ["<run_id>", ...]
    GET /api/runs/<id>/graph      -> graph.json   (paper + clamped DOFs)
    GET /api/runs/<id>/cards      -> [card, ...]   (every cards/*.json)
    GET /api/runs/<id>/map        -> map.json      (axes + survivor positions)
    GET /api/runs/<id>/run        -> run.json      (header counts)

map.json / run.json are recomputed deterministically from cards/ on every
request if missing or stale, so the API never serves a map that disagrees with
the cards on disk.
"""
from __future__ import annotations

import json
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from . import mapping

ROOT = Path.cwd()
RUNS = ROOT / "runs"
DIST = ROOT / "dashboard" / "dist"

LANDING = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    "<title>frameshift engine</title></head>"
    "<body style='font-family:system-ui,sans-serif;background:#0e1420;"
    "color:#e8eef2;max-width:640px;margin:60px auto;padding:0 24px;line-height:1.6'>"
    "<h2 style='color:#5eead4'>frameshift engine</h2>"
    "<p>API 在 <code>/api/runs</code>。看板尚未构建：</p>"
    "<pre style='background:#131b2b;padding:12px 16px;border-radius:8px'>"
    "cd dashboard\nnpm install\nnpm run build</pre>"
    "<p>构建后回到仓库根重启 <code>python -m engine.cli serve</code> 即可。</p>"
    "</body></html>"
)


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_cards(run_dir):
    cdir = run_dir / "cards"
    if not cdir.is_dir():
        return []
    return [_load_json(p) for p in sorted(cdir.glob("*.json"))]


def _map_for(run_dir):
    """map.json if present, else assembled on the fly from cards/."""
    p = run_dir / "map.json"
    if p.is_file():
        return _load_json(p)
    return mapping.build_map(_load_cards(run_dir))


def _run_for(run_dir):
    p = run_dir / "run.json"
    if p.is_file():
        return _load_json(p)
    graph = {}
    gp = run_dir / "graph.json"
    if gp.is_file():
        graph = _load_json(gp)
    return mapping.build_run(run_dir.name, graph, _load_cards(run_dir))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        directory = str(DIST) if DIST.is_dir() else str(ROOT)
        super().__init__(*a, directory=directory, **kw)

    # silence default per-request logging noise
    def log_message(self, fmt, *args):  # noqa: A003
        pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _api(self, parts):
        # parts == ["api", "runs", ...]
        if len(parts) == 2:
            if not RUNS.is_dir():
                return self._send_json([])
            return self._send_json(
                sorted(d.name for d in RUNS.iterdir() if d.is_dir()))

        run_dir = RUNS / parts[2]
        if not run_dir.is_dir():
            return self._send_json({"error": "run not found"}, 404)

        if len(parts) == 3:
            return self._send_json({"error": "specify graph|cards|map|run"}, 404)

        sub = parts[3]
        if sub == "graph":
            return self._send_json(_load_json(run_dir / "graph.json"))
        if sub == "cards":
            return self._send_json(_load_cards(run_dir))
        if sub == "map":
            return self._send_json(_map_for(run_dir))
        if sub == "run":
            return self._send_json(_run_for(run_dir))
        return self._send_json({"error": "unknown endpoint"}, 404)

    def do_GET(self):
        parts = [p for p in self.path.split("?")[0].split("/") if p]
        if parts[:2] == ["api", "runs"]:
            try:
                return self._api(parts)
            except FileNotFoundError as e:
                return self._send_json({"error": f"missing file: {e}"}, 404)
            except Exception as e:  # noqa: BLE001 — surface, don't crash the loop
                return self._send_json({"error": str(e)}, 500)
        # SPA fallback: a path with no file extension (e.g. a client route)
        # that doesn't resolve to a real file -> serve index.html.
        last = parts[-1] if parts else ""
        if (DIST.is_dir() and "." not in last and self.path != "/"
                and not (DIST / self.path.lstrip("/")).exists()):
            self.path = "/"
        if not DIST.is_dir() and self.path in ("/", "/index.html"):
            body = LANDING.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()


def serve(port=8420):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    where = "dashboard/dist" if DIST.is_dir() else "landing page"
    print(f"frameshift serving at http://127.0.0.1:{port}")
    print(f"  api    : /api/runs")
    print(f"  static : {where}")
    print(f"  runs   : {RUNS}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
