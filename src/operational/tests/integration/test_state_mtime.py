"""Integration tests for ``_PersistentRepo`` cross-process mtime reload (P1-11).

Companion to :mod:`test_state_locking`. The lock test proves that two
processes writing the same file don't interleave (``_dump`` is serialized).

This module proves the *read* side of the contract: when a peer process
commits a write to the backing JSON file, the original process's
:meth:`needs_reload` reports ``True``, :meth:`reload` actually picks up the
new data, and :meth:`reload` is a no-op when nothing changed.

Why this matters: ``pav tui`` keeps an in-memory copy of the persistent
repos for fast rendering. If the user runs ``pav habit create ...`` from
another terminal while the TUI is open, the TUI's view of habits will go
stale. The mtime + reload hooks let the TUI refresh loop cheaply ask each
repo "did anything change?" and re-hydrate on demand.

The fixture in :mod:`tests.integration.conftest` redirects state to a
tmp dir before the app imports — same isolation as ``test_state_locking``.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import sys
import tempfile
from datetime import UTC, date, datetime, time
from pathlib import Path


_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from operational.cli import state as cli_state  # noqa: E402
from operational.entities.metric import SleepRecord  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _child_write_empty_store(sd: str) -> None:
    """Subprocess entrypoint: write raw ``{}`` directly to the backing file.

    Bypasses :class:`_PersistentRepo` entirely — uses
    :meth:`Path.write_text` to overwrite the JSON file with an empty
    object. This is necessary because both ``_PersistentRepo.clear()``
    (which UNLINKs the file and syncs the writer's mtime to 0) and
    ``_dump()`` (which READS the on-disk state and merges it back into
    its output, preserving any record still on disk) cannot produce a
    visible mtime advance whose contents are "the parent's record is
    gone."

    The closest analogue to a real peer-side delete is therefore a raw
    file overwrite — not something any code path under ``_PersistentRepo``
    will produce today, but exactly what we need to prove the
    *replace-not-merge* half of :meth:`reload`'s contract.

    Module-level so :mod:`multiprocessing.spawn` can pickle it across
    the Windows process boundary.
    """
    import json
    from pathlib import Path

    sleep_records_path = Path(sd) / "sleep_records.json"
    sleep_records_path.write_text(json.dumps({}, indent=2, ensure_ascii=False), encoding="utf-8")


def _child_write_sleep(record_id: str, quality_score: int, state_dir: str) -> None:
    """Subprocess entrypoint: write one SleepRecord and dump.

    Mirror of :func:`test_state_locking._child_write_sleep`. The reload
    contract is meaningless if the parent can read the file directly, so
    we have to commit the write from a separate process to actually move
    the on-disk mtime past what the parent's :attr:`_loaded_mtime_ns` saw.
    """
    os.environ["TIME_TASKER_STATE_DIR"] = state_dir
    import importlib

    from operational.cli import state as child_state

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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_needs_reload_is_false_right_after_upsert() -> None:
    """``needs_reload()`` returns False immediately after our own upsert.

    After ``upsert``, ``_dump`` runs and updates ``_loaded_mtime_ns`` to
    the just-written mtime — the in-memory view is in sync with disk, so
    ``needs_reload()`` must report False. Without this, the TUI refresh
    loop would burn cycles re-rendering on every interaction.
    """
    cli_state.sleep_records.clear()
    assert cli_state.sleep_records.needs_reload() is False

    record = SleepRecord(
        id="slp_self",
        date=date(2026, 7, 1),
        bedtime=time(22, 0),
        wake_time=time(6, 0),
        quality_score=8,
        created_at=datetime.now(UTC),
    )
    cli_state.sleep_records.upsert(record)

    # Own write was caught by ``_dump`` which updated ``_loaded_mtime_ns``.
    assert cli_state.sleep_records.needs_reload() is False


def test_needs_reload_is_true_after_external_subprocess_write() -> None:
    """A subprocess write to the same backing file triggers ``needs_reload()``.

    Simulates ``pav tui`` (this process) holding the repo while ``pav
    metric sleep --quality 9`` runs in another terminal and commits a
    SleepRecord. After the child exits, the parent's :meth:`needs_reload`
    must report True so the TUI refresh loop knows to re-hydrate.
    """
    state_dir = Path(tempfile.gettempdir()) / "time-tasker-mtime-test-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    sleep_records_path = state_dir / "sleep_records.json"
    sleep_records_path.unlink(missing_ok=True)

    # Parent writes first to create the file, then snapshots its mtime.
    # The parent's repo instance was bound to ``_HOME_STATE_DIR`` at module
    # load — not ``state_dir``. To make this test realistic, we re-point
    # the parent's repo to ``state_dir`` directly via a controlled reload.
    os.environ["TIME_TASKER_STATE_DIR"] = str(state_dir)
    import importlib

    importlib.reload(cli_state)
    repo = cli_state.sleep_records
    repo.clear()

    parent_record = SleepRecord(
        id="slp_parent",
        date=date(2026, 7, 1),
        bedtime=time(22, 0),
        wake_time=time(6, 0),
        quality_score=7,
        created_at=datetime.now(UTC),
    )
    repo.upsert(parent_record)

    # Snapshot the mtime the parent thinks is current.
    assert repo.needs_reload() is False
    parent_loaded_mtime = repo._loaded_mtime_ns
    assert parent_loaded_mtime > 0, "parent's snapshot mtime should be set after dump"

    # Spawn a child that writes a different record to the SAME file.
    # ``multiprocessing.spawn`` is Windows-safe and gives a fresh interpreter
    # per child — mirrors a real terminal invocation.
    ctx = mp.get_context("spawn")
    p = ctx.Process(
        target=_child_write_sleep,
        args=("slp_child", 9, str(state_dir)),
    )
    p.start()
    p.join(timeout=30)
    assert p.exitcode == 0, f"child crashed (exitcode={p.exitcode})"

    # Parent's view must now be stale: mtime advanced, snapshot didn't.
    assert repo.needs_reload() is True, (
        "needs_reload should be True after a peer's commit, "
        f"but mtime ns was {repo._current_mtime_ns()} "
        f"vs snapshot {parent_loaded_mtime}"
    )


def test_reload_picks_up_peer_writes() -> None:
    """``reload()`` re-hydrates in-memory store from disk after a peer commit.

    Confirms the read path: once :meth:`needs_reload` reports True,
    calling :meth:`reload` actually replaces the in-memory ``_store``
    with the peer's data (so the parent's repo now sees the child's
    record). ``reload()`` returns True when it did work, False when
    the file hadn't moved — the TUI loop relies on this return value.
    """
    state_dir = Path(tempfile.gettempdir()) / "time-tasker-mtime-test-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    sleep_records_path = state_dir / "sleep_records.json"
    sleep_records_path.unlink(missing_ok=True)

    os.environ["TIME_TASKER_STATE_DIR"] = str(state_dir)
    import importlib

    importlib.reload(cli_state)
    repo = cli_state.sleep_records
    repo.clear()

    parent_record = SleepRecord(
        id="slp_parent",
        date=date(2026, 7, 1),
        bedtime=time(22, 0),
        wake_time=time(6, 0),
        quality_score=7,
        created_at=datetime.now(UTC),
    )
    repo.upsert(parent_record)
    assert repo.get("slp_parent") is not None

    # No peer write yet → reload is a no-op.
    assert repo.reload() is False

    # Peer commits a record under a different id.
    ctx = mp.get_context("spawn")
    p = ctx.Process(
        target=_child_write_sleep,
        args=("slp_child", 9, str(state_dir)),
    )
    p.start()
    p.join(timeout=30)
    assert p.exitcode == 0, f"child crashed (exitcode={p.exitcode})"

    # Parent's view is stale; reload must say "yes I did work".
    assert repo.needs_reload() is True
    assert repo.reload() is True, "reload() should report it re-hydrated"

    # And the peer's record is now visible in the parent's store.
    assert repo.get("slp_child") is not None, (
        "after reload, parent's _store should contain the peer's record"
    )
    assert repo.get("slp_child").quality_score == 9

    # Second reload call right after → no-op (mtime hasn't moved again).
    assert repo.reload() is False
    assert repo.needs_reload() is False


def test_reload_replaces_store_not_merges() -> None:
    """``reload()`` REPLACES the in-memory store rather than merging.

    Documented contract (see ``_PersistentRepo.reload`` docstring):
    "_dump already read-merge-writes from the on-disk perspective, so
    any commit a peer made is the source of truth — our local view of
    any ID would just be a stale shadow."

    This test verifies the *replace* half of that contract: if the parent
    mutates a record in-memory but never writes to disk, and a peer
    *deletes* the same id on disk, then reload clears the parent's view.
    We exercise the delete path by having the peer overwrite the JSON
    file with raw ``{}`` (bypassing ``_PersistentRepo`` entirely — both
    ``clear()`` (UNLINK + mtime sync to 0) and ``_dump()`` (read-merge-write
    that preserves on-disk records) cannot produce the needed
    mtime-advance + contents-cleared state). This is the closest
    analogue to a future peer-side delete (which doesn't exist yet —
    every CLI command uses ``upsert``).
    """
    state_dir = Path(tempfile.gettempdir()) / "time-tasker-mtime-test-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    sleep_records_path = state_dir / "sleep_records.json"
    sleep_records_path.unlink(missing_ok=True)

    os.environ["TIME_TASKER_STATE_DIR"] = str(state_dir)
    import importlib

    importlib.reload(cli_state)
    repo = cli_state.sleep_records
    repo.clear()

    record = SleepRecord(
        id="slp_replace",
        date=date(2026, 7, 1),
        bedtime=time(22, 0),
        wake_time=time(6, 0),
        quality_score=6,
        created_at=datetime.now(UTC),
    )
    repo.upsert(record)
    assert repo.get("slp_replace") is not None

    # Simulate a peer resetting the file to an empty store. We bypass
    # both ``_PersistentRepo.clear()`` (UNLINKs the file AND syncs the
    # writer's mtime to 0 — intentional anti-phantom-bump) and ``_dump()``
    # (which READS on-disk state and merges it back into its output,
    # preserving any record still on disk). The only path that produces
    # a visible mtime advance whose contents are "the parent's record
    # is gone" is a raw ``Path.write_text("{}")`` overwrite, which is
    # what ``_child_write_empty_store`` does. It bypasses
    # :class:`_PersistentRepo` entirely so the helper stays free of any
    # import-time state and remains safely picklable across the Windows
    # process boundary.
    ctx = mp.get_context("spawn")
    p = ctx.Process(target=_child_write_empty_store, args=(str(state_dir),))
    p.start()
    p.join(timeout=30)
    assert p.exitcode == 0, f"child crashed (exitcode={p.exitcode})"

    # Parent's view should now be replaced: the record is gone.
    assert repo.needs_reload() is True
    assert repo.reload() is True
    assert repo.get("slp_replace") is None, (
        "reload should REPLACE in-memory store with disk contents "
        "(peer cleared the file → parent must see empty store)"
    )

    # Cleanup.
    for f in state_dir.glob("*"):
        f.unlink()
