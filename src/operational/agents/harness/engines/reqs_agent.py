#!/usr/bin/env python
"""Functional Reqs Validator — Agent node: cross-checks SPEC.md vs actual CLI behavior."""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]
_SPEC_PATH = _ROOT.parent.parent.parent / "SPEC.md"


def run_pav(args: str) -> tuple[int, str, str]:
    cmd = ["uv", "run", "--directory", str(_ROOT), "pav", *args.split()]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout or "", r.stderr or ""


def parse_json(args: str) -> Any:
    _, stdout, _ = run_pav(args)
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def validate_ueid_format(id_str: str) -> bool:
    """Validate UEID format: ^[a-z]{3,5}_[a-z0-9_]+"""
    return bool(re.match(r"^[a-z]{3,5}_[a-z0-9_]+$", id_str))


def validate_enum_value(value: str, valid_values: list[str]) -> bool:
    return value in valid_values


def validate_habit_category(cat: str) -> bool:
    """HabitCategory values: COGNITIVE, PHYSIOLOGICAL, SOCIAL, CREATIVE, RITUAL (NOT MENTAL)."""
    valid = {"COGNITIVE", "PHYSIOLOGICAL", "SOCIAL", "CREATIVE", "RITUAL"}
    return cat.upper() in valid


def validate_routine_type(rtype: str) -> bool:
    """RoutineType values: ENTRY, CORE, TRANSITION, EXIT (NOT SHALLOW)."""
    valid = {"ENTRY", "CORE", "TRANSITION", "EXIT"}
    return rtype.upper() in valid


def validate_policy_state(state: str) -> bool:
    valid = {"PUSH", "MAINTAIN", "REDUCE", "RECOVER"}
    return state.upper() in valid


def check_qhe_formula(data: list[dict]) -> list[dict[str, Any]]:
    """Verify Q_HE values are in [0, 1]."""
    errors = []
    for item in (data if isinstance(data, list) else []):
        if isinstance(item, dict):
            for key in ("qhe", "qhe_score"):
                if key in item:
                    try:
                        val = float(item[key])
                        if not (0.0 <= val <= 1.0):
                            errors.append({
                                "type": "qhe_out_of_range",
                                "id": item.get("id", "unknown"),
                                "value": val,
                                "expected": "0.0 <= qhe <= 1.0",
                            })
                    except (ValueError, TypeError):
                        pass
    return errors


