"""Integration tests for `pav sync` subcommand (T8).

Exercises the Typer app via CliRunner with a mocked `_run_vault_sync`
so tests run in-process without spawning real subprocesses.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

# Ensure operational CLI is importable.
OPERATIONAL_SRC = Path(__file__).resolve().parents[2] / "apps" / "cli" / "src"
if str(OPERATIONAL_SRC) not in sys.path:
    sys.path.insert(0, str(OPERATIONAL_SRC))

from operational.cli.commands.sync_cmd import app  # noqa: E402


runner = CliRunner()


@pytest.fixture
def mock_subprocess() -> Iterator:
    """Patch _run_vault_sync to return canned JSON, no real subprocess."""
    responses = {}

    def _fake(subcmd, vault, db, json_out):
        key = (subcmd, vault, db)
        if key not in responses:
            responses[key] = (0, json.dumps({"ok": True, "subcmd": subcmd}))
        return responses[key]

    with patch(
        "operational.cli.commands.sync_cmd._run_vault_sync",
        side_effect=_fake,
    ):
        # Make every (subcmd, vault, db) lookup succeed by default.
        yield responses


@pytest.fixture
def mock_subprocess_fail() -> Iterator:
    """Patch _run_vault_sync to return non-zero exit code."""
    def _fake(_subcmd, _vault, _db, _json_out):
        return 1, ""

    with patch(
        "operational.cli.commands.sync_cmd._run_vault_sync",
        side_effect=_fake,
    ):
        yield


class TestSyncHelp:
    def test_app_help_lists_subcommands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "vault" in result.stdout
        assert "code" in result.stdout
        assert "all" in result.stdout
        assert "status" in result.stdout
        assert "conflicts" in result.stdout


class TestSyncVault:
    def test_vault_invokes_subprocess(self, mock_subprocess):
        result = runner.invoke(
            app, ["vault", "--vault", "C:/test/vault", "--json"]
        )
        assert result.exit_code == 0
        parsed = json.loads(result.stdout)
        assert parsed["ok"] is True
        assert parsed["subcmd"] == "vault"

    def test_vault_text_output(self, mock_subprocess):
        result = runner.invoke(
            app, ["vault", "--vault", "C:/test/vault"]
        )
        assert result.exit_code == 0


class TestSyncCode:
    def test_code_invokes_subprocess(self, mock_subprocess):
        result = runner.invoke(
            app, ["code", "--vault", "C:/test/vault", "--json"]
        )
        assert result.exit_code == 0
        parsed = json.loads(result.stdout)
        assert parsed["subcmd"] == "code"


class TestSyncAll:
    def test_all_invokes_subprocess(self, mock_subprocess):
        result = runner.invoke(
            app, ["all", "--vault", "C:/test/vault", "--json"]
        )
        assert result.exit_code == 0
        parsed = json.loads(result.stdout)
        assert parsed["subcmd"] == "all"


class TestSyncStatus:
    def test_status_invokes_subprocess(self, mock_subprocess):
        result = runner.invoke(app, ["status", "--json"])
        assert result.exit_code == 0
        parsed = json.loads(result.stdout)
        assert parsed["subcmd"] == "status"

    def test_status_with_vault(self, mock_subprocess):
        result = runner.invoke(
            app, ["status", "--vault", "C:/test/vault", "--json"]
        )
        assert result.exit_code == 0


class TestSyncConflicts:
    def test_conflicts_invokes_subprocess(self, mock_subprocess):
        result = runner.invoke(
            app, ["conflicts", "--vault", "C:/test/vault", "--json"]
        )
        assert result.exit_code == 0
        parsed = json.loads(result.stdout)
        assert parsed["subcmd"] == "conflicts"


class TestExitCodes:
    def test_nonzero_exit_propagates(self, mock_subprocess_fail):
        result = runner.invoke(
            app, ["vault", "--vault", "C:/test/vault", "--json"]
        )
        assert result.exit_code != 0

    def test_missing_vault_argument_fails(self, mock_subprocess):
        result = runner.invoke(app, ["vault", "--json"])
        assert result.exit_code != 0


class TestJsonOutputShape:
    def test_vault_json_has_required_keys(self, mock_subprocess):
        result = runner.invoke(
            app, ["vault", "--vault", "C:/test/vault", "--json"]
        )
        assert result.exit_code == 0
        parsed = json.loads(result.stdout)
        assert "ok" in parsed
        assert "subcmd" in parsed
        assert parsed["subcmd"] == "vault"

    def test_status_json_has_required_keys(self, mock_subprocess):
        result = runner.invoke(app, ["status", "--json"])
        parsed = json.loads(result.stdout)
        assert "ok" in parsed
        assert "subcmd" in parsed