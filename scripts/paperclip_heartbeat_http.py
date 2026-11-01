"""Paperclip canonical HTTP adapter — Phase 1 of the migration path.

Wraps our M169 ``_build_paperclip_graph`` factory as a stdlib HTTP
server so the canonical Paperclip (``paperclipai/paperclip``, 67k⭐
MIT) can POST heartbeats to us. Per
``paperclip-orchestrator-specs.md`` §6.4 + §9.3, this is the **parallel
run** step — both systems run side-by-side, neither replaces the other.

Contract (matches §6.4 verbatim):

    POST /heartbeat
    Authorization: Bearer {HEARTBEAT_TOKEN}
    Body: {"runId", "agentId", "context": {"taskId", "wakeReason"},
           "specText", ...custom payloadTemplate fields...}

    → HTTP 200 with {"status", "commitSha", "worktreePath", "error"}

Env vars:
    HEARTBEAT_PORT  (default 8765)
    HEARTBEAT_TOKEN (default "dev-token-do-not-use-in-prod")

Run:
    python scripts/paperclip_heartbeat_http.py
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — add <repo>/src so paperclip imports resolve.
# ---------------------------------------------------------------------------
THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parent.parent
SRC_ROOT = REPO_ROOT / "src"
for _p in (str(REPO_ROOT), str(SRC_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.ikigai.src.agents.paperclip.graph import (  # noqa: E402
    _build_paperclip_graph,
)
from src.ikigai.src.agents.paperclip.state import (  # noqa: E402
    PaperclipStateDict,
)

# ---------------------------------------------------------------------------
# Configuration (env-driven; no hardcoded secrets)
# ---------------------------------------------------------------------------
HEARTBEAT_PORT = int(os.environ.get("HEARTBEAT_PORT", "8765"))
HEARTBEAT_TOKEN = os.environ.get("HEARTBEAT_TOKEN", "dev-token-do-not-use-in-prod")
DEFAULT_CHECKPOINT_DB = os.environ.get("PAPERCLIP_CHECKPOINT_DB", "data/paperclip.db")


def _build_initial_state(payload: dict[str, Any]) -> PaperclipStateDict:
    """Map canonical Paperclip's heartbeat payload onto PaperclipStateDict.

    Per M190-paperclip-canonical-adapter/SPEC.md "Field mapping":
    context.taskId → task_id, specText → spec_text, messages=[] (OPEN-3).
    """
    context = payload.get("context") or {}
    return {
        "task_id": context.get("taskId") or payload.get("taskId") or "",
        "spec_text": payload.get("specText") or "",
        "messages": [],
    }


def handle_heartbeat(payload: dict[str, Any]) -> dict[str, Any]:
    """Pure function — invoke the paperclip graph for one heartbeat payload.

    Returns the RunHandle shape canonical Paperclip expects. Exposed as
    a module-level function so the unit tests can call it without
    spinning up an HTTP server.
    """
    run_id = str(payload.get("runId") or "")
    initial_state = _build_initial_state(payload)
    task_id = initial_state.get("task_id") or "heartbeat-unknown"

    config = {
        "configurable": {
            "thread_id": task_id,
            "checkpoint_db": DEFAULT_CHECKPOINT_DB,
            "entry_point": "read_spec",
        }
    }

    try:
        graph = _build_paperclip_graph(checkpoint_db=DEFAULT_CHECKPOINT_DB, entry_point="read_spec")
        final = graph.invoke(initial_state, config=config)
    except Exception as exc:
        return {
            "status": "failed",
            "runId": run_id,
            "commitSha": None,
            "worktreePath": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

    err_type = (final or {}).get("error_type")
    if err_type:
        return {
            "status": "failed",
            "runId": run_id,
            "commitSha": final.get("commit_sha"),
            "worktreePath": final.get("worktree_path"),
            "error": f"{err_type}: {final.get('error_message', '')}",
        }

    return {
        "status": "succeeded",
        "runId": run_id,
        "commitSha": final.get("commit_sha"),
        "worktreePath": final.get("worktree_path"),
        "error": None,
    }


# ---------------------------------------------------------------------------
# HTTP handler (stdlib http.server)
# ---------------------------------------------------------------------------
class HeartbeatHandler(BaseHTTPRequestHandler):
    """Validates the Authorization header, parses the JSON body, and
    delegates to ``handle_heartbeat``. Only POST /heartbeat is handled;
    every other route returns 404.
    """

    def do_GET(self) -> None:
        self.send_error(404, "POST /heartbeat only")

    def do_POST(self) -> None:
        if self.path != "/heartbeat":
            self.send_error(404, f"unknown route: {self.path}")
            return

        # The body is drained BEFORE the authorization check: answering 401
        # while the request body is still unread makes the client see a
        # connection reset (httpx.ReadError / WinError 10053) instead of the
        # 401. Reproduced in 3 of 6 runs of the root suite before the fix.
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b""

        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {HEARTBEAT_TOKEN}":
            self._write_json(401, {"error": "unauthorized"})
            return
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._write_json(400, {"error": f"invalid JSON: {exc}"})
            return

        if not payload.get("context", {}).get("taskId") and not payload.get("taskId"):
            self._write_json(422, {"error": "taskId missing from payload"})
            return
        if not payload.get("specText"):
            self._write_json(422, {"error": "specText missing from payload"})
            return

        result = handle_heartbeat(payload)
        self._write_json(200, result)

    def _write_json(self, status: int, body: dict[str, Any]) -> None:
        body_bytes = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def log_message(self, fmt: str, *args: Any) -> None:
        # Quiet default stderr logging; tests assert on response body, not logs.
        sys.stderr.write(f"[paperclip-heartbeat] {fmt % args}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run_server(host: str = "0.0.0.0", port: int = HEARTBEAT_PORT) -> None:
    """Start the heartbeat server on ``host:port``. Blocks forever."""
    server = ThreadingHTTPServer((host, port), HeartbeatHandler)
    sys.stderr.write(
        f"[paperclip-heartbeat] listening on {host}:{port}, "
        f"token=<set {'yes' if HEARTBEAT_TOKEN else 'no'}>"
        "\n"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("[paperclip-heartbeat] shutting down\n")
        server.server_close()


if __name__ == "__main__":
    run_server()
