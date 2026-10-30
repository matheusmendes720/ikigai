"""Paperclip run-state persistence — JSON snapshots to ``data/paperclip/runs/``.

Each completed (or failed) Paperclip invocation writes a structured JSON
snapshot for post-mortem debugging. Snapshots are append-only; old runs
are GC'd at ``MAX_RUNS`` (100, configurable) to keep the directory bounded.

Path layout::

    <runs_dir>/<YYYY-MM-DDTHH-MM-SS>Z_<task_id>.json

Each file is a single JSON object with the following shape::

    {
        "run_id": "uuid",
        "task_id": "hello-world",
        "started_at": "2026-10-12T01:42:17Z",
        "finished_at": "2026-10-12T01:42:42Z",
        "duration_s": 25.0,
        "adapter": "pi",
        "status": "ok" | "error" | "spec_ambiguous",
        "gates_consulted": [{"gate": "CostGate", "allowed": true, "reason": "..."}],
        "steps": [
            {"node": "read_spec", "ts": "...", "keys": [...], "error_type": null}
        ],
        "final_state": {"commit_sha": "...", "tests_ok": true, ...}
    }

Filename timestamps use ISO 8601 ``YYYY-MM-DDTHH-MM-SSZ`` so lexical sort
matches chronological order — older files are detected first by
``list_recent_runs()`` and GC'd first when the directory grows.

GC is best-effort: locked files (Windows transient I/O) are logged and
skipped rather than raising — the caller has more important things to
worry about than post-mortem cleanup.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("paperclip.persistence")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_RUNS_DIR = Path("data/paperclip/runs")
MAX_RUNS = 100  # GC after this many files

VALID_STATUSES = ("ok", "error", "spec_ambiguous", "blocked_by_gate", "running")


# ---------------------------------------------------------------------------
# RunRecord — in-memory snapshot of one Paperclip run
# ---------------------------------------------------------------------------
@dataclass
class RunRecord:
    """Structured snapshot of one Paperclip run; serialises to JSON via :meth:`to_dict`.

    Fields mirror the JSON schema in the module docstring. ``to_dict``
    handles the type-coercion dance (Path -> str, datetime -> ISO str)
    so callers can build the record with natural types.
    """

    task_id: str
    started_at: str
    finished_at: str | None = None
    duration_s: float | None = None
    adapter: str = "unknown"
    status: str = "running"
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    gates_consulted: list[dict[str, Any]] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    final_state: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dict (all values are primitives, lists, or dicts)."""
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_s": self.duration_s,
            "adapter": self.adapter,
            "status": self.status,
            "gates_consulted": list(self.gates_consulted),
            "steps": list(self.steps),
            "final_state": self._sanitize_final_state(),
            "error": self.error,
        }

    def _sanitize_final_state(self) -> dict[str, Any]:
        """Drop non-JSON-safe values from ``final_state`` (Path, set, etc.)."""
        out: dict[str, Any] = {}
        for k, v in self.final_state.items():
            if isinstance(v, (str, int, float, bool, list, dict, type(None))):
                out[k] = v
            else:
                out[k] = str(v)
        return out


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------
def _filename_ts(now: datetime | None = None) -> str:
    """ISO 8601 ``YYYY-MM-DDTHH-MM-SSZ`` (filesystem-safe, lexically sortable)."""
    when = now or datetime.now(UTC)
    return when.strftime("%Y-%m-%dT%H-%M-%SZ")


def _safe_task_id(task_id: str) -> str:
    """Sanitise ``task_id`` for filesystem (replace path separators)."""
    return task_id.replace("/", "_").replace("\\", "_").replace("..", "_").strip() or "unknown"


