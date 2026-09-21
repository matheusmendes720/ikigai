"""Adapter for interfaces/cli tasks.jsonl file."""

import json
import os
import sys
from pathlib import Path
from typing import Any

from contracts.common import UEID
from contracts.task_change import PropagationEvent

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TASKS_JSONL = PROJECT_ROOT / "data" / "tasks.jsonl"

# R1.1: 14-field unified schema (replaces the prior 6-field set).
# Spans the prior CliAdapter fields AND the _write_tasks_to_data fields
# (sys_ikigai/vault/task_io.py) so the schema has a single source of truth.
SUPPORTED_FIELDS = {
    "id",
    "title",
    "description",
    "horizon",
    "priority",
    "project_id",
    "estimated_minutes",
    "done",
    "done_at",
    "ueid",
    "vector",
    "due",
    "written_at",
    "source_fork",
}


class CliAdapter:
    """Read/write the interfaces/cli tasks.jsonl slice."""

    name = "cli"

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        if not TASKS_JSONL.exists():
            return None
        for line in TASKS_JSONL.read_text().splitlines():
            if not line.strip():
                continue
            task: dict[str, Any] = json.loads(line)
            if task.get("ueid") == ueid:
                return task
        return None

    @staticmethod
    def _acquire_file_lock(fh) -> None:
        """R1.2: cross-platform exclusive lock on a binary-mode lock file.

        POSIX  → fcntl.flock(LOCK_EX)
        Windows → msvcrt.locking(fd, LK_LOCK, 1)

        `fh` must be opened in BINARY mode — `msvcrt.locking` raises
        `PermissionError` on text-mode handles on Windows. We deliberately
        use a sidecar lock file (TASKS_JSONL.lock) instead of locking the
        JSONL itself, because:
          - `os.replace` on Windows fails if the target is open (even
            briefly) for shared write — keeping TASKS_JSONL closed during
            the rename avoids spurious PermissionError.
          - text-mode `open(..., encoding='utf-8')` is incompatible with
            msvcrt.locking. Binary mode is required.
        """
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)

    @staticmethod
    def _release_file_lock(fh) -> None:
        """Release the lock acquired by `_acquire_file_lock`."""
        if sys.platform == "win32":
            import msvcrt

            try:
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                # Already unlocked (e.g. file was never locked by us)
                pass
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def apply_change(self, event: PropagationEvent) -> None:
        if event.action.value != "create":
            return  # v1 only supports create

        TASKS_JSONL.parent.mkdir(parents=True, exist_ok=True)
        # R1.1: Persist the unified 14-field schema. `event.fields` carries the
        # caller-supplied payload (from Deep Agent via ikigai_write_tasks);
        # `id`/`written_at`/`source_fork` are filled in from the event metadata.
        record = {
            "id": event.fields.get("id"),
            "title": event.fields.get("title"),
            "description": event.fields.get("description"),
            "horizon": event.fields.get("horizon"),
            "priority": event.fields.get("priority", "medium"),
            "project_id": event.fields.get("project_id"),
            "estimated_minutes": event.fields.get("estimated_minutes"),
            "done": event.fields.get("done", False),
            "done_at": event.fields.get("done_at"),
            "ueid": event.ueid,
            "vector": event.fields.get("vector"),
            "due": event.fields.get("due"),
            "written_at": event.approved_at.isoformat(),
            "source_fork": event.source_fork,
        }
        line = json.dumps(record) + "\n"

        # R1.2: Serialize concurrent writers via a sidecar lock file. Without
        # this, two writers (e.g. MCP co-fire + worker.run_once) can race:
        # writer A reads existing (no ueid), writer B reads existing (no ueid),
        # both write/rename, last rename wins and one record is silently lost.
        #
        # Companion test in tests/mesh/adapters/test_cli.py asserts the
        # 5-writer round-trip is lossless.
        lock_path = TASKS_JSONL.with_name(TASKS_JSONL.name + ".lock")
        with lock_path.open("wb") as lock_fh:
            self._acquire_file_lock(lock_fh)
            try:
                # Dedup: read existing, skip if ueid already present. O(n) but
                # acceptable for v1 task counts (dozens, not millions). The
                # other adapters (Taskdog, SolverforgeCalendar) use SQLite
                # UPSERT; CliAdapter uses JSONL because the slice is meant to
                # be human-readable.
                existing = (
                    TASKS_JSONL.read_text(encoding="utf-8")
                    if TASKS_JSONL.exists()
                    else ""
                )
                for prev_line in existing.splitlines():
                    if not prev_line.strip():
                        continue
                    try:
                        prev = json.loads(prev_line)
                    except json.JSONDecodeError:
                        continue
                    if prev.get("ueid") == str(event.ueid):
                        # Idempotent: do_task_add + worker.run_once both call
                        # us for the same CREATE event; only the first call
                        # writes.
                        return

                # Atomic append via temp + rename (works on Windows + Unix).
                tmp = TASKS_JSONL.with_suffix(".tmp")
                tmp.write_text(existing + line, encoding="utf-8")
                os.replace(tmp, TASKS_JSONL)
            finally:
                self._release_file_lock(lock_fh)

    def supports_field(self, field_name: str) -> bool:
        return field_name in SUPPORTED_FIELDS
