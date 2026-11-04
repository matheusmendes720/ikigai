"""Serverless canonical-scope drift detector (ADR-037, 2026-11-01).

REPLACES the harness-bound scope detector that used to live in this file.
The previous detector scanned ``src/ikigai/src/{agents,mcp_server,...}`` and
asserted the size of ``IKIGAI_TOOLS``. That subject was retired by the
human decision recorded in ADR-037 (serverless / cloud-native phase): the
legacy langchain/langgraph harness, the local chat REPL and the stdio MCP
servers are PC-only and are no longer part of the published repository.

Retiring an assertion is not the same as dropping a guard. This module keeps
the SAME rigour over the NEW canonical surface:

1. the retired runtime is absent from the published tree (no re-introduction);
2. the canonical contract surface is the single source of truth;
3. the mesh fork surface is exactly the cloud-safe adapters;
4. UEID keeps its canonical 4-part format (ADR-014);
5. the vault stays append-only and the agent layer stays planner-only
   (ADR-013) for the code that survived the pivot.

Drift tests are append-only: when the canonical surface changes again, ADD a
test here (or in ``test_drift_extended_invariants.py``) instead of weakening
an existing one.

Run::

    pytest src/ikigai/tests/test_canonical_scope.py -v
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

THIS_FILE = Path(__file__).resolve()
IKIGAI_PKG = THIS_FILE.parent.parent
REPO_ROOT = IKIGAI_PKG.parent.parent

# ── Retired runtime (must never come back to the published tree) ──────────
# 2026-11-02: the four pre-ADR-037 trees are now retired WHOLE, not file by
# file. ADR-037 was first executed as a set of .gitignore rules that excluded
# individual files inside trees that stayed published — so 84 of the 91 files
# in sys_ikigai/ and 25 of the 26 in src/mesh/ kept shipping. The trees are
# now unpublished as units (ADR-037 §"publicação independente").
RETIRED_PATHS = (
    "sys_ikigai",
    "src/mesh",
    "interfaces",
    "vibe-ops",
    "src/agents",
    "src/ikigai/src/agents",
    "src/ikigai/src/chat",
    "src/ikigai/src/mcp_server",
    "src/ikigai/src/plugins",
    "src/ikigai/src/ikigai_wrapper.py",
    "src/ikigai/src/gateway_client.py",
    "src/tuiboard",
    "src/solverforge_calendar",
    "interfaces/tui",
    "vibe-ops/vibeops-tui",
    "plugins/paperclipai",
    "langgraph.json",
)

# ── Canonical surface (must stay published) ────────────────────────────────
CANONICAL_PATHS = (
    "src/contracts",
    "src/services",
    "src/transport",
    "src/data",
    # The bot is the first non-desktop client (ADR-037 D8). The renewed scope
    # says the branch IS the service: api + bot + store. A branch that ships
    # the api without the client is not the service it claims to be.
    "src/bot",
    "vault",
    "specs",
    "docs",
)

UEID_4PART = re.compile(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")


def _tracked(repo: Path) -> set[str]:
    """Return the tracked file set of the repository under test.

    `git ls-files` QUOTES a path that holds a non-ASCII character, and the
    quotes are part of the output: the PT-BR strategic prose comes back as
    `"strategics/Planejamento (Estratégico e Tático).md"`, which begins with
    a double quote and matches no `startswith("strategics/")`. A guard that
    reads the quoted form cannot SEE the file — and a path a guard cannot see
    is a path the guard cannot protect.

    `-z` makes git separate the paths with NUL and quote nothing, so what
    comes back is the paths themselves.
    """
    import subprocess

    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo,
        capture_output=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=False,
    )
    if proc.returncode != 0:  # not a git checkout (e.g. sdist) — skip
        pytest.skip("not a git checkout")
    return {path for path in proc.stdout.split("\0") if path}


# ---------------------------------------------------------------------------
# 1. The retired runtime is gone from the published tree
# ---------------------------------------------------------------------------
def test_retired_runtime_is_not_published() -> None:
    tracked = _tracked(REPO_ROOT)
    offenders = [p for p in RETIRED_PATHS if any(f == p or f.startswith(p + "/") for f in tracked)]
    assert not offenders, (
        "Retired PC-only runtime is published again (ADR-037): " + ", ".join(offenders)
    )


def test_no_tracked_file_imports_the_retired_harness() -> None:
    import subprocess

    pattern = (
        r"^[[:space:]]*(from|import)[[:space:]]+[A-Za-z0-9_.]*"
        r"(agents|chat|mcp_server|plugins|ikigai_wrapper|gateway_client)"
        r"([^A-Za-z0-9_]|$)"
    )
    proc = subprocess.run(
        [
            "git",
            "grep",
            "-l",
            "-E",
            pattern,
            "--include=*.py",
            "--",
            "src/",
            ":!src/ikigai/tests/test_canonical_scope.py",
            ":!src/ikigai/tests/test_drift_invariants.py",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    offenders = [line for line in proc.stdout.split() if line]
    assert not offenders, (
        "Published files still import the retired harness: " + ", ".join(offenders)
    )


# ---------------------------------------------------------------------------
# 2. The canonical surface stays published
# ---------------------------------------------------------------------------
def test_canonical_surface_is_published() -> None:
    tracked = _tracked(REPO_ROOT)
    missing = [
        p
        for p in CANONICAL_PATHS
        if not any(f == p or f.startswith(p + "/") for f in tracked)
    ]
    assert not missing, "Canonical path missing from the published tree: " + ", ".join(missing)


def test_the_vault_prose_is_published() -> None:
    """The vault is the prose the store is built from (ADR-037 D4).

    The sync reads `vault/ikigai/closing-2026` and upserts what it finds,
    and the image copies the vault for exactly that reason. "The directory
    is tracked" is not enough — a vault with four scaffolding files and no
    planning tree publishes a service with an empty memory, and nothing
    fails: the sync simply has nothing to ingest.
    """
    tracked = _tracked(REPO_ROOT)
    prose = [
        path
        for path in tracked
        if path.startswith("vault/ikigai/closing-2026/") and path.endswith(".md")
    ]
    assert prose, (
        "the vault's planning tree is not published — the sync would ingest "
        "nothing and the store would start empty"
    )


# ---------------------------------------------------------------------------
# 3. Contracts are the single source of truth
# ---------------------------------------------------------------------------
def test_contracts_are_the_single_source_of_truth() -> None:
    tracked = _tracked(REPO_ROOT)
    # The meta-planner contracts are a separate family and must stay inside
    # the ikigai project (src/ikigai/contracts/), never inside src/contracts/.
    assert not any(f.startswith("src/contracts/proposal") for f in tracked)


def test_no_published_file_imports_the_unpublished_trees() -> None:
    """Nothing published may import a tree that is no longer published.

    This is the guard that keeps the cut from rotting. ``sys_ikigai/`` and
    ``src/mesh/`` are unpublished as whole trees (ADR-037), so an import of
    them would break a fresh clone — and, worse, would drag the legacy back
    in through the packaging. The previous guard in this slot checked that
    ``src/mesh/`` exposed only the cloud-safe adapters, which PRESERVED the
    mesh as published; the mesh is retired, and this is its replacement.
    """
    import subprocess

    proc = subprocess.run(
        [
            "git",
            "grep",
            "-l",
            "-E",
            r"^[[:space:]]*(from|import)[[:space:]]+[A-Za-z0-9_.]*"
            r"(sys_ikigai|mesh)([^A-Za-z0-9_]|$)",
            "--include=*.py",
            "--",
            "src/",
            ":!src/ikigai/tests/test_canonical_scope.py",
            ":!src/ikigai/tests/test_drift_invariants.py",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    offenders = [line for line in proc.stdout.split() if line]
    assert not offenders, (
        "Published files still import the unpublished runtime: " + ", ".join(offenders)
    )


# ---------------------------------------------------------------------------
# 4. The image's build context is published
# ---------------------------------------------------------------------------
# The Dockerfile copies from the working tree. A COPY of a path that is not
# tracked fails the BUILD, not the tests: the image never comes up, and the
# failure says nothing about the cause. The manifest and the lock of the
# Poetry package are the case that matters — they are what `poetry install`
# resolves the service's dependencies from — and they are exactly the kind of
# file a shape-based ignore rule swallows.
DOCKERFILE = REPO_ROOT / "deploy" / "Dockerfile"


def test_everything_the_image_copies_is_published() -> None:
    source = DOCKERFILE.read_text(encoding="utf-8")
    tracked = _tracked(REPO_ROOT)

    copied: list[str] = []
    for line in source.splitlines():
        if not line.startswith("COPY "):
            continue
        parts = line.split()[1:]
        copied.extend(parts[:-1])  # the last argument is the destination

    missing = [
        path
        for path in copied
        if not any(
            t == path
            or t == path.rstrip("/")
            or t.startswith(path.rstrip("/") + "/")
            for t in tracked
        )
    ]
    assert not missing, (
        "the Dockerfile copies paths that are not published — the image would "
        "fail to build, and the failure would say nothing about the cause: "
        + ", ".join(missing)
    )


def test_the_branch_publishes_the_strategic_prose() -> None:
    """The image copies `strategics/`, so the branch must carry the prose.

    The PT-BR documents are the grounding the vault excerpt points at
    (`vault/_strategics_excerpt.md` names them as the full foundation). They
    were tracked before the ADR-037 cut, and the cut took them out as
    collateral: the junk rules exclude a root directory by its SHAPE, and
    `strategics` is a bare identifier with no dot — so git never descended
    into it, and the index sweep removed the prose along with the retired
    runtime.

    Nothing failed. The image simply lost the owner's strategic content, and
    the drift net reported it as a path the image copied but the branch did
    not publish. The invariant is therefore stated from both ends: the prose
    is published, and the image copies only what is published.
    """
    tracked = _tracked(REPO_ROOT)
    prose = [p for p in tracked if p.startswith("strategics/") and p.endswith(".md")]
    assert prose, (
        "the PT-BR strategic prose is not published — the image copies "
        "strategics/, the vault excerpt names those documents as the full "
        "grounding, and the store would be built without them"
    )


# The words a published document uses to say "this directory is not in the
# branch". A tree-diagram line carrying one of them is a claim, and the claim
# is checked against the index below.
_UNPUBLISHED_CLAIM = ("untracked", "not published", "unpublished")


def test_the_published_docs_do_not_deny_a_published_directory() -> None:
    """A document must not call a directory unpublished when the index says
    it is published.

    The prose under `strategics/` is tracked; the vendored fork beside it is
    not. Getting that backwards in a published document sends the next reader
    — and the next agent — after a directory the branch does not carry, and
    the Dockerfile that copies it fails the BUILD on a fresh clone.

    So the guard reads the CLAIM and checks it against the index: a directory
    a document calls untracked must have nothing tracked under it.
    """
    tracked = _tracked(REPO_ROOT)
    offenders: list[str] = []

    for doc in ("AGENTS.md", "README.md", "CLAUDE.md"):
        path = REPO_ROOT / doc
        if not path.exists():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            # Only the ROOT level of the tree: a nested entry's name is
            # relative to its parent, and a root-anchored comparison would
            # read it as a path that does not exist.
            if not stripped.startswith(("├──", "└──")):
                continue
            before, sep, comment = stripped.partition("#")
            if not sep or not any(word in comment.lower() for word in _UNPUBLISHED_CLAIM):
                continue
            tokens = before.lstrip("│├└─ ").split()
            if not tokens or not tokens[0].endswith("/"):
                continue
            name = tokens[0]
            if any(t.startswith(name) for t in tracked):
                offenders.append(f"{doc}:{number}: {name}")

    assert not offenders, (
        "a published document calls a directory unpublished, but the index "
        "carries files under it: " + "; ".join(offenders)
    )


# ---------------------------------------------------------------------------
# 5. UEID format (ADR-014)
# ---------------------------------------------------------------------------
def test_ueid_4part_format_is_canonical() -> None:
    assert UEID_4PART.match("life:task:abc123:def456")
    assert not UEID_4PART.match("LIFE:task:abc123:def456")
    assert not UEID_4PART.match("life:task:abc123")


# ---------------------------------------------------------------------------
# 6. Planner-only surface (ADR-013) for the code that survived
# ---------------------------------------------------------------------------
FORBIDDEN_IN_AGENT_LAYER = (
    "sys_ikigai.core.scoring",
    "ikigai.core.heuristics",
    "cybernetics.daily_loop",
)


def test_no_algorithm_constants_in_agent_code() -> None:
    """The algorithm modules must not be IMPORTED by the planner layer.

    The pattern is anchored on the import statement: a module that merely
    NAMES the retired module in its prose ("the formula was deleted along
    with src/ikigai/core/scoring/") is documenting the boundary, not
    crossing it — and a grep that reads prose as code fails the honest
    documentation of the very thing it guards.
    """
    import subprocess

    pattern = (
        r"^[[:space:]]*(from|import)[[:space:]]+"
        r"(" + "|".join(re.escape(name) for name in FORBIDDEN_IN_AGENT_LAYER) + ")"
        r"([^A-Za-z0-9_]|$)"
    )
    proc = subprocess.run(
        [
            "git",
            "grep",
            "-l",
            "-E",
            pattern,
            "--include=*.py",
            "--",
            "src/services/",
            "src/contracts/",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert not [line for line in proc.stdout.split() if line], (
        "ADR-013 violation: scoring/policy math reached the planner layer"
    )


def test_published_tree_has_no_llm_sdk_dependency() -> None:
    """The published tree must not depend on an LLM SDK (ADR-037 D7).

    The retired reflection package was the only subject of this invariant.
    The pivot made it STRONGER rather than vacuous: the agent is the harness
    (`pi`), and it is EXTERNAL (ADR-037 D7 — "a repo NÃO constrói harness").
    So no published file may import an LLM SDK. The published surface is the
    data layer: it serves artifacts over MCP and knows nothing about models.
    """
    import subprocess

    proc = subprocess.run(
        [
            "git",
            "grep",
            "-l",
            "-E",
            r"^[[:space:]]*(import|from)[[:space:]]+(openai|anthropic|langchain|litellm)",
            "--include=*.py",
            "--",
            "src/",
            ":!src/ikigai/tests/test_canonical_scope.py",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert not [line for line in proc.stdout.split() if line], (
        "The reflection package must stay LLM-free"
    )


def test_algorithm_constants_stay_out_of_the_agent_layer() -> None:
    import subprocess

    proc = subprocess.run(
        [
            "git",
            "grep",
            "-l",
            "-E",
            r"algorithm_constants",
            "--include=*.py",
            "--",
            "src/",
            ":!src/ikigai/tests/test_canonical_scope.py",
            ":!src/ikigai/tests/test_drift_invariants.py",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert not [line for line in proc.stdout.split() if line], (
        "ADR-019 R7: the agent layer must not read the algorithm constants"
    )
