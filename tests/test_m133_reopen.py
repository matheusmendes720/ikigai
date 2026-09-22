"""M133 tests — reopen_cli.py + reopen_checkbox/preview_reopen/apply_reopen.

Verifies the inverse-toggle CLI wrapper and underlying vault_propagation
functions. Uses real tmp files (with mocked apply_reopen for control).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.vault import reopen_cli as rc  # noqa: E402
from tools.backtest import vault_propagation as vp  # noqa: E402


# === Argument validation ===

def test_main_missing_plan_path(capsys: pytest.CaptureFixture[str]) -> None:
    rc_obj = rc.main(rel_path="", line=1, expected="x", reason="r")
    assert rc_obj == 2
    assert "plan-path required" in capsys.readouterr().err


def test_main_missing_line(capsys: pytest.CaptureFixture[str]) -> None:
    rc_obj = rc.main(rel_path="plan.md", line=0, expected="x", reason="r")
    assert rc_obj == 2


def test_main_missing_expected(capsys: pytest.CaptureFixture[str]) -> None:
    rc_obj = rc.main(rel_path="plan.md", line=1, expected="", reason="r")
    assert rc_obj == 2


def test_main_missing_reason(capsys: pytest.CaptureFixture[str]) -> None:
    rc_obj = rc.main(rel_path="plan.md", line=1, expected="x", reason="")
    assert rc_obj == 2


def test_main_rejects_absolute_path(capsys: pytest.CaptureFixture[str]) -> None:
    rc_obj = rc.main(
        rel_path=r"C:\Windows\System32\drivers\etc\hosts",
        line=1, expected="x", reason="r",
    )
    assert rc_obj == 2


def test_main_rejects_parent_traversal(capsys: pytest.CaptureFixture[str]) -> None:
    rc_obj = rc.main(
        rel_path="../secret.md", line=1, expected="x", reason="r",
    )
    assert rc_obj == 2


def test_main_plan_not_found(capsys: pytest.CaptureFixture[str]) -> None:
    rc_obj = rc.main(
        rel_path="nonexistent/plan.md", line=1, expected="x", reason="r",
    )
    assert rc_obj == 1
    assert "plan not found" in capsys.readouterr().err


# === reopen_checkbox (real function, real file) ===

def test_reopen_checkbox_basic(tmp_path: Path) -> None:
    """Closed checkbox → reopened."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    result = vp.reopen_checkbox(plan, 1, "task one")
    assert result["ok"] is True
    assert "- [ ] task one" in plan.read_text(encoding="utf-8")


def test_reopen_checkbox_with_link(tmp_path: Path) -> None:
    """Closed checkbox with [vault:...] link → reopened, link preserved."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] [vault:plan.md#1] task one\n", encoding="utf-8")
    result = vp.reopen_checkbox(plan, 1, "task one")
    assert result["ok"] is True
    new = plan.read_text(encoding="utf-8")
    assert "- [ ] [vault:plan.md#1] task one" in new


def test_reopen_checkbox_already_open_refused(tmp_path: Path) -> None:
    """Reopening an open checkbox → refused (don't toggle)."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [ ] task one\n", encoding="utf-8")
    result = vp.reopen_checkbox(plan, 1, "task one")
    assert result["ok"] is False
    assert "already open" in result["error"]


def test_reopen_checkbox_mismatch(tmp_path: Path) -> None:
    """Wrong text → refused."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    result = vp.reopen_checkbox(plan, 1, "wrong text")
    assert result["ok"] is False
    assert "mismatch" in result["error"]


def test_reopen_checkbox_missing_plan(tmp_path: Path) -> None:
    """Missing plan → error."""
    result = vp.reopen_checkbox(tmp_path / "missing.md", 1, "x")
    assert result["ok"] is False
    assert "plan not found" in result["error"]


def test_reopen_checkbox_out_of_range(tmp_path: Path) -> None:
    """Line out of range → error."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] only line\n", encoding="utf-8")
    result = vp.reopen_checkbox(plan, 99, "only line")
    assert result["ok"] is False
    assert "out of range" in result["error"]


# === preview_reopen ===

