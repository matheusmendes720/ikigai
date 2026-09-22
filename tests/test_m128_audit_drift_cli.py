"""M128 tests — audit_drift_cli.py (vault_diff CLI wrapper).

Verifies the CLI wrapper around vault_propagation.audit_drift().
Tests use mocked audit_drift output so they're hermetic.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.vault import audit_drift_cli as adc  # noqa: E402


@pytest.fixture
def mock_drift_data() -> dict[str, object]:
    """Synthetic audit_drift output for tests."""
    return {
        "summary": {
            "unmarked_done": 2,
            "phantom_task": 3,
            "planned_orphan": 5,
        },
        "drifts": [
            {
                "drift_kind": "unmarked_done",
                "plan_file": "vault/plan.md",
                "plan_line": 10,
                "plan_text": "Task A",
                "taskdog_id": 100,
                "taskdog_status": "completed",
                "taskdog_name": "Task A [vault:plan.md#10]",
            },
            {
                "drift_kind": "unmarked_done",
                "plan_file": "vault/plan.md",
                "plan_line": 11,
                "plan_text": "Task B",
                "taskdog_id": 101,
                "taskdog_status": "completed",
                "taskdog_name": "Task B [vault:plan.md#11]",
            },
            {
                "drift_kind": "phantom_task",
                "plan_file": None,
                "plan_line": None,
                "plan_text": None,
                "taskdog_id": 200,
                "taskdog_status": "pending",
                "taskdog_name": "Orphan task",
            },
            {
                "drift_kind": "planned_orphan",
                "plan_file": "vault/orphan.md",
                "plan_line": 5,
                "plan_text": "Orphan checkbox",
                "taskdog_id": None,
                "taskdog_status": None,
                "taskdog_name": None,
            },
        ] * 3,  # 12 drifts total (2*unmarked_done + 3*phantom + 5*planned_orphan)
    }


@pytest.fixture
def patched_audit_drift(
    monkeypatch: pytest.MonkeyPatch, mock_drift_data: dict[str, object]
) -> None:
    """Replace audit_drift() with a function returning our mock data."""
    monkeypatch.setattr(adc, "_audit_drift", lambda: mock_drift_data)


# === _format_summary ===

def test_format_summary_no_drift() -> None:
    """Empty drift dict produces a friendly 'no drift' message."""
    out = adc._format_summary({"summary": {}, "drifts": []})
    assert "no drift detected" in out.lower()


def test_format_summary_with_drift(mock_drift_data: dict[str, object]) -> None:
    """Drift dict → human-readable summary table."""
    out = adc._format_summary(mock_drift_data)
    assert "Vault" in out
    assert "unmarked_done" in out
    assert "phantom_task" in out
    assert "planned_orphan" in out
    assert "Total drifts: 12" in out


# === _format_kind_table ===

def test_format_kind_table_no_match(mock_drift_data: dict[str, object]) -> None:
    """Asking for a kind not in the data → friendly 'no drifts' message."""
    out = adc._format_kind_table(mock_drift_data["drifts"], "nonexistent_kind")  # type: ignore[arg-type]
    assert "no drifts" in out.lower()


def test_format_kind_table_caps_at_20(mock_drift_data: dict[str, object]) -> None:
    """Tables truncate at 20 entries + show '... and N more'."""
    big_drifts = [{"drift_kind": "phantom_task", "plan_file": f"f{i}.md", "plan_line": i,
                   "plan_text": f"text {i}", "taskdog_id": i, "taskdog_status": "pending",
                   "taskdog_name": f"task {i}"} for i in range(25)]
    out = adc._format_kind_table(big_drifts, "phantom_task")  # type: ignore[arg-type]
    assert "and 5 more" in out


# === main ===

def test_main_human_output(patched_audit_drift: None, capsys: pytest.CaptureFixture[str]) -> None:
    """Default → human-readable output."""
    rc = adc.main()
    assert rc == 0
    captured = capsys.readouterr()
    assert "Drifts by kind:" in captured.out
    assert "planned_orphan" in captured.out


def test_main_json_output(patched_audit_drift: None, capsys: pytest.CaptureFixture[str]) -> None:
    """--json emits valid JSON."""
    rc = adc.main(json_output=True)
    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert "drifts" in parsed
    assert "summary" in parsed
    assert len(parsed["drifts"]) == 12


def test_main_kind_filter(
    patched_audit_drift: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """--kind-filter shows only drifts of that kind."""
    rc = adc.main(kind_filter="planned_orphan")
    assert rc == 0
    captured = capsys.readouterr()
    assert "planned_orphan" in captured.out
    # Should not show other kinds in summary mode.
    assert "Drifts of kind" in captured.out


def test_main_kind_filter_json(
    patched_audit_drift: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """--json + --kind-filter returns filtered JSON."""
    rc = adc.main(json_output=True, kind_filter="phantom_task")
    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    for d in parsed["drifts"]:
        assert d["drift_kind"] == "phantom_task"


def test_main_exit_on_drift_no_drift(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--exit-on-drift with no drift → exit 0."""
    monkeypatch.setattr(adc, "_audit_drift", lambda: {"summary": {}, "drifts": []})
    rc = adc.main(exit_on_drift=True)
    assert rc == 0


def test_main_exit_on_drift_with_drift(
    patched_audit_drift: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """--exit-on-drift with drift → exit 1 (CI-friendly)."""
    rc = adc.main(exit_on_drift=True)
    assert rc == 1


def test_main_audit_drift_raises(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """audit_drift() raises → exit 2 (different from exit-on-drift)."""
    def _raise() -> dict[str, object]:
        raise RuntimeError("vault missing")
    monkeypatch.setattr(adc, "_audit_drift", _raise)
    rc = adc.main()
    assert rc == 2
    captured = capsys.readouterr()
    assert "ERROR" in captured.err
    assert "vault missing" in captured.err


def test_main_audit_drift_raises_with_exit_on(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--exit-on-drift + error → exit 2 (not 1)."""
    def _raise() -> dict[str, object]:
        raise RuntimeError("boom")
    monkeypatch.setattr(adc, "_audit_drift", _raise)
    rc = adc.main(exit_on_drift=True)
    assert rc == 2


# === CLI integration ===

def test_audit_drift_register_function_exists() -> None:
    """The Typer registration function exists and is callable."""
    from interfaces.cli.v2 import register_audit_drift
    assert callable(register_audit_drift)


def test_audit_drift_register_wires_to_typer_app() -> None:
    """register_audit_drift wires a Typer command named 'audit-drift'."""
    import typer
    from interfaces.cli.v2 import register_audit_drift
    app = typer.Typer()
    register_audit_drift(app)
    # Typer stores commands in app.registered_commands
    cmd_names = [cmd.name for cmd in app.registered_commands]
    assert "audit-drift" in cmd_names
