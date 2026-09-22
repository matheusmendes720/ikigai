"""M131 tests — apply_toggle_cli.py (vault toggle CLI wrapper).

Verifies the CLI wrapper around vault_propagation.preview_toggle / apply_toggle.
Tests use mocked preview_toggle / apply_toggle functions so they're hermetic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.vault import apply_toggle_cli as atc  # noqa: E402


# === _resolve_plan_path ===

def test_resolve_plan_path_rejects_absolute(tmp_path: Path) -> None:
    """Absolute paths raise ValueError."""
    # Use a real Windows absolute path (POSIX-style /etc/passwd is relative on Windows).
    with pytest.raises(ValueError, match="absolute paths not allowed"):
        atc._resolve_plan_path(r"C:\Windows\System32\drivers\etc\hosts")


def test_resolve_plan_path_rejects_parent_traversal(tmp_path: Path) -> None:
    """Parent traversal (..) raises ValueError."""
    with pytest.raises(ValueError, match="parent traversal not allowed"):
        atc._resolve_plan_path("../sneaky.md")


def test_resolve_plan_path_resolves_to_vault() -> None:
    """Relative paths resolve to <repo_root>/vault/<rel>."""
    result = atc._resolve_plan_path("drafts/plan.md")
    assert result.name == "plan.md"
    assert "vault" in result.parts


# === main: argument validation ===

def test_main_unknown_command(capsys: pytest.CaptureFixture[str]) -> None:
    """Unknown command → exit 2."""
    rc = atc.main("nope")
    assert rc == 2
    captured = capsys.readouterr()
    assert "unknown command" in captured.err


def test_main_missing_plan_path(capsys: pytest.CaptureFixture[str]) -> None:
    rc = atc.main("preview")
    assert rc == 2
    assert "plan-path required" in capsys.readouterr().err


def test_main_missing_line(capsys: pytest.CaptureFixture[str]) -> None:
    rc = atc.main("preview", rel_path="plan.md")
    assert rc == 2
    assert "line required" in capsys.readouterr().err


def test_main_zero_line(capsys: pytest.CaptureFixture[str]) -> None:
    rc = atc.main("preview", rel_path="plan.md", line=0)
    assert rc == 2


def test_main_missing_expected(capsys: pytest.CaptureFixture[str]) -> None:
    rc = atc.main("preview", rel_path="plan.md", line=1)
    assert rc == 2
    assert "expected required" in capsys.readouterr().err


def test_main_apply_missing_reason(capsys: pytest.CaptureFixture[str]) -> None:
    rc = atc.main("apply", rel_path="plan.md", line=1, expected="x")
    assert rc == 2
    assert "reason required" in capsys.readouterr().err


def test_main_toggle_missing_reason(capsys: pytest.CaptureFixture[str]) -> None:
    rc = atc.main("toggle", rel_path="plan.md", line=1, expected="x")
    assert rc == 2


# === main: plan-not-found ===

def test_main_plan_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Non-existent plan → exit 1."""
    # Point to a vault path that doesn't exist.
    # Use a path that's syntactically valid but doesn't exist.
    rel = "nonexistent/plan.md"
    rc = atc.main("preview", rel_path=rel, line=1, expected="x")
    assert rc == 1
    assert "plan not found" in capsys.readouterr().err


# === main: preview ===

def test_main_preview_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Successful preview → exit 0, prints 'Would become'."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [ ] task one\n- [ ] task two\n", encoding="utf-8")
    # Make _resolve_plan_path return our tmp_path
    monkeypatch.setattr(atc, "_resolve_plan_path", lambda rp: plan)
    rc = atc.main("preview", rel_path="plan.md", line=1, expected="task one")
    assert rc == 0
    captured = capsys.readouterr()
    assert "Would become" in captured.out
    assert "- [x] task one" in captured.out


def test_main_preview_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Preview that fails → exit 1, prints REFUSED."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] already done\n", encoding="utf-8")
    monkeypatch.setattr(atc, "_resolve_plan_path", lambda rp: plan)
    rc = atc.main("preview", rel_path="plan.md", line=1, expected="not matching")
    assert rc == 1
    captured = capsys.readouterr()
    assert "REFUSED" in captured.out


# === main: apply (real vault files) ===
#
# These tests use the real vault_propagation path. We create a real plan
# file in a tmp dir and patch _resolve_plan_path to point at it, AND
# patch the underlying vault_propagation.preview_toggle / apply_toggle
# so we don't have to worry about repo_root / VAULT_DIR path resolution.

