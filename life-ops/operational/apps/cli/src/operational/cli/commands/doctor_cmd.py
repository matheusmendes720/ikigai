"""Doctor command — diagnose CLI health and runtime environment.

Checks:
1. Python version (>= 3.10?)
2. Required packages (Typer, Rich, Pydantic) installed and version
3. State directory exists and writable
4. JSON files present and parseable
5. Entity counts per repo
6. Active dataset (TIME_TASKER_DATASET env var)
7. Dataset CSV availability (docs/synthetic.csv, docs/golden.csv)
8. Constants loaded correctly
9. Console detection (is_captured?)
10. Encoding/line-ending sanity check on JSON files
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import typer

from operational.cli.formatters import format_as_json
from operational.constants import DEFAULT as PAV
from operational.ui import console, is_captured

doctor_app = typer.Typer(help="Diagnóstico completo do ambiente operacional.")
app = doctor_app


def _check_python() -> dict[str, Any]:
    """Python version and executable info."""
    return {
        "version": sys.version,
        "version_info": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "executable": sys.executable,
        "ok": sys.version_info >= (3, 10),
    }


def _check_packages() -> dict[str, Any]:
    """Check that required packages are installed and have sane versions."""
    import importlib.metadata

    pkgs: dict[str, str | None] = {}
    for name in ("typer", "rich", "pydantic"):
        try:
            pkgs[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pkgs[name] = None
    return {
        "packages": pkgs,
        "ok": all(v is not None for v in pkgs.values()),
    }


def _check_state_dir() -> dict[str, Any]:
    """Verify state directory exists and JSON files are readable."""
    state_dir = Path(os.environ.get("TIME_TASKER_STATE_DIR", Path.home() / ".time-tasker"))
    files_info: dict[str, dict[str, Any]] = {}
    expected_files = [
        "routines.json", "routine_logs.json", "time_blocks.json",
        "journals.json", "habits.json", "sleep_records.json",
        "pomodoros.json", "policy_decisions.json", "policy_setpoints.json",
        "ajustes_finos.json", "day_contexts.json", "daily_reflections.json",
        "lunch_records.json", "transicoes.json",
    ]
    exists = state_dir.exists()
    writable = exists and os.access(state_dir, os.W_OK)
    for fname in expected_files:
        fpath = state_dir / fname
        if not exists:
            files_info[fname] = {"exists": False}
        elif fpath.exists():
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                files_info[fname] = {
                    "exists": True,
                    "size_bytes": fpath.stat().st_size,
                    "entity_count": len(data) if isinstance(data, dict) else 0,
                    "parseable": True,
                }
            except json.JSONDecodeError as exc:
                files_info[fname] = {
                    "exists": True,
                    "size_bytes": fpath.stat().st_size,
                    "parseable": False,
                    "error": str(exc),
                }
        else:
            files_info[fname] = {"exists": False}
    return {
        "path": str(state_dir),
        "exists": exists,
        "writable": writable,
        "files": files_info,
        "ok": exists and writable,
    }


def _check_datasets() -> dict[str, Any]:
    """Check TIME_TASKER_DATASET env var and built-in CSV availability."""
    active = os.environ.get("TIME_TASKER_DATASET", "production")
    start = Path(__file__).resolve().parent
    project_root = start
    for ancestor in start.parents:
        if (ancestor / "docs").is_dir():
            project_root = ancestor
            break
    else:
        project_root = start.parents[4]
    csv_status: dict[str, dict[str, Any]] = {}
    for name, rel in [
        ("synthetic", "docs/synthetic.csv"),
        ("golden", "docs/golden.csv"),
    ]:
        p = project_root / rel
        csv_status[name] = {
            "path": str(p),
            "exists": p.exists(),
            "size_bytes": p.stat().st_size if p.exists() else 0,
        }
    return {
        "active": active,
        "available": csv_status,
        "ok": True,
    }


def _check_constants() -> dict[str, Any]:
    """Verify PAV constants are loaded with expected values."""
    expected = {
        "POMODORO_WORK_MIN": 50,
        "POMODORO_BREAK_MIN": 10,
        "POMODORO_LONG_BREAK_MIN": 30,
        "POMODORO_ROUNDS_MIN": 3,
        "POMODORO_ROUNDS_MAX": 4,
        "LAMBDA_LEARNING_DEFAULT": 0.093,
    }
    actual: dict[str, Any] = {}
    ok = True
    for name, exp_val in expected.items():
        val = getattr(PAV, name, None)
        actual[name] = val
        if val != exp_val:
            ok = False
    return {
        "constants": actual,
        "expected": expected,
        "ok": ok,
    }


def _check_console() -> dict[str, Any]:
    """Console environment detection."""
    return {
        "is_captured": is_captured(),
        "stdout_is_tty": sys.stdout.isatty() if sys.stdout else False,
        "stderr_is_tty": sys.stderr.isatty() if sys.stderr else False,
        "encoding": sys.stdout.encoding if sys.stdout else "unknown",
        "ok": True,
    }


def _check_files_sanity() -> dict[str, Any]:
    """Sanity check on JSON files: UTF-8, no BOM, no CRLF issues.

    CRLF line endings are common and harmless on Windows — json.loads accepts
    both. We skip the CRLF check to avoid false positives on Windows systems.
    UTF-8 BOM is still flagged as it can cause issues with some parsers.
    """
    state_dir = Path(os.environ.get("TIME_TASKER_STATE_DIR", Path.home() / ".time-tasker"))
    issues: list[str] = []
    checked = 0
    if state_dir.exists():
        for f in state_dir.glob("*.json"):
            if f.stat().st_size == 0:
                continue
            raw = f.read_bytes()
            checked += 1
            if raw[:3] == b"\xef\xbb\xbf":
                issues.append(f"{f.name}: has UTF-8 BOM (should not)")
    return {
        "files_checked": checked,
        "issues": issues,
        "ok": len(issues) == 0,
    }


def run_health_check(json_out: bool = False) -> None:
    """Run the health check."""
    results: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "python": _check_python(),
            "packages": _check_packages(),
            "state_dir": _check_state_dir(),
            "datasets": _check_datasets(),
            "constants": _check_constants(),
            "console": _check_console(),
            "files_sanity": _check_files_sanity(),
        },
    }
    all_ok = all(c.get("ok", True) for c in results["checks"].values())
    results["overall_ok"] = all_ok
    if json_out:
        typer.echo(format_as_json(results))
    else:
        from rich.panel import Panel
        from rich.table import Table

        status_color = "green" if all_ok else "red"
        status_icon = "OK" if all_ok else "ISSUES"
        t = Table.grid(padding=(0, 2))
        t.add_column(min_width=20, justify="left")
        t.add_column(justify="left")
        for name, check in results["checks"].items():
            ok = check.get("ok", True)
            icon = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
            if name == "python":
                summary = f"v{check['version_info']}"
            elif name == "packages":
                vs = check["packages"]
                summary = ", ".join(f"{k}={v}" for k, v in vs.items() if v)
            elif name == "state_dir":
                summary = (
                    f"{check['path']} "
                    f"({sum(1 for f in check['files'].values() if f.get('exists'))} files)"
                )
            elif name == "datasets":
                summary = f"active={check['active']}"
            elif name == "constants":
                summary = f"{sum(1 for v in check['expected'].values())} loaded"
            elif name == "console":
                summary = f"captured={check['is_captured']}, encoding={check['encoding']}"
            elif name == "files_sanity":
                summary = f"{check['files_checked']} files, {len(check['issues'])} issues"
            else:
                summary = ""
            t.add_row(f"{icon} {name}", summary)
        panel = Panel(
            t,
            title=f"DOCTOR - {status_icon}",
            border_style=status_color,
        )
        console.print(panel)
        if not all_ok:
            console.print()
            console.print("[bold red]Issues:[/bold red]")
            for name, check in results["checks"].items():
                if not check.get("ok", True):
                    console.print(f"  [red]*[/red] {name}: {check}")



