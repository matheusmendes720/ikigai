"""Shared data model and process helpers for the code review orchestrator.

Kept separate from the CLI so the topology, the checks and the report
formatting can each stay small enough to review in one sitting.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class CheckStatus(Enum):
    PASS = auto()
    FAIL = auto()
    SKIP = auto()
    WARN = auto()


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    summary: str = ""
    details: list[str] = field(default_factory=list)
    annotations: list[dict] = field(default_factory=list)
    preexisting: list[str] = field(default_factory=list)

    def is_ok(self) -> bool:
        return self.status in (CheckStatus.PASS, CheckStatus.SKIP, CheckStatus.WARN)


@dataclass
class ReviewReport:
    results: list[CheckResult] = field(default_factory=list)
    files_changed: int = 0
    base_ref: str = "main"

    def all_passed(self) -> bool:
        return all(r.is_ok() for r in self.results)

    def failed_checks(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == CheckStatus.FAIL]


@dataclass(frozen=True)
class PackageSpec:
    """How one package is built, type checked and linted.

    The fields mirror `.github/workflows/ci.yml` exactly. The review
    orchestrator must not invent a second opinion about how a package is
    checked: if the matrix says `mypy -p src.ikigai.src`, the review runs
    the same command, in the same directory, with the same environment.
    """

    name: str
    path: str
    manager: str
    mypy_target: tuple[str, ...] = ()
    ruff_target: str = ""
    env: tuple[tuple[str, str], ...] = ()
    pytest: bool = False


def tool(name: str) -> str:
    """Resolve a CLI tool to an executable that works on this host.

    On Windows the `uv` and `poetry` entries on PATH may be the WSL builds,
    which cannot drive the native Windows virtualenvs. Prefer the native
    binaries shipped under ~/.local/bin when they exist.
    """
    found = shutil.which(name)
    if os.name != "nt":
        if found:
            return found
        raise SystemExit(f"code_review: required tool {name!r} not found on PATH")
    local = Path.home() / ".local" / "bin" / f"{name}.exe"
    if local.exists():
        return str(local)
    if found:
        return found
    raise SystemExit(f"code_review: required tool {name!r} not found on PATH")


# Variables that must never be inherited from the reviewer's own process.
#
# Each check runs inside the environment of the package that owns the files.
# If the reviewer's shell exports a PYTHONPATH, that path is injected into the
# package's interpreter and its site-packages win over the package's own
# dependencies: a different `pydantic_core` build then shadows the installed
# one and the check dies with
#
#     ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
#
# which measures the reviewer's shell, not the package. The environment a
# package declares explicitly (MYPYPATH/PYTHONPATH in the CI matrix) is
# applied AFTER the inherited values are dropped, so it always wins.
_INHERITED_LEAK_VARS = ("PYTHONPATH", "PYTHONHOME", "MYPYPATH")


def run(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    merged = {k: v for k, v in os.environ.items() if k not in _INHERITED_LEAK_VARS}
    if env:
        merged.update(env)
    return subprocess.run(
        cmd,
        check=False,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        env=merged,
    )
