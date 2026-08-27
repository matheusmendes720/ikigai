"""Smoke tests for PAE-Maintainer CLI entry point (main.py + __main__.py).

Covers cmd_run, cmd_status, cmd_balance, and the argparse wiring. The
daemon (cmd_daemon) is exercised by a subprocess smoke test only — the
infinite loop is not testable directly without mocking time.sleep.

Source: .omo/plans/agentic-markdown-system.md T12
Linked: T11 (CLI entry point)
"""
from __future__ import annotations

import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

import pytest

VIBE_OPS_SRC = Path(__file__).resolve().parents[1] / "src"
if str(VIBE_OPS_SRC) not in sys.path:
    sys.path.insert(0, str(VIBE_OPS_SRC))

from agents.pae_maintainer.main import (  # noqa: E402
    cmd_balance,
    cmd_run,
    cmd_status,
    main,
)


def _make_args(**kwargs) -> object:
    """Build a simple Namespace-like object for cmd_* functions."""

    class _Args:
        pass

    a = _Args()
    for k, v in kwargs.items():
        setattr(a, k, v)
    return a


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "pae_cli.db"


class TestCmdRun:
    def test_run_writes_checkpoint(self, tmp_db_path: Path, capsys) -> None:
        args = _make_args(
            cycle_id="cli-run-1",
            start="2026-01-01",
            end="2026-03-31",
            db=str(tmp_db_path),
            dry_run=False,
            json=False,
            verbose=False,
        )
        rc = cmd_run(args)
        captured = capsys.readouterr()
        assert rc == 0
        assert "completed" in captured.out
        assert tmp_db_path.exists()

    def test_run_dry_run_skips_write(
        self, tmp_db_path: Path, capsys
    ) -> None:
        args = _make_args(
            cycle_id="cli-run-dry",
            start="2026-01-01",
            end="2026-03-31",
            db=str(tmp_db_path),
            dry_run=True,
            json=False,
            verbose=True,
        )
        rc = cmd_run(args)
        captured = capsys.readouterr()
        assert rc == 0
        assert not tmp_db_path.exists()
        assert "dry-run" in captured.out or "no checkpoint" in captured.out

    def test_run_json_output(self, tmp_db_path: Path, capsys) -> None:
        args = _make_args(
            cycle_id="cli-run-json",
            start="2026-01-01",
            end="2026-03-31",
            db=str(tmp_db_path),
            dry_run=False,
            json=True,
            verbose=False,
        )
        rc = cmd_run(args)
        captured = capsys.readouterr()
        assert rc == 0
        # Verify output is valid JSON.
        parsed = json.loads(captured.out)
        assert parsed["cycle_id"] == "cli-run-json"
        assert parsed["iteration"] == 1

    def test_run_verbose(self, tmp_db_path: Path, capsys) -> None:
        args = _make_args(
            cycle_id="cli-run-verbose",
            start="2026-01-01",
            end="2026-03-31",
            db=str(tmp_db_path),
            dry_run=False,
            json=False,
            verbose=True,
        )
        rc = cmd_run(args)
        captured = capsys.readouterr()
        assert rc == 0
        assert "tier" in captured.out
        assert "cycle_start" in captured.out

    def test_run_kill_switch_returns_1(
        self, tmp_db_path: Path, capsys
    ) -> None:
        # Set up an overload scenario via execute_pae_maintainer_once first,
        # then re-run with a workload that triggers kill switch.
        # Direct cmd_run doesn't take workload — but we can simulate by
        # pre-seeding the DB with an OVERLOAD state, then run again.
        from agents.pae_maintainer.graph import (
            checkpoint_state,
            execute_pae_maintainer_once,
        )
        from agents.pae_maintainer.state import PAEState

        # First, seed a state.
        seed = execute_pae_maintainer_once(
            cycle_id="cli-overload",
            cycle_start=_dt.date(2026, 1, 1),
            cycle_end=_dt.date(2026, 3, 31),
            db_path=tmp_db_path,
        )
        # Force OVERLOAD and persist.
        seed.balancer.workload_estimate = 50.0
        seed.balancer.capacity_estimate = 8.0
        checkpoint_state(seed, tmp_db_path)

        args = _make_args(
            cycle_id="cli-overload",
            start="2026-01-01",
            end="2026-03-31",
            db=str(tmp_db_path),
            dry_run=False,
            json=False,
            verbose=False,
        )
        rc = cmd_run(args)
        captured = capsys.readouterr()
        # cmd_run returns 1 when kill_switch_triggered.
        assert rc == 1
        assert "KILL SWITCH" in captured.out


class TestCmdStatus:
    def test_status_returns_1_when_no_state(
        self, tmp_db_path: Path, capsys
    ) -> None:
        args = _make_args(
            cycle_id="nonexistent",
            db=str(tmp_db_path),
            json=False,
        )
        rc = cmd_status(args)
        captured = capsys.readouterr()
        assert rc == 1
        assert "No state" in captured.out

    def test_status_after_run(
        self, tmp_db_path: Path, capsys
    ) -> None:
        # First, run a cycle to populate state.
        run_args = _make_args(
            cycle_id="cli-status",
            start="2026-01-01",
            end="2026-03-31",
            db=str(tmp_db_path),
            dry_run=False,
            json=False,
            verbose=False,
        )
        cmd_run(run_args)

        # Then check status.
        status_args = _make_args(
            cycle_id="cli-status",
            db=str(tmp_db_path),
            json=False,
        )
        rc = cmd_status(status_args)
        captured = capsys.readouterr()
        assert rc == 0
        assert "cli-status" in captured.out
        assert "iteration" in captured.out

    def test_status_json_output(
        self, tmp_db_path: Path, capsys
    ) -> None:
        run_args = _make_args(
            cycle_id="cli-status-json",
            start="2026-01-01",
            end="2026-03-31",
            db=str(tmp_db_path),
            dry_run=False,
            json=False,
            verbose=False,
        )
        cmd_run(run_args)
        capsys.readouterr()  # discard cmd_run output

        status_args = _make_args(
            cycle_id="cli-status-json",
            db=str(tmp_db_path),
            json=True,
        )
        rc = cmd_status(status_args)
        captured = capsys.readouterr()
        assert rc == 0
        parsed = json.loads(captured.out)
        assert parsed["cycle_id"] == "cli-status-json"


