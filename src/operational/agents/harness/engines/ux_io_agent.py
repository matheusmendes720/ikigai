#!/usr/bin/env python
"""UX/IO Analyst — Agent node: maps CLI commands to expected IO patterns."""

import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]
_OUTPUT_COLS = 80  # Standard terminal width


def run_pav(args: str) -> tuple[int, str, str]:
    cmd = ["uv", "run", "--directory", str(_ROOT), "pav", *args.split()]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout or "", r.stderr or ""


def detect_truncation(output: str, cols: int = _OUTPUT_COLS) -> list[dict[str, Any]]:
    issues = []
    for i, line in enumerate(output.splitlines(), 1):
        if len(line) > cols:
            issues.append({"line": i, "length": len(line), "preview": line[:60]})
    return issues


def parse_json_output(stdout: str) -> dict[str, Any] | list | None:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def main() -> dict[str, Any]:
    results: dict[str, Any] = {
        "commands_tested": [],
        "io_patterns": {},
        "truncation_issues": [],
        "tty_bugs": [],
        "json_coverage": {},
        "command_count": 0,
    }

    commands = [
        "habit list --json",
        "routine list --json",
        "metric list --json",
        "policy decisions --json",
        "state show --json",
        "report daily --json",
        "report weekly --json",
        "demo show --json",
        "reflect list --json",
        "lunch list --json",
        "doctor --json",
        "home",
    ]

    for cmd in commands:
        results["command_count"] += 1
        results["commands_tested"].append(cmd)

        t0 = time.time()
        exit_code, stdout, stderr = run_pav(cmd)
        latency_ms = (time.time() - t0) * 1000

        parsed = parse_json_output(stdout)
        is_json = parsed is not None
        is_table = not is_json and bool(stdout.strip())

        # Detect truncation in non-JSON output
        truncations = detect_truncation(stdout) if is_table else []
        if truncations:
            results["truncation_issues"].append({"command": cmd, "lines": truncations})

        # TTY bug: JSON command producing table when should be JSON
        if "--json" in cmd and not is_json and exit_code == 0:
            results["tty_bugs"].append({
                "command": cmd,
                "expected": "JSON",
                "got": "table/rich",
                "preview": stdout[:100],
            })

        results["io_patterns"][cmd] = {
            "exit_code": exit_code,
            "latency_ms": round(latency_ms, 1),
            "output_type": "json" if is_json else ("table" if is_table else "empty"),
            "output_lines": len(stdout.splitlines()),
            "output_chars": len(stdout),
            "parsed_fields": list(parsed[0].keys()) if isinstance(parsed, list) and parsed else None,
        }

    # Load dataset CSV to get expected schema
    csv_path = _ROOT / "datasets" / "6month" / "synthetic_180d.csv"
    if csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            results["dataset_schema"] = {
                "columns": reader.fieldnames,
                "sample": next(reader, None),
            }

    results["commands_with_json"] = [c for c in results["commands_tested"] if "--json" in c]
    results["commands_without_json"] = [c for c in results["commands_tested"] if "--json" not in c]

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return results


if __name__ == "__main__":
    main()
