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

import fnmatch
import re
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
    # The retired root CLI hub. Its manifest was deleted with the root project,
    # but the package it published stayed tracked — and `life/cli/cli.py`
    # imports `interfaces.cli.notify_cli` at module scope, so a fresh clone
    # could not import it at all. A published tree that cannot be imported is
    # not published, it is broken.
    "life",
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
    # The documents that present the retired system AS THE RUNNING SYSTEM.
    # ADR-037 §"publicação independente": the branch publishes the product,
    # and the material that speaks about the old system in the present tense
    # stays on the owner's disk. The decision record — the ADRs, the
    # data-layer series, the dated audits, the cut — stays published,
    # because a decision that cites what it eliminated is how it is
    # evaluated.
    ".claude/loop",
    ".claude/commands",
    ".claude/helpers",
    "reports",
    "docs/architecture",
    "docs/design-system",
    "docs/integrations",
    "docs/specs",
    "docs/superpowers/glossaries",
    "docs/ARCHITECTURE_INDEX.md",
    "docs/CONCEPTUAL_MODEL.md",
    "docs/SPEC.md",
    "docs/SYSTEMS_TOPOLOGY.md",
    "docs/LANGRAPH_DEV.md",
    "docs/FORK_WORKFLOW.md",
    "docs/PAV_INVENTORY.md",
    "docs/M139-blocked.md",
    "docs/2026-09-29-langgraph-dev-studio-e2e.md",
    "docs/.sdd-progress.md",
    "docs/ÍNDICE PROGRESSIVO.md",
    # The specs numbered by the retired roadmap (M<n>-*). One class, one
    # pattern: the canonical specs are not numbered — specs/harness/ and
    # specs/data-layer/ are.
    "specs/M[0-9]*",
    # The post-pivot scope cut (2026-11-05). The repository has to read like
    # a NEW project: a cold agent that clones it must not meet the
    # architecture of a system that no longer exists. These are that
    # system's own description — its decision surface, its diagnostics, its
    # design canvases, its agent skills, its vendored tools, its planners,
    # its examples, its wiki.
    "code-docs/brd",
    "code-docs/prd",
    "code-docs/diagnostic",
    "code-docs/design",
    "code-docs/ikigai",
    "code-docs/observability",
    "code-docs/proposals",
    "code-docs/specs",
    "code-docs/00-INDEX.md",
    "code-docs/00-INDEX-specs.md",
    "code-docs/README.md",
    "code-docs/glossary.md",
    "docs/diagnostics",
    "docs/decisions",
    "docs/research",
    "docs/archive",
    "docs/openwiki-visualizer",
    "docs/superpowers/plans",
    "docs/DEPLOY.md",
    "docs/memory-audit-2026-09.md",
    "docs/interface-usability-diagnostic-2026-09-08.md",
    "docs/vanilla-pivot.html",
    "taskwarrior",
    "tools",
    "src/planner",
    "src/life_tatics",
    ".agents/skills",
    ".claude/agents",
    ".claude/workflows",
    ".claude/AGENTS.md",
    ".claude/settings.json",
    "src/ikigai/souls",
    "src/ikigai/tools",
    "src/ikigai/scripts",
    "src/ikigai/docs",
    "src/ikigai/contracts",
    "src/ikigai/tests/reports",
    "src/ikigai/CHANGELOG.md",
    "src/ikigai/SPEC.md",
    "specs/agentic-markdown-system",
    "specs/period-reports-sync",
    "specs/vault-bidirectional-sync",
    ".github/wiki",
    ".github/ISSUE_TEMPLATE",
    "diagrams",
    "examples",
    "notes",
    "openwiki",
    ".codex",
    "data/test-fixtures",
    ".github/scripts/test_review.py",
    ".github/scripts/type_review.py",
    ".github/scripts/setup_hooks.py",
    ".github/workflows/openwiki-update.yml",
    ".pre-commit-config.yaml",
    "omo.json",
    ".omo-initdeep-*.json",
    "CHANGELOG.md",
    # The planning tree of the pre-ADR-037 model — the task/plan hierarchy,
    # the PAV metrics, the mesh events, the investigations. Nothing imported
    # it: the DOM is the model, and the store's SQL mirrors the DOM.
    "src/contracts/base.py",
    "src/contracts/entrega.py",
    "src/contracts/investigation.py",
    "src/contracts/meta.py",
    "src/contracts/metrics.py",
    "src/contracts/objetivo.py",
    "src/contracts/planning.py",
    "src/contracts/projeto.py",
    "src/contracts/sonho.py",
    "src/contracts/tarefa.py",
    "src/contracts/task.py",
    "src/contracts/task_change.py",
    # The classes: the ADRs of the replaced architecture, the specs of the
    # retired roadmap, and the third-party skills that shared the harness
    # with the cadences. Each exception below carves out what stays.
    "code-docs/adr/*.md",
    "docs/superpowers/specs/*.md",
    ".claude/skills/*",
)

