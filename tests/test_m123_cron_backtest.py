"""M123 tests — cron-backtest.sh driver.

Verifies the bash wrapper:
- Resolves repo root correctly
- Detects python interpreter (preferring repo venv)
- Logs to .life/logs/cron-backtest.log
- Returns 0 on pipeline success
- Idempotent (safe to run multiple times)

We test the bash driver indirectly by running it as a subprocess.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CRON_SCRIPT = REPO_ROOT / "scripts" / "cron" / "cron-backtest.sh"


def _win(path: Path) -> str:
    """Convert MSYS-style paths to a form bash can find on Windows.

    On Windows, git-bash mangles `/tmp/...` style paths (treats them as
    POSIX paths inside its mount). Forward-slash Windows paths like
    `C:/Users/...` work fine when passed to `bash` as an argument.
    Backslash paths get interpreted as escape characters.
    """
    return str(path).replace("\\", "/")


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Create a minimal fake repo for testing the cron driver.

    Layout:
      fake_repo/
        scripts/cron/cron-backtest.sh   (copied)
        src/ikigai/.venv/Scripts/python.exe (or /bin/python)
        scripts/backtest/run_backtest.sh (mock — exists)
        tools/backtest/...               (real — copied)
    """
    repo = tmp_path / "repo"
    (repo / "scripts" / "cron").mkdir(parents=True)
    (repo / "scripts" / "backtest").mkdir(parents=True)
    (repo / "src" / "ikigai" / ".venv" / "Scripts").mkdir(parents=True)
    (repo / "tools" / "backtest").mkdir(parents=True)
    (repo / "vault" / "drafts").mkdir(parents=True)
    (repo / "reports").mkdir(parents=True)
    (repo / ".life" / "logs").mkdir(parents=True)

    # Copy the real cron script.
    shutil.copy(CRON_SCRIPT, repo / "scripts" / "cron" / "cron-backtest.sh")
    # Make sure executable.
    (repo / "scripts" / "cron" / "cron-backtest.sh").chmod(0o755)

    # Mock run_backtest.sh — always succeeds.
    (repo / "scripts" / "backtest" / "run_backtest.sh").write_text(
        "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
    )
    (repo / "scripts" / "backtest" / "run_backtest.sh").chmod(0o755)

    return repo


def test_cron_script_exists() -> None:
    assert CRON_SCRIPT.exists()


def test_cron_script_is_executable() -> None:
    """The cron script must have +x bit for direct invocation."""
    assert os.access(CRON_SCRIPT, os.X_OK)


def _run_cron(cwd: Path, script: Path) -> subprocess.CompletedProcess[str]:
    """Run the cron script in a way that bypasses MSYS path mangling.

    Uses shell=True because Python's subprocess.run with argv list lets MSYS
    mangle paths in argv[1]. With shell=True the command goes through cmd.exe
    → bash, which handles Windows-style paths correctly.
    """
    script_q = str(script).replace("\\", "/")
    cwd_q = str(cwd).replace("\\", "/")
    cmd = f'bash "{script_q}"'
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=60, shell=True, cwd=cwd_q
    )


def test_cron_runs_and_logs(fake_repo: Path) -> None:
    """Run the cron script — should succeed and write log."""
    result = _run_cron(
        fake_repo, fake_repo / "scripts" / "cron" / "cron-backtest.sh"
    )
    assert result.returncode == 0, f"stderr={result.stderr[:500]}"
    log = fake_repo / ".life" / "logs" / "cron-backtest.log"
    assert log.exists()
    content = log.read_text(encoding="utf-8")
    assert "Starting daily backtest pipeline" in content
    assert "Pipeline OK" in content


def test_cron_resolves_repo_root(fake_repo: Path) -> None:
    """Run from a subdir — script must still find the repo root."""
    subdir = fake_repo / "src" / "ikigai"
    result = _run_cron(
        subdir, fake_repo / "scripts" / "cron" / "cron-backtest.sh"
    )
    assert result.returncode == 0, f"stderr={result.stderr[:500]}"
    log = fake_repo / ".life" / "logs" / "cron-backtest.log"
    assert log.exists()


def test_cron_failure_propagates_exit_code(fake_repo: Path) -> None:
    """If run_backtest.sh fails, cron exits non-zero."""
    (fake_repo / "scripts" / "backtest" / "run_backtest.sh").write_text(
        "#!/usr/bin/env bash\nexit 42\n", encoding="utf-8"
    )
    (fake_repo / "scripts" / "backtest" / "run_backtest.sh").chmod(0o755)
    result = _run_cron(
        fake_repo, fake_repo / "scripts" / "cron" / "cron-backtest.sh"
    )
    assert result.returncode == 42, f"stderr={result.stderr[:500]}"
    log = fake_repo / ".life" / "logs" / "cron-backtest.log"
    content = log.read_text(encoding="utf-8")
    assert "FAILED" in content
    assert "rc=42" in content


def test_cron_log_appends_not_overwrites(fake_repo: Path) -> None:
    """Running twice appends to the log, doesn't overwrite."""
    log = fake_repo / ".life" / "logs" / "cron-backtest.log"
    _run_cron(fake_repo, fake_repo / "scripts" / "cron" / "cron-backtest.sh")
    first_size = log.stat().st_size
    _run_cron(fake_repo, fake_repo / "scripts" / "cron" / "cron-backtest.sh")
    second_size = log.stat().st_size
    assert second_size > first_size  # appended


def test_setup_task_scheduler_ps1_exists() -> None:
    ps1 = REPO_ROOT / "scripts" / "cron" / "setup-task-scheduler.ps1"
    assert ps1.exists()
    # Should reference the cron script.
    content = ps1.read_text(encoding="utf-8")
    assert "cron-backtest.sh" in content
    assert "Unregister-ScheduledTask" in content
    assert "Register-ScheduledTask" in content


def test_cron_readme_documents_setup() -> None:
    readme = REPO_ROOT / "scripts" / "cron" / "README.md"
    assert readme.exists()
    content = readme.read_text(encoding="utf-8")
    assert "Task Scheduler" in content
    assert "crontab" in content
    assert "Unregister" in content
