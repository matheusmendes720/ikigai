"""Vault-to-taskdog sync engine — Phase B6 v1.

Unidirectional: vault markdown (SOT) → taskdog (fork). Incremental diff
against data/sync-state.json. Per-action try/except isolation. Atomic
state writes (write .tmp then rename).

D1: unidirectional vault→taskdog only (no reverse).
D2: on-demand CLI trigger (no daemon/cron).
D3: taskdog is MVP fork (not tuiboard/solverforge-calendar).
D4: frontmatter-tagged tasks as sync unit (tags:[task] OR type:task).
D5: data/sync-state.json incremental diff.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import src.mesh.queue
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# Domain models
# ─────────────────────────────────────────────────────────────────────────────


class SyncActionKind(str, Enum):
    NEW = "new"
    CHANGED = "changed"
    CHANGED_TO_DONE = "changed_to_done"
    UNCHANGED = "unchanged"


class SyncAdapterError(BaseModel):
    """Adapter-level error — happens BEFORE per-task loop.

    Used for failures that have no per-UEID context (e.g. vault parse
    fails before any task is processed, or `adapter.list_all()` throws).
    Discriminator: NO `ueid` field.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    error: str


class SyncPerTaskError(BaseModel):
    """Per-task push/emit error — has UEID context.

    Used when an individual task's adapter call fails inside the
    per-task loop. Discriminator: HAS `ueid` field.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    ueid: str
    error: str


# Discriminated union for SyncResult.errors / ReverseSyncResult.errors.
# Pydantic v2 picks the right model by field presence (ueid present → PerTask).
SyncError = SyncPerTaskError | SyncAdapterError


class TaskRecord(BaseModel):
    """One task extracted from a vault markdown frontmatter."""

    model_config = {"frozen": True, "extra": "forbid"}

    ueid: str
    title: str
    status: str  # "planned" | "in_progress" | "done"
    priority: str | None = None
    due: str | None = None
    vault_path: str


class SyncAction(BaseModel):
    """One classified diff action to push to taskdog."""

    model_config = {"frozen": True, "extra": "forbid"}

    kind: SyncActionKind
    record: TaskRecord
    taskdog_id: str | None = None  # populated after successful push


class SyncTaskEntry(BaseModel):
    """Per-UEID entry stored in sync-state.json."""

    model_config = {"frozen": True, "extra": "forbid"}

    last_synced_at: str
    last_status: str
    taskdog_id: str | None = None
    vault_path: str


class SyncState(BaseModel):
    """Full sync state document."""

    model_config = {"frozen": True, "extra": "forbid"}

    version: int = 1
    last_sync_at: str | None = None
    tasks: dict[str, SyncTaskEntry] = Field(default_factory=dict)


class SyncResult(BaseModel):
    """Summary returned by run_sync().

    Not frozen: run_sync() accumulates counters (scanned, added, updated,
    completed, skipped, parse_errors, errors, duration_s) across the
    parse → diff → push pipeline. The other 4 models are frozen because
    they are immutable snapshots; SyncResult is an accumulator.
    """

    model_config = {"frozen": False, "extra": "forbid"}

    scanned: int = 0
    added: int = 0
    updated: int = 0
    completed: int = 0
    skipped: int = 0
    parse_errors: int = 0
    errors: list[SyncError] = Field(default_factory=list)
    duration_s: float = 0.0


class ReverseSyncTaskEntry(BaseModel):
    """Per-UEID entry stored in sync-state-reverse.json."""

    model_config = {"frozen": True, "extra": "forbid"}

    last_seen_status: str
    last_seen_title: str
    taskdog_id: int | None = None
    vault_path: str | None = None


class ReverseSyncState(BaseModel):
    """Full reverse sync state document — taskdog-side snapshot."""

    model_config = {"frozen": True, "extra": "forbid"}

    version: int = 1
    last_sync_at: str | None = None
    tasks: dict[str, ReverseSyncTaskEntry] = Field(default_factory=dict)


class ReverseSyncResult(BaseModel):
    """Summary returned by reverse_sync() — NOT frozen, accumulates."""

    model_config = {"frozen": False, "extra": "forbid"}

    scanned: int = 0
    emitted: int = 0
    skipped: int = 0
    errors: list[SyncError] = Field(default_factory=list)
    duration_s: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def parse_vault_tasks(vault_root: Path) -> list[TaskRecord]:
    """Walk vault_root/**/*.md, parse frontmatter, return task records.

    Keeps only files where frontmatter has ``tags`` containing ``"task"``
    OR ``type == "task"`` (D4 discriminator).
    """
    from ikigai.vault.frontmatter_to_dict import frontmatter_to_dict

    tasks: list[TaskRecord] = []
    if not vault_root.is_dir():
        return tasks

    for md_path in vault_root.rglob("*.md"):
        try:
            fm = frontmatter_to_dict(md_path)
        except Exception:
            # parse error — skip file, caller counts it
            continue

        # D4 discriminator
        tags: list[str] = fm.get("tags", []) or []
        is_task = "task" in tags or fm.get("type") == "task"
        if not is_task:
            continue

        ueid = fm.get("ueid")
        if not ueid:
            continue

        tasks.append(
            TaskRecord(
                ueid=str(ueid),
                title=str(fm.get("title", "")),
                status=str(fm.get("status", "planned")),
                priority=str(fm.get("priority")) if fm.get("priority") else None,
                due=str(fm.get("due")) if fm.get("due") else None,
                vault_path=str(md_path),
            )
        )
    return tasks


def load_state(state_path: Path) -> SyncState:
    """Read sync state. Initialise empty state if file is absent."""
    if state_path.exists():
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return SyncState.model_validate(data)
    return SyncState(version=1, tasks={})


def save_state(state_path: Path, state: SyncState) -> None:
    """Atomic write: write to .tmp then os.replace() (cross-platform safe).

    os.replace() is atomic on POSIX and silently replaces an existing
    target on Windows. Path.rename() calls os.rename(), which on Windows
    raises FileExistsError if the target exists — breaking the second
    save_state() call in any per-task loop.
    """
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(state.model_dump_json(), encoding="utf-8")
    os.replace(tmp, state_path)


def load_reverse_state(state_path: Path) -> ReverseSyncState:
    """Read reverse sync state. Initialise empty state if file absent."""
    if state_path.exists():
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return ReverseSyncState.model_validate(data)
    return ReverseSyncState(version=1)


def save_reverse_state(state_path: Path, state: ReverseSyncState) -> None:
    """Atomic write: write to .tmp then os.replace() (cross-platform safe)."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(state.model_dump_json(), encoding="utf-8")
    os.replace(tmp, state_path)