# The exceptions to the retired classes: what the current scope rests on.
# They live inside trees that are otherwise retired, so the class needs its
# exceptions named — the same shape the ignore rules use.
RETIRED_EXCEPTIONS = (
    # The decisions the contracts rest on: the transport, the scope
    # discipline, the UEID (twice) and the pivot.
    "code-docs/adr/README.md",
    "code-docs/adr/ADR-011-ikigai-mcp-http-sse-transport.md",
    "code-docs/adr/ADR-013-canonical-scope-discipline.md",
    "code-docs/adr/ADR-014-ueid-canonical-format.md",
    "code-docs/adr/ADR-033-ueid-single-source-mandate.md",
    "code-docs/adr/ADR-037-data-layer-canonical-turn.md",
    # The websocket sync channel and the retrieval layer that feeds it.
    "code-docs/adr/ADR-039-websocket-sync-transport.md",
    # The client state: the drafts, and what is deliberately NOT here.
    "code-docs/adr/ADR-040-client-state-and-drafts.md",
    # The runtime routing, the blocking question and the panel (ADR-041).
    "code-docs/adr/ADR-041-runtime-routing-and-human-in-the-loop.md",
    # The routing table in the repository, and the harness's own gate (ADR-042).
    "code-docs/adr/ADR-042-routing-table-in-the-repository.md",
    # The write-back to the vault: the store writes the prose, and the prose
    # never rewrites the store (ADR-043).
    "code-docs/adr/ADR-043-vault-write-back.md",
    # The Mini App: the owner's panel, inside the Telegram, authenticated by
    # Telegram's own signature (ADR-044).
    "code-docs/adr/ADR-044-mini-app-panel.md",
    # The published surface: the route of the panel in the repository, and the
    # gate of its own that watches it (ADR-045).
    "code-docs/adr/ADR-045-public-route-and-its-gate.md",
    # The amendment to the write-back: the writer records what it wrote
    # (ADR-047).
    "code-docs/adr/ADR-047-write-back-records-what-it-wrote.md",
    # The pivot's own series, and the record of the cut that preceded it.
    "docs/superpowers/specs/2026-10-30-05-cut.md",
    "docs/superpowers/specs/2026-11-01-00-data-layer-series.md",
    "docs/superpowers/specs/2026-11-01-01-unified-dom.md",
    "docs/superpowers/specs/2026-11-01-02-cloud-store.md",
    "docs/superpowers/specs/2026-11-01-03-service-transport-pi.md",
    # The published projection of the cadences: a drift test holds these four
    # byte for byte against specs/harness/skills/.
    ".claude/skills/ikigai-daily",
    ".claude/skills/ikigai-weekly",
    ".claude/skills/ikigai-monthly",
    ".claude/skills/ikigai-quarterly",
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
def _is_retired(path: str, retired: str) -> bool:
    """Does `path` belong to a retired entry?

    A plain entry is a path or a tree: the path itself, or anything under it.
    An entry with a wildcard is a CLASS — the specs numbered by the retired
    roadmap are ninety-five directories, and naming each of them would be a
    list that goes stale the moment one is added.

    A class can have exceptions. The ADRs of the replaced architecture are a
    class, and the five the contracts rest on are carved out by name — the
    same shape the ignore rules use. An exception is a path or a tree: the
    path itself, or anything under it.
    """
    for exception in RETIRED_EXCEPTIONS:
        if path == exception or path.startswith(exception + "/"):
            return False
    if "*" in retired or "?" in retired:
        return fnmatch.fnmatch(path, retired)
    return path == retired or path.startswith(retired + "/")


def test_retired_runtime_is_not_published() -> None:
    tracked = _tracked(REPO_ROOT)
    offenders = [p for p in RETIRED_PATHS if any(_is_retired(f, p) for f in tracked)]
    assert not offenders, "Retired PC-only runtime is published again (ADR-037): " + ", ".join(
        offenders
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
    assert not offenders, "Published files still import the retired harness: " + ", ".join(
        offenders
    )


# ---------------------------------------------------------------------------
# 2. The canonical surface stays published
# ---------------------------------------------------------------------------
def test_canonical_surface_is_published() -> None:
    tracked = _tracked(REPO_ROOT)
    missing = [
        p for p in CANONICAL_PATHS if not any(f == p or f.startswith(p + "/") for f in tracked)
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
    assert not offenders, "Published files still import the unpublished runtime: " + ", ".join(
        offenders
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
            t == path or t == path.rstrip("/") or t.startswith(path.rstrip("/") + "/")
            for t in tracked
        )
    ]
    assert not missing, (
        "the Dockerfile copies paths that are not published — the image would "
        "fail to build, and the failure would say nothing about the cause: " + ", ".join(missing)
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
