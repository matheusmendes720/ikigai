"""The published tree, as a cold agent meets it.

A clone has to read like a NEW project: the product, the prose it ingests,
the contract it enforces, and the decisions that define it. Two things break
that, and both are mechanical enough to guard.

1. **A document that links to a path that is not published.** The reader
   follows the link and lands on a 404 — the repository telling them about a
   system it does not ship. The retired trees themselves are named in
   `test_canonical_scope.py`; this is the other half of the same problem: the
   pointers that outlived the files.

2. **The contracts package exporting the vocabulary of a model that was
   replaced.** `src.contracts` is what every layer imports. A name from the
   old pyramid in its public API is a name a new client can build on — and
   the planning tree (`metrics`, `planning`, `task`, …) went out with the
   scope it belonged to (ADR-037 §"publicação independente").

Both are checked against the TRACKED file set, not the filesystem. The
retired trees stay on the owner's disk, so a filesystem check would pass
here and fail in a clone — the opposite of what a guard is for.
"""

from __future__ import annotations

import posixpath
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

#: A markdown link: `[text](target)`. The target may be wrapped in angle
#: brackets (`](<path>)`), which is how a path with spaces is written.
_LINK = re.compile(r"\[[^\]\n]*\]\(\s*(<[^>\n]*>|[^)\s]+)\s*\)")

#: The modules the published contract surface is made of: the DOM, its
#: kinds, the store's constants, the error surface, and the identity.
_CONTRACT_MODULES = ("common", "dom", "dom_kinds", "errors")


def _tracked() -> set[str]:
    """The tracked file set, with NUL separation so nothing is quoted."""
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=False,
    )
    if proc.returncode != 0:  # not a git checkout (e.g. sdist) — skip
        import pytest

        pytest.skip("not a git checkout")
    return {path for path in proc.stdout.split("\0") if path}


def _resolves(rel: str, target: str, tracked: set[str]) -> bool:
    """Does this link point at something the branch publishes?

    The rules are GitHub's, not this repository's convenience:

    - a target starting with `/` is REPOSITORY-ROOT relative, so `/../x`
      escapes the repository and resolves to nothing;
    - anything else is relative to the file's own directory;
    - a directory target is satisfied by any published file under it.
    """
    text = target.strip()
    if text.startswith("<") and text.endswith(">"):
        text = text[1:-1]
    if text.startswith(("http://", "https://", "mailto:", "data:")):
        return True
    text = text.split("#")[0].split("?")[0]
    if not text:
        return True

    if text.startswith("/"):
        candidates = [posixpath.normpath(text.lstrip("/"))]
    else:
        base = posixpath.dirname(rel)
        candidates = [posixpath.normpath(posixpath.join(base, text))]

    for candidate in candidates:
        if candidate in tracked or candidate + ".md" in tracked:
            return True
        prefix = candidate.rstrip("/") + "/"
        if any(path.startswith(prefix) for path in tracked):
            return True
    return False


def test_a_published_document_links_only_to_published_paths() -> None:
    """No published document points at something the branch does not publish.

    The cut took the trees away; this holds the POINTERS honest. A link to a
    document that is no longer published is a 404 the reader meets, and it
    says the repository is bigger than it is.
    """
    tracked = _tracked()
    offenders: list[str] = []
    for rel in sorted(path for path in tracked if path.endswith(".md")):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        for target in _LINK.findall(text):
            if not _resolves(rel, target, tracked):
                offenders.append(f"{rel} -> {target}")

    assert not offenders, (
        "published documents link to paths the branch does not publish: "
        + "; ".join(offenders[:20])
    )


def test_the_contracts_package_exposes_only_the_dom() -> None:
    """`src.contracts` publishes the DOM's vocabulary, and nothing else.

    The planning tree of the pre-ADR-037 model — the task hierarchy, the PAV
    metrics, the mesh events — is gone from the tree, and its names must be
    gone from the public API too. A name a client can import is a name a
    client can build on.
    """
    import src.contracts as contracts
    from src.contracts import common, dom, dom_kinds, errors

    published: set[str] = set()
    for module in (common, dom, dom_kinds, errors):
        published |= {name for name in dir(module) if not name.startswith("_")}

    exported = set(contracts.__all__)
    assert exported <= published, (
        "the contracts package exports names that belong to no published "
        "contract module: " + ", ".join(sorted(exported - published))
    )
