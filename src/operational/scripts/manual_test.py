"""Comprehensive manual test script for operational CLI.

Exercises every CLI command, captures I/O to CSV, produces usability report.
Each command is run via subprocess the same way a human would from the terminal.

Usage:
    uv run python scripts/manual_test.py              # run tests
    uv run python scripts/manual_test.py --clear     # clear state first
    uv run python scripts/manual_test.py --seed      # seed demo data first (default: auto-seed if empty)
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from datetime import date, datetime, UTC
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "test_results"
STATE_DIR = Path.home() / ".time-tasker"

# ── Helpers ────────────────────────────────────────────────────────────────

def run_cmd(args: list[str], input_text: str = "") -> tuple[int, str, str]:
    """Run 'uv run --directory <root> pav [args]' via subprocess.

    Uses 'uv run' directly (not 'python -m uv run') so the subprocess
    inherits the system PATH and finds the uv binary correctly.
    """
    cmd = ["uv", "run", "--directory", str(ROOT), "pav", *args]
    r = subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
    )
    return r.returncode, r.stdout or "", r.stderr or ""


def clear_state() -> None:
    """Wipe all JSON state files so the system is clean."""
    for fpath in STATE_DIR.glob("*.json"):
        fpath.write_text("[]", encoding="utf-8")


def ensure_seed() -> None:
    """Seed demo data if the state directory is empty or all files are empty."""
    files = list(STATE_DIR.glob("*.json"))
    needs_seed = not files or all(
        fpath.read_text(encoding="utf-8").strip() in ("", "[]")
        for fpath in files
    )
    if needs_seed:
        print("  [seeding demo data …]")
        run_cmd(["demo", "seed"])
        time.sleep(0.5)


# ── CSV schema ─────────────────────────────────────────────────────────────

CSV_FIELDS = [
    "timestamp", "test_id", "category", "command", "subcommand",
    "args", "stdin_input", "exit_code",
    "stdout_preview", "stderr_preview",
    "expected_fields", "actual_fields",
    "pass_fail", "notes",
]

# ── Test cases ─────────────────────────────────────────────────────────────
# (test_id, category, args_list, stdin_text, expected_substring_in_output)

TESTS: list[tuple] = [
    # ── routine ─────────────────────────────────────────────────────────────
    (
        "routine_01", "routine",
        ["routine", "create", "Test Routine CLI", "MANHA", "CORE"],
        "",
        "Criando rotina",
    ),
    (
        "routine_02", "routine",
        ["routine", "list", "--json"],
        "",
        "id",
    ),
    (
        "routine_03", "routine",
        ["routine", "list", "--period", "MANHA", "--json"],
        "",
        "MANHA",
    ),

    # ── block ────────────────────────────────────────────────────────────────
    (
        "block_01", "block",
        ["block", "create", "TARDE", "--label", "Deep work block CLI"],
        "",
        "id",
    ),
    (
        "block_02", "block",
        ["block", "list", "--json"],
        "",
        "id",
    ),
    (
        "block_03", "block",
        ["block", "list", "--period", "TARDE", "--json"],
        "",
        "TARDE",
    ),

    # ── journal ─────────────────────────────────────────────────────────────
    (
        "journal_01", "journal",
        ["journal", "create", "--text", "Test journal entry via CLI script"],
        "",
        "Criando entrada",
    ),
    (
        "journal_02", "journal",
        ["journal", "list", "--json"],
        "",
        "id",
    ),

    # ── habit ──────────────────────────────────────────────────────────────
    (
        "habit_01", "habit",
        ["habit", "create", "Test Habit CLI", "physiological",
         "--resistance", "3", "--weight", "0.7"],
        "",
        "id",
    ),
    (
        "habit_02", "habit",
        ["habit", "list", "--json"],
        "",
        "id",
    ),
    (
        "habit_03", "habit",
        ["habit", "list", "--category", "physiological", "--json"],
        "",
        "physiological",
    ),

    # ── metric sleep ────────────────────────────────────────────────────────
    (
        "metric_sleep_01", "metric",
        ["metric", "sleep", "--quality", "8",
         "--bed-hour", "22", "--bed-minute", "30",
         "--wake-hour", "6", "--wake-minute", "30"],
        "",
        "id",
    ),
    (
        "metric_sleep_02", "metric",
        ["metric", "list", "--json"],
        "",
        "id",
    ),

    # ── metric energy ───────────────────────────────────────────────────────
    (
        "metric_energy_01", "metric",
        ["metric", "energy", "--energia", "7", "--foco", "8"],
        "",
        "id",
    ),

    # ── policy ──────────────────────────────────────────────────────────────
    (
        "policy_01", "policy",
        ["policy", "setpoints", "--json"],
        "",
        "id",
    ),
    (
        "policy_02", "policy",
        ["policy", "decisions", "--json"],
        "",
        "id",
    ),

    # ── demo ────────────────────────────────────────────────────────────────
    (
        "demo_01", "demo",
        ["demo", "show", "--json"],
        "",
        "Routines",
    ),
    (
        "demo_02", "demo",
        ["demo", "show"],
        "",
        "Entity",
    ),

    # ── state ───────────────────────────────────────────────────────────────
    (
        "state_01", "state",
        ["state", "show", "--json"],
        "",
        "date",
    ),

    # ── reflect entrada (interactive — piped stdin) ─────────────────────────
    (
        "reflect_entrada_01", "reflect",
        ["reflect", "entrada", "--date", date.today().isoformat(), "--json"],
        "parar test input\nrepetir test input\nsempre test input\nbig win test\n7",
        "id",
    ),

    # ── reflect saida (interactive — piped stdin) ──────────────────────────
    (
        "reflect_saida_01", "reflect",
        ["reflect", "saida", "--date", date.today().isoformat(), "--json"],
        "deu certo test\ndeu errado test\nmaior aprendizado test\najustes test\n6",
        "id",
    ),

    # ── reflect list ────────────────────────────────────────────────────────
    (
        "reflect_list_01", "reflect",
        ["reflect", "list", "--json"],
        "",
        "id",
    ),

    # ── report ───────────────────────────────────────────────────────────────
    (
        "report_01", "report",
        ["report", "daily", "--json"],
        "",
        "sleep_hours",
    ),
    (
        "report_02", "report",
        ["report", "weekly", "--json"],
        "",
        "start",
    ),

    # ── lunch ───────────────────────────────────────────────────────────────
    (
        "lunch_01", "lunch",
        ["lunch", "create", "--eat", "45", "--rest", "20",
         "--notas", "Test lunch via CLI script"],
        "",
        "LUNCH RECORD",
    ),
    (
        "lunch_02", "lunch",
        ["lunch", "list", "--json"],
        "",
        "id",
    ),

    # ── doctor ───────────────────────────────────────────────────────────────
    (
        "doctor_01", "doctor",
        ["doctor", "--json"],
        "",
        "checks",
    ),
    (
        "doctor_02", "doctor",
        ["doctor"],
        "",
        "python",
    ),

    # ── home ────────────────────────────────────────────────────────────────
    (
        "home_01", "home",
        ["home"],
        "q",
        "PAV-OS",
    ),
]

# ── Reporter ────────────────────────────────────────────────────────────────

def write_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)


def build_report(csv_path: Path, report_path: Path) -> None:
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    total = len(rows)
    passed = sum(1 for r in rows if r["pass_fail"] == "PASS")
    failed = [r for r in rows if r["pass_fail"] == "FAIL"]

    categories: dict[str, list] = {}
    for r in rows:
        categories.setdefault(r["category"], []).append(r)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# PAV Operational — Manual Test Report\n\n")
        f.write(f"**Generated:** {datetime.now(UTC).isoformat()}  \n")
        f.write(f"**Root:** `{ROOT}`  \n")
        f.write(f"**State:** `{STATE_DIR}`\n\n")

        f.write(f"## Summary\n\n")
        f.write(f"- **Total tests:** {total}\n")
        f.write(f"- **Passed:** {passed}  \n")
        f.write(f"- **Failed:** {len(failed)}  \n")
        f.write(f"- **Pass rate:** {100*passed/total:.0f}%\n\n")

        f.write("## Results by Category\n\n")
        f.write("| Category | Total | Passed | Failed | Rate |\n")
        f.write("|----------|-------|--------|--------|------|\n")
        for cat in sorted(categories):
            crows = categories[cat]
            p = sum(1 for r in crows if r["pass_fail"] == "PASS")
            f.write(f"| {cat} | {len(crows)} | {p} | {len(crows)-p} | {100*p/len(crows):.0f}% |\n")

        if failed:
            f.write("\n## Failed Tests\n\n")
            f.write("| # | Command | Exit | Notes |\n")
            f.write("|---|---------|------|-------|\n")
            for r in failed:
                args_short = r["args"].replace("\"", "")[:60]
                f.write(f"| {r['test_id']} | `pav {args_short}` | {r['exit_code']} | {r['notes'][:80]} |\n")

        f.write("\n## State Files After Tests\n\n")
        for fpath in sorted(STATE_DIR.glob("*.json")):
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                count = len(data) if isinstance(data, list) else 1
                f.write(f"- **{fpath.stem}**: {count} record(s)\n")
            except Exception as ex:
                f.write(f"- **{fpath.stem}**: ERROR — {ex}\n")

        f.write("\n## All Test Results\n\n")
        f.write("| # | Cat | Command | Exit | Pass? | Expected | Actual |\n")
        f.write("|---|-----|---------|------|--------|---------|--------|\n")
        for r in rows:
            args_short = r["args"].replace("\"", "")[:35]
            f.write(f"| {r['test_id']} | {r['category']} | "
                    f"`pav {args_short}` | {r['exit_code']} | {r['pass_fail']} | "
                    f"{r['expected_fields'][:25]} | {r['actual_fields'][:25]} |\n")

# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="PAV CLI comprehensive manual test")
    ap.add_argument("--clear", action="store_true", help="Clear state before testing")
    ap.add_argument("--seed", action="store_true", help="Force seed demo data before testing")
    args = ap.parse_args()

    RESULTS.mkdir(exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    csv_path = RESULTS / f"manual_test_{ts}.csv"
    report_path = RESULTS / f"usability_report_{ts}.md"

    print("=" * 60)
    print("PAV OPERATIONAL — Manual CLI Test")
    print("=" * 60)

    if args.clear:
        print("\n[1/3] Clearing state …")
        clear_state()

    print("\n[2/3] Ensuring demo seed …")
    ensure_seed()
    # Always seed if --seed flag, or if state is still empty
    if args.seed:
        print("  [re-seeding …]")
        clear_state()
        run_cmd(["demo", "seed"])
        time.sleep(0.5)

    print(f"\n[3/3] Running {len(TESTS)} test cases …\n")
    rows: list[dict] = []

    for i, (test_id, category, cmd_args, stdin, expected) in enumerate(TESTS, 1):
        subcommand = cmd_args[1] if len(cmd_args) > 1 else cmd_args[0]
        row: dict = {
            "timestamp": datetime.now(UTC).isoformat(),
            "test_id": test_id,
            "category": category,
            "command": cmd_args[0],
            "subcommand": subcommand,
            "args": " ".join(cmd_args),
            "stdin_input": stdin.replace("\n", "\\n")[:100],
            "exit_code": "",
            "stdout_preview": "",
            "stderr_preview": "",
            "expected_fields": expected,
            "actual_fields": "",
            "pass_fail": "",
            "notes": "",
        }
        label = f"[{i:02d}/{len(TESTS)}] {test_id}"
        try:
            code, stdout, stderr = run_cmd(cmd_args, input_text=stdin)
            row["exit_code"] = code
            row["stdout_preview"] = stdout[:400].replace("\n", "  ")[:400]
            row["stderr_preview"] = stderr[:200].replace("\n", "  ")[:200]

            # Try to parse stdout as JSON and extract field names
            try:
                data = json.loads(stdout)
                if isinstance(data, dict):
                    row["actual_fields"] = ",".join(list(data.keys())[:15])
                elif isinstance(data, list) and data:
                    row["actual_fields"] = ",".join(list(data[0].keys())[:10]) if isinstance(data[0], dict) else str(type(data[0]))
            except Exception:
                row["actual_fields"] = stdout[:80].replace("\n", " ").strip()[:80]

            # Pass = exit 0 AND expected string appears in stdout or stderr
            ok_text = expected in (stdout + stderr)
            ok_code = code == 0
            row["pass_fail"] = "PASS" if (ok_text and ok_code) else "FAIL"
            if not ok_code:
                row["notes"] = f"exit={code}"
            elif not ok_text:
                row["notes"] = f"'{expected}' not found in output"

            status = "✅" if row["pass_fail"] == "PASS" else "❌"
            print(f"  {label:35s} {status}  (exit={code})")

        except Exception as e:
            row["pass_fail"] = "ERROR"
            row["notes"] = str(e)[:100]
            print(f"  {label:35s} ⚠️  ERROR: {e}")

        rows.append(row)

    write_csv(rows, csv_path)
    build_report(csv_path, report_path)

    passed = sum(1 for r in rows if r["pass_fail"] == "PASS")
    failed = sum(1 for r in rows if r["pass_fail"] in ("FAIL", "ERROR"))
    print(f"\n{'='*60}")
    print(f"Done — {passed} passed, {failed} failed")
    print(f"  CSV:   {csv_path}")
    print(f"  Report: {report_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
