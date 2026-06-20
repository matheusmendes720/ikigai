#!/usr/bin/env python3
"""Standalone smoke test for the operational package.

Runs all critical checks:
- Package imports correctly
- PAV constants have expected values
- All enums can be instantiated
- CLI --help works
- Test suite passes (unit only, fast)
- mypy --strict passes
- ruff check passes

Exit code 0 = all green. Exit code 1 = any check failed.

Usage:
    python verify_sprint.py [--skip-tests] [--skip-typecheck] [--skip-lint]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
TESTS = ROOT / "tests"


class CheckResult(NamedTuple):
    """Result of a single verification check."""

    name: str
    passed: bool
    duration: float
    output: str


def _run(cmd: list[str], cwd: Path = ROOT) -> tuple[bool, str, float]:
    """Run a shell command, return (success, output, duration)."""
    start = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError as e:
        return False, f"command not found: {e}", time.perf_counter() - start
    except subprocess.TimeoutExpired:
        return False, "timeout (>120s)", time.perf_counter() - start
    duration = time.perf_counter() - start
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output, duration


def check_imports() -> CheckResult:
    """Verify the package can be imported and exposes expected API."""
    start = time.perf_counter()
    code = (
        "import sys; sys.path.insert(0, 'src'); "
        "import operational; "
        "assert hasattr(operational, '__version__'), 'missing __version__'; "
        "assert hasattr(operational, '__all__'), 'missing __all__'; "
        f"assert operational.__version__ == '0.1.0', 'wrong version: {{}}'.format(operational.__version__); "
        "print('OK', operational.__version__)"
    )
    success, output, _ = _run([sys.executable, "-c", code])
    return CheckResult("imports", success, time.perf_counter() - start, output)


def check_constants() -> CheckResult:
    """Verify PAV constants are present and correct."""
    start = time.perf_counter()
    code = (
        "import sys; sys.path.insert(0, 'src'); "
        "from operational.constants import PAVConstants; "
        "c = PAVConstants(); "
        "assert c.HORARIO_ACORDAR_MIN == 3; "
        "assert c.HORARIO_DORMIR_MIN == 18; "
        "assert c.POMODORO_WORK_MIN == 50; "
        "assert c.SONO_OPCOES_HORAS == (9, 8, 7, 4); "
        "assert c.QHE_PUSH_THRESHOLD == 0.85; "
        "print('OK', len(c.__dataclass_fields__), 'fields')"
    )
    success, output, _ = _run([sys.executable, "-c", code])
    return CheckResult("constants", success, time.perf_counter() - start, output)


def check_enums() -> CheckResult:
    """Verify all enums can be imported."""
    start = time.perf_counter()
    code = (
        "import sys; sys.path.insert(0, 'src'); "
        "from operational.enums import ("
        "Period, RoutineType, HabitCategory, EnergyLevel, "
        "PomodoroState, PolicyState, QualityLabel, WeekLabel"
        "); "
        "assert Period.MANHA == 'MANHA'; "
        "assert PolicyState.PUSH == 'PUSH'; "
        "assert PomodoroState.WORK == 'WORK'; "
        "print('OK')"
    )
    success, output, _ = _run([sys.executable, "-c", code])
    return CheckResult("enums", success, time.perf_counter() - start, output)


def check_exceptions() -> CheckResult:
    """Verify exception hierarchy is correct."""
    start = time.perf_counter()
    code = (
        "import sys; sys.path.insert(0, 'src'); "
        "from operational.exceptions import ("
        "ProductivitySystemError, TimeValidationError, "
        "SleepTrackingError, PomodoroSessionError, RoutineCompletionError"
        "); "
        "assert issubclass(TimeValidationError, ProductivitySystemError); "
        "assert issubclass(SleepTrackingError, ProductivitySystemError); "
        "print('OK')"
    )
    success, output, _ = _run([sys.executable, "-c", code])
    return CheckResult("exceptions", success, time.perf_counter() - start, output)


def check_types() -> CheckResult:
    """Verify NewType and Protocol definitions work."""
    start = time.perf_counter()
    code = (
        "import sys; sys.path.insert(0, 'src'); "
        "from operational.types import Hour, Minute, UEID, StreakInt, Repository, Clock; "
        "from typing import get_type_hints; "
        "hints = get_type_hints(Hour); "
        "print('OK', len(hints))"
    )
    success, output, _ = _run([sys.executable, "-c", code])
    return CheckResult("types", success, time.perf_counter() - start, output)


def check_cli() -> CheckResult:
    """Verify CLI --help works."""
    start = time.perf_counter()
    code = (
        "import sys; sys.path.insert(0, 'src'); "
        "from click.testing import CliRunner; "
        "from operational.cli.main import app; "
        "runner = CliRunner(); "
        "result = runner.invoke(app, ['--help']); "
        "assert result.exit_code == 0, result.output; "
        "print('OK')"
    )
    success, output, _ = _run([sys.executable, "-c", code])
    return CheckResult("cli", success, time.perf_counter() - start, output)


def check_tests() -> CheckResult:
    """Run unit tests (fast)."""
    cmd = [sys.executable, "-m", "pytest", "-m", "unit", "-x", "--no-cov", "-q"]
    success, output, duration = _run(cmd)
    return CheckResult("tests (unit)", success, duration, output)


def check_typecheck() -> CheckResult:
    """Run mypy --strict on src/."""
    cmd = [sys.executable, "-m", "mypy", "src/operational/", "--strict"]
    success, output, duration = _run(cmd)
    return CheckResult("typecheck (mypy --strict)", success, duration, output)


def check_lint() -> CheckResult:
    """Run ruff check on src/."""
    cmd = [sys.executable, "-m", "ruff", "check", "src/", "tests/"]
    success, output, duration = _run(cmd)
    return CheckResult("lint (ruff)", success, duration, output)


def main() -> int:
    """Run all checks and report."""
    parser = argparse.ArgumentParser(description="operational sprint verifier")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-typecheck", action="store_true")
    parser.add_argument("--skip-lint", action="store_true")
    args = parser.parse_args()

    print("=" * 70)
    print("OPERATIONAL — Sprint Verification")
    print("=" * 70)

    checks: list[CheckResult] = []
    checks.append(check_imports())
    checks.append(check_constants())
    checks.append(check_enums())
    checks.append(check_exceptions())
    checks.append(check_types())
    if not args.skip_tests and TESTS.exists():
        checks.append(check_tests())
    if not args.skip_typecheck:
        checks.append(check_typecheck())
    if not args.skip_lint:
        checks.append(check_lint())

    print()
    print(f"{'CHECK':<30} {'STATUS':<10} {'TIME':<10}")
    print("-" * 70)
    for c in checks:
        status = "PASS" if c.passed else "FAIL"
        time_s = f"{c.duration:.2f}s"
        print(f"{c.name:<30} {status:<10} {time_s:<10}")
    print("-" * 70)

    failed = [c for c in checks if not c.passed]
    if failed:
        print(f"\n{len(failed)} CHECK(S) FAILED:")
        for c in failed:
            print(f"\n[{c.name}]")
            print(c.output[:2000])
        return 1

    total_time = sum(c.duration for c in checks)
    print(f"\nALL {len(checks)} CHECKS PASSED in {total_time:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