def main() -> dict[str, Any]:
    results: dict[str, Any] = {
        "spec_gaps": [],
        "algorithm_errors": [],
        "enum_errors": [],
        "ueid_errors": [],
        "passed_checks": [],
    }

    # 1. Read SPEC.md if present
    spec_content = ""
    if _SPEC_PATH.exists():
        spec_content = _SPEC_PATH.read_text(encoding="utf-8")

    # 2. Check habit list output
    habits_data = parse_json("habit list --json")
    if isinstance(habits_data, list):
        for habit in habits_data:
            if not isinstance(habit, dict):
                continue
            # UEID check
            hid = habit.get("id", "")
            if hid and not validate_ueid_format(hid):
                results["ueid_errors"].append({"id": hid, "type": "habit"})
            # Category enum
            cat = habit.get("category", "")
            if cat and not validate_habit_category(cat):
                results["enum_errors"].append({
                    "id": hid,
                    "field": "category",
                    "value": cat,
                    "expected": "COGNITIVE|PHYSIOLOGICAL|SOCIAL|CREATIVE|RITUAL",
                })
            # Name present
            if not habit.get("name"):
                results["spec_gaps"].append({"id": hid, "issue": "missing name field"})
        results["passed_checks"].append(f"habit_list: {len(habits_data)} habits validated")

    # 3. Check routine list output
    routines_data = parse_json("routine list --json")
    if isinstance(routines_data, list):
        for routine in routines_data:
            if not isinstance(routine, dict):
                continue
            rid = routine.get("id", "")
            if rid and not validate_ueid_format(rid):
                results["ueid_errors"].append({"id": rid, "type": "routine"})
            rtype = routine.get("routine_type", "")
            if rtype and not validate_routine_type(rtype):
                results["enum_errors"].append({
                    "id": rid,
                    "field": "routine_type",
                    "value": rtype,
                    "expected": "ENTRY|CORE|TRANSITION|EXIT",
                })
        results["passed_checks"].append(f"routine_list: {len(routines_data)} routines validated")

    # 4. Check policy decisions for state + severity
    policy_data = parse_json("policy decisions --json")
    if isinstance(policy_data, list):
        qhe_errors = check_qhe_formula(policy_data)
        results["algorithm_errors"].extend(qhe_errors)

        for decision in policy_data:
            if not isinstance(decision, dict):
                continue
            state = decision.get("state", "")
            if state and not validate_policy_state(state):
                results["enum_errors"].append({
                    "id": decision.get("id", "unknown"),
                    "field": "state",
                    "value": state,
                    "expected": "PUSH|MAINTAIN|REDUCE|RECOVER",
                })
            # severity should be str literal: INFO/WARNING/CRITICAL
            severity = decision.get("severity", "")
            if severity and severity not in ("INFO", "WARNING", "CRITICAL"):
                results["enum_errors"].append({
                    "id": decision.get("id", "unknown"),
                    "field": "severity",
                    "value": severity,
                    "expected": "INFO|WARNING|CRITICAL",
                })
        results["passed_checks"].append(f"policy_decisions: {len(policy_data)} decisions validated")

    # 5. Check daily report for H(t) / Q_HE fields
    report_data = parse_json("report daily --json")
    if isinstance(report_data, dict):
        if "qhe" in report_data or "qhe_score" in report_data:
            qhe_val = report_data.get("qhe") or report_data.get("qhe_score")
            if qhe_val is not None:
                try:
                    qhe = float(qhe_val)
                    if 0.0 <= qhe <= 1.0:
                        results["passed_checks"].append(f"daily_report: qhe={qhe:.3f} in [0,1]")
                    else:
                        results["algorithm_errors"].append({
                            "type": "qhe_out_of_range",
                            "value": qhe,
                            "expected": "0.0 <= qhe <= 1.0",
                        })
                except (ValueError, TypeError):
                    results["algorithm_errors"].append({"type": "qhe_not_numeric", "value": qhe_val})

    # 6. Check that report weekly uses correct date range
    weekly_data = parse_json("report weekly --json")
    if isinstance(weekly_data, dict):
        if "start" in weekly_data and "end" in weekly_data:
            results["passed_checks"].append("weekly_report: has start/end date range")
        else:
            results["spec_gaps"].append({"report": "weekly", "issue": "missing start/end fields"})

    # 7. Verify SPEC.md mentions key formulas
    spec_checks = [
        ("Q_HE", r"Q_HE\s*=\s*H\(t\)"),
        ("H(t)", r"H\(t\)\s*=\s*1\s*-\s*e\^\("),
        ("Policy FSM", r"PUSH.*MAINTAIN.*REDUCE.*RECOVER"),
        ("UEID", r"\^[a-z]\{3,5\}_"),
        ("HabitCategory.COGNITIVE", r"COGNITIVE"),
        ("RoutineType.CORE", r"CORE"),
    ]
    for label, pattern in spec_checks:
        if re.search(pattern, spec_content, re.IGNORECASE):
            results["passed_checks"].append(f"spec_doc: {label} documented")
        else:
            results["spec_gaps"].append(f"spec_doc: {label} NOT found in SPEC.md")

    results["summary"] = {
        "passed": len(results["passed_checks"]),
        "enum_errors": len(results["enum_errors"]),
        "ueid_errors": len(results["ueid_errors"]),
        "algorithm_errors": len(results["algorithm_errors"]),
        "spec_gaps": len(results["spec_gaps"]),
    }

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return results


if __name__ == "__main__":
    main()
