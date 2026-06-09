"""E2E: CLI end-to-end workflow — create, list, report across domains."""
from __future__ import annotations

from typer.testing import CliRunner

from operational.cli import app

runner = CliRunner()


def test_full_daily_workflow() -> None:
    """Simulate a complete daily session via CLI."""
    # 1. Record sleep
    r1 = runner.invoke(app, ["metric", "sleep", "--quality", "9", "--bed-hour", "22", "--wake-hour", "6"])
    assert r1.exit_code == 0
    assert ("SLEEP RECORD" in r1.stdout) or ("Sleep logged" in r1.stdout)

    # 2. Create routines
    r2 = runner.invoke(app, ["routine", "create", "Morning routine", "MANHA", "ENTRY", "--start-hour", "4", "--end-hour", "5"])
    assert r2.exit_code == 0
    assert ("NOVA ROTINA" in r2.stdout) or ("Rotina" in r2.stdout)

    r3 = runner.invoke(app, ["routine", "create", "Deep work", "TARDE", "CORE", "--start-hour", "8", "--end-hour", "12"])
    assert r3.exit_code == 0

    # 3. Create a time block
    r4 = runner.invoke(app, ["block", "create", "MANHA", "--label", "Running"])
    assert r4.exit_code == 0
    assert ("✓" in r4.stdout) or ("Created time block" in r4.stdout)

    # 4. Create journal entry
    r5 = runner.invoke(app, ["journal", "create", "--text", "Great day of focused work."])
    assert r5.exit_code == 0
    assert ("✓" in r5.stdout) or ("Created journal entry" in r5.stdout)

    # 5. Create habit
    r6 = runner.invoke(app, ["habit", "create", "Drink water", "physiological", "--resistance", "2"])
    assert r6.exit_code == 0
    assert ("✓" in r6.stdout) or ("Created habit" in r6.stdout)

    # 6. Generate daily report
    r7 = runner.invoke(app, ["report", "daily"])
    assert r7.exit_code == 0
    # Rich-rendered (EASE/HARDWORK/Cartesiano) or markdown fallback
    assert any(s in r7.stdout for s in ("EASE", "Daily V3", "Daily Summary", "HARDWORK"))


def test_json_workflow() -> None:
    """All commands support --json flag."""
    r = runner.invoke(app, ["routine", "create", "JSON Test", "MANHA", "CORE", "--json"])
    assert r.exit_code == 0
    assert '"id"' in r.stdout

    r = runner.invoke(app, ["block", "create", "TARDE", "--json"])
    assert r.exit_code == 0
    assert '"id"' in r.stdout


def test_help_all_groups() -> None:
    """Every command group responds to --help."""
    for group in ["routine", "block", "journal", "habit", "metric", "policy", "report"]:
        r = runner.invoke(app, [group, "--help"])
        assert r.exit_code == 0, f"{group} --help failed"