def diff(tasks: list[TaskRecord], state: SyncState) -> list[SyncAction]:
    """Classify each vault task against current state.

    NEW      — UEID not in state.tasks
    CHANGED  — status differs from last_status (not "done")
    CHANGED_TO_DONE — status differs AND current status is "done"
    UNCHANGED — status unchanged
    """
    actions: list[SyncAction] = []
    for record in tasks:
        entry = state.tasks.get(record.ueid)
        if entry is None:
            actions.append(SyncAction(kind=SyncActionKind.NEW, record=record))
        elif entry.last_status != record.status:
            if record.status == "done":
                actions.append(SyncAction(kind=SyncActionKind.CHANGED_TO_DONE, record=record))
            else:
                actions.append(SyncAction(kind=SyncActionKind.CHANGED, record=record))
        else:
            actions.append(SyncAction(kind=SyncActionKind.UNCHANGED, record=record))
    return actions


def push(actions: list[SyncAction], adapter: Any) -> tuple[list[SyncAction], list[dict[str, Any]]]:
    """Execute each SyncAction against the taskdog MCP adapter.

    Per-action try/except isolation. Returns (updated_actions, errors).
    On success the action.taskdog_id is set.
    """
    updated: list[SyncAction] = []
    errors: list[SyncError] = []

    for action in actions:
        if action.kind == SyncActionKind.UNCHANGED:
            updated.append(action)
            continue

        try:
            if action.kind == SyncActionKind.CHANGED_TO_DONE:
                resp = adapter.call_tool("taskdog_done", {"ueid": action.record.ueid})
            else:  # NEW or CHANGED — upsert via taskdog_add
                resp = adapter.call_tool(
                    "taskdog_add",
                    {
                        "ueid": action.record.ueid,
                        "title": action.record.title,
                        "priority": action.record.priority,
                        "due": action.record.due,
                    },
                )
            # Capture returned taskdog id if present
            td_id: str | None = None
            if isinstance(resp, dict):
                td_id = resp.get("id") or resp.get("taskdog_id")
            updated_action = SyncAction(
                kind=action.kind,
                record=action.record,
                taskdog_id=td_id,
            )
            updated.append(updated_action)
        except Exception as exc:
            errors.append(SyncPerTaskError(ueid=action.record.ueid, error=str(exc)))
            updated.append(action)  # preserve action but not updated

    return updated, errors


