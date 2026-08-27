"""Tests for VaultLock — file-level mutex for vault writes."""
from __future__ import annotations

import shutil
import tempfile
import threading
import time
from pathlib import Path

import pytest

from ikigai.vault.lock import VaultLock


@pytest.fixture
def tmp_lock_dir() -> Path:
    d = Path(tempfile.mkdtemp(prefix="vault_lock_test_"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_serial_writes(tmp_lock_dir: Path) -> None:
    lock_path = tmp_lock_dir / "vault.lock"
    writes: list[int] = []

    def writer(i: int) -> None:
        with VaultLock(lock_path):
            writes.append(i)
            time.sleep(0.01)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(writes) == list(range(5))


def test_lock_released_on_exception(tmp_lock_dir: Path) -> None:
    lock_path = tmp_lock_dir / "vault.lock"
    with pytest.raises(RuntimeError):
        with VaultLock(lock_path):
            raise RuntimeError("boom")
    # Should NOT deadlock — re-acquire immediately
    with VaultLock(lock_path):
        pass


def test_creates_lock_file_if_missing(tmp_lock_dir: Path) -> None:
    lock_path = tmp_lock_dir / "fresh.lock"
    assert not lock_path.exists()
    with VaultLock(lock_path):
        assert lock_path.exists()


def test_reentrant_acquire_release(tmp_lock_dir: Path) -> None:
    """Acquire → release → re-acquire pattern (no leak, no deadlock)."""
    lock_path = tmp_lock_dir / "reentry.lock"
    for _ in range(3):
        with VaultLock(lock_path):
            pass