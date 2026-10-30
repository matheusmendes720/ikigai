"""Paperclip — worktree MSYS bash path fix tests (M178).

Three focused tests for ``_to_posix_path`` — the helper that converts a
Windows path to POSIX form so MSYS bash can resolve it on Windows:

* ``test_to_posix_path_on_windows_uses_cygpath`` — happy path on
  Windows: ``cygpath -u`` is invoked and its stdout becomes the result.
* ``test_to_posix_path_on_non_windows_passthrough`` — on Linux/macOS
  the helper returns ``str(path)`` directly, with NO ``cygpath`` call
  (the feature is gated, not platform-sniffed).
* ``test_to_posix_path_falls_back_when_cygpath_missing`` — when
  ``shutil.which("cygpath")`` returns ``None`` (e.g. a Windows box
  without Git for Windows), the helper falls back to ``str(path)``
  without crashing — graceful degradation over hard-fail.

These tests guard the M178 fix: ``paperclip run --spec ...`` was
failing on Windows because MSYS bash couldn't resolve the
backslash-separated absolute path Python handed it. The fix shells
out to ``cygpath -u`` to translate to ``/c/Users/foo`` form, which
bash on Windows understands natively.

Companion to ``nodes/worktree.py``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from src.ikigai.src.agents.paperclip.nodes.worktree import _to_posix_path


def test_to_posix_path_on_windows_uses_cygpath() -> None:
    """Windows + cygpath available → helper calls cygpath and returns its stdout."""
    win_path = Path("C:\\Users\\foo")
    expected_posix = "/c/Users/foo"
    completed = subprocess.CompletedProcess(
        args=["cygpath", "-u", str(win_path)],
        returncode=0,
        stdout=f"{expected_posix}\n",
        stderr="",
    )
    with (
        patch.object(sys, "platform", "win32"),
        patch("shutil.which", return_value="/usr/bin/cygpath"),
        patch("subprocess.run", return_value=completed) as mock_run,
    ):
        result = _to_posix_path(win_path)
    assert result == expected_posix, f"expected {expected_posix!r}, got {result!r}"
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert args[0] == ["cygpath", "-u", str(win_path)]
    assert kwargs.get("capture_output") is True
    assert kwargs.get("text") is True
    assert kwargs.get("timeout") == 5


def test_to_posix_path_on_non_windows_passthrough() -> None:
    """Linux/macOS → helper returns str(path) without invoking cygpath.

    Uses ``PurePosixPath`` to avoid Windows's POSIX-path mangling (on
    Windows, ``Path("/usr/local/bin")`` becomes ``\\usr\\local\\bin``
    because Windows doesn't recognize it as absolute). The helper's
    contract is "return str(path)"; the path's *kind* (Pure vs Windows)
    is irrelevant on a non-Windows platform because the helper returns
    before touching the path system.
    """
    from pathlib import PurePosixPath

    unix_path = PurePosixPath("/usr/local/bin")
    with (
        patch.object(sys, "platform", "linux"),
        patch("shutil.which") as mock_which,
        patch("subprocess.run") as mock_run,
    ):
        result = _to_posix_path(unix_path)  # type: ignore[arg-type]
    assert result == "/usr/local/bin", (
        f"non-Windows passthrough should return str(path); got {result!r}"
    )
    mock_which.assert_not_called()
    mock_run.assert_not_called()


def test_to_posix_path_falls_back_when_cygpath_missing() -> None:
    """Windows + cygpath missing → helper falls back to str(path), no crash."""
    win_path = Path("C:\\Users\\foo")
    with (
        patch.object(sys, "platform", "win32"),
        patch("shutil.which", return_value=None),
        patch("subprocess.run") as mock_run,
    ):
        result = _to_posix_path(win_path)
    assert result == str(win_path), f"missing cygpath should fall back to str(path); got {result!r}"
    mock_run.assert_not_called()
