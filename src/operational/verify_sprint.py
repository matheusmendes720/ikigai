#!/usr/bin/env python3
"""Standalone smoke test for the operational uv workspace.

Runs all critical checks against the actual workspace layout
(``packages/core/src/operational/`` + ``apps/cli/`` + ``apps/tui/``):

- Package imports correctly + exposes ``__version__`` / ``__all__``
- PAV constants have expected values
- All enums can be instantiated
- Exception hierarchy is correct
- NewType / Protocol definitions load
- CLI ``pav --help`` works (via the installed entry point)
- Unit test suite passes
- ruff check passes (skipped gracefully if ruff missing)
- ruff format --check passes (skipped gracefully if ruff missing)

Namespace shadowing note
------------------------
``apps/cli/src/operational/__init__.py`` installs a namespace stub that
shadows the canonical ``packages/core/src/operational/__init__.py`` in
editable installs — whichever package claims the namespace first wins.
Every subprocess check is therefore run with ``PYTHONPATH`` prepended
by ``packages/core/src`` so the canonical core package always wins.

mypy is intentionally not gated here — the repo has no ``mypy.ini`` /
``[tool.mypy]`` block yet, so the gate would be misleading (it would
only fail on the missing-config error, not on real type errors). When
mypy config lands, gate it back in.

Exit code 0 = all green (including graceful SKIPs). Exit code 1 = any
non-skipped check failed.

Usage:
    python verify_sprint.py [--skip-tests] [--skip-lint] [--skip-format]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent
TESTS = ROOT / "tests"
CORE_INIT = ROOT / "packages" / "core" / "src" / "operational" / "__init__.py"


def _core_pythonpath() -> str:
    """Return PYTHONPATH that points at ``packages/core/src`` first.

    The CLI app installs an ``operational`` namespace stub at
    ``apps/cli/src/operational/__init__.py`` that shadows the canonical
    core package — ``import operational`` from a normal venv resolves to
    the CLI stub and loses the core ``__all__``. Prepending the core
    source dir forces the canonical package to win without changing
    sys.path globally.
    """
    core_src = str(ROOT / "packages" / "core" / "src")
    existing = os.environ.get("PYTHONPATH", "")
    return f"{core_src}{os.pathsep}{existing}" if existing else core_src


class CheckResult(NamedTuple):
    """Result of a single verification check."""

    name: str
    passed: bool
    duration: float
    output: str


def _run(
    cmd: list[str],
    *,
    cwd: Path = ROOT,
    timeout: int = 300,
    env_extra: dict[str, str] | None = None,
) -> tuple[bool, str, float]:
    """Run a shell command, return (success, output, duration).

    Args:
        cmd: argv list.
        cwd: working directory.
        timeout: subprocess timeout in seconds.
        env_extra: extra env vars merged on top of ``os.environ`` (PYTHONPATH
            is prepended with the core source dir by default; pass
            ``env_extra={"PYTHONPATH": ""}`` to disable).
    """
    start = time.perf_counter()
    env = os.environ.copy()
    env["PYTHONPATH"] = _core_pythonpath()
    if env_extra:
        env.update(env_extra)
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except FileNotFoundError as e:
        return False, f"command not found: {e}", time.perf_counter() - start
    except subprocess.TimeoutExpired:
        return False, f"timeout (>{timeout}s)", time.perf_counter() - start
    duration = time.perf_counter() - start
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output, duration


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_imports() -> CheckResult:
    """Verify the package can be imported and exposes ``__version__`` + ``__all__``."""
    start = time.perf_counter()
    code = (
        "import operational; "
        "assert hasattr(operational, '__version__'), 'missing __version__'; "
        "assert hasattr(operational, '__all__'), 'missing __all__'; "
        "assert operational.__version__ == '0.1.0', 'wrong version'; "
        "print('OK', operational.__version__, 'exports:', len(operational.__all__))"
    )
    success, output, _ = _run([sys.executable, "-c", code])
    return CheckResult("imports", success, time.perf_counter() - start, output)


def check_constants() -> CheckResult:
    """Verify PAV constants are present and correct."""
    start = time.perf_counter()
    code = (
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
    """Verify TypeAlias and Protocol definitions work.

    ``Hour``/``Minute``/``UEID``/``StreakInt``/``Score`` are
    :data:`typing.Annotated` aliases of a primitive type + a Pydantic
    :class:`Field` (see ``packages/core/src/operational/types.py``).
    At runtime, ``typing.get_origin(Hour)`` returns ``typing.Annotated``
    (the form), and ``typing.get_args(Hour)[0]`` returns the inner
    primitive (``int``). ``Repository`` / ``Clock`` / ``Logger`` are
    :func:`typing.runtime_checkable` Protocols — ``get_origin`` on a
    non-parameterized class returns ``None``.
    """
    start = time.perf_counter()
    code = (
        "from typing import get_origin, get_args; "
        "from operational.types import Hour, Minute, UEID, StreakInt, Repository, Clock; "
        # Annotated TypeAliases — first arg of get_args is the inner primitive.
        "h = get_args(Hour)[0]; "
        "assert h is int, f'Hour inner={h}'; "
        "m = get_args(Minute)[0]; "
        "assert m is int, f'Minute inner={m}'; "
        "u = get_args(UEID)[0]; "
        "assert u is str, f'UEID inner={u}'; "
        "s = get_args(StreakInt)[0]; "
        "assert s is int, f'StreakInt inner={s}'; "
        # Protocol / runtime classes — get_origin returns None (not generic at use-site).
        "assert get_origin(Repository) is None, f'Repository origin={get_origin(Repository)}'; "
        "assert get_origin(Clock) is None; "
        # Sanity: get_origin for an Annotated alias is typing.Annotated itself.
        "assert get_origin(Hour) is not None; "
        "print('OK')"
    )
    success, output, _ = _run([sys.executable, "-c", code])
    return CheckResult("types", success, time.perf_counter() - start, output)


def check_cli_help() -> CheckResult:
    """Verify the Typer CLI is invokable and its ``--help`` flag works.

    Spawns ``python -m operational.cli.app --help`` as a subprocess so the
    check is independent of whether ``click`` is importable in the active
    venv (typer 0.26 bundles click internally as ``typer._click`` and the
    external ``click`` package may not be installed). The ``PYTHONPATH``
    prepend (set by :func:`_run` via :func:`_core_pythonpath`) ensures the
    canonical ``packages/core/src/operational/__init__.py`` wins, and the
    .pth-installed editable hooks make ``operational.cli`` resolvable.
    """
    start = time.perf_counter()
    success, output, _ = _run([sys.executable, "-m", "operational.cli.app", "--help"])
    return CheckResult("cli (--help)", success, time.perf_counter() - start, output)


def check_unit_tests() -> CheckResult:
    """Run fast unit tests (scoped to ``tests/unit/``).

    The project does **not** use ``@pytest.mark.unit`` decorators — tests
    are directory-scoped (``tests/unit/`` for fast/no-I/O,
    ``tests/integration/`` for storage pipelines, etc.). The historical
    ``pytest -m unit`` invocation in this script deselected every test
    because no marker was registered on any test file.
    """
    unit_dir = ROOT / "tests" / "unit"
    if not unit_dir.exists():
        return CheckResult(
            "tests (unit)",
            True,
            0.0,
            "SKIP — tests/unit/ not present in this checkout",
        )
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(unit_dir),
        "-x",
        "--no-cov",
        "-q",
        "--tb=short",
    ]
    success, output, duration = _run(cmd, timeout=600)
    return CheckResult("tests (unit)", success, duration, output)


def check_lint() -> CheckResult:
    """Run ``ruff check`` on the canonical core package.

    Scope is :data:`packages/core/src` — the PAV kernel's pure-logic layer.
    Pre-existing lint tech-debt in ``apps/cli``, ``apps/tui``, and
    ``agents/`` is out of scope for verify_sprint (see P1-13 +
    ``docs/P1-CORRECTIONS-MAP.md``); broad ruff gates live in CI and the
    pre-commit hook rather than in this smoke script.

    Gracefully skips with a SKIP status if ruff isn't installed in the
    active venv (uv prunes dev deps unless ``--all-extras`` is used).
    """
    start = time.perf_counter()
    probe_code = "import importlib.util; exit(0 if importlib.util.find_spec('ruff') else 1)"
    ok, _, _ = _run([sys.executable, "-c", probe_code])
    if not ok:
        return CheckResult(
            "lint (ruff)",
            True,
            time.perf_counter() - start,
            "SKIP — ruff not installed (install with: uv pip install ruff)",
        )
    core_src = ROOT / "packages" / "core" / "src"
    if not core_src.exists():
        return CheckResult(
            "lint (ruff)",
            True,
            time.perf_counter() - start,
            f"SKIP — {core_src} not present in this checkout",
        )
    success, output, duration = _run(
        [sys.executable, "-m", "ruff", "check", str(core_src)], timeout=300
    )
    return CheckResult("lint (ruff)", success, duration, output)


def check_format() -> CheckResult:
    """Run ``ruff format --check`` on the canonical core package.

    Same scope as :func:`check_lint` — only ``packages/core/src`` is
    checked, matching the git-tracked ruff config at the package root.
    Same graceful skip when ruff is unavailable.
    """
    start = time.perf_counter()
    probe_code = "import importlib.util; exit(0 if importlib.util.find_spec('ruff') else 1)"
    ok, _, _ = _run([sys.executable, "-c", probe_code])
    if not ok:
        return CheckResult(
            "format (ruff --check)",
            True,
            time.perf_counter() - start,
            "SKIP — ruff not installed (install with: uv pip install ruff)",
        )
    core_src = ROOT / "packages" / "core" / "src"
    if not core_src.exists():
        return CheckResult(
            "format (ruff --check)",
            True,
            time.perf_counter() - start,
            f"SKIP — {core_src} not present in this checkout",
        )
    success, output, duration = _run(
        [sys.executable, "-m", "ruff", "format", "--check", str(core_src)], timeout=300
    )
    return CheckResult("format (ruff --check)", success, duration, output)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main() -> int:
    """Run all checks and report."""
    parser = argparse.ArgumentParser(description="operational sprint verifier")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-lint", action="store_true")
    parser.add_argument("--skip-format", action="store_true")
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
    checks.append(check_cli_help())
    if not args.skip_tests and TESTS.exists():
        checks.append(check_unit_tests())
    if not args.skip_lint:
        checks.append(check_lint())
    if not args.skip_format:
        checks.append(check_format())

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