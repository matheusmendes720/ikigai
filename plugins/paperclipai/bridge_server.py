from __future__ import annotations

import asyncio, json, logging, os, sys, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

BIND_HOST = os.environ.get("LIFE_PAPERCLIP_BIND", "127.0.0.1")
BIND_PORT = int(os.environ.get("LIFE_PAPERCLIP_PORT", "8741"))

LIFE_ROOT = Path(__file__).resolve().parents[2]
VAULT_DIR = LIFE_ROOT / "vault"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("bridge")


_io_loop: asyncio.AbstractEventLoop | None = None


def _io_thread_main():
    global _io_loop
    _io_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_io_loop)
    _io_loop.run_forever()


_io_thread = threading.Thread(target=_io_thread_main, daemon=True)
_io_thread.start()
time.sleep(0.1)


def _run_async(coro):
    future = asyncio.run_coroutine_threadsafe(coro, _io_loop)
    return future.result(timeout=30)


async def _cli_async(*args: str) -> tuple[int, str, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "interfaces.cli", *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(LIFE_ROOT),
        )
        try:
            out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return (124, "", "timed out")
        return (proc.returncode, out_b.decode(errors="replace"), err_b.decode(errors="replace"))
    except Exception as exc:
        return (1, "", str(exc))


def _cli_json(*args: str) -> dict:
    code, stdout, stderr = _run_async(_cli_async(*args, "--json"))
    if code == 0:
        try:
            return json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            return {"ok": False, "error": "json decode error", "stderr": stderr}
    return {"ok": False, "error": f"exit {code}", "stderr": stderr}


def _handle_status() -> dict:
    code, stdout, stderr = _run_async(_cli_async("--version"))
    return {"status": "ok" if code == 0 else "degraded", "version": stdout.strip() or "unknown", "stderr": stderr[:100]}


def _handle_task_add(params: dict) -> dict:
    return _cli_json(
        "task-add",
        "--title", params.get("title", ""),
        "--priority", params.get("priority", "medium"),
        "--description", params.get("description") or "",
    )


def _handle_plan_run(params: dict) -> dict:
    goal = params.get("goal", "")
    return _cli_json("v2", "plan", "--goal", goal)


def _handle_vault_read(params: dict) -> dict:
    rel = params.get("path", "")
    if not rel or rel.startswith("/") or ".." in rel:
        return {"ok": False, "error": "invalid path"}
    abs_path = (VAULT_DIR / rel).resolve()
    try:
        abs_path.relative_to(VAULT_DIR.resolve())
    except ValueError:
        return {"ok": False, "error": "path outside vault"}
    if not abs_path.is_file():
        return {"ok": False, "error": f"not found: {rel}"}
    try:
        return {"ok": True, "content": abs_path.read_text(encoding="utf-8"), "path": str(abs_path)}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def _handle_issue_sync(params: dict) -> dict:
    from datetime import datetime, timezone
    sync_log = VAULT_DIR / "paperclipai_issues" / "sync_log.md"
    sync_log.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    line = (
        f"- [{ts}] event={params.get('event')} entityId={params.get('entityId')} "
        f"source={params.get('source', 'paperclipai')}\n"
    )
    with sync_log.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return {"ok": True, "synced": True}


class BridgeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, status: int, body: dict):
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/status":
            self._json(200, _handle_status())
            return
        if self.path.startswith("/sync/vault"):
            qs = self.path.split("?", 1)
            params = dict(kv.split("=", 1) for kv in qs[1].split("&") if "=" in kv) if len(qs) > 1 else {}
            self._json(200, _handle_vault_read(params))
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path not in ("/invoke", "/sync/issues"):
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except json.JSONDecodeError as exc:
            self._json(400, {"ok": False, "error": str(exc)})
            return
        if self.path == "/invoke":
            action = payload.get("action", "")
            params = payload.get("params", {})
            handlers = {"task_add": _handle_task_add, "plan_run": _handle_plan_run}
            result = handlers.get(action, lambda _: {"ok": False, "error": f"unknown action: {action}"})(params)
            self._json(200 if result.get("ok") else 422, result)
        else:
            self._json(200, _handle_issue_sync(payload))

    def log_message(self, fmt, *args):
        pass


def main():
    try:
        server = HTTPServer((BIND_HOST, BIND_PORT), BridgeHandler)
    except OSError as exc:
        log.error("Failed to bind %s:%s: %s", BIND_HOST, BIND_PORT, exc)
        sys.exit(1)
    log.info("Bridge server listening on http://%s:%s", BIND_HOST, BIND_PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