@pytest.fixture
def real_plan_in_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Create a real plan file in tmp and patch _resolve_plan_path to find it."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [ ] task one\n- [ ] task two\n", encoding="utf-8")
    monkeypatch.setattr(atc, "_resolve_plan_path", lambda rp: plan)
    return plan


def test_main_apply_ok(
    real_plan_in_tmp: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Successful apply → exit 0, file actually mutated."""
    plan = real_plan_in_tmp

    # Patch the underlying vault_propagation functions so they operate on
    # our tmp file directly (bypassing VAULT_DIR resolution).
    from tools.backtest import vault_propagation as vp

    def fake_preview(plan_path, target_line, expected_text):
        return {
            "ok": True,
            "preview": True,
            "would_become": f"- [x] {expected_text}",
            "file_path": str(plan_path),
            "checkboxes_done_after": 1,
        }

    def fake_apply(plan_path, target_line, expected_text, actor, reason, *, require_preview_ok=True):
        # Mutate the file ourselves.
        text = plan_path.read_text(encoding="utf-8")
        new_text = text.replace(f"- [ ] {expected_text}", f"- [x] {expected_text}", 1)
        plan_path.write_text(new_text, encoding="utf-8")
        vp.append_event({"event": "fake_apply", "actor": actor, "reason": reason})
        return {"ok": True, "file_path": str(plan_path)}

    monkeypatch.setattr(vp, "preview_toggle", fake_preview)
    monkeypatch.setattr(vp, "apply_toggle", fake_apply)

    rc = atc.main("apply", rel_path="plan.md", line=1, expected="task one",
                  reason="test", actor="cli-test")
    assert rc == 0
    assert "- [x] task one" in plan.read_text(encoding="utf-8")


def test_main_apply_refused_by_preview(
    real_plan_in_tmp: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Apply with preview failure → exit 1, file NOT mutated."""
    plan = real_plan_in_tmp

    from tools.backtest import vault_propagation as vp

    def fake_preview(plan_path, target_line, expected_text):
        return {
            "ok": False,
            "error": f"line {target_line} mismatch: expected {expected_text!r}",
            "file_path": str(plan_path),
        }

    def fake_apply(plan_path, target_line, expected_text, actor, reason, *, require_preview_ok=True):
        # This shouldn't be called when preview refuses, but record anyway.
        return {"ok": False, "refused": True, "preview": {"ok": False}}

    monkeypatch.setattr(vp, "preview_toggle", fake_preview)
    monkeypatch.setattr(vp, "apply_toggle", fake_apply)

    rc = atc.main("apply", rel_path="plan.md", line=1, expected="not matching",
                  reason="test", actor="cli-test")
    assert rc == 1
    # File was NOT mutated
    assert "- [ ] task one" in plan.read_text(encoding="utf-8")


def test_main_apply_skip_preview(
    real_plan_in_tmp: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--skip-preview bypasses the preview gate (trusted scripts only)."""
    plan = real_plan_in_tmp

    from tools.backtest import vault_propagation as vp

    apply_called_with_skip = []

    def fake_apply(plan_path, target_line, expected_text, actor, reason, *, require_preview_ok=True):
        apply_called_with_skip.append(require_preview_ok)
        return {
            "ok": False,
            "error": "text mismatch",
            "file_path": str(plan_path),
        }

    monkeypatch.setattr(vp, "apply_toggle", fake_apply)

    rc = atc.main("apply", rel_path="plan.md", line=1, expected="not matching",
                  reason="test", actor="cli-test", skip_preview=True)
    assert rc == 1
    # Skip preview was honored (apply_toggle called with require_preview_ok=False).
    assert apply_called_with_skip == [False]


# === main: toggle (combined) ===

def test_main_toggle_combined_success(
    real_plan_in_tmp: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """toggle = preview + apply; both succeed → exit 0, file mutated."""
    plan = real_plan_in_tmp

    from tools.backtest import vault_propagation as vp

    def fake_preview(plan_path, target_line, expected_text):
        return {
            "ok": True,
            "preview": True,
            "would_become": f"- [x] {expected_text}",
            "file_path": str(plan_path),
            "checkboxes_done_after": 1,
        }

    def fake_apply(plan_path, target_line, expected_text, actor, reason, *, require_preview_ok=True):
        text = plan_path.read_text(encoding="utf-8")
        new_text = text.replace(f"- [ ] {expected_text}", f"- [x] {expected_text}", 1)
        plan_path.write_text(new_text, encoding="utf-8")
        return {"ok": True, "file_path": str(plan_path)}

    monkeypatch.setattr(vp, "preview_toggle", fake_preview)
    monkeypatch.setattr(vp, "apply_toggle", fake_apply)

    rc = atc.main("toggle", rel_path="plan.md", line=1, expected="task one",
                  reason="test", actor="cli-test")
    assert rc == 0
    assert "- [x] task one" in plan.read_text(encoding="utf-8")


def test_main_toggle_refused_by_preview(
    real_plan_in_tmp: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """toggle where preview fails → exit 1, no mutation."""
    plan = real_plan_in_tmp

    from tools.backtest import vault_propagation as vp

    def fake_preview(plan_path, target_line, expected_text):
        return {"ok": False, "error": "mismatch", "file_path": str(plan_path)}

    apply_called = []

    def fake_apply(plan_path, *args, **kwargs):
        apply_called.append(True)
        return {"ok": True}

    monkeypatch.setattr(vp, "preview_toggle", fake_preview)
    monkeypatch.setattr(vp, "apply_toggle", fake_apply)

    rc = atc.main("toggle", rel_path="plan.md", line=1, expected="not matching",
                  reason="test", actor="cli-test")
    assert rc == 1
    # apply_toggle was NOT called (preview refused → no mutation)
    assert apply_called == []


# === JSON output ===

def test_main_preview_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """preview --json emits valid JSON."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [ ] task one\n", encoding="utf-8")
    monkeypatch.setattr(atc, "_resolve_plan_path", lambda rp: plan)
    rc = atc.main("preview", rel_path="plan.md", line=1, expected="task one", json_output=True)
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed.get("ok") is True
    assert parsed.get("preview") is True


def test_main_apply_json_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """apply --json with preview failure returns JSON with refused=true."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [x] already done\n", encoding="utf-8")
    monkeypatch.setattr(atc, "_resolve_plan_path", lambda rp: plan)
    rc = atc.main("apply", rel_path="plan.md", line=1, expected="not matching",
                  reason="test", actor="cli-test", json_output=True)
    assert rc == 1
    parsed = json.loads(capsys.readouterr().out)
    assert parsed.get("refused") is True
    assert "preview" in parsed


# === Typer registration ===

def test_vault_toggle_register_function_exists() -> None:
    """The Typer registration function exists."""
    from interfaces.cli.v2 import register_vault_toggle
    assert callable(register_vault_toggle)


def test_vault_toggle_register_wires_three_commands() -> None:
    """register_vault_toggle wires 3 commands: vault-preview, vault-apply, vault-toggle."""
    import typer
    from interfaces.cli.v2 import register_vault_toggle
    app = typer.Typer()
    register_vault_toggle(app)
    cmd_names = [cmd.name for cmd in app.registered_commands]
    assert "vault-preview" in cmd_names
    assert "vault-apply" in cmd_names
    assert "vault-toggle" in cmd_names


# === Exception handling ===

def test_main_preview_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unexpected exception → exit 2."""
    plan = tmp_path / "plan.md"
    plan.write_text("- [ ] task one\n", encoding="utf-8")
    monkeypatch.setattr(atc, "_resolve_plan_path", lambda rp: plan)

    def _raise(*args, **kwargs):
        raise RuntimeError("disk error")
    monkeypatch.setattr(atc, "_preview", _raise)
    rc = atc.main("preview", rel_path="plan.md", line=1, expected="task one")
    assert rc == 2
    assert "disk error" in capsys.readouterr().err


# === Absolute path / parent traversal are tested at _resolve_plan_path level ===
# These confirm the guards exist and are called.
def test_main_rejects_absolute_path(capsys: pytest.CaptureFixture[str]) -> None:
    """Absolute path → exit 2 (caught by _resolve_plan_path)."""
    rc = atc.main("preview", rel_path=r"C:\Windows\System32\drivers\etc\hosts",
                  line=1, expected="x")
    assert rc == 2


def test_main_rejects_parent_traversal(capsys: pytest.CaptureFixture[str]) -> None:
    """Parent traversal → exit 2."""
    rc = atc.main("preview", rel_path="../secret.md", line=1, expected="x")
    assert rc == 2
