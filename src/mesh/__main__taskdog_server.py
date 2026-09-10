"""Tiny HTTP server for taskdog SQLite DB on :8000.

B5 fix 2026-09-10: taskdog CLI requires an HTTP server on :8000, but the
taskdog binary has no `serve` subcommand. This module provides a minimal
HTTP bridge that exposes the taskdog SQLite DB at the endpoints taskdog
CLI expects.

Endpoints (matched to taskdog CLI patterns observed in error messages):
- GET  /api/v1/tasks              → list all non-archived tasks
- POST /api/v1/tasks              → create task
- POST /api/v1/tasks/{id}/done    → mark done
- DELETE /api/v1/tasks/{id}       → remove

Why not use a real server? taskdog's HTTP API is undocumented + version-
specific. This is a thin shim covering the CLI's basic operations.
For full taskdog features, run taskdog's actual HTTP server (out of scope
for B5 — see [[loop-prod-ready-broken-state-2026-09-09]]).

Run:
    python -m src.mesh.__main__taskdog_server --port 8000

Or as an entry point (after `pip install -e .`):
    ikigai-taskdog-server
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

# Default taskdog DB path (matches CliAdapter convention; per CLAUDE.md
# `## vibe-ops` TaskdogAdapter uses data/taskdog/tasks.db).
DEFAULT_DB_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "taskdog" / "tasks.db"
)


def _bootstrap_sys_path() -> None:
    """Ensure mesh.adapters is importable for CliAdapter/TaskdogAdapter."""
    module_path = Path(__file__).resolve()
    worktree_src = module_path.parents[2]
    worktree_root = module_path.parents[3]
    for path in (str(worktree_root), str(worktree_src)):
        if path not in sys.path:
            sys.path.insert(0, path)


_bootstrap_sys_path()


class TaskdogRequestHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler exposing the taskdog SQLite DB."""

    db_path: Path = DEFAULT_DB_PATH

    def do_GET(self) -> None:
        if self.path == "/api/v1/tasks" or self.path.startswith("/api/v1/tasks?"):
            self._list_tasks()
        elif self.path.startswith("/api/v1/tasks/"):
            task_id = self.path.split("/")[-1]
            self._get_task(task_id)
        else:
            self._json_response(404, {"error": f"unknown path: {self.path}"})

    def do_POST(self) -> None:
        body = self._read_body()
        if self.path == "/api/v1/tasks":
            self._create_task(body)
        elif "/done" in self.path:
            task_id = self.path.split("/")[-2]
            self._mark_done(task_id)
        else:
            self._json_response(404, {"error": f"unknown path: {self.path}"})

    def do_DELETE(self) -> None:
        if self.path.startswith("/api/v1/tasks/"):
            task_id = self.path.split("/")[-1]
            self._delete_task(task_id)
        else:
            self._json_response(404, {"error": f"unknown path: {self.path}"})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Quieter logs — only print errors
        if "error" in format.lower() or " 5" in format:
            super().log_message(format, *args)

    # --- handlers ---

    def _list_tasks(self) -> None:
        if not self.db_path.exists():
            self._json_response(200, {"tasks": [], "total_count": 0})
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM tasks WHERE status != 'archived'"
                ).fetchall()
                tasks = [dict(r) for r in rows]
            self._json_response(
                200,
                {"tasks": tasks, "total_count": len(tasks)},
            )
        except sqlite3.Error as e:
            self._json_response(500, {"error": f"db error: {e}"})

    def _get_task(self, task_id: str) -> None:
        if not self.db_path.exists():
            self._json_response(404, {"error": "db not found"})
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT * FROM tasks WHERE id = ? OR ueid = ?",
                    (task_id, task_id),
                ).fetchone()
            if row is None:
                self._json_response(404, {"error": f"task {task_id} not found"})
            else:
                conn.row_factory = sqlite3.Row
                self._json_response(200, dict(row))
        except sqlite3.Error as e:
            self._json_response(500, {"error": f"db error: {e}"})

    def _create_task(self, body: dict[str, Any]) -> None:
        # Minimal create — taskdog CLI rarely creates via HTTP
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY, ueid TEXT, title TEXT,
                        status TEXT DEFAULT 'pending', priority TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )"""
                )
                conn.execute(
                    "INSERT INTO tasks (id, title, status, priority) VALUES (?, ?, 'pending', ?)",
                    (body.get("id", "manual"), body.get("title", ""), body.get("priority", "medium")),
                )
                conn.commit()
            self._json_response(201, {"created": body.get("id", "manual")})
        except sqlite3.Error as e:
            self._json_response(500, {"error": f"db error: {e}"})

    def _mark_done(self, task_id: str) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute(
                    "UPDATE tasks SET status = 'done' WHERE id = ? OR ueid = ?",
                    (task_id, task_id),
                )
                conn.commit()
                if cur.rowcount == 0:
                    self._json_response(404, {"error": f"task {task_id} not found"})
                else:
                    self._json_response(200, {"marked_done": task_id})
        except sqlite3.Error as e:
            self._json_response(500, {"error": f"db error: {e}"})

    def _delete_task(self, task_id: str) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute(
                    "DELETE FROM tasks WHERE id = ? OR ueid = ?",
                    (task_id, task_id),
                )
                conn.commit()
                self._json_response(200, {"deleted": task_id, "rows": cur.rowcount})
        except sqlite3.Error as e:
            self._json_response(500, {"error": f"db error: {e}"})

    # --- helpers ---

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _json_response(self, code: int, body: dict[str, Any]) -> None:
        payload = json.dumps(body, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tiny HTTP shim for taskdog DB on :8000")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    TaskdogRequestHandler.db_path = args.db

    server = HTTPServer((args.host, args.port), TaskdogRequestHandler)
    print(f"taskdog HTTP shim listening on http://{args.host}:{args.port} (db={args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
