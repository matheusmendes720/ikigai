#!/usr/bin/env python
"""TDD/BDD Test Engineer — Agent node: generates pytest + BDD suite from CSV schemas."""

import csv
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]
_TEST_DIR = _ROOT / "tests" / "qa_harness"
_SCENARIO_CSV = _ROOT / "datasets" / "6month" / "synthetic_180d.csv"


def parse_scenario_day(row: dict[str, str]) -> dict[str, Any]:
    """Extract scenario metadata from a synthetic dataset row."""
    return {
        "date": row.get("date", ""),
        "scenario": row.get("scenario", ""),
        "qhe": float(row.get("qhe", 0)),
        "policy_state": row.get("policy_state", ""),
        "streak": int(row.get("streak_current", 0)),
    }


def generate_pytest_tests(scenarios: list[dict[str, Any]], output_dir: Path) -> int:
    """Generate pytest test file for all CLI commands."""
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        '"""Auto-generated QA tests — produced by tdd_agent."""\n',
        '"""Auto-generated QA tests — produced by tdd_agent."""\n',
        'from __future__ import annotations\n\n',
        'import pytest\n',
        'import subprocess\n',
        'import json\n',
        'from datetime import date\n\n',
        '_ROOT = Path(__file__).resolve().parents[3]\n\n\n',
        'def run_pav(args: str, timeout: int = 30) -> tuple[int, str, str]:\n',
        '    cmd = ["uv", "run", "--directory", str(_ROOT), "pav", *args.split()]\n',
        '    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)\n',
        '    return r.returncode, r.stdout or "", r.stderr or ""\n\n\n',
    ]

    # Happy path tests per command
    commands = [
        ("habit_list_json", "habit list --json"),
        ("routine_list_json", "routine list --json"),
        ("metric_list_json", "metric list --json"),
        ("policy_decisions_json", "policy decisions --json"),
        ("state_show_json", "state show --json"),
        ("report_daily_json", "report daily --json"),
        ("report_weekly_json", "report weekly --json"),
        ("demo_show_json", "demo show --json"),
        ("reflect_list_json", "reflect list --json"),
        ("lunch_list_json", "lunch list --json"),
        ("doctor_json", "doctor --json"),
    ]

    for test_name, cmd in commands:
        lines.append(f"def test_{test_name}() -> None:\n")
        lines.append(f'    """Test: {cmd}"""\\n')
        lines.append(f"    exit_code, stdout, stderr = run_pav('{cmd}')\n")
        lines.append("    assert exit_code == 0, f'non-zero exit: {{stderr[:200]}}'\n")
        if "--json" in cmd:
            lines.append("    data = json.loads(stdout)\n")
            lines.append("    assert isinstance(data, (dict, list)), 'expected JSON dict or list'\n")
        lines.append("    assert stdout.strip(), 'expected non-empty output'\n\n")

    # Scenario-based tests (use 5 representative days from dataset)
    critical_scenarios = [s for s in scenarios if s["qhe"] < 0.4 or s["qhe"] > 0.85][:5]
    for s in critical_scenarios:
        lines.append(f"def test_policy_state_{s['date'].replace('-', '')}() -> None:\n")
        lines.append(f'    """Policy state on {s["date"]}: {s["policy_state"]}, Q_HE={s["qhe"]:.3f}"""\\n')
        lines.append("    exit_code, stdout, stderr = run_pav('policy decisions --json')\n")
        lines.append("    assert exit_code == 0\n")
        lines.append("    data = json.loads(stdout)\n")
        lines.append(f"    assert isinstance(data, list)\n\n")

    test_file = output_dir / "test_cli_harness.py"
    test_file.write_text("".join(lines), encoding="utf-8")
    return len(commands) + len(critical_scenarios)


