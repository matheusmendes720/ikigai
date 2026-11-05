"""The published tree may only depend on what the published tree holds.

Two holes this guard closes, both found by READING the tree rather than by
running a test:

1. **`life/cli/cli.py` imported `interfaces.cli.notify_cli` at module scope.**
   `interfaces/` is unpublished as a whole tree (ADR-037), so a FRESH CLONE
   could not import the published package at all — `ModuleNotFoundError: No
   module named 'interfaces'` — while the tree still shipped as published.
   The guard that should have caught it (`test_canonical_scope.py`) greps
   `src/` for two families of retired imports: `life/` is not under `src/`,
   and `interfaces` was in neither family. A guard that only looks at the
   directory it was written for does not protect the tree it was written
   about.

2. **The shape-based `.gitignore` rules match a ROOT NAME.** `!/*/`
   re-includes every root directory, and `/*[^A-Za-z0-9_.-]*` cannot match a
   path one directory deep, because `*` never crosses a `/`. A junk root
   directory (`$FT`, a shell-redirect leftover) was therefore descended into,
   and one junk file inside it ended up TRACKED. The `.gitignore` now
   excludes the directory; this guard holds that honest.

The first test is the general one, and it is the one that matters: **for
every published file, every local top-level import must land in a published
directory.** A local import is one whose root names a directory that exists
at the repository root. A third-party module never does, so it is out of
scope by construction, and the rule needs no list of exemptions to stay
honest — the list of retired trees would be exactly the kind of list that
rots.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
IKIGAI_PKG = THIS_FILE.parent.parent
REPO_ROOT = IKIGAI_PKG.parent.parent

# A top-level import: `import X`, `from X import ...`, `from X.Y import ...`.
# A relative import (`.`, `..`) does not name a top-level package and is not
# matched — the character after the keyword must be a name.
_IMPORT = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)")

# A root name that carries a character no file may legitimately contain. The
# same class the `.gitignore` shape rules use.
_JUNK_NAME = re.compile(r"[^A-Za-z0-9_.-]")


def _tracked(repo: Path) -> set[str]:
    """Return the tracked file set of the repository under test.

    `git ls-files` QUOTES a path that holds a non-ASCII character, and the
    quotes are part of the output. `-z` makes git separate the paths with NUL
    and quote nothing.
    """
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo,
        capture_output=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=False,
    )
    if proc.returncode != 0:  # not a git checkout (e.g. sdist) — skip
        return set()
    return {path for path in proc.stdout.split("\0") if path}


def _published_roots(tracked: set[str]) -> set[str]:
    """The root directory names that hold at least one tracked file."""
    return {path.split("/", 1)[0] for path in tracked if "/" in path}


def _local_roots_on_disk() -> set[str]:
    """The root directory names that exist on this disk, published or not."""
    return {entry.name for entry in REPO_ROOT.iterdir() if entry.is_dir()}


def _imported_roots(path: Path) -> set[str]:
    """The top-level package names a published module imports."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return {match.group(1) for match in map(_IMPORT.match, text.splitlines()) if match}


def test_no_published_file_imports_an_unpublished_package() -> None:
    """A published file may not import a local package the branch does not hold.

    This is the rule that would have caught `life/cli/cli.py` importing
    `interfaces.cli.notify_cli`: `interfaces/` is on the owner's disk and out
    of the branch, so the import resolves locally and fails on every other
    machine — which is to say, on the VPS and on CI.
    """
    tracked = _tracked(REPO_ROOT)
    if not tracked:  # not a git checkout — nothing to assert
        return

    published = _published_roots(tracked)
    local = _local_roots_on_disk()

    offenders: dict[str, list[str]] = {}
    for path in sorted(tracked):
        if not path.endswith(".py"):
            continue
        for root in _imported_roots(REPO_ROOT / path):
            if root not in local:
                continue  # stdlib or third-party — not a local dependency
            if root in published:
                continue
            offenders.setdefault(root, []).append(path)

    assert not offenders, (
        "Published files import packages the branch does not publish (a fresh "
        "clone cannot import them): "
        + "; ".join(
            f"{root} <- {', '.join(paths)}" for root, paths in sorted(offenders.items())
        )
    )


def test_every_tracked_file_exists_on_disk() -> None:
    """The published surface is the index AND the files.

    The two can disagree without leaving a trace in the suite: a file that
    goes missing leaves `git status` reporting it as deleted, while every
    guard that reads `git ls-files` still counts it as published — the
    published package reads as present to the drift net and is absent to the
    interpreter that has to import it.

    This is the invariant that says the two agree.
    """
    tracked = _tracked(REPO_ROOT)
    if not tracked:
        return

    missing = [path for path in sorted(tracked) if not (REPO_ROOT / path).exists()]

    assert not missing, (
        f"{len(missing)} tracked file(s) are not on disk: "
        + ", ".join(missing[:20])
        + ". The index and the worktree disagree."
    )


def test_no_junk_named_root_directory_holds_a_tracked_file() -> None:
    """A root directory whose name carries an illegal character holds nothing.

    The `.gitignore` excludes such a directory, so a tracked file beneath it
    means the rule and the index disagree — the shape sweep missed it once
    already (`$FT/.claude/loop/progress.md`).
    """
    tracked = _tracked(REPO_ROOT)
    if not tracked:
        return

    offenders: list[str] = []
    for path in sorted(tracked):
        head = path.split("/", 1)[0]
        if "/" in path and _JUNK_NAME.search(head):
            offenders.append(path)

    assert not offenders, (
        "Tracked files live under a junk-named root directory: " + ", ".join(offenders)
    )
