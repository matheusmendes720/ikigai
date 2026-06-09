"""Tests that home v2 pauses with 'Press Enter to continue' after each command."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

_TMP_STATE = Path(tempfile.gettempdir()) / "time-tasker-home-pause-test"
_TMP_STATE.mkdir(parents=True, exist_ok=True)
os.environ["TIME_TASKER_STATE_DIR"] = str(_TMP_STATE)

import sys
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from operational.cli.app import app  # noqa: E402

runner = CliRunner()


class TestHomeV2Pause:
    def test_pause_prompt_appears(self, monkeypatch) -> None:
        """After selecting a menu option, 'Press Enter to continue' should appear."""
        # Bypass the menu prompt (answer '5' = dashboard) and the pause prompt (Enter)
        from rich.prompt import Prompt
        prompt_calls = []

        def fake_ask(*args, **kwargs):
            prompt_calls.append((args, kwargs))
            return ""  # simulate user pressing Enter

        monkeypatch.setattr(Prompt, "ask", fake_ask)

        # Run 'home --v2' and provide input: "5" then Enter (via fake_ask)
        result = runner.invoke(app, ["home", "--v2"], input="5\n")
        # The fake_ask should have been called for both the menu choice
        # and the pause prompt
        assert len(prompt_calls) >= 2, f"Expected at least 2 prompt calls, got {len(prompt_calls)}"

        # The pause prompt should contain "Press Enter to continue"
        pause_calls = [
            (args, kwargs)
            for (args, kwargs) in prompt_calls
            if args and "Press Enter" in str(args[0])
        ]
        assert len(pause_calls) >= 1, \
            f"Expected at least one 'Press Enter to continue' prompt, got prompts: {prompt_calls}"

    def test_no_pause_for_quit(self, monkeypatch) -> None:
        """When user chooses 'q', no pause prompt should appear (clean exit)."""
        from rich.prompt import Prompt

        # Use a counter + max-iterations guard instead of signal (Windows compat)
        call_count = {"n": 0}
        MAX_CALLS = 5  # menu + maybe 1 pause = should be way under this

        def fake_ask(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] > MAX_CALLS:
                # Bail out: simulate quit
                return "q"
            # First call is the menu (return "q" to quit)
            if call_count["n"] == 1:
                return "q"
            # Subsequent calls would be pause prompts — bail to prevent loop
            return "q"

        monkeypatch.setattr(Prompt, "ask", fake_ask)

        prompt_calls = []
        original_fake = fake_ask
        def tracker(*args, **kwargs):
            prompt_calls.append((args, kwargs))
            return original_fake(*args, **kwargs)
        monkeypatch.setattr(Prompt, "ask", tracker)

        try:
            runner.invoke(app, ["home", "--v2"])
        except Exception:
            pass

        # Find any 'Press Enter' prompt — should not exist for quit
        pause_calls = [
            (args, kwargs)
            for (args, kwargs) in prompt_calls
            if args and "Press Enter" in str(args[0])
        ]
        assert len(pause_calls) == 0, \
            f"Quit should not trigger a pause prompt, got {len(pause_calls)} pause calls"
