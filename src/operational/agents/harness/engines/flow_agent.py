#!/usr/bin/env python
"""Flow Analyzer — Agent node: traces CLI call graph, finds dead ends and missing --json."""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]
_CLI_DIR = _ROOT / "apps" / "cli" / "src" / "operational" / "cli"


def run_pav(args: str) -> tuple[int, str, str]:
    cmd = ["uv", "run", "--directory", str(_ROOT), "pav", *args.split()]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout or "", r.stderr or ""


def scan_cli_app() -> dict[str, Any]:
    """Read app.py and extract all subcommand registrations."""
    app_py = _CLI_DIR / "app.py"
    if not app_py.exists():
        return {"error": f"app.py not found at {app_py}"}

    content = app_py.read_text(encoding="utf-8")

    # Find all add_typer / typer_command registrations
    commands: dict[str, dict[str, Any]] = {}
    subcommand_pattern = re.compile(r'(?:add_typer|app\.command)\s*\(\s*(\w+)[,\.]')
    json_pattern = re.compile(r'--json')

    for match in subcommand_pattern.finditer(content):
        cmd_name = match.group(1)
        commands[cmd_name] = {
            "registered": True,
            "has_json_flag": False,
            "module": None,
        }

    # Check which commands have --json in their help
    return {"commands": commands, "total_found": len(commands)}


def test_all_commands() -> dict[str, Any]:
    """Run every CLI command with --json and without, catalog results."""
    all_commands = [
        "habit", "routine", "block", "journal", "metric",
        "policy", "reflect", "report", "state", "demo",
        "doctor", "lunch", "home",
    ]

    subcommands: dict[str, list[str]] = {
        "habit": ["list", "create"],
        "routine": ["list", "create"],
        "block": ["list", "create"],
        "journal": ["list", "create"],
        "metric": ["list", "sleep", "energy"],
        "policy": ["setpoints", "decisions"],
        "reflect": ["list", "entrada", "saida"],
        "report": ["daily", "weekly"],
        "state": ["show"],
        "demo": ["show", "seed"],
        "lunch": ["list", "create"],
    }

    results: dict[str, Any] = {
        "with_json": {},
        "without_json": {},
        "errors": {},
        "dead_ends": [],
    }

    for cmd in all_commands:
        subs = subcommands.get(cmd, ["--help"])
        for sub in subs:
            full_cmd = f"{cmd} {sub} --json"
            exit_code, stdout, stderr = run_pav(full_cmd)
            is_json = stdout.strip().startswith(("[", "{"))

            results["with_json"][full_cmd] = {
                "exit": exit_code,
                "is_json": is_json,
                "lines": len(stdout.splitlines()),
            }

            if exit_code != 0:
                results["errors"][full_cmd] = stderr[:200]

            # Check without --json
            full_cmd_no_json = f"{cmd} {sub}"
            exit_code2, stdout2, _ = run_pav(full_cmd_no_json)
            has_table = bool(stdout2.strip()) and not stdout2.strip().startswith(("[", "{"))
            results["without_json"][full_cmd_no_json] = {
                "exit": exit_code2,
                "has_table": has_table,
                "lines": len(stdout2.splitlines()),
            }

            # Dead end: command succeeds but produces no useful output
            if exit_code == 0 and not stdout.strip() and not is_json:
                results["dead_ends"].append(full_cmd)

    return results


def main() -> dict[str, Any]:
    results: dict[str, Any] = {}

    # 1. Scan app.py for registered commands
    scan = scan_cli_app()
    results["registered_commands"] = scan

    # 2. Test all commands for JSON coverage
    flow = test_all_commands()
    results["flow_analysis"] = flow

    results["commands_with_json"] = [k for k, v in flow["with_json"].items() if v["is_json"]]
    results["commands_without_json"] = [k for k, v in flow["with_json"].items() if not v["is_json"]]
    results["dead_end_commands"] = flow["dead_ends"]
    results["error_commands"] = list(flow["errors"].keys())

    # Build call graph (simplified: command → output type)
    call_graph: dict[str, list[str]] = {}
    for cmd_full in results["commands_with_json"]:
        parts = cmd_full.split()
        parent = parts[0]
        child = "_".join(parts[:2]) if len(parts) > 1 else parent
        call_graph.setdefault(parent, []).append(child)
    results["call_graph"] = call_graph

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return results


if __name__ == "__main__":
    main()
