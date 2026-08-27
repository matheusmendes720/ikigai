"""File-backed task queue for agent work distribution.

Matches LangGraph's concept of a shared work queue that persists across agent runs.
Tasks are JSON files on disk — durable, inspectable, and recoverable.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class Task(BaseModel):
    """A single unit of work in the queue."""

    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    name: str = Field(description="Human-readable task name")
    description: str = Field(default="")
    agent_id: str | None = Field(
        default=None,
        description="Assigned agent node ID (None = unassigned)",
    )
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    priority: TaskPriority = Field(default=TaskPriority.NORMAL)
    payload: dict[str, Any] = Field(default_factory=dict, description="Task input data")
    result: dict[str, Any] | None = Field(default=None, description="Task output data")
    error: str | None = Field(default=None)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str | None = Field(default=None)
    finished_at: str | None = Field(default=None)
    tags: list[str] = Field(default_factory=list)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=2)

    def duration_s(self) -> float | None:
        if self.started_at and self.finished_at:
            start = datetime.fromisoformat(self.started_at)
            finish = datetime.fromisoformat(self.finished_at)
            return (finish - start).total_seconds()
        return None


class TaskQueue:
    """File-backed FIFO + priority queue using JSON files on disk.

    Structure:
        ~/.time-tasker/agent_harness/{workflow_id}_queue/
            pending/       ← one JSON file per task
            running/       ← tasks currently being executed
            done/          ← completed tasks (for history)
            failed/        ← failed tasks

    Internally uses a manifest JSON file to track task ordering by priority.
    """

    def __init__(self, workflow_id: str, base_dir: Path | None = None):
        if base_dir is None:
            base_dir = Path.home() / ".time-tasker" / "agent_harness"
        self.base_dir = base_dir / f"{workflow_id}_queue"
        self.manifest_path = self.base_dir / "manifest.json"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for subdir in ("pending", "running", "done", "failed"):
            (self.base_dir / subdir).mkdir(parents=True, exist_ok=True)

    # ── Manifest helpers ──────────────────────────────────────────────────

    def _read_manifest(self) -> dict[str, dict]:
        if self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return {}

    def _write_manifest(self, manifest: dict[str, dict]) -> None:
        self.manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    def _task_path(self, task_id: str, subdir: str) -> Path:
        return self.base_dir / subdir / f"{task_id}.json"

    # ── Queue operations ──────────────────────────────────────────────────

    def enqueue(self, task: Task) -> str:
        """Add a task to the queue. Returns task ID."""
        manifest = self._read_manifest()
        manifest[task.id] = {
            "id": task.id,
            "status": task.status.value,
            "priority": task.priority.value,
            "name": task.name,
            "agent_id": task.agent_id,
            "created_at": task.created_at,
        }
        self._write_manifest(manifest)
        self._task_path(task.id, "pending").write_text(
            task.model_dump_json(indent=2), encoding="utf-8"
        )
        return task.id

    def dequeue(self, agent_id: str | None = None) -> Task | None:
        """Pop the highest-priority pending task (optionally filtered by agent_id)."""
        manifest = self._read_manifest()
        pending = [
            (tid, meta) for tid, meta in manifest.items()
            if meta["status"] == TaskStatus.PENDING.value
            and (agent_id is None or meta.get("agent_id") is None or meta.get("agent_id") == agent_id)
        ]
        if not pending:
            return None

        # Sort by priority desc, then created_at asc
        pending.sort(key=lambda x: (-x[1]["priority"], x[1]["created_at"]))
        task_id, _ = pending[0]

        # Load full task
        task = Task.model_validate_json(
            self._task_path(task_id, "pending").read_text(encoding="utf-8")
        )
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(UTC).isoformat()
        task.agent_id = agent_id

        # Update manifest + move to running/
        manifest[task_id]["status"] = TaskStatus.RUNNING.value
        manifest[task_id]["started_at"] = task.started_at
        manifest[task_id]["agent_id"] = agent_id
        self._write_manifest(manifest)

        (self.base_dir / "pending" / f"{task_id}.json").unlink(missing_ok=True)
        self._task_path(task_id, "running").write_text(
            task.model_dump_json(indent=2), encoding="utf-8"
        )
        return task

    def complete(self, task_id: str, result: dict[str, Any]) -> None:
        manifest = self._read_manifest()
        if task_id in manifest:
            manifest[task_id]["status"] = TaskStatus.DONE.value
            manifest[task_id]["finished_at"] = datetime.now(UTC).isoformat()
            self._write_manifest(manifest)

        task_file = self._task_path(task_id, "running")
        if task_file.exists():
            task = Task.model_validate_json(task_file.read_text(encoding="utf-8"))
            task.status = TaskStatus.DONE
            task.finished_at = datetime.now(UTC).isoformat()
            task.result = result
            task_file.rename(self._task_path(task_id, "done"))

    def fail(self, task_id: str, error: str) -> None:
        manifest = self._read_manifest()
        if task_id in manifest:
            manifest[task_id]["status"] = TaskStatus.FAILED.value
            manifest[task_id]["finished_at"] = datetime.now(UTC).isoformat()
            manifest[task_id]["error"] = error
            self._write_manifest(manifest)

        task_file = self._task_path(task_id, "running")
        if task_file.exists():
            task = Task.model_validate_json(task_file.read_text(encoding="utf-8"))
            task.status = TaskStatus.FAILED
            task.finished_at = datetime.now(UTC).isoformat()
            task.error = error
            task_file.rename(self._task_path(task_id, "failed"))

    # ── Inspection ────────────────────────────────────────────────────────

    def stats(self) -> dict[str, int]:
        manifest = self._read_manifest()
        counts: dict[str, int] = {s.value: 0 for s in TaskStatus}
        for meta in manifest.values():
            counts[meta["status"]] = counts.get(meta["status"], 0) + 1
        return counts

    def list_pending(self, limit: int = 50) -> list[Task]:
        tasks = []
        for fpath in sorted((self.base_dir / "pending").glob("*.json"))[:limit]:
            try:
                tasks.append(Task.model_validate_json(fpath.read_text(encoding="utf-8")))
            except Exception:
                continue
        return sorted(tasks, key=lambda t: (-t.priority.value, t.created_at))

    def list_done(self, limit: int = 20) -> list[Task]:
        tasks = []
        for fpath in sorted((self.base_dir / "done").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            try:
                tasks.append(Task.model_validate_json(fpath.read_text(encoding="utf-8")))
            except Exception:
                continue
        return tasks

    def get_task(self, task_id: str) -> Task | None:
        for subdir in ("pending", "running", "done", "failed"):
            p = self._task_path(task_id, subdir)
            if p.exists():
                return Task.model_validate_json(p.read_text(encoding="utf-8"))
        return None