# ---------------------------------------------------------------------------
# persist_run — write one snapshot to disk
# ---------------------------------------------------------------------------
def persist_run(
    record: RunRecord,
    runs_dir: Path = DEFAULT_RUNS_DIR,
    *,
    max_runs: int = MAX_RUNS,
    now: datetime | None = None,
) -> Path:
    """Write ``record`` to ``<runs_dir>/<ts>_<task_id>.json``.

    Returns the resolved file path. Creates ``runs_dir`` if missing. When
    the directory holds more than ``max_runs`` files, deletes the oldest
    (lexical sort on the filename timestamp prefix is equivalent to
    chronological order for our ISO 8601 format).

    Args:
        record: The run snapshot to serialise.
        runs_dir: Target directory (default ``data/paperclip/runs``).
        max_runs: GC trigger — oldest files removed when count exceeds this.
        now: Override clock for tests; defaults to ``datetime.now(UTC)``.

    Returns:
        The :class:`Path` of the written file.
    """
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)

    ts = _filename_ts(now)
    safe_id = _safe_task_id(record.task_id)
    path = runs_dir / f"{ts}_{safe_id}.json"

    payload = record.to_dict()
    # Atomic write — write to .tmp then rename so a crashed process never
    # leaves a half-written JSON file in the runs directory.
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    log.info("persisted run %s to %s", record.run_id, path)
    _gc_runs_dir(runs_dir, max_runs=max_runs)
    return path


def _gc_runs_dir(runs_dir: Path, *, max_runs: int) -> None:
    """Delete oldest files when ``runs_dir`` has more than ``max_runs`` entries.

    Best-effort: locked files are logged and skipped, never raised.
    """
    try:
        files = sorted(runs_dir.glob("*.json"))
    except OSError as exc:
        log.warning("could not list runs dir %s: %s", runs_dir, exc)
        return

    excess = len(files) - max_runs
    if excess <= 0:
        return

    for old_path in files[:excess]:
        try:
            old_path.unlink()
            log.info("gc removed %s", old_path)
        except OSError as exc:
            log.warning("gc skipped %s: %s", old_path, exc)


# ---------------------------------------------------------------------------
# list_recent_runs — most-recent N runs, newest first
# ---------------------------------------------------------------------------
def list_recent_runs(
    runs_dir: Path = DEFAULT_RUNS_DIR,
    *,
    limit: int = 20,
) -> list[Path]:
    """Return paths to the most recent ``limit`` run files, newest first.

    Newest-first ordering is achieved by reverse-sorting on the filename
    timestamp prefix (ISO 8601 ``YYYY-MM-DDTHH-MM-SSZ``). Returns an empty
    list when ``runs_dir`` does not exist.
    """
    runs_dir = Path(runs_dir)
    if not runs_dir.exists():
        return []
    try:
        files = sorted(runs_dir.glob("*.json"), reverse=True)
    except OSError as exc:
        log.warning("could not list runs dir %s: %s", runs_dir, exc)
        return []
    return files[:limit]


# ---------------------------------------------------------------------------
# load_run — read one snapshot back as a dict
# ---------------------------------------------------------------------------
def load_run(path: Path) -> dict[str, Any]:
    """Load one run file as a :class:`dict` (for TUI / dashboard inspection).

    Raises :class:`FileNotFoundError` if ``path`` is missing,
    :class:`json.JSONDecodeError` if the file is corrupt.
    """
    path = Path(path)
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result


# ---------------------------------------------------------------------------
# Convenience builder — capture a RunRecord from graph invocation outputs
# ---------------------------------------------------------------------------
def build_record_from_state(
    *,
    task_id: str,
    adapter: str,
    started_at: str,
    finished_at: str | None,
    steps: list[dict[str, Any]],
    final_state: dict[str, Any],
    gates_consulted: list[dict[str, Any]],
    error: str | None = None,
) -> RunRecord:
    """Build a :class:`RunRecord` from the captured CLI run-output bag. Status
    is derived from ``final_state.error_type`` / ``error``.
    """
    duration: float | None = None
    if started_at and finished_at:
        try:
            t0 = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
            duration = max(0.0, (t1 - t0).total_seconds())
        except ValueError:
            duration = None

    err_type = (final_state or {}).get("error_type")
    if error is not None or err_type:
        status = "error"
    else:
        status = "ok"

    return RunRecord(
        task_id=task_id,
        started_at=started_at,
        finished_at=finished_at,
        duration_s=duration,
        adapter=adapter,
        status=status,
        gates_consulted=list(gates_consulted),
        steps=list(steps),
        final_state=dict(final_state or {}),
        error=error,
    )