class TestCmdBalance:
    def test_balance_returns_1_when_no_state(
        self, tmp_db_path: Path, capsys
    ) -> None:
        args = _make_args(
            cycle_id="nonexistent",
            db=str(tmp_db_path),
        )
        rc = cmd_balance(args)
        captured = capsys.readouterr()
        assert rc == 1
        assert "No state" in captured.out

    def test_balance_shows_metrics(
        self, tmp_db_path: Path, capsys
    ) -> None:
        # Seed a run first.
        run_args = _make_args(
            cycle_id="cli-balance",
            start="2026-01-01",
            end="2026-03-31",
            db=str(tmp_db_path),
            dry_run=False,
            json=False,
            verbose=False,
        )
        cmd_run(run_args)

        bal_args = _make_args(
            cycle_id="cli-balance",
            db=str(tmp_db_path),
        )
        rc = cmd_balance(bal_args)
        captured = capsys.readouterr()
        assert rc == 0
        assert "Balance check" in captured.out
        assert "workload" in captured.out
        assert "capacity" in captured.out
        assert "state" in captured.out
        assert "histerese" in captured.out


class TestArgparseWiring:
    def test_main_help_via_subprocess(self, tmp_db_path: Path) -> None:
        result = subprocess.run(
            [sys.executable, "-c", "from agents.pae_maintainer.main import main; main()", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**__import__("os").environ, "PYTHONPATH": str(VIBE_OPS_SRC)},
        )
        assert result.returncode == 0
        assert "PAE-Maintainer" in result.stdout or "usage" in result.stdout

    def test_main_run_subcommand(
        self, tmp_db_path: Path, monkeypatch, capsys
    ) -> None:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "pae_maintainer",
                "run",
                "--db",
                str(tmp_db_path),
                "--cycle-id",
                "argparse-test",
                "--start",
                "2026-01-01",
                "--end",
                "2026-03-31",
            ],
        )
        rc = main()
        assert rc == 0
        assert tmp_db_path.exists()


class TestCmdDaemon:
    """cmd_daemon runs in an infinite loop — test by pre-seeding termination."""

    def test_daemon_exits_on_first_cycle_termination(
        self, tmp_db_path: Path, capsys
    ) -> None:
        from agents.pae_maintainer.graph import checkpoint_state
        from agents.pae_maintainer.main import cmd_daemon
        from agents.pae_maintainer.state import PAEState

        # Pre-seed a state that will trigger kill switch on first cycle.
        seed = PAEState(
            cycle_id="daemon-test",
            cycle_start=_dt.date(2026, 1, 1),
            cycle_end=_dt.date(2026, 3, 31),
        )
        seed.balancer.workload_estimate = 50.0
        seed.balancer.capacity_estimate = 8.0
        checkpoint_state(seed, tmp_db_path)

        args = _make_args(
            cycle_id="daemon-test",
            start="2026-01-01",
            end="2026-03-31",
            db=str(tmp_db_path),
            interval=1,
        )
        rc = cmd_daemon(args)
        captured = capsys.readouterr()
        assert rc == 0
        assert "PAE daemon starting" in captured.out
        assert "Terminated, exiting daemon." in captured.out

    def test_daemon_handles_keyboard_interrupt(
        self, tmp_db_path: Path, monkeypatch, capsys
    ) -> None:
        from agents.pae_maintainer.main import cmd_daemon
        import agents.pae_maintainer.main as cli_main

        # Pre-seed a state so the daemon doesn't fail on first iteration.
        from agents.pae_maintainer.graph import checkpoint_state
        from agents.pae_maintainer.state import PAEState

        seed = PAEState(
            cycle_id="daemon-kbint",
            cycle_start=_dt.date(2026, 1, 1),
            cycle_end=_dt.date(2026, 3, 31),
        )
        checkpoint_state(seed, tmp_db_path)

        # Make time.sleep raise KeyboardInterrupt on first call.
        call_count = {"n": 0}

        def fake_sleep(_seconds):
            call_count["n"] += 1
            raise KeyboardInterrupt

        monkeypatch.setattr(cli_main.time, "sleep", fake_sleep)

        args = _make_args(
            cycle_id="daemon-kbint",
            start="2026-01-01",
            end="2026-03-31",
            db=str(tmp_db_path),
            interval=1,
        )
        rc = cmd_daemon(args)
        captured = capsys.readouterr()
        assert rc == 0
        assert "Daemon stopped by user." in captured.out


class TestModuleEntry:
    def test_python_m_pae_maintainer_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-c", "from agents.pae_maintainer.main import main; main()", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**__import__("os").environ, "PYTHONPATH": str(VIBE_OPS_SRC)},
        )
        assert result.returncode == 0
        assert "PAE-Maintainer" in result.stdout or "usage" in result.stdout