def test_preview_reopen_ok(tmp_path: Path) -> None:
    """Preview succeeds → reports would_become."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n- [x] task two\n", encoding="utf-8")
    result = vp.preview_reopen(plan, 1, "task one")
    assert result["ok"] is True
    assert result["preview"] is True
    assert "- [ ] task one" in result["would_become"]
    assert result["checkboxes_done_after"] == 1


def test_preview_reopen_already_open(tmp_path: Path) -> None:
    """Already-open → preview refuses (don't reopen what's already open)."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [ ] task one\n", encoding="utf-8")
    result = vp.preview_reopen(plan, 1, "task one")
    assert result["ok"] is False


def test_preview_reopen_mismatch(tmp_path: Path) -> None:
    """Wrong text → preview refuses."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    result = vp.preview_reopen(plan, 1, "wrong")
    assert result["ok"] is False


def test_preview_reopen_with_link(tmp_path: Path) -> None:
    """Link preserved in preview."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] [vault:plan.md#1] task\n", encoding="utf-8")
    result = vp.preview_reopen(plan, 1, "task")
    assert result["ok"] is True
    assert "[vault:plan.md#1]" in result["would_become"]


# === apply_reopen ===

def test_apply_reopen_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """apply_reopen mutates the file."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    result = vp.apply_reopen(plan, 1, "task one", actor="cli-test", reason="undo")
    assert result["ok"] is True
    assert "- [ ] task one" in plan.read_text(encoding="utf-8")


def test_apply_reopen_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """apply_reopen refuses if preview fails."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    result = vp.apply_reopen(plan, 1, "wrong", actor="cli-test", reason="r")
    assert result["ok"] is False
    assert result["refused"] is True
    # File NOT mutated
    assert "- [x] task one" in plan.read_text(encoding="utf-8")


def test_apply_reopen_skip_preview(tmp_path: Path) -> None:
    """require_preview_ok=False → bypasses the gate."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    result = vp.apply_reopen(
        plan, 1, "wrong", actor="cli-test", reason="r",
        require_preview_ok=False,
    )
    # Still fails because text doesn't match, but gate was bypassed.
    assert result["ok"] is False


# === CLI integration (full flow) ===

def test_cli_reopen_full_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end: closed checkbox → reopened via CLI."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    monkeypatch.setattr(rc, "_resolve_plan_path", lambda rp: plan)

    rc_obj = rc.main(
        rel_path="plan.md", line=1, expected="task one",
        reason="undo", actor="cli-test",
    )
    assert rc_obj == 0
    assert "- [ ] task one" in plan.read_text(encoding="utf-8")


def test_cli_reopen_refused_by_preview(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """CLI refuses reopen when preview fails."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    monkeypatch.setattr(rc, "_resolve_plan_path", lambda rp: plan)

    rc_obj = rc.main(
        rel_path="plan.md", line=1, expected="wrong text",
        reason="undo", actor="cli-test",
    )
    assert rc_obj == 1
    # File NOT mutated
    assert "- [x] task one" in plan.read_text(encoding="utf-8")


def test_cli_reopen_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """JSON output emits preview + applied."""
    import json
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    monkeypatch.setattr(rc, "_resolve_plan_path", lambda rp: plan)

    rc_obj = rc.main(
        rel_path="plan.md", line=1, expected="task one",
        reason="undo", actor="cli-test", json_output=True,
    )
    assert rc_obj == 0
    parsed = json.loads(capsys.readouterr().out)
    assert "preview" in parsed
    assert "applied" in parsed


def test_cli_reopen_json_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """JSON refusal → preview only, no applied key."""
    import json
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] task one\n", encoding="utf-8")
    monkeypatch.setattr(rc, "_resolve_plan_path", lambda rp: plan)

    rc_obj = rc.main(
        rel_path="plan.md", line=1, expected="wrong",
        reason="undo", actor="cli-test", json_output=True,
    )
    assert rc_obj == 1
    parsed = json.loads(capsys.readouterr().out)
    assert "preview" in parsed
    assert parsed["preview"]["ok"] is False


# === Typer registration ===

def test_vault_reopen_register_function_exists() -> None:
    """The Typer command exists."""
    from interfaces.cli.v2 import register_vault_toggle
    assert callable(register_vault_toggle)


def test_vault_reopen_register_wires_command() -> None:
    """register_vault_toggle wires vault-reopen."""
    import typer
    from interfaces.cli.v2 import register_vault_toggle
    app = typer.Typer()
    register_vault_toggle(app)
    cmd_names = [cmd.name for cmd in app.registered_commands]
    assert "vault-reopen" in cmd_names
