"""VaultLock — file-level mutex for vault writes.

Cross-platform: msvcrt on Windows (locking), fcntl on POSIX.
Releases on normal exit AND on exception (context manager contract).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import TracebackType

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


class VaultLock:
    """Context manager that acquires an exclusive OS-level lock on `path`.

    The file is created on entry if missing. Locks are released both on
    normal exit and on exception.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None
        self._owns_file = False

    def __enter__(self) -> "VaultLock":
        # Create the lock file if missing (parents must already exist)
        self._owns_file = not self.path.exists()
        self._fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            if sys.platform == "win32":
                # msvcrt.locking blocks (1 block of 1 byte at offset 0)
                msvcrt.locking(self._fd, msvcrt.LK_LOCK, 1)
            else:
                fcntl.flock(self._fd, fcntl.LOCK_EX)
        except Exception:
            os.close(self._fd)
            self._fd = None
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._fd is None:
            return
        try:
            if sys.platform == "win32":
                msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None
            if self._owns_file and self.path.exists():
                try:
                    self.path.unlink()
                except OSError:
                    pass  # another holder will clean up


__all__ = ["VaultLock"]