"""The repository root must stay reachable by git.

A gitignore pattern matches a directory as readily as a file, and git does not
descend into a directory it excluded. A root directory with a short name was
therefore invisible to `git add` until someone remembered to negate it by hand:
the October and November specification series stayed untracked for two months
for exactly that reason, and `data/` was still missing its negation.

The check asks git which rule decided, rather than assuming. A root directory
may be excluded on purpose — `logs/` and `dist/` are runtime and should be — but
it must never be excluded by a bare character class, because that rule was
written to catch junk files and it cannot tell a file from a directory.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GITIGNORE = REPO_ROOT / ".gitignore"

# A pattern built only from character classes matches a directory name as well
# as a file name.
_BARE_CLASS = re.compile(r"/(?:\[[^\]]+\])+")

# A negation whose pattern ends in "/" matches directories only. This is the
# shape that re-includes a root directory while leaving a junk file ignored.
_DIRECTORY_NEGATION = re.compile(r"!/\[[^\]]+\]\*/")


def _ignore_lines() -> list[str]:
    text = GITIGNORE.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines()]


def _root_directories() -> list[Path]:
    return [
        entry for entry in REPO_ROOT.iterdir() if entry.is_dir() and not entry.name.startswith(".")
    ]


def _deciding_rule(path: str) -> str | None:
    """The pattern that excludes the path, or None when it is not excluded.

    `git check-ignore -v` prints the last matching pattern, which is the one
    that decided the outcome.
    """
    result = subprocess.run(
        ["git", "check-ignore", "-v", "--no-index", "--", path],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if result.returncode != 0:
        return None

    # The output is "<source>:<linenum>:<pattern>\t<pathname>".
    record = result.stdout.decode("utf-8", "replace").split("\t", 1)[0]
    _, _, pattern = record.split(":", 2)
    pattern = pattern.strip()
    if pattern.startswith("!"):
        # A NEGATION means the path is not excluded. `check-ignore -v` still
        # prints it and still exits 0, so the exit status alone cannot be
        # trusted here — the pattern has to be read.
        return None
    return pattern


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not on PATH")
def test_no_root_directory_is_shadowed_by_a_class_pattern() -> None:
    """A wholesale exclusion is fine. An accidental one is the bug."""
    shadowed: list[tuple[str, str]] = []

    for entry in _root_directories():
        pattern = _deciding_rule(f"{entry.name}/")
        if pattern is None:
            continue
        if _BARE_CLASS.fullmatch(pattern):
            shadowed.append((entry.name, pattern))

    assert not shadowed, (
        f"root directories excluded by a bare character-class pattern: {shadowed}. "
        "That rule was written to catch junk files and it cannot tell a file "
        "from a directory. Git never descends into a directory it excluded, so "
        "every file below it is invisible to `git add`."
    )


def test_a_bare_character_class_pattern_has_a_directory_negation() -> None:
    """A bare class pattern shadows directories; the negation must sit beside it."""
    lines = _ignore_lines()

    has_bare_class = any(_BARE_CLASS.fullmatch(line) for line in lines)
    has_directory_negation = any(_DIRECTORY_NEGATION.fullmatch(line) for line in lines)

    assert not has_bare_class or has_directory_negation, (
        "the .gitignore holds a bare character-class pattern and no directory-only "
        "negation. Any root directory with a short name is then invisible to git "
        "until someone negates it by hand."
    )


def test_the_tracked_exceptions_under_data_stay_reachable() -> None:
    """`data/` carries tracked source. A wholesale exclusion would lose it.

    The tracked source is ONE marker file. The SQLite fixtures that sat beside
    it belonged to the store that is Postgres now, and they left with the rest
    of the pre-ADR-037 corpus (2026-11-05): the retired-path guard keeps them
    from coming back, and the general guard above keeps whatever IS tracked
    reachable. This one names the exception, so that the rule that re-includes
    it stays a named rule and not an accident of ordering.
    """
    for relative in ("data/investigation_queue/.keep",):
        assert _deciding_rule(relative) is None, (
            f"{relative} is excluded by a rule, but it is tracked source. A new "
            "file beside it would be silently ignored."
        )


def test_the_harness_configuration_is_not_ignored() -> None:
    """The harness's configuration is published, so git has to take it.

    `.pi/mcp.json` is how the api is declared to the harness. If it is
    ignored, `git add` on it fails with "ignored" no matter what the
    repository's own rules say — and the reason is not always the repository:
    a `.gitignore` INSIDE `.pi/` overrides the one at the root, because the
    deeper file's patterns come last.

    The retired harness left such a file behind — `*` — and it swallowed the
    configuration whole. The check is on the FILE, because that is what git
    decides when it is asked to take it: a directory's verdict is a different
    question, and `check-ignore` answers it with a path type it guesses
    rather than the one git walks with.
    """
    assert _deciding_rule(".pi/mcp.json") is None, (
        "the harness's MCP configuration is ignored — the api is declared to "
        "nobody. If a `.pi/.gitignore` is to blame, it overrides the rule at "
        "the repository root."
    )


def _tracked_paths() -> list[str]:
    """Every tracked path, minus the gitlinks.

    A gitlink is a submodule: its content lives in another repository, and
    the parent's ignore rules do not govern it.
    """
    result = subprocess.run(
        ["git", "ls-files", "-s", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    paths: list[str] = []
    for entry in result.stdout.decode("utf-8", "replace").split("\0"):
        if not entry:
            continue
        meta, _, path = entry.partition("\t")
        if meta.split(" ", 1)[0] == "160000":
            continue
        paths.append(path)
    return paths


def test_no_tracked_file_is_ignored() -> None:
    """An ignore rule must never swallow something the repository tracks.

    This is the guard that makes a rewrite of the junk rules safe: the rules
    catch a root path by its SHAPE, and a shape is coarse. If a legitimate
    file ever falls inside a caught shape, the file is tracked but a new
    sibling beside it is not — the exclusion becomes invisible exactly where
    it starts costing.
    """
    shadowed = [path for path in _tracked_paths() if _deciding_rule(path) is not None]

    assert not shadowed, (
        f"tracked files matched by an ignore rule: {shadowed[:20]}. They are in "
        "the index, so the exclusion is invisible — but a new file beside any "
        "of them would be silently untracked. Re-include the path explicitly."
    )
