"""The ignore rules have to decide the same thing on every machine.

Git reads `.gitignore` byte for byte, and a CRLF checkout changes what it
decides. A pattern that ends in "/" is a DIRECTORY rule — "re-include this
directory" — and the "\r" that CRLF leaves at the end of the line is part of
the pattern, so the directory rule stops matching. Then the LAST rule that
matches decides, and on a Windows clone that is not the rule that decides on
Linux:

    LF   : data/test-fixtures/  ->  addable
    CRLF : data/test-fixtures/  ->  IGNORED

The same ignore file, two verdicts, two machines. And the verdict decides
whether a file can be tracked at all: the root-directory re-inclusions
(`!/[A-Za-z0-9_]*/`, `!/strategics/`, `!/data/`) are all directory rules, so
under CRLF the published surface can become silently un-addable — which is
exactly how the pre-ADR-037 corpus went missing, and how nobody noticed for
two months.

This guard pins the shape instead of the symptom:

1. `.gitattributes` holds `.gitignore` at LF, so every checkout reads the
   rules the same way;
2. the `.gitignore` on disk carries no CR at all — which is what a checkout
   that honoured the attribute looks like;
3. and the rule that re-includes `data/test-fixtures/` is still there, so the
   one directory whose verdict flipped is named explicitly.

Falsifiable by construction: drop the `.gitattributes` rule and a fresh
Windows checkout stops satisfying (1) and (2), and the guard says so.
"""

from __future__ import annotations

import re
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
IKIGAI_PKG = THIS_FILE.parent.parent
REPO_ROOT = IKIGAI_PKG.parent.parent

GITIGNORE = REPO_ROOT / ".gitignore"
GITATTRIBUTES = REPO_ROOT / ".gitattributes"

# The rule that re-includes the directory whose verdict flipped. The path
# ends in "/" — a DIRECTORY rule — which is the shape CRLF breaks.
_FIXTURES_RULE = "!/data/test-fixtures/"


def _attribute_rules() -> list[str]:
    if not GITATTRIBUTES.exists():
        return []
    return [
        line.strip()
        for line in GITATTRIBUTES.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def test_the_ignore_rules_are_pinned_to_lf() -> None:
    """`.gitattributes` holds `.gitignore` at LF on every platform."""
    rules = _attribute_rules()

    pinned = any(
        re.fullmatch(r"\.gitignore\s+.*\beol=lf\b", rule) for rule in rules
    )

    assert pinned, (
        "`.gitattributes` does not hold `.gitignore` at LF. Git reads the "
        "ignore rules byte for byte, and a CRLF checkout breaks every "
        "DIRECTORY rule — the re-inclusions that keep the published surface "
        "addable — so the same file decides differently on Windows and on "
        "Linux. Expected a rule like `.gitignore text eol=lf`; found: "
        + "; ".join(rules)
    )


def test_the_ignore_file_on_disk_carries_no_carriage_return() -> None:
    """The checkout honoured it: the rules on disk are the rules in the index."""
    if not GITIGNORE.exists():
        return

    raw = GITIGNORE.read_bytes()
    carriage_returns = raw.count(b"\r")

    assert carriage_returns == 0, (
        f"`.gitignore` carries {carriage_returns} carriage return(s). A CRLF "
        "checkout breaks the directory rules, so git decides differently here "
        "than on the machine that wrote the file. `git add` then ignores a "
        "file that the same command accepts elsewhere."
    )


def test_the_fixture_directory_is_still_named_back() -> None:
    """The one directory whose verdict flipped keeps its re-inclusion."""
    if not GITIGNORE.exists():
        return

    lines = {
        line.strip() for line in GITIGNORE.read_text(encoding="utf-8").splitlines()
    }

    assert _FIXTURES_RULE in lines, (
        f"`.gitignore` no longer holds `{_FIXTURES_RULE}`. That directory holds "
        "tracked source, and a wholesale exclusion would lose it — silently, "
        "because the files are already in the index."
    )
