"""pytest wrapper for the bash notify-wrap smoke test.

Runs tests/loop/test_notify_wrap.sh and asserts its exit code + key
markers in its stdout. Lets pytest collect/run the suite end-to-end.

Windows note: subprocess.run(["bash", ...]) fails with WinError 193
because subprocess.CreateProcess on Windows can't exec cygwin bash
directly. Workaround: use shell=True with a bash command string,
which routes through cmd.exe correctly on Windows.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
WRAP = REPO_ROOT / ".claude/helpers/notify-wrap.sh"
BASH_TEST = THIS_DIR / "test_notify_wrap.sh"


def _bash_path(p: Path) -> str:
    """Convert a Windows Path to a cygwin/git-bash-compatible path.

    bash on Windows expects forward-slash paths. Use as_posix() which
    gives "C:/Users/..."; bash on git-bash accepts that as well.
    """
    return p.as_posix()


def test_notify_wrap_bash_test_exists():
    assert WRAP.exists(), f"notify-wrap.sh missing at {WRAP}"
    assert BASH_TEST.exists(), f"bash test missing at {BASH_TEST}"


def test_notify_wrap_bash_test_passes(tmp_path, monkeypatch):
    """Run the bash test and assert all 4 PASS lines + exit 0."""
    monkeypatch.setenv("NOTIFY_FILE", str(tmp_path / "notifications.log"))
    log = tmp_path / "notifications.log"
    if log.exists():
        log.unlink()

    # shell=True routes through cmd.exe on Windows. The bash script runs
    # under cygwin bash because cmd.exe's PATH includes /usr/bin.
    cmd_str = "bash " + chr(34) + _bash_path(BASH_TEST) + chr(34)
    result = subprocess.run(
        cmd_str,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
        shell=True,
    )
    assert result.returncode == 0, (
        f"bash test failed (rc={result.returncode}):\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    expected_lines = [
        "PASS: success path wrote notification",
        "PASS: failure path wrote notification + propagated rc=1",
        "PASS: log contains title + rc + elapsed",
        "PASS: usage error when no command (rc=64)",
        "ALL notify-wrap tests passed",
    ]
    for line in expected_lines:
        assert line in result.stdout, f"missing expected: {line!r}\nstdout:\n{result.stdout}"


def test_notify_wrap_real_command(tmp_path, monkeypatch):
    """End-to-end: notify-wrap.sh echoes a string, log contains TITLE + rc."""
    monkeypatch.setenv("NOTIFY_FILE", str(tmp_path / "notifications.log"))
    log = tmp_path / "notifications.log"
    if log.exists():
        log.unlink()

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{REPO_ROOT}/src:{env.get('PYTHONPATH', '')}"

    # Run notify-wrap.sh schedule-name title-smoke-test "echo smoke-output"
    cmd_str = (
        "bash " + chr(34) + _bash_path(WRAP) + chr(34)
        + " schedule-name title-smoke-test " + chr(34) + "echo smoke-output" + chr(34)
    )
    result = subprocess.run(
        cmd_str,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        shell=True,
    )
    assert result.returncode == 0, f"wrap failed: {result.stderr}"
    assert log.exists()
    content = log.read_text(encoding="utf-8")
    # TITLE is in the log as the user-visible notification header
    assert "title-smoke-test" in content, f"missing title in log:\n{content}"
    assert "rc=0" in content, f"missing rc in log:\n{content}"