def run_sync(
    vault_root: Path,
    state_path: Path,
    adapter: Any,
) -> SyncResult:
    """Full sync: load state → parse vault → diff → push → save state."""
    t0 = time.monotonic()
    result = SyncResult()

    # 1. Load state
    state = load_state(state_path)

    # 2. Parse vault
    try:
        tasks = parse_vault_tasks(vault_root)
    except Exception as exc:
        result.parse_errors = 1
        result.errors.append(SyncAdapterError(error=f"vault_parse_failed: {exc}"))
        result.duration_s = time.monotonic() - t0
        return result

    result.scanned = len(tasks)

    # 3. Diff
    actions = diff(tasks, state)

    # 4. Push
    updated_actions, push_errors = push(actions, adapter)
    result.errors.extend(push_errors)

    # 5. Tally + atomic state write per successful action
    now_iso = datetime.now(timezone.utc).isoformat()
    new_tasks: dict[str, SyncTaskEntry] = dict(state.tasks)

    for action in updated_actions:
        if action.kind == SyncActionKind.UNCHANGED:
            result.skipped += 1
            continue
        if action.kind == SyncActionKind.NEW:
            result.added += 1
        elif action.kind == SyncActionKind.CHANGED:
            result.updated += 1
        elif action.kind == SyncActionKind.CHANGED_TO_DONE:
            result.completed += 1

        # Build updated entry
        entry = SyncTaskEntry(
            last_synced_at=now_iso,
            last_status=action.record.status,
            taskdog_id=action.taskdog_id,
            vault_path=action.record.vault_path,
        )
        new_tasks[action.record.ueid] = entry

        # Atomic state write per task (D5: write AFTER each success)
        new_state = SyncState(
            version=1,
            last_sync_at=now_iso,
            tasks=new_tasks,
        )
        save_state(state_path, new_state)

    result.duration_s = time.monotonic() - t0
    return result


def reverse_sync(
    state_path: Path,
    adapter: Any,
    source_fork: str = "taskdog",
) -> ReverseSyncResult:
    """Enumerate adapter (taskdog) state, diff vs snapshot, emit TaskChange events.

    Pipeline:
      1. Load reverse snapshot
      2. list_all() from adapter
      3. For each row, classify (NEW/CHANGED/CHANGED_TO_DONE/UNCHANGED)
      4. Emit TaskChange via src.mesh.queue.enqueue() (uses module-level
         QUEUE_DIR) for non-UNCHANGED rows
      5. Update snapshot atomically per task (or at end)

    Note: the queue directory is taken from `src.mesh.queue.QUEUE_DIR`
    (module-level). Tests override this with monkeypatch.setattr. There
    is no `review_queue_dir` parameter — keep that invariant.

    Orphan handling (v1): NEW UEIDs not in snapshot are SKIPPED (vault_path
    unknown). v1.3 will add vault lookup.
    """
    import uuid

    from src.contracts.task_change import TaskAction, TaskChange

    t0 = time.monotonic()
    result = ReverseSyncResult()

    # 1. Load state
    state = load_reverse_state(state_path)

    # 2. Enumerate adapter
    try:
        rows = adapter.list_all()
    except Exception as exc:
        result.errors.append(SyncAdapterError(error=f"adapter_list_failed: {exc}"))
        result.duration_s = time.monotonic() - t0
        return result

    result.scanned = len(rows)

    # 3-4. Classify + emit
    new_tasks: dict[str, ReverseSyncTaskEntry] = dict(state.tasks)
    now_iso = datetime.now(timezone.utc).isoformat()

    for row in rows:
        ueid = row.get("ueid")
        if not ueid:
            result.skipped += 1
            continue

        status = row.get("status", "planned")
        title = row.get("name", "")  # taskdog uses 'name' not 'title'

        entry = state.tasks.get(ueid)

        # Orphan: new UEID not in snapshot -> skip (v1)
        if entry is None:
            result.skipped += 1
            continue

        # Unchanged
        if entry.last_seen_status == status and entry.last_seen_title == title:
            result.skipped += 1
            continue

        # Classify action
        if status == "done" and entry.last_seen_status != "done":
            action = TaskAction.DONE
        else:
            action = TaskAction.UPDATE

        # Emit
        try:
            event = TaskChange(
                event_id=str(uuid.uuid4()),
                ueid=ueid,
                action=action,
                fields={
                    "status": status,
                    "title": title,
                    "vault_path": entry.vault_path,
                },
                source_fork=source_fork,
                timestamp=datetime.now(timezone.utc),
            )
            # Use dynamic import to allow test patching
            src.mesh.queue.enqueue(event)
            result.emitted += 1
        except Exception as exc:
            result.errors.append(SyncPerTaskError(ueid=ueid, error=str(exc)))
            continue

        # Update snapshot entry
        new_tasks[ueid] = ReverseSyncTaskEntry(
            last_seen_status=status,
            last_seen_title=title,
            taskdog_id=entry.taskdog_id,
            vault_path=entry.vault_path,
        )

    # 5. Save updated snapshot
    new_state = ReverseSyncState(
        version=1,
        last_sync_at=now_iso,
        tasks=new_tasks,
    )
    save_reverse_state(state_path, new_state)

    result.duration_s = time.monotonic() - t0
    return result
