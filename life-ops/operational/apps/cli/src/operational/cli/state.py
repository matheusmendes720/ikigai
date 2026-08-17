"""Persistent app state for the CLI layer.

Each repository is backed by a JSON file so that data survives across
``subprocess`` calls (interactive home menu) and process restarts.

Under the hood it uses an :class:`InMemoryRepository` for speed, but
calls ``dump()`` after every write and ``load()`` at import time.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any

from operational.entities.ajuste_fino import AjusteFino
from operational.entities.habit import Habit
from operational.entities.journal import JournalEntry
from operational.entities.metric import SleepRecord
from operational.entities.policy import PolicyDecision, PolicySetpoints
from operational.entities.pomodoro import PomodoroRound
from operational.entities.portfolio import PortfolioArtifact
from operational.entities.routine import Routine, RoutineLog
from operational.entities.time_block import TimeBlock
from operational.entities.v3 import (
    DailyReflection,
    DayContext,
    LunchRecord,
    TransicaoRegistrada,
)
from operational.persistence.memory import InMemoryRepository

# ---------------------------------------------------------------------------
# Where state lives
# ---------------------------------------------------------------------------
_STATE_DIR_ENV = "TIME_TASKER_STATE_DIR"
_HOME_STATE_DIR = Path.home() / ".time-tasker"


def _state_dir() -> Path:
    """Resolve the current state directory at every access.

    ``_PersistentRepo._path`` is bound to *this* return value when each repo
    is instantiated, so a late env-var change will only affect repos that are
    created AFTER the override. Existing repo instances keep their original
    path — that's deliberate (a repo's file path is part of its identity).

    Why this is *not* a module-level constant:

    When a subprocess spawned via :mod:`multiprocessing.spawn` imports this
    module, ``sys.modules`` carries no parent context, but ``os.environ`` is
    inherited from the parent. If the test harness later sets
    ``TIME_TASKER_STATE_DIR`` to a per-child path (e.g. to isolate each
    child's writes), a module-level ``_STATE_DIR`` would have been captured
    at the parent's value and the per-child override would silently fail.

    The original constant form was the source of test_state_locking
    intermittent failures during P0 #7 — read-merge-write on ``_dump``
    assumes each subprocess writes to its own file, but the captured
    constant funneled every child's write to the parent's path.
    """
    path = Path(os.environ.get(_STATE_DIR_ENV, _HOME_STATE_DIR))
    path.mkdir(parents=True, exist_ok=True)
    return path


class _PersistentRepo(InMemoryRepository):
    """In-memory repo that snapshots to a JSON file on every mutation."""

    def __init__(self, model_class: type, filename: str) -> None:
        super().__init__(model_class)
        self._path = _state_dir() / filename
        # mtime (ns) of the file as observed at the last successful load or
        # dump. Used by ``needs_reload`` / ``reload`` to detect cross-process
        # writes (e.g. a CLI mutation committed by another process while this
        # TUI keeps an in-memory copy of the repo).
        self._loaded_mtime_ns: int = 0
        self._load()
        self._loaded_mtime_ns = self._current_mtime_ns()

    # -- mtime + cross-process reload -------------------------------------

    def _current_mtime_ns(self) -> int:
        """Return the current mtime of the backing file, or 0 if absent."""
        try:
            return self._path.stat().st_mtime_ns
        except OSError:
            # File may have been unlinked between dump and stat; treat as
            # "no file present" rather than propagating.
            return 0

    def needs_reload(self) -> bool:
        """Return ``True`` if the backing file changed since the last load.

        Compares the on-disk mtime against the snapshot recorded after the
        most recent :meth:`_load` / :meth:`_dump`. Cross-process writers
        (e.g. a CLI subcommand invoked from another terminal while this TUI
        is running) bump the mtime on every commit; the TUI's in-memory
        ``_store`` stays stale until :meth:`reload` runs.
        """
        current = self._current_mtime_ns()
        return current > self._loaded_mtime_ns

    def reload(self) -> bool:
        """Re-read the backing file if it changed since the last load/dump.

        Returns ``True`` when a reload actually happened (so callers — like
        the TUI refresh loop — can cheaply decide whether to re-render).

        Sequence:

        1. :meth:`needs_reload` — early-out if mtime hasn't moved.
        2. Snapshot the set of IDs currently in memory so we can detect
           removals from another process.
        3. Re-run :meth:`_load` (replaces ``_store`` with on-disk contents).
        4. Update ``_loaded_mtime_ns`` to the new on-disk value.
        5. **Merging caveat:** we intentionally *replace* the in-memory store
           rather than merging. ``_dump`` already read-merge-writes from the
           on-disk perspective, so any commit a peer made is the source of
           truth — our local view of any ID would just be a stale shadow.
           This is the same semantics :meth:`_load` has had since the file
           was first introduced.
        """
        if not self.needs_reload():
            return False
        self._load()
        self._loaded_mtime_ns = self._current_mtime_ns()
        return True

    # -- helpers ----------------------------------------------------------

    def _path_for(self, filename: str) -> Path:
        return _state_dir() / filename

    def _load(self) -> None:
        """Load seed data from JSON (mode='json' dump format).

        REPLACES :attr:`_store` with the file contents (after :meth:`clear`).
        This is intentional — the docstring on :meth:`reload` describes
        reload as a *replace*, not a merge, because ``_dump`` already
        read-merge-writes from the on-disk perspective and any commit
        made by a peer is the source of truth. Merging here would let a
        locally-mutated but unpersisted record "shadow" a peer's
        authoritative deletion; replacing lets reload drop those
        shadows cleanly.

        Constructor-time calls (line 78) pass through cleanly too —
        ``_store`` starts empty, so clear-then-update is identical to
        update.
        """
        self._store.clear()
        if not self._path.exists():
            return
        try:
            raw: dict[str, dict[str, Any]] = json.loads(self._path.read_text("utf-8"))
            self._store.update(raw)
        except (json.JSONDecodeError, OSError):
            pass  # corrupt file → start fresh

    @contextmanager
    def _locked_dump(self) -> Iterator[IO[str]]:
        """Hold an exclusive OS-level lock on a sibling ``.lock`` file.

        Used to serialize concurrent ``_dump()`` invocations across processes
        (e.g. parallel Typer ``CliRunner.invoke`` calls, ``subprocess`` from
        the home menu, or a TUI writer while the CLI is mid-write). Uses
        ``fcntl.flock`` on POSIX and ``msvcrt.locking`` on Windows so the
        serialization is honored by any process that opens the lock file,
        not just those sharing the same Python interpreter.
        """
        lock_path = self._path.with_suffix(self._path.suffix + ".lock")
        # Open in append+read mode, create if missing. The lock is on the file
        # *handle*, not the file contents — ``a+`` always creates and never
        # truncates, which is what we want for a sibling lock file.
        fh = open(lock_path, "a+", encoding="utf-8")
        try:
            if os.name == "nt":
                import msvcrt

                # ``locking(fd, LK_LOCK, 1)`` blocks until the OS grants the
                # lock on the first byte of the file. Releases on close.
                msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                # ``LOCK_EX`` blocks until exclusive lock acquired.
                # ``LOCK_NB`` would raise on contention — we want to wait.
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            yield fh
        finally:
            try:
                if os.name == "nt":
                    # ``LK_UNLCK`` on the same range releases the lock.
                    import msvcrt

                    try:
                        fh.seek(0)
                        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
                else:
                    import fcntl

                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            finally:
                fh.close()

    def _dump(self) -> None:
        """Snapshot every stored entity in JSON mode.

        Sequence (under :meth:`_locked_dump`):

        1. **Read** the on-disk state (if any). This sees what other
           processes have already committed; without this merge step, a
           fresh subprocess that has only its own in-memory record would
           overwrite everyone else's contributions.
        2. **Merge** in-memory state into the on-disk state. Same-ID records
           resolve to the in-memory view (newer write wins); distinct IDs
           from other processes are preserved.
        3. Serialize the merged map to JSON.
        4. Write to a sibling ``.json.tmp`` file.
        5. ``os.replace`` onto the final path (atomic on POSIX and Windows).

        Steps 1–5 are wrapped in an exclusive OS-level lock so concurrent
        ``subprocess`` invocations of the CLI (or TUI+CLI mixed mode) cannot
        interleave reads and writes against the same file. The lock spans
        the full read-merge-write because the merge itself is racy if two
        subprocesses each load ``{}`` from disk before either writes.

        Edge cases:

        - **Missing file** (first write ever) — ``on_disk`` is ``{}`` and
          the merge equals the in-memory view.
        - **Corrupt file** (``json.JSONDecodeError``) — treat as ``{}``;
          the next successful write replaces it. The corrupt original
          stays on disk until ``os.replace`` swaps in the new content.
        - **In-memory empty, file non-empty** — dump the file contents
          unchanged. This happens when ``clear()`` is followed by a ``load``
          path; defensive against accidental flushes.
        """
        with self._locked_dump():
            # Step 1: read on-disk state (BEST-EFFORT — missing or corrupt
            # files mean "no prior contributions from other processes").
            on_disk: dict[str, dict[str, Any]] = {}
            if self._path.exists():
                try:
                    raw = self._path.read_text("utf-8")
                    parsed: object = json.loads(raw)
                    if isinstance(parsed, dict):
                        on_disk = parsed
                except (json.JSONDecodeError, OSError):
                    # Corrupt or unreadable — start fresh; the next write
                    # will replace the bad bytes atomically.
                    pass
            # Step 2: merge. In-memory wins on ID conflict; the on-disk map
            # carries every record from other processes we haven't touched.
            merged: dict[str, dict[str, Any]] = {**on_disk, **self._store}
            # Step 3: serialize.
            serialized: dict[str, dict[str, Any]] = {}
            for eid, data in merged.items():
                serialized[eid] = self._model_class.model_validate(data).model_dump(
                    mode="json",  # date/datetime → iso strings
                    exclude={*self._model_class.model_computed_fields.keys()},
                )
            # Step 4 + 5: write to tmp, atomic-replace.
            text = json.dumps(serialized, indent=2, ensure_ascii=False)
            tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
            # Write to tmp first, then atomically replace the canonical file.
            # On a crash mid-write, only the ``.tmp`` file is left behind —
            # the real file is either fully old or fully new, never half-written.
            with open(tmp_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text.replace("\r\n", "\n"))
            os.replace(tmp_path, self._path)
            # Sync the observed mtime so the writer's own ``needs_reload``
            # doesn't fire on the next tick — without this, every TUI
            # refresh would reload the file we just committed.
            self._loaded_mtime_ns = self._current_mtime_ns()

    # -- override persistence hooks ---------------------------------------

    def _persist_one(self, entity_id: str, data: dict[str, Any]) -> None:
        super()._persist_one(entity_id, data)
        self._dump()

    def _remove_one(self, entity_id: str) -> None:
        super()._remove_one(entity_id)
        self._dump()

    def clear(self) -> None:
        super().clear()
        if self._path.exists():
            self._path.unlink()
            # We removed the file we wrote; sync the observed mtime so the
            # next ``needs_reload`` doesn't see a phantom bump.
            self._loaded_mtime_ns = self._current_mtime_ns()


# ---------------------------------------------------------------------------
# Repositories — one per entity type, persisted to ``~/.time-tasker/*.json``
# ---------------------------------------------------------------------------
routines: _PersistentRepo = _PersistentRepo(Routine, "routines.json")
routine_logs: _PersistentRepo = _PersistentRepo(RoutineLog, "routine_logs.json")
time_blocks: _PersistentRepo = _PersistentRepo(TimeBlock, "time_blocks.json")
journals: _PersistentRepo = _PersistentRepo(JournalEntry, "journals.json")
habits: _PersistentRepo = _PersistentRepo(Habit, "habits.json")
sleep_records: _PersistentRepo = _PersistentRepo(SleepRecord, "sleep_records.json")
pomodoros: _PersistentRepo = _PersistentRepo(PomodoroRound, "pomodoros.json")
policy_decisions: _PersistentRepo = _PersistentRepo(PolicyDecision, "policy_decisions.json")
policy_setpoints: _PersistentRepo = _PersistentRepo(PolicySetpoints, "policy_setpoints.json")
ajustes_finos: _PersistentRepo = _PersistentRepo(AjusteFino, "ajustes_finos.json")
portfolio_artifacts: _PersistentRepo = _PersistentRepo(
    PortfolioArtifact,
    "portfolio_artifacts.json",
)

# V3 entities
day_contexts: _PersistentRepo = _PersistentRepo(DayContext, "day_contexts.json")
daily_reflections: _PersistentRepo = _PersistentRepo(DailyReflection, "daily_reflections.json")
lunch_records: _PersistentRepo = _PersistentRepo(LunchRecord, "lunch_records.json")
transicoes: _PersistentRepo = _PersistentRepo(TransicaoRegistrada, "transicoes.json")


# ---------------------------------------------------------------------------
# Cross-process reload helper
# ---------------------------------------------------------------------------
# Module-level singleton references. Exposed so the TUI refresh loop (and any
# other long-lived consumer) can ask "did anyone else touch the JSON files
# since I last looked?" without holding its own references to each repo.
_ALL_REPOS: tuple[_PersistentRepo, ...] = (
    routines,
    routine_logs,
    time_blocks,
    journals,
    habits,
    sleep_records,
    pomodoros,
    policy_decisions,
    policy_setpoints,
    ajustes_finos,
    portfolio_artifacts,
    day_contexts,
    daily_reflections,
    lunch_records,
    transicoes,
)


def reload_stale_repos() -> list[str]:
    """Reload every repo whose backing file changed since the last load.

    Iterates the 14 module-level :class:`_PersistentRepo` singletons and
    calls :meth:`_PersistentRepo.reload` on each. Returns the list of
    filenames that actually reloaded (for cheap "did anything change?"
    checks in callers like the TUI refresh loop).

    The TUI calls this on every ``set_interval`` tick (typically 1–5s) so
    cross-process CLI writes — e.g. ``pav metric sleep`` invoked from
    another terminal — become visible without restarting the TUI.
    """
    reloaded: list[str] = []
    for repo in _ALL_REPOS:
        if repo.reload():
            reloaded.append(repo._path.name)
    return reloaded


# ---------------------------------------------------------------------------
# Auto-load dataset on boot (if requested via env var)
# ---------------------------------------------------------------------------
def _auto_load_dataset() -> None:
    """If TIME_TASKER_DATASET is set and the state dir is empty, load from CSV.

    Skips if any state file already exists (don't overwrite user data).
    Skips silently on errors (the user can run ``operational demo import-csv``
    manually if needed).
    """
    dataset_name = os.environ.get("TIME_TASKER_DATASET")
    if not dataset_name or dataset_name == "production":
        return
    if any(_state_dir().glob("*.json")):
        return
    try:
        from operational.cli.csv_loader import import_from_csv_as_entities
        from operational.cli.dataset_selector import resolve_dataset

        ref = resolve_dataset(dataset_name)
        if not ref.csv_path or not ref.csv_path.exists():
            return
        groups = import_from_csv_as_entities(ref.csv_path)
        repo_map = {
            "routine": routines,
            "routine_log": routine_logs,
            "time_block": time_blocks,
            "journal_entry": journals,
            "habit": habits,
            "sleep_record": sleep_records,
            "pomodoro_round": pomodoros,
            "policy_decision": policy_decisions,
            "policy_setpoints": policy_setpoints,
            "ajuste_fino": ajustes_finos,
            "day_context": day_contexts,
            "daily_reflection": daily_reflections,
            "lunch_record": lunch_records,
            "transicao": transicoes,
        }
        for etype, entities in groups.items():
            if etype in repo_map:
                for ent in entities:
                    repo_map[etype].upsert(ent)
    except Exception:
        pass  # silent — let the user debug via `operational doctor`


_auto_load_dataset()
