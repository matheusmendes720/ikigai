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

3. **A test module that the suite COLLECTS was not PUBLISHED.** The
   `.gitignore` excludes every top-level module under `src/ikigai/tests/` —
   the retired suite — and re-includes the survivors by name. A guard written
   after that rule was therefore SILENTLY UNPUBLISHABLE: `git add` refused
   it, the file stayed on the owner's disk, the suite ran it, and the clone
   did not have it. The owner read 149 tests locally and the clone ran 147.
   Nothing in the suite noticed, because the suite that runs in the clone is
   the clone's own.

The first test is the general one, and it is the one that matters: **for
every published file, every local top-level import must land in a published
directory.** A local import is one whose root names a directory that exists
at the repository root. A third-party module never does, so it is out of
scope by construction, and the rule needs no list of exemptions to stay
honest — the list of retired trees would be exactly the kind of list that
rots.
"""

from __future__ import annotations

import ast
import json
import os
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
        + "; ".join(f"{root} <- {', '.join(paths)}" for root, paths in sorted(offenders.items()))
    )


def test_every_tracked_file_exists_on_disk() -> None:
    """The published surface is the index AND the files.

    The two can disagree without leaving a trace in the suite: a file that
    goes missing leaves `git status` reporting it as deleted, while every
    guard that reads `git ls-files` still counts it as published — the
    published package reads as present to the drift net and is absent to the
    interpreter that has to import it.

    This is the invariant that says the two agree.

    A symlink counts as materialized when the LINK is there, dangling or
    not: whether it resolves is a different question, and it has its own
    guard below.
    """
    tracked = _tracked(REPO_ROOT)
    if not tracked:
        return

    missing = [path for path in sorted(tracked) if not os.path.lexists(REPO_ROOT / path)]

    assert not missing, (
        f"{len(missing)} tracked file(s) are not on disk: "
        + ", ".join(missing[:20])
        + ". The index and the worktree disagree."
    )


def test_no_published_symlink_points_outside_the_repository() -> None:
    """A published symlink has to resolve inside the branch, for everybody.

    The four cadence skills of `.claude/skills/` were published as symlinks
    to ABSOLUTE paths on the owner's machine, pointing into
    `src/ikigai/src/agents/` — the tree ADR-037 unpublished and that no
    clone carries. On the owner's disk they were already dangling; in a
    clone they are dangling links to a directory that does not exist. The
    agent that loads them finds nothing, and nothing says why.

    The target is read from the BLOB, not from the worktree: a checkout
    without symlink support materialises the link as a plain file carrying
    the path as text, and the guard has to see what git will write
    everywhere, not what one platform happened to write here.
    """
    proc = subprocess.run(
        ["git", "ls-files", "-s", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=False,
    )
    if proc.returncode != 0:
        return

    offenders: list[str] = []
    for entry in proc.stdout.split("\0"):
        if not entry:
            continue
        meta, _, path = entry.partition("\t")
        mode, sha = meta.split()[0], meta.split()[1]
        if mode != "120000":  # only symlinks carry a target
            continue
        blob = subprocess.run(
            ["git", "cat-file", "blob", sha],
            cwd=REPO_ROOT,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        target = blob.stdout.strip()
        if not target:
            continue
        if Path(target).is_absolute() or target.startswith("~"):
            offenders.append(f"{path} -> {target} (absolute)")
            continue
        resolved = (REPO_ROOT / path).parent / target
        try:
            resolved.resolve().relative_to(REPO_ROOT.resolve())
        except ValueError:
            offenders.append(f"{path} -> {target} (escapes the repository)")
            continue
        if not os.path.lexists(resolved):
            offenders.append(f"{path} -> {target} (dangling)")

    assert not offenders, "published symlinks that do not resolve inside the branch: " + "; ".join(
        offenders[:20]
    )


def test_the_published_cadence_skills_are_the_projection() -> None:
    """`.claude/skills/ikigai-*` carries the published skills, byte for byte.

    The four cadence skills — daily, weekly, monthly, quarterly — were
    published as symlinks into the retired harness, so the agent that loads
    them found a broken pointer instead of a routine. They are copies of the
    projection now, and this is what keeps them copies: a skill that drifts
    is an agent running a routine the repository no longer describes.
    """
    projection = REPO_ROOT / "specs" / "harness" / "skills"
    published = {
        "ikigai-daily": "daily-note",
        "ikigai-weekly": "weekly-review",
        "ikigai-monthly": "monthly-review",
        "ikigai-quarterly": "quarterly-plan",
    }

    drifted: list[str] = []
    for target_name, source_name in published.items():
        source = projection / source_name / "SKILL.md"
        target = REPO_ROOT / ".claude" / "skills" / target_name / "SKILL.md"
        if not source.exists() or not target.exists():
            drifted.append(f"{target_name} (missing)")
            continue
        if source.read_text(encoding="utf-8").replace("\r\n", "\n") != target.read_text(
            encoding="utf-8"
        ).replace("\r\n", "\n"):
            drifted.append(f"{target_name} (drifted)")

    assert not drifted, "the published cadence skills are not the projection: " + ", ".join(drifted)


def test_the_daily_note_skill_prescribes_calls_the_CONTRACT_accepts() -> None:
    """The skill's own call has to satisfy the contract it is written against.

    Measured on the box, 2026-11-11: the cadence run sent `kinds` as an
    OBJECT (`{"item": "nota"}`) and the contract refused it — `query.kinds:
    Input should be a valid tuple` — so the run fell back to searching by
    text, and the day's note was built without the quarter's work. A skill
    that prescribes a call nobody validated is a skill that fails at 22:00, in
    a run nobody watches, so the prescription is parsed and validated HERE,
    against the same model the API validates with.
    """
    from src.contracts.dom import SearchQuery

    skill = (REPO_ROOT / "specs" / "harness" / "skills" / "daily-note" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    steps = skill.split("Steps:", 1)[-1].split("## ", 1)[0]
    prescriptions = re.findall(r'\{"query": \{.*?\}\}', steps)

    assert prescriptions, (
        "the daily-note skill prescribes no call at all — it cannot be wrong, "
        "but it cannot work either"
    )

    for raw in prescriptions:
        query = json.loads(raw)["query"]
        # The contract is the authority: this is the model the API validates with.
        SearchQuery.model_validate(query)
        assert isinstance(query.get("kinds"), list), (
            "kinds is a LIST of names — the contract refused an object on the "
            "box (query.kinds: Input should be a valid tuple)"
        )
        assert all(isinstance(kind, str) for kind in query["kinds"]), (
            "kinds carries kind NAMES, not objects"
        )
        assert query.get("quarter"), (
            "a search without the quarter returns every plan in the store and has to be paged"
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

    assert not offenders, "Tracked files live under a junk-named root directory: " + ", ".join(
        offenders
    )


def _retired_test_modules() -> set[str]:
    """The modules `conftest.py` excludes from collection.

    Read from the AST rather than by import: importing the conftest of the
    suite that is running this test has side effects (it rewrites `sys.path`
    and `tempfile.tempdir`), and the file is not importable by name from
    here. The tuple is a literal, so the AST carries its value exactly.
    """
    source = (IKIGAI_PKG / "tests" / "conftest.py").read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        # `LEGACY_TEST_MODULES: tuple[str, ...] = (...)` is an ANNOTATED
        # assignment — `ast.AnnAssign`, not `ast.Assign`. Both are accepted
        # so the guard survives either spelling of the declaration.
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        elif isinstance(node, ast.Assign):
            targets = list(node.targets)
            value = node.value
        else:
            continue
        if value is None:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "LEGACY_TEST_MODULES":
                return {str(item) for item in ast.literal_eval(value)}
    return set()


def test_every_test_module_is_published_or_retired() -> None:
    """A test module is either published or explicitly retired. Never neither.

    The suite runs from the worktree, so a module that is on disk but not in
    the index runs HERE and does not run in a clone. The count the owner reads
    locally is then larger than the count the clone runs, and the difference
    is exactly the guard that was supposed to catch the thing nobody caught.

    This is not hypothetical: the `.gitignore` excludes every top-level module
    under `src/ikigai/tests/` — the retired suite — and re-includes the
    survivors by name. A guard written after that rule was silently
    unpublishable: `git add` refused it, the file stayed on disk, and the
    suite ran it anyway.

    A clone holds neither the retired modules nor the caches, so in a clone
    this test has nothing to say — which is the correct verdict there.
    """
    tracked = _tracked(REPO_ROOT)
    if not tracked:
        return

    retired = _retired_test_modules()
    tests_dir = IKIGAI_PKG / "tests"

    offenders: list[str] = []
    for path in sorted(tests_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative in tracked:
            continue
        if path.name in retired:
            continue
        offenders.append(relative)

    assert not offenders, (
        "test modules that are neither published nor retired: "
        + ", ".join(offenders[:20])
        + ". The suite runs them here and not in a clone. Name them back in the "
        ".gitignore (they ship) or in LEGACY_TEST_MODULES (they do not)."
    )


def test_no_published_markdown_carries_a_junk_byte() -> None:
    """A NUL or a BOM in the published prose is junk — and it hides.

    MEASURED on the box (2026-11-09): five of the nine strategic documents
    carried a UTF-8 BOM **and** one NUL byte where a digit belonged — the text
    read ``See \\x000-ÍNDICE-PROGRESSIVO.md`` — and the loader, which anchors
    the frontmatter pattern on the FIRST byte, saw no frontmatter and indexed
    **no document at all**. A fifth NUL turned up in the vault's evidence file,
    in the same place: the first digit of a numbered sequence.

    The corruption was invisible. The files are readable, the agent reads them
    by name, the store carries them, and the suite is green — but a NUL makes
    git treat the file as binary, so the diff that would have shown the damage
    showed "Bin 4806 -> 4723 bytes" instead of a line.

    This is the same class the `.gitignore` spends its first section on (the
    junk a malformed shell redirect leaves behind), one level up: junk INSIDE
    a file that is otherwise legitimate.

    Falsification: put a NUL back into any published markdown and this fails.
    """
    tracked = _tracked(REPO_ROOT)
    if not tracked:
        return

    offenders: list[str] = []
    for relative in sorted(tracked):
        if not relative.endswith(".md"):
            continue
        path = REPO_ROOT / relative
        if not path.exists():
            continue
        raw = path.read_bytes()
        problems: list[str] = []
        nuls = raw.count(b"\x00")
        if nuls:
            problems.append(f"{nuls} NUL")
        if raw.startswith(b"\xef\xbb\xbf"):
            problems.append("BOM")
        if problems:
            offenders.append(f"{relative} ({', '.join(problems)})")

    assert not offenders, (
        "published markdown carries junk bytes: "
        + "; ".join(offenders)
        + ". A NUL hides the frontmatter from the parser, and a BOM hides it "
        "from git's diff."
    )
