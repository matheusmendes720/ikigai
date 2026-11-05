"""A lint gate that resolves to no file is green forever — so assert it does not.

`ruff check src/` in the `ikigai` CI matrix entry resolved to ZERO files for
months, and the gate was green on every run. The cause was a divergence
between git and ruff's gitignore matcher: the shape rules in `.gitignore`
swallow a root name that is a bare identifier — "src" is one — and the
re-inclusion that brings the directory back to git is a DIRECTORY rule, which
leaves a file matched deeper down excluded from ruff's own directory walk.
git saw three published files; ruff saw none.

Nothing failed, because a lint target that resolves to nothing has nothing to
complain about. The drift net has one answer for this class of defect, and it
is not another rule: **the gate has to prove it is looking at something.**

So this guard runs each CI lint target exactly the way CI runs it and compares
the file set it would check against the file set the branch actually
publishes. A target that sees nothing, or that sees a different set, fails.

Falsifiable by construction: exclude the published loader from `.gitignore`
again and this test fails, naming the files that went missing.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
IKIGAI_PKG = THIS_FILE.parent.parent
REPO_ROOT = IKIGAI_PKG.parent.parent

# Each entry is the CI matrix entry: the package directory CI runs in, the
# lint target CI passes to ruff inside it, and the tree the target is meant to
# cover. The third is not the second: `src/ikigai` holds the suite and the
# package, but its lint target is `src/` — the published package alone.
LINT_TARGETS: tuple[tuple[str, str, str], ...] = (
    ("src/ikigai", "src/", "src/ikigai/src"),
    ("src/contracts", ".", "src/contracts"),
    ("src/data", ".", "src/data"),
    ("src/services", ".", "src/services"),
    ("src/transport", ".", "src/transport"),
)


def _ruff() -> str | None:
    """The ruff this environment runs the gate with, or None."""
    found = shutil.which("ruff")
    if found:
        return found
    beside = Path(sys.executable).parent / ("ruff.exe" if sys.platform == "win32" else "ruff")
    return str(beside) if beside.exists() else None


def _tracked_python(relative: str) -> set[str]:
    """The published Python under a directory, as repo-relative posix paths."""
    proc = subprocess.run(
        ["git", "ls-files", "-z", "--", relative],
        cwd=REPO_ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=False,
    )
    if proc.returncode != 0:
        return set()
    return {
        path.replace("\\", "/")
        for path in proc.stdout.split("\0")
        if path.endswith(".py")
    }


def _ruff_would_check(ruff: str, package: str, target: str) -> set[str]:
    """The files ruff resolves for a target, as repo-relative posix paths."""
    proc = subprocess.run(
        [ruff, "check", "--show-files", target],
        cwd=REPO_ROOT / package,
        capture_output=True,
        text=True,
        check=False,
    )
    resolved: set[str] = set()
    for line in proc.stdout.splitlines():
        candidate = Path(line.strip())
        if not candidate.is_absolute():
            candidate = (REPO_ROOT / package / candidate).resolve()
        try:
            relative = candidate.relative_to(REPO_ROOT)
        except ValueError:
            continue
        resolved.add(relative.as_posix())
    return resolved


def test_every_ci_lint_target_sees_the_published_python() -> None:
    """Every CI lint target resolves to the Python the branch publishes."""
    ruff = _ruff()
    if ruff is None:
        import pytest

        pytest.skip("ruff is not installed in this environment")

    for package, target, tree in LINT_TARGETS:
        published = _tracked_python(tree)
        if not published:
            continue  # nothing published under this package — nothing to check
        seen = _ruff_would_check(ruff, package, target)

        missing = published - seen
        assert not missing, (
            f"the lint target `{target}` of `{package}` does not see "
            f"{len(missing)} published file(s): "
            + ", ".join(sorted(missing))
            + ". A gate that resolves to no file is green forever."
        )
