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

#: A line that DECLARES a repository path: a BULLET, or a table row, whose
#: first content is a code-spanned path. "- `src/planner/` — markdown-only
#: planning notes" is a declaration.
#:
#: The bullet marker is required, and that is the whole trick: a wrapped
#: continuation ("  `src/mesh/`, no `interfaces/`") does not declare a
#: location, it continues one. Only the line that STARTS the item declares
#: something, so only it is held to account.
_DECLARES_PATH = re.compile(r"^\s*(?:[-*+]\s+|\|\s*)`([^`\n]+)`")


#: A declaration is a PATH: it crosses a directory separator and it is not a
#: command. `uv run --frozen --extra dev` has spaces; `sys.path` and
#: `Artifact` have no separator. Neither declares a location in this tree.
def _is_a_path(token: str) -> bool:
    return "/" in token and " " not in token.strip()


#: Markers of ABSENCE. A line that declares a path may say, ON THAT SAME
#: LINE, that the path is gone. The marker has to be on the declaration's own
#: line: a neighbour's "never" is not a permission — that is exactly the
#: loophole that let a stale bullet hide behind the anti-pattern above it.
#:
#: "no" is deliberately NOT one of them: "markdown-only planning notes; no
#: code" describes a tree that is not there.
_ABSENCE = (
    "never",
    "retired",
    "unpublished",
    "not published",
    "not deleted",
    "gone",
    "cut",
    "removed",
    "no longer",
    "does not publish",
    "do not publish",
)

#: The trees that are PROSE, not a description of the repository. The vault
#: and the strategic tree are the owner's own writing: they are allowed to
#: speak of a system the branch does not publish — the owner decided that the
#: whole vault stays published (2026-11-05) even though most of it describes
#: the retired runtime. A guard that forced edits to that prose would be
#: guarding the wrong thing.
_PROSE_TREES = ("vault/", "strategics/")

#: The documents that describe the tree AS IT IS, and that a cold agent reads
#: first. A guide is not history: it says what is here now, so a path it
#: declares has to exist now.
#:
#: The historical documents are exempt by category, not by listing: an ADR
#: records a decision at a date and the dated spec series records a design at
#: a date — the same clause that keeps the dated audits keeps them. They may
#: name a tree that is gone; that is what being a record means.
_GUIDES = ("AGENTS.md", "README.md")

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


def test_a_published_document_declares_only_published_paths() -> None:
    """A guide that names a tree the branch does not publish sends the reader
    looking for files that are not there.

    This is the other half of the link guard above. A link is a pointer the
    reader follows; a DECLARATION is a statement about the shape of the tree,
    and a cold agent reads it as fact. The scope cut took the trees away and
    left three guides still describing them — `AGENTS.md` listing
    `src/life_tatics/` and `src/planner/`, `specs/AGENTS.md` describing a
    hundred files across ninety-five milestone directories, and the pull
    request template telling contributors to run `uv run pytest` at a root
    that has no Python project.

    A declaration may be relative to the repository root or to the document's
    own directory; both are accepted, because both are used.
    """
    tracked = _tracked()
    offenders: list[str] = []
    for rel in sorted(path for path in tracked if path.endswith(".md")):
        if rel.startswith(_PROSE_TREES):
            continue
        if posixpath.basename(rel) not in _GUIDES:
            continue
        text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for lineno, line in enumerate(lines):
            match = _DECLARES_PATH.match(line)
            if not match:
                continue
            if any(marker in _item_text(lines, lineno) for marker in _ABSENCE):
                continue
            target = match.group(1).strip()
            if not _is_a_path(target):
                continue
            if not _is_published(rel, target, tracked):
                offenders.append(f"{rel}:{lineno} -> {target}")

    assert not offenders, (
        "published documents declare paths the branch does not publish: "
        + "; ".join(offenders[:20])
    )


def _item_text(lines: list[str], lineno: int) -> str:
    """The list item that starts at `lineno`: the line and its continuations.

    A marker of absence may sit on the declaration's own line or on the lines
    that CONTINUE the same item — "…is a vendored third-party fork with its own
    `.git/` — untracked here, never commit its contents" is one sentence in two
    lines. It may NOT sit on the previous item: that is how a stale bullet
    hides behind the anti-pattern above it.
    """
    collected = [lines[lineno]]
    for following in lines[lineno + 1 :]:
        stripped = following.strip()
        if not stripped or stripped.startswith(("-", "*", "+", "|")):
            break
        collected.append(following)
    return " ".join(" ".join(collected).split()).lower()


def _is_published(rel: str, target: str, tracked: set[str]) -> bool:
    """Is this declared path one the branch publishes?

    Accepted: a path relative to the repository root, a path relative to the
    document's own directory, a path with a line range on it, and a
    SHORT-HAND — the tail of a published path, which is how a guide inside
    `src/services/` writes `services/`.
    """
    text = target.strip().rstrip("/")
    # A line range is not part of the path: `src/contracts/common.py:40-48`.
    text = text.split(":", 1)[0] if re.fullmatch(r"[^:]+:\d+(-\d+)?", text) else text
    if not text or text.startswith(("/", "~", "$", "<")):
        return True
    if any(char in text for char in "*?["):
        return True

    candidates = {text, posixpath.normpath(posixpath.join(posixpath.dirname(rel), text))}
    for candidate in candidates:
        if candidate in tracked or candidate + ".md" in tracked:
            return True
        if any(path.startswith(candidate + "/") for path in tracked):
            return True
    # The short-hand: `services/` means `src/services/`, and
    # `tests/store/test_store_rls.py` means `src/ikigai/tests/store/...`.
    if any(text in path.split("/") for path in tracked):
        return True
    return any(path.endswith("/" + text) for path in tracked)


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