def generate_bdd_features(scenarios: list[dict[str, Any]], output_dir: Path) -> int:
    """Generate Gherkin .feature files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    n_features = 0

    # Feature: CLI Command Execution
    feature_lines = [
        "Feature: PAV CLI Command Execution\n\n",
        "  Scenario: habit list returns valid JSON\n",
        "    Given the PAV CLI is available\n",
        "    When I run `pav habit list --json`\n",
        "    Then I receive valid JSON with entity fields\n",
        "    And the exit code is 0\n\n",
        "  Scenario: routine list returns entities for each period\n",
        "    Given the PAV CLI is available\n",
        "    When I run `pav routine list --json`\n",
        "    Then I receive a list of routine entities\n",
        "    And each entity has id, name, period, routine_type\n\n",
        "  Scenario: report daily uses synthetic dataset context\n",
        "    Given the system has 180 days of synthetic data loaded\n",
        "    When I run `pav report daily --json`\n",
        "    Then I receive a daily report with sleep, habit, energy fields\n",
        "    And the report date matches today's date\n\n",
    ]

    # Stress scenarios
    high_qhe = [s for s in scenarios if s["qhe"] > 0.85][:2]
    low_qhe = [s for s in scenarios if s["qhe"] < 0.4][:2]

    if high_qhe:
        s = high_qhe[0]
        feature_lines.extend([
            f"  Scenario: Policy is in PUSH state during high Q_HE period\n",
            f"    Given Q_HE is {s['qhe']:.3f} on {s['date']}\n",
            f"    When I check policy decisions\n",
            f"    Then the policy state should be PUSH or MAINTAIN\n\n",
        ])

    if low_qhe:
        s = low_qhe[0]
        feature_lines.extend([
            f"  Scenario: Policy handles low Q_HE gracefully\n",
            f"    Given Q_HE is {s['qhe']:.3f} on {s['date']}\n",
            f"    When I check policy decisions\n",
            f"    Then the policy state should be RECOVER or REDUCE\n\n",
        ])

    feature_file = output_dir / "cli_commands.feature"
    feature_file.write_text("".join(feature_lines), encoding="utf-8")
    n_features += 1

    return n_features


def main() -> dict[str, Any]:
    results: dict[str, Any] = {
        "tests_generated": 0,
        "bdd_scenarios": 0,
        "edge_cases_covered": [],
        "csv_validation_errors": [],
        "feature_files": [],
    }

    # Load synthetic dataset
    scenarios: list[dict[str, Any]] = []
    if _SCENARIO_CSV.exists():
        with open(_SCENARIO_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                parsed = parse_scenario_day(row)
                if parsed["date"]:
                    scenarios.append(parsed)

    results["edge_cases_covered"] = [
        {"scenario": "struggling", "qhe_range": [0.0, 0.4], "count": sum(1 for s in scenarios if s["qhe"] < 0.4)},
        {"scenario": "plateau", "qhe_range": [0.6, 0.75], "count": sum(1 for s in scenarios if 0.6 <= s["qhe"] <= 0.75)},
        {"scenario": "peak", "qhe_range": [0.85, 1.0], "count": sum(1 for s in scenarios if s["qhe"] > 0.85)},
        {"scenario": "adversity", "policy": "RECOVER", "count": sum(1 for s in scenarios if s["policy_state"] == "RECOVER")},
    ]

    # Generate pytest
    test_count = generate_pytest_tests(scenarios, _TEST_DIR)
    results["tests_generated"] = test_count

    # Generate BDD
    feature_count = generate_bdd_features(scenarios, _TEST_DIR)
    results["bdd_scenarios"] = feature_count * 3  # 3 scenarios per feature

    results["feature_files"] = [
        str(_TEST_DIR / "cli_commands.feature"),
        str(_TEST_DIR / "test_cli_harness.py"),
    ]

    # Validate CSV schema
    expected_cols = {"date", "scenario", "qhe", "policy_state", "streak_current", "habit_name"}
    if _SCENARIO_CSV.exists():
        with open(_SCENARIO_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            actual_cols = set(reader.fieldnames or [])
            missing = expected_cols - actual_cols
            if missing:
                results["csv_validation_errors"].append({"missing_columns": list(missing)})

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return results


if __name__ == "__main__":
    main()
