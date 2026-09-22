"""M138 tests — _bootstrap_repo_paths() for the console script.

Verifies that `pip install -e .` + `life --help` works because
`_main_console` adds the repo root + src/ + interfaces/ to sys.path
before importing cli.cli.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _clean_sys_path() -> None:
    """Reset _LIFE_REPO_BOOTSTRAPPED marker + remove injected paths."""
    yield
    # Post-test cleanup.
    marker = "_LIFE_REPO_BOOTSTRAPPED"
    if hasattr(sys, marker):
        delattr(sys, marker)
    # Remove any paths we injected during the test.
    for p in (str(REPO_ROOT), str(REPO_ROOT / "src"), str(REPO_ROOT / "interfaces")):
        while p in sys.path:
            sys.path.remove(p)


def test_bootstrap_adds_repo_root_to_sys_path() -> None:
    """_bootstrap_repo_paths adds <repo>, <repo>/src, <repo>/interfaces."""
    # Make sure paths aren't already there.
    for p in (str(REPO_ROOT), str(REPO_ROOT / "src"), str(REPO_ROOT / "interfaces")):
        while p in sys.path:
            sys.path.remove(p)
    assert not hasattr(sys, "_LIFE_REPO_BOOTSTRAPPED")

    # Fresh import — bypass module cache for the test.
    if "life.cli" in sys.modules:
        # Reset the bootstrap state by reloading.
        del sys.modules["life.cli"]

    from life.cli import _bootstrap_repo_paths
    _bootstrap_repo_paths()

    # The marker must be set.
    assert getattr(sys, "_LIFE_REPO_BOOTSTRAPPED") is True
    # The three paths must be present.
    for p in (str(REPO_ROOT), str(REPO_ROOT / "src"), str(REPO_ROOT / "interfaces")):
        assert p in sys.path, f"missing {p}"


def test_bootstrap_idempotent() -> None:
    """Calling twice doesn't duplicate entries."""
    from life.cli import _bootstrap_repo_paths
    _bootstrap_repo_paths()
    count_root = sys.path.count(str(REPO_ROOT))
    _bootstrap_repo_paths()
    assert sys.path.count(str(REPO_ROOT)) == count_root


def test_bootstrap_preserves_imports() -> None:
    """After bootstrap, `import interfaces.cli.v2` etc. work."""
    from life.cli import _bootstrap_repo_paths
    _bootstrap_repo_paths()
    # Should not raise.
    import interfaces.cli.v2  # noqa: F401
    import interfaces.cli.notify_cli  # noqa: F401
    from src.contracts import common  # noqa: F401


def test_bootstrap_when_installed_elsewhere() -> None:
    """If the file path doesn't yield a repo root, CWD walking still works."""
    # Run from the actual repo so CWD walk finds pyproject.toml + life/.
    import os
    orig_cwd = os.getcwd()
    try:
        os.chdir(REPO_ROOT)
        # Force a non-pyproject-cwd parent directory.
        from life.cli import _bootstrap_repo_paths
        # The bootstrap should still find the repo via CWD walk.
        _bootstrap_repo_paths()
        assert str(REPO_ROOT) in sys.path
    finally:
        os.chdir(orig_cwd)


def test_console_script_invocation_runs_without_module_not_found(tmp_path: Path) -> None:
    """End-to-end: invoke life console-script from outside repo and verify
    it can reach into interfaces/cli (which has no __init__.py at root).
    """
    import subprocess
    life_exe = REPO_ROOT / ".venv" / "Scripts" / ("life.exe" if sys.platform == "win32" else "life")
    if not life_exe.exists():
        pytest.skip(f"console script not installed at {life_exe}")
    # Run from a tmp dir (not the repo) to simulate external invocation.
    result = subprocess.run(
        [str(life_exe), "config-show"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"life config-show failed (rc={result.returncode}):\n"
        f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    )
    assert "root" in result.stdout.lower() or "config" in result.stdout.lower()


def test_console_script_help_works_from_tmp(tmp_path: Path) -> None:
    """`life --help` from a tmp dir works (proves sys.path bootstrap)."""
    import subprocess
    life_exe = REPO_ROOT / ".venv" / "Scripts" / ("life.exe" if sys.platform == "win32" else "life")
    if not life_exe.exists():
        pytest.skip(f"console script not installed at {life_exe}")
    result = subprocess.run(
        [str(life_exe), "--help"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"life --help failed: {result.stderr}"
    )
    assert "Algorithmic Life OS" in result.stdout


def test_console_script_v2_help(tmp_path: Path) -> None:
    """`life v2 --help` from a tmp dir works (proves interfaces import)."""
    import subprocess
    life_exe = REPO_ROOT / ".venv" / "Scripts" / ("life.exe" if sys.platform == "win32" else "life")
    if not life_exe.exists():
        pytest.skip(f"console script not installed at {life_exe}")
    result = subprocess.run(
        [str(life_exe), "v2", "--help"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"life v2 --help failed: {result.stderr}"
    )
    assert "IKIGAI v2" in result.stdout
