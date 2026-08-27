#!/usr/bin/env python
"""Interface Styler — Agent node: validates Rich table output, ANSI colors, TTY fallback."""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
ANSI_CODES = {
    "30": "black", "31": "red", "32": "green", "33": "yellow",
    "34": "blue", "35": "magenta", "36": "cyan", "37": "white",
}


def run_pav(args: str) -> tuple[int, str, str]:
    cmd = ["uv", "run", "--directory", str(_ROOT), "pav", *args.split()]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout or "", r.stderr or ""


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


def extract_ansi_codes(text: str) -> list[str]:
    return ANSI_ESCAPE.findall(text)


def detect_color_usage(output: str) -> dict[str, Any]:
    codes = extract_ansi_codes(output)
    stripped = strip_ansi(output)
    return {
        "has_colors": len(codes) > 0,
        "color_count": len(codes),
        "unique_codes": sorted(set(codes)),
        "has_256_colors": any("5;" in c for c in codes),
        "has_true_color": any("2;" in c for c in codes),
        "plain_length": len(stripped),
        "ansi_length": len(output),
    }


def detect_truncation(output: str, widths: list[int] | None = None) -> list[dict[str, Any]]:
    widths = widths or [80, 120, 200]
    issues = []
    for line in output.splitlines():
        plain = strip_ansi(line)
        for w in widths:
            if len(plain) > w:
                issues.append({
                    "width_violated": w,
                    "actual_length": len(plain),
                    "preview": plain[:60],
                })
                break
    return issues


def check_table_structure(output: str) -> dict[str, Any]:
    lines = output.splitlines()
    return {
        "line_count": len(lines),
        "has_separators": any(set(l).issubset({"─", "─", "|", "═", "+"}) for l in lines),
        "has_headers": any(l.strip().startswith(("id", "name", "date", "state")) for l in lines[:3]),
        "separator_chars": sum(1 for l in lines if l.strip() and set(l.strip()).issubset({"─", "═", "|"})),
    }


def check_tty_fallback(command_with_json: str, command_without_json: str) -> dict[str, Any]:
    """Check if --json flag properly switches from Rich table to JSON."""
    _, stdout_json, _ = run_pav(command_with_json)
    _, stdout_table, _ = run_pav(command_without_json)

    is_json = stdout_json.strip().startswith(("[", "{"))
    is_table = not is_json and bool(stdout_json.strip())

    color_json = detect_color_usage(stdout_json)
    color_table = detect_color_usage(stdout_table)

    return {
        "json_output_is_json": is_json,
        "json_output_has_colors": color_json["has_colors"],
        "table_output_is_table": is_table and not ANSI_ESCAPE.sub("", stdout_table).startswith(("[", "{")),
        "table_output_has_colors": color_table["has_colors"],
        "proper_transition": is_json and not color_json["has_colors"],
    }


def main() -> dict[str, Any]:
    results: dict[str, Any] = {
        "style_issues": [],
        "truncation_issues": [],
        "color_issues": [],
        "tty_fallback_broken": [],
        "commands_analyzed": 0,
    }

    table_commands = [
        "habit list",
        "routine list",
        "metric list",
        "policy setpoints",
        "state show",
        "doctor",
    ]

    for cmd in table_commands:
        results["commands_analyzed"] += 1

        # Analyze table output
        _, stdout, stderr = run_pav(cmd)
        if not stdout.strip():
            results["style_issues"].append({"command": cmd, "issue": "empty output"})
            continue

        color_info = detect_color_usage(stdout)
        table_info = check_table_structure(stdout)
        truncations = detect_truncation(stdout)

        if truncations:
            results["truncation_issues"].append({
                "command": cmd,
                "line_count": len(stdout.splitlines()),
                "violations": truncations[:3],
            })

        if not color_info["has_colors"]:
            results["color_issues"].append({
                "command": cmd,
                "issue": "no ANSI color codes found (table may be monochrome)",
                "output_preview": stdout[:100],
            })

        # Check TTY fallback: --json vs no --json
        json_cmd = cmd + " --json"
        fallback = check_tty_fallback(json_cmd, cmd)
        if not fallback["proper_transition"]:
            results["tty_fallback_broken"].append({
                "command": cmd,
                "json_is_json": fallback["json_output_is_json"],
                "json_has_colors": fallback["json_output_has_colors"],
                "table_is_table": fallback["table_output_is_table"],
            })

        results["style_issues"].append({
            "command": cmd,
            "colors": color_info,
            "table_structure": table_info,
            "truncations_found": len(truncations),
        })

    # Summary stats
    results["summary"] = {
        "total_commands": results["commands_analyzed"],
        "with_truncation": len(results["truncation_issues"]),
        "with_color_issues": len(results["color_issues"]),
        "fallback_broken": len(results["tty_fallback_broken"]),
    }

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return results


if __name__ == "__main__":
    main()
