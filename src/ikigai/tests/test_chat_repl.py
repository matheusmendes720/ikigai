"""T-17.3 + M16: Smoke tests for scripts/chat_repl.py (soul-aware REPL).

M16 SHIPPED scripts/chat_repl.py with no test coverage. These tests
prevent silent regressions:
- File exists + is valid Python
- --help flag exits cleanly with usage text
- Empty stdin (immediate EOF) exits cleanly without traceback
- Single input line + EOF exits cleanly without traceback
- --vault is required (argparse rejects missing required arg)

The REPL is interactive; we don't test the interactive loop directly (would
require pexpect / TUI driver). Instead, test the surfaces that matter:
parseable CLI args + clean exit on EOF + soul-aware output.
"""

from __future__ import annotations

import os
import py_compile
import subprocess
import sys
from pathlib import Path

import pytest

DEVNULL_PATH = os.devnull  # '/dev/null' on POSIX, 'nul' on Windows


# Repo layout: src/ikigai/tests/test_chat_repl.py → repo root is 3 parents up.
REPO = Path(__file__).resolve().parents[3]
CHAT_REPL = REPO / "scripts" / "chat_repl.py"


class TestChatReplFile:
    """Validates chat_repl.py file presence and Python validity."""

    def test_chat_repl_path_exists(self) -> None:
        assert CHAT_REPL.exists(), f"chat_repl.py not found at {CHAT_REPL}"

    def test_chat_repl_syntax_valid(self) -> None:
        """chat_repl.py must compile to bytecode (catches Python syntax errors)."""
        try:
            py_compile.compile(str(CHAT_REPL), doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"chat_repl.py has syntax error: {e}")


class TestChatReplCli:
    """Validates CLI surface: --help, --vault required, --profile flag."""

    def test_help_flag_exits_zero(self) -> None:
        """`--help` must exit 0 (argparse convention) and print usage text."""
        result = subprocess.run(
            [sys.executable, str(CHAT_REPL), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"--help exited non-zero: rc={result.returncode}\n"
            f"stderr={result.stderr}"
        )
        # argparse always prints "usage:" on --help
        combined = (result.stdout + result.stderr).lower()
        assert "usage:" in combined, (
            f"--help output missing 'usage:': {combined[:200]}"
        )
        # The description (IKIGAI REPL) should appear in --help text
        assert "repl" in combined or "chat" in combined, (
            f"--help output missing 'repl' or 'chat': {combined[:200]}"
        )

    def test_vault_required(self) -> None:
        """`--vault` is required; running without it must exit non-zero with usage."""
        result = subprocess.run(
            [sys.executable, str(CHAT_REPL)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # argparse exits 2 for missing required args
        assert result.returncode != 0, (
            "chat_repl.py without --vault should fail (missing required arg); "
            f"got rc=0\nstdout={result.stdout[:200]}"
        )
        combined = (result.stdout + result.stderr).lower()
        assert "vault" in combined, (
            f"Missing --vault error should mention 'vault': {combined[:200]}"
        )

    def test_profile_flag_accepted(self, tmp_path: Path) -> None:
        """`--profile ikigai-planner` should be accepted (no parse error)."""
        # Use empty stdin via os.devnull so the REPL exits on EOF after parse.
        with open(DEVNULL_PATH, "rb") as devnull:
            result = subprocess.run(
                [
                    sys.executable,
                    str(CHAT_REPL),
                    "--vault", str(tmp_path),
                    "--thread", "test-profile-flag",
                    "--profile", "ikigai-planner",
                ],
                stdin=devnull,
                capture_output=True,
                text=True,
                timeout=10,
            )
        # arg parse must succeed (rc != 2 from argparse); remaining output is
        # the soul summary. We only assert NO argparse error.
        combined = (result.stdout + result.stderr).lower()
        assert "unrecognized arguments" not in combined, (
            f"--profile rejected by argparse: {combined[:200]}"
        )


class TestChatReplEofHandling:
    """Validates EOF (empty stdin / Ctrl+D / immediate close) exits gracefully."""

    def test_empty_stdin_exits_clean(self, tmp_path: Path) -> None:
        """Empty stdin must exit without traceback (graceful EOF handling)."""
        with open(DEVNULL_PATH, "rb") as devnull:
            result = subprocess.run(
                [
                    sys.executable,
                    str(CHAT_REPL),
                    "--vault", str(tmp_path),
                    "--thread", "test-empty-stdin",
                ],
                stdin=devnull,
                capture_output=True,
                text=True,
                timeout=10,
            )
        combined = result.stdout + result.stderr
        assert "Traceback" not in combined, (
            f"chat_repl.py crashed on empty stdin:\n{combined[:500]}"
        )

    def test_single_input_then_eof(self, tmp_path: Path) -> None:
        """Sending 'hello' followed by EOF should NOT crash (graceful)."""
        result = subprocess.run(
            [
                sys.executable,
                str(CHAT_REPL),
                "--vault", str(tmp_path),
                "--thread", "test-single-input",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            input="hello\n",
        )
        combined = result.stdout + result.stderr
        assert "Traceback" not in combined, (
            f"chat_repl.py crashed on single input:\n{combined[:500]}"
        )


class TestChatReplSoulAware:
    """Validates REPL output includes the active soul (M16 feature)."""

    def test_banner_includes_soul_name(self, tmp_path: Path) -> None:
        """The soul summary should appear in stdout on EOF (banner persists)."""
        with open(DEVNULL_PATH, "rb") as devnull:
            result = subprocess.run(
                [
                    sys.executable,
                    str(CHAT_REPL),
                    "--vault", str(tmp_path),
                    "--thread", "test-banner",
                    "--profile", "ikigai-planner",
                ],
                stdin=devnull,
                capture_output=True,
                text=True,
                timeout=10,
            )
        combined = result.stdout + result.stderr
        # M16 soul-aware REPL prints the soul summary at startup (banner).
        # The ikigai-planner soul should appear by name OR by characteristic
        # marker ("Planner Soul" in the source).
        assert "planner" in combined.lower() or "soul" in combined.lower(), (
            f"REPL output missing soul banner content:\n{combined[:500]}"
        )