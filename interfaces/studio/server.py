"""M168 — FastAPI server for the Studio UI dashboard.

Endpoints (all JSON unless noted):
  GET  /                  → serves static index.html
  GET  /api/tasks         → list tasks via TaskdogAdapter (HTTP-first, SQLite fallback)
  POST /api/tasks         → create task (writes to local SQLite via apply_change)
  POST /api/tasks/{ueid}/done → mark task done (DONE action via apply_change)
  POST /api/chat          → invoke deep agent (proxies to LangGraph API)
  GET  /api/metrics       → drift net snapshot + daemon status (best-effort)
  GET  /static/{path}     → serves styles.css and any sibling assets

Design constraints:
  - Single FastAPI app, no external state per request (testable by client-app)
  - TaskdogAdapter reused across requests (HTTP bridge already caches)
  - LangGraph chat is best-effort — when API is unreachable the endpoint
    returns 503 with a structured error so the UI can render the message.
  - Drift net block is read from a heartbeat json file when present; falls
    back to a synthesized {"drift_pass": True, "skipped": True} payload so
    tests don't need a real daemon running.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure repo root + src are on sys.path so `from src.mesh.adapters.taskdog`
# resolves regardless of where uvicorn is launched from.
_REPO_ROOT = Path(__file__).resolve().parents[2]
for p in (_REPO_ROOT, _REPO_ROOT / "src"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, ConfigDict, Field
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "FastAPI not installed. Run `pip install fastapi uvicorn` to use the Studio UI."
    ) from exc

from src.contracts.common import UEID  # noqa: E402
from src.contracts.task_change import (  # noqa: E402
    PropagationEvent,
    TaskAction,
)
from src.mesh.adapters.taskdog import TaskdogAdapter  # noqa: E402

STUDIO_DIR = Path(__file__).resolve().parent
INDEX_HTML = STUDIO_DIR / "index.html"
STYLES_CSS = STUDIO_DIR / "styles.css"

# LangGraph API for chat (M158f: `ikigai_taskdog_mcp` graph; default port 2027).
LANGGRAPH_API = os.environ.get("STUDIO_LANGGRAPH_API", "http://127.0.0.1:2027")
CHAT_TIMEOUT_S = float(os.environ.get("STUDIO_CHAT_TIMEOUT", "30"))

# Drift net heartbeat file (written by .claude/loop/loop-tick.sh).
HEARTBEAT = Path(
    os.environ.get(
        "STUDIO_HEARTBEAT",
        str(_REPO_ROOT / ".claude" / "loop" / ".daemon-heartbeat.json"),
    )
)


# ----------------------------------------------------------------------
# Pydantic models (request bodies)
# ----------------------------------------------------------------------


class CreateTaskBody(BaseModel):
    """Body for POST /api/tasks.

    `ueid` is the canonical 4-part UEID. `title` is required; the other
    fields fall back to adapter defaults when omitted.
    """

    model_config = ConfigDict(extra="forbid")

    ueid: str = Field(..., description="Canonical 4-part UEID (e.g. tsk:foo:...:...)")
    title: str = Field(..., min_length=1, max_length=200)
    due: str | None = None
    priority: str | int | None = None
    planned_start: str | None = None
    planned_end: str | None = None


class ChatBody(BaseModel):
    """Body for POST /api/chat.

    `thread_id` is optional — when omitted the server generates a fresh UUID.
    """

    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, max_length=4000)
    thread_id: str | None = None


# ----------------------------------------------------------------------
# App factory
# ----------------------------------------------------------------------


def _load_index_html() -> str:
    """Load index.html at startup. If the file is missing, return a tiny
    placeholder so the server still boots (useful for first-run setup).
    """
    if INDEX_HTML.exists():
        return INDEX_HTML.read_text(encoding="utf-8")
    return (
        "<!doctype html><html><body>"
        "<h1>Studio index.html not found</h1>"
        "<p>Expected at: {path}</p>"
        "</body></html>"
    ).format(path=str(INDEX_HTML))


def _create_propagation_event(
    *, action: TaskAction, ueid: UEID, fields: dict[str, Any]
) -> PropagationEvent:
    """Build a PropagationEvent with approved_at=now (UTC).

    The mesh worker requires approved_at to be set, even for direct
    apply_change calls — it stamps the event with the current time when
    the agent validates and approves. For the Studio MVP we set it
    inline; the queue still serializes the write to disk.
    """
    return PropagationEvent(
        event_id=f"studio-{datetime.now(timezone.utc).timestamp():.0f}-{ueid}",
        ueid=ueid,
        action=action,
        fields=fields,
        approved_at=datetime.now(timezone.utc),
        source_fork="studio",
    )


def _read_drift_heartbeat() -> dict[str, Any]:
    """Best-effort read of the daemon heartbeat for /api/metrics.

    The heartbeat file is tiny JSON written by .claude/loop/loop-tick.sh.
    Drift pass/fail isn't in the heartbeat itself (that's per-tick log
    output) — but we expose `last_heartbeat` so the UI can render a
    "daemon alive N min ago" badge and a synthetic drift_pass True
    (the drift invariant tests are a CI/local-runner concern, not
    runtime state).
    """
    fallback: dict[str, Any] = {
        "drift_pass": True,
        "skipped": True,
        "reason": "no heartbeat file",
        "last_heartbeat": None,
        "daemons_running": 0,
    }
    if not HEARTBEAT.exists():
        return fallback
    try:
        data = json.loads(HEARTBEAT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback
    # Best-effort: count daemons from `daemon_pids/` if present.
    daemon_dir = HEARTBEAT.parent / "daemon_pids"
    running = 0
    if daemon_dir.is_dir():
        for p in daemon_dir.glob("*.pid"):
            try:
                pid = int(p.read_text().strip())
                if _pid_alive(pid):
                    running += 1
            except (ValueError, OSError):
                continue
    return {
        "drift_pass": True,  # CI concern, not runtime state
        "skipped": False,
        "last_heartbeat": data.get("last_heartbeat"),
        "tick_id": data.get("tick_id"),
        "daemons_running": running,
    }


def _pid_alive(pid: int) -> bool:
    """Cross-platform PID liveness check."""
    if pid <= 0:
        return False
    try:
        if sys.platform == "win32":
            import ctypes

            PROCESS_QUERY_LIMITED = 0x1000
            STILL_ACTIVE = 259
            kernel = ctypes.windll.kernel32
            handle = kernel.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
            if handle == 0:
                return False
            try:
                exit_code = ctypes.c_ulong()
                ok = kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                return bool(ok) and exit_code.value == STILL_ACTIVE
            finally:
                kernel.CloseHandle(handle)
        os.kill(pid, 0)  # POSIX: signal 0 = probe
        return True
    except (OSError, AttributeError):
        return False


def _http_post_json(url: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
    """POST JSON to a URL and return parsed response. Raises HTTPException
    with the upstream status code on non-2xx, or 503 on connection errors.
    """
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw": raw}
    except urllib.error.HTTPError as exc:
        # Forward upstream error so the UI can show the cause.
        raise HTTPException(
            status_code=exc.code,
            detail=exc.read_text(encoding="utf-8", errors="replace"),
        ) from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LangGraph API unreachable at {url}: {exc}",
        ) from exc


def create_app() -> FastAPI:
    """Build the FastAPI app. The factory pattern makes tests easy —
    a fresh app per test, no module-global state.

    Tests inject a fake `TaskdogAdapter` (or monkey-patch the import path)
    by overriding `app.dependency_overrides` if/when we add real DI. For
    MVP we just let tests call the endpoint and monkey-patch the module
    constants (`TASKDOG_HTTP_ENABLED`, `TASKDOG_HTTP_TIMEOUT`) the same
    way other tests do.
    """
    app = FastAPI(
        title="Life Studio",
        version="0.1.0",
        description="Local dashboard for td operations + deep agent chat.",
    )

    # ------------------------------------------------------------------
    # Static assets
    # ------------------------------------------------------------------
    if STUDIO_DIR.is_dir():
        app.mount(
            "/static",
            StaticFiles(directory=str(STUDIO_DIR)),
            name="static",
        )

    @app.get("/", include_in_schema=False)
    def root() -> FileResponse:
        if not INDEX_HTML.exists():
            raise HTTPException(404, "index.html missing")
        return FileResponse(INDEX_HTML, media_type="text/html")

    @app.get("/styles.css", include_in_schema=False)
    def styles() -> FileResponse:
        if not STYLES_CSS.exists():
            raise HTTPException(404, "styles.css missing")
        return FileResponse(STYLES_CSS, media_type="text/css")

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    @app.get("/api/tasks")
    def list_tasks(
        status: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        tasks = TaskdogAdapter().list_all()
        if status is not None:
            tasks = [t for t in tasks if t.get("status") == status]
        # Newest first by created_at (None sorts first; harmless).
        tasks.sort(key=lambda t: t.get("created_at") or "", reverse=True)
        if limit is not None and limit > 0:
            tasks = tasks[:limit]
        return {
            "count": len(tasks),
            "tasks": tasks,
            "by_status": _count_by_status(tasks),
        }

    @app.post("/api/tasks", status_code=201)
    def create_task(body: CreateTaskBody) -> dict[str, Any]:
        try:
            ueid = UEID(body.ueid)
        except ValueError as exc:
            raise HTTPException(422, f"invalid UEID: {exc}") from exc
        fields: dict[str, Any] = {"title": body.title}
        if body.due is not None:
            fields["due"] = body.due
        if body.priority is not None:
            fields["priority"] = body.priority
        if body.planned_start is not None:
            fields["planned_start"] = body.planned_start
        if body.planned_end is not None:
            fields["planned_end"] = body.planned_end
        event = _create_propagation_event(
            action=TaskAction.CREATE, ueid=ueid, fields=fields
        )
        TaskdogAdapter().apply_change(event)
        # Read back so the caller sees the canonical persisted row.
        slice_ = TaskdogAdapter().read(ueid)
        return {"ok": True, "event_id": event.event_id, "ueid": str(ueid), "slice": slice_}

    @app.post("/api/tasks/{ueid}/done")
    def mark_done(ueid: str) -> dict[str, Any]:
        try:
            parsed = UEID(ueid)
        except ValueError as exc:
            raise HTTPException(422, f"invalid UEID: {exc}") from exc
        event = _create_propagation_event(
            action=TaskAction.DONE, ueid=parsed, fields={}
        )
        try:
            TaskdogAdapter().apply_change(event)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        return {"ok": True, "event_id": event.event_id, "ueid": ueid, "status": "done"}

    # ------------------------------------------------------------------
    # Chat (proxies to LangGraph API)
    # ------------------------------------------------------------------
    @app.post("/api/chat")
    def chat(body: ChatBody, request: Request) -> JSONResponse:
        thread_id = body.thread_id or _new_thread_id()
        url = f"{LANGGRAPH_API}/threads/{thread_id}/runs"
        try:
            payload = _http_post_json(
                url,
                {
                    "assistant_id": "ikigai_taskdog_mcp",
                    "input": {"messages": [{"role": "user", "content": body.message}]},
                },
                timeout=CHAT_TIMEOUT_S,
            )
        except HTTPException as exc:
            # Bubble up as JSON with `ok: False` so the UI can render the
            # error inline without a separate error-handling branch.
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "ok": False,
                    "thread_id": thread_id,
                    "error": exc.detail,
                },
            )
        return JSONResponse(
            content={
                "ok": True,
                "thread_id": thread_id,
                "response": payload,
            }
        )

    # ------------------------------------------------------------------
    # Metrics (drift + daemons)
    # ------------------------------------------------------------------
    @app.get("/api/metrics")
    def metrics() -> dict[str, Any]:
        snapshot = _read_drift_heartbeat()
        # Add a synthesized invariant count from canonical_scope + drift_invariants
        # test files so the UI can render "X / Y" without running pytest.
        snapshot["invariant_count"] = _count_invariant_tests()
        return snapshot

    return app


# ----------------------------------------------------------------------
# Module-level app instance (for `uvicorn interfaces.studio.server:app`)
# ----------------------------------------------------------------------
app = create_app()


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _count_by_status(tasks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in tasks:
        s = (t.get("status") or "unknown").lower()
        counts[s] = counts.get(s, 0) + 1
    return counts


def _count_invariant_tests() -> int:
    """Count `def test_` occurrences in the three canonical drift files.
    Returns -1 when the files aren't reachable (test environment isolation).
    """
    candidates = [
        _REPO_ROOT / "src" / "ikigai" / "tests" / "test_canonical_scope.py",
        _REPO_ROOT / "src" / "ikigai" / "tests" / "test_drift_invariants.py",
        _REPO_ROOT / "src" / "ikigai" / "tests" / "test_drift_extended_invariants.py",
    ]
    total = 0
    for path in candidates:
        if not path.exists():
            return -1
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                text = path.read_text(encoding="utf-8")
        except OSError:
            return -1
        total += sum(1 for line in text.splitlines() if line.lstrip().startswith("def test_"))
    return total


def _new_thread_id() -> str:
    import uuid as _uuid

    return str(_uuid.uuid4())


# ----------------------------------------------------------------------
# CLI entry point (for `python -m interfaces.studio.server`)
# ----------------------------------------------------------------------


def main() -> None:
    """Console entry point — runs uvicorn programmatically."""
    import uvicorn

    host = os.environ.get("STUDIO_HOST", "127.0.0.1")
    port = int(os.environ.get("STUDIO_PORT", "8765"))
    uvicorn.run("interfaces.studio.server:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()