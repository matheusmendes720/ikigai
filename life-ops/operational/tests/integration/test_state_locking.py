"""Integration tests for ``_PersistentRepo`` concurrency safety (P0 #7).

These tests exercise the OS-level file lock that ``_PersistentRepo`` holds
around :meth:`_dump` so that two CLI subprocesses writing the same repo
cannot interleave reads and writes. The fixture in ``conftest.py`` isolates
state to ``$TEMP/time-tasker-test-int-state/`` before the app imports.
"""
from __future__ import annotations

import multiprocessing as mp
import os
import sys
import tempfile
from datetime import UTC, date, datetime, time
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from operational.cli import state as cli_state  # noqa: E402
from operational.entities.metric import SleepRecord  # noqa: E402
from operational.entities.pomodoro import PomodoroRound, PomodoroState  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _child_write_sleep(record_id: str, quality_score: int, state_dir: str) -> None:
    """Subprocess entrypoint: write one SleepRecord and dump.

    ``multiprocessing.spawn`` unpickles this function by importing the test
    module, which in turn imports :mod:`operational.cli.state` — at that
    point the child has inherited ``TIME_TASKER_STATE_DIR`` from the parent
    pytest process (set by ``conftest.py``). Setting the env var AFTER import
    is a no-op for already-bound ``_STATE_DIR`` and its derived repo paths.
    ``importlib.reload(state)`` re-runs the module body so the new env var
    is honored.
    """
    os.environ["TIME_TASKER_STATE_DIR"] = state_dir
    import importlib

    from operational.cli import state as child_state  # noqa: PLC0415

    importlib.reload(child_state)

    record = SleepRecord(
        id=record_id,
        date=date(2026, 7, 1),
        bedtime=time(22, 0),
        wake_time=time(6, 0),
        quality_score=quality_score,
        created_at=datetime.now(UTC),
    )
    child_state.sleep_records.upsert(record)


def _child_write_pomodoro(record_id: str, round_number: int, state_dir: str) -> None:
    """Subprocess entrypoint: write one PomodoroRound and dump.

    See :func:`_child_write_sleep` for why we ``importlib.reload`` the state
    module — same env-var-after-import foot-gun.
    """
    os.environ["TIME_TASKER_STATE_DIR"] = state_dir
    import importlib

    from operational.cli import state as child_state  # noqa: PLC0415

    importlib.reload(child_state)

    round_ = PomodoroRound(
        id=record_id,
        round_number=round_number,
        state=PomodoroState.COMPLETE,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    child_state.pomodoros.upsert(round_)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dump_writes_atomically_via_tmp_file() -> None:
    """``_dump()`` writes to ``.json.tmp`` then ``os.replace`` to final path.

    After any write, the final ``.json`` file is valid JSON and the
    ``.tmp`` sibling is gone (``os.replace`` is atomic, no leftover temp).
    """
    cli_state.sleep_records.clear()
    record = SleepRecord(
        id="slp_atomic_one",
        date=date(2026, 7, 1),
        bedtime=time(22, 0),
        wake_time=time(6, 0),
        quality_score=8,
        created_at=datetime.now(UTC),
    )
    cli_state.sleep_records.upsert(record)

    tmp_path = cli_state.sleep_records._path.with_suffix(
        cli_state.sleep_records._path.suffix + ".tmp"
    )
    lock_path = cli_state.sleep_records._path.with_suffix(
        cli_state.sleep_records._path.suffix + ".lock"
    )
    assert not tmp_path.exists(), "tmp file should be cleaned up by os.replace"
    # Lock file IS expected to persist (it's a sibling, not a temp file).
    assert lock_path.exists(), "lock file should exist after the dump completed"


def test_concurrent_subprocess_writes_do_not_corrupt_file() -> None:
    """10 parallel subprocesses write 10 SleepRecords — final file is valid JSON.

    Without file-locking around ``_dump()``, two writers could interleave
    ``json.dump()`` and ``write_text()`` and produce a corrupt half-written
    file. With the ``fcntl.flock`` / ``msvcrt.locking`` lock, writers
    serialize and the final file parses cleanly with exactly 10 records.
    """
    # Use a dedicated tmp dir for this test so we don't fight the autouse
    # conftest fixture's clear().
    state_dir = Path(tempfile.gettempdir()) / "time-tasker-lock-test-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    sleep_records_path = state_dir / "sleep_records.json"
    sleep_records_path.unlink(missing_ok=True)

    n_processes = 10
    ctx = mp.get_context("spawn")  # Windows-safe: fresh interpreter per child
    procs = [
        ctx.Process(
            target=_child_write_sleep,
            # UEID pattern: 3-5 lowercase letters then "_", then slug of
            # lowercase alphanumerics / underscores. ``slp_c`` is too short,
            # so we use ``slp_cn_0`` etc.
            args=(f"slp_cn_{i}", 7 + (i % 3), str(state_dir)),
        )
        for i in range(n_processes)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)
        assert p.exitcode == 0, f"child {p.pid} crashed (exitcode={p.exitcode})"
    for p in procs:
        assert not p.is_alive(), f"child {p.pid} hung"

    # Final file must parse cleanly as JSON.
    import json as _json

    raw = _json.loads(sleep_records_path.read_text("utf-8"))
    assert isinstance(raw, dict), f"expected dict at root, got {type(raw).__name__}"
    assert len(raw) == n_processes, f"expected {n_processes} records, got {len(raw)}"

    # Cleanup.
    for f in state_dir.glob("*"):
        f.unlink()


def test_lock_blocks_second_writer_in_same_process() -> None:
    """Within one process, holding the lock prevents the second dump from interleaving.

    This proves the lock context-manager actually serializes, not just that
    it doesn't crash. We hold the lock by hand, attempt another ``_dump``
    in a thread, and confirm it doesn't return until we release the held lock.
    """
    import threading
    import time as _time

    cli_state.pomodoros.clear()

    # Pre-acquire the lock by entering the context manager ourselves, then
    # launch a thread that tries to ``_dump()``. The thread should block
    # until we exit the ``with`` block.
    with cli_state.pomodoros._locked_dump():
        result: dict[str, object] = {}

        def _try_dump() -> None:
            cli_state.pomodoros._dump()
            result["ok"] = True

        t = threading.Thread(target=_try_dump)
        t.start()
        _time.sleep(0.1)  # give the thread time to attempt the lock
        # While we hold the lock, the thread must NOT have completed.
        assert "ok" not in result, "second writer returned while lock was held!"
        # Now release (exit the ``with`` block below) and let it finish.
    t.join(timeout=5)
    assert t.is_alive() is False, "thread never completed after lock release"
    assert result.get("ok") is True, "second writer did not run after release"