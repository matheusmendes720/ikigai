"""Drift invariants over the canonical (ADR-037) published surface.

2026-11-02 — rewritten as part of the ADR-037 cut.

The previous version of this file guarded the *pre-ADR-037* runtime: the
kill-switch constants in ``sys_ikigai/security/algorithm_constants.json``, the
``vault_write`` wrapper as the single enforcement point, and the transition
validator traversal. Those subjects left the published tree together with the
rest of the pre-ADR-037 system, so guarding them here guarded nothing.

Drift tests are append-only in spirit: the invariant is not dropped, it is
**translated** to the surface that replaced it. Each invariant below is the
canonical form of a retired one, and the mapping is stated in its docstring.

Run::

    pytest src/ikigai/tests/test_drift_invariants.py -v
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent.parent.parent

# The published transport surface. ADR-037 D6: the old custom MCP gateway
# (22 tools, 9 of them pointing at tools that did not exist) is gone; the
# published transport is fastmcp over HTTP with this exact tool set.
CANONICAL_TOOLS: frozenset[str] = frozenset(
    {
        "search_artifacts",
        "get_artifact",
        "upsert_artifact",
        "delete_artifact",
        "list_relations",
        "embed_text",
    }
)

# The published source surface, for the layering invariants.
PUBLISHED_ROOTS: tuple[str, ...] = (
    "src/contracts",
    "src/data",
    "src/services",
    "src/transport",
)


def _published_files() -> list[str]:
    """Tracked files under the published source roots."""
    proc = subprocess.run(
        ["git", "ls-files", "--", *PUBLISHED_ROOTS],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return [line for line in proc.stdout.split() if line]


def _git_grep(pattern: str, *paths: str) -> list[str]:
    proc = subprocess.run(
        ["git", "grep", "-l", "-E", pattern, "--", *paths],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return [line for line in proc.stdout.split() if line]


def _decorator_name(node: ast.expr) -> str:
    """The trailing name of a decorator, whether it is Name, Attribute or Call."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


# ---------------------------------------------------------------------------
# 1. The transport surface is exactly the canonical tool set
# ---------------------------------------------------------------------------
# Translation of: "the MCP surface is a fixed, contract-bound set" (the old
# gateway's 22 tools were the thing that rotted — 9 of them pointed at tools
# that did not exist).
def test_transport_exposes_exactly_the_canonical_tools() -> None:
    source = (REPO_ROOT / "src" / "transport" / "mcp_server.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    tools: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if any("tool" in _decorator_name(dec) for dec in node.decorator_list):
            tools.add(node.name)

    assert tools == set(CANONICAL_TOOLS), (
        "the published transport must expose exactly the canonical tool set. "
        f"extra={sorted(tools - set(CANONICAL_TOOLS))} "
        f"missing={sorted(set(CANONICAL_TOOLS) - tools)}"
    )


# ---------------------------------------------------------------------------
# 2. The layering holds: transport -> services -> data
# ---------------------------------------------------------------------------
# Translation of: "vault_write is the SOLE writer" (ADR-012). The canonical
# form is that no surface talks to the store directly — the transport speaks
# to the services, and the services speak to the data client.
def test_transport_does_not_talk_to_the_data_client_directly() -> None:
    source = (REPO_ROOT / "src" / "transport" / "mcp_server.py").read_text(encoding="utf-8")
    assert "src.data" not in source, (
        "the transport must go through src/services/, not straight to the data "
        "client — one writer per store (ADR-037 D5)"
    )
    assert "src.services" in source, (
        "the transport must call the services layer (ADR-037 D6)"
    )


def test_only_the_service_layer_touches_the_data_client() -> None:
    """Only the data client and the service layer may reach the store.

    Translation of: "vault_write is the sole writer" (ADR-012) and ADR-037 D5
    ("um writer por store"). The published store has exactly one writer — the
    service layer — and the transport may not bypass it.
    """
    offenders = [
        path
        for path in _published_files()
        if path.endswith(".py")
        and not path.startswith(("src/data/", "src/services/"))
        and "src.data" in (REPO_ROOT / path).read_text(encoding="utf-8")
    ]
    assert not offenders, (
        "only src/data/ and src/services/ may reach the store — one writer per "
        f"store (ADR-037 D5). Offenders: {offenders}"
    )


# ---------------------------------------------------------------------------
# 3. The UEID pattern has a single source
# ---------------------------------------------------------------------------
# Translation of: the UEID 4-vs-5-part drift (`ueid-5part-canonical-decision`
# / `ueid-4part-canonical-decision`). Three regexes used to live in the repo;
# now the published surface has exactly one.
def test_ueid_pattern_has_a_single_source() -> None:
    """The pattern must be DEFINED in exactly one published module.

    The grep looks for the definition, not for the name: the SQL CHECK in
    `0001_init.sql` copies the pattern verbatim — by design, and guarded by
    `test_uid_check_matches_contract_pattern` — and its commentary names the
    Python constant it was copied from. A grep that counted names would
    punish the documentation of the invariant.
    """
    offenders = _git_grep(r"^_UEID_PATTERN\s*=", *PUBLISHED_ROOTS)
    assert offenders == ["src/contracts/common.py"], (
        "the UEID pattern must be defined in exactly one published module "
        f"(src/contracts/common.py). Found: {offenders}"
    )


# ---------------------------------------------------------------------------
# 4. Every write is versioned and idempotent
# ---------------------------------------------------------------------------
# Translation of: "vault_write is append-only and audited". The canonical
# form is ADR-037 D5 — `revision` + `idempotency_key`, conflict = 409, never
# last-write-wins.
def test_every_write_carries_a_revision_and_an_idempotency_key() -> None:
    from src.contracts.dom import WriteRequest

    fields = WriteRequest.model_fields
    for required in ("artifact", "idempotency_key", "client_id"):
        assert required in fields, f"WriteRequest is missing `{required}`"
        assert fields[required].is_required(), (
            f"WriteRequest.{required} must be required — a write without it "
            "cannot be versioned or de-duplicated"
        )
    assert "expected_revision" in fields, (
        "WriteRequest must carry `expected_revision` — a stale revision is a "
        "409, never a silent overwrite (ADR-037 D5)"
    )


# ---------------------------------------------------------------------------
# 5. The cut is a PUBLICATION cut: nothing retired ships, nothing retired dies
# ---------------------------------------------------------------------------
def test_the_retired_runtime_is_neither_published_nor_deleted() -> None:
    """The pre-ADR-037 system leaves the branch but stays on the owner's disk.

    ADR-037 §"publicação independente": the PC-only surfaces stay out of the
    remote repository. They are gitignored, not deleted — the owner still runs
    them locally, and the git history keeps them.
    """
    retired = ("sys_ikigai", "src/mesh", "interfaces", "vibe-ops")
    tracked = set(subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split())
    published = [
        path for path in tracked if path.split("/")[0] in retired or path.startswith("src/mesh/")
    ]
    assert not published, (
        "the retired runtime is published again: " + ", ".join(sorted(published)[:10])
    )

    # The corpus lives on the OWNER's disk, and the owner's disk is not the
    # CI runner's disk: a fresh clone has none of these trees, by design —
    # that is what "unpublished, not deleted" means for anybody else.
    #
    # What must never happen is a HALF-deleted corpus: three trees present
    # and one gone is what a bad `rm` leaves behind, and the branch cannot
    # be re-cloned to recover it. So the check is on the PARTIAL state, and
    # it keeps its teeth exactly where it matters — on the owner's machine.
    present = [tree for tree in retired if (REPO_ROOT / tree).exists()]
    if present and len(present) != len(retired):
        missing = [tree for tree in retired if tree not in present]
        raise AssertionError(
            "the retired runtime must stay on the owner's disk (gitignored, "
            f"not deleted). Missing: {missing}"
        )


def test_the_legacy_suite_is_excluded_from_collection() -> None:
    """The retired suite is excluded from collection, not deleted.

    `conftest.py` carries the `collect_ignore` list. If it regresses, the
    local suite starts collecting modules that import code that is no longer
    published — and the failure looks like an import error, not like a scope
    decision.
    """
    source = (THIS_FILE.parent / "conftest.py").read_text(encoding="utf-8")
    assert "collect_ignore" in source, (
        "conftest.py must keep excluding the retired test modules from collection"
    )
    assert "LEGACY_TEST_MODULES" in source, (
        "conftest.py must declare the retired modules explicitly — an implicit "
        "exclusion is one that rots"
    )


# ---------------------------------------------------------------------------
# 6. The harness's copy of the skills is the published projection
# ---------------------------------------------------------------------------
# The projection in `specs/harness/skills/` is the source; the copy under
# `.pi/skills/` is what the harness loads. A copy that drifted is an agent
# running a routine the repository no longer describes — and the drift is
# invisible, because both files look right on their own.
#
# The check is local: the copy is runtime state and does not ship in the
# branch, so a checkout without it has nothing to compare.
def test_the_installed_skills_match_the_projection() -> None:
    projection = REPO_ROOT / "specs" / "harness" / "skills"
    installed = REPO_ROOT / ".pi" / "skills"
    if not installed.exists():
        pytest.skip("the harness's skills are not installed in this checkout")

    def _skills(root: Path) -> dict[str, str]:
        return {
            path.parent.name: path.read_text(encoding="utf-8").replace("\r\n", "\n")
            for path in sorted(root.glob("*/SKILL.md"))
        }

    expected = _skills(projection)
    actual = _skills(installed)

    assert set(actual) == set(expected), (
        "the harness's copy of the skills is not the projection: "
        f"only-installed={sorted(set(actual) - set(expected))} "
        f"only-projected={sorted(set(expected) - set(actual))}"
    )
    drifted = sorted(name for name in expected if actual[name] != expected[name])
    assert not drifted, (
        "the harness's copy of these skills drifted from the projection: "
        + ", ".join(drifted)
    )


# ---------------------------------------------------------------------------
# 7. The relation direction is stated, everywhere the agent reads it
# ---------------------------------------------------------------------------
#
# `PARENT_OF` has a direction, and the canonical contract says which: the edge
# starts at the artifact being written (store-write, step 4) and the plan's
# write carries `PARENT_OF` to the phases (quarterly-plan, step 4) — the
# PARENT is the source.
#
# MEASURED on the box (2026-11-09), on the edges the `quarterly-plan` wrote:
# 13 of 13 `parent_of` edges carried the CHILD as the source — the hierarchy
# upside down — while 9 of 9 `derives_from` edges carried the derived artifact
# as the source, which is the right way round. Two sentences a step apart said
# "the source is the artifact being written" and "PARENT_OF to the phases", and
# the agent read the second as "the child points at its parent". The relation
# is append-only, so the thirteen edges stay in the graph.
#
# The repair is prose: ONE sentence that admits a single reading, in the
# canonical contract and in every copy the agent loads. This holds it there.
RELATION_DIRECTION_PHRASE = "the direction of an edge is the direction of its name"


def test_the_relation_direction_is_stated_where_the_agent_reads_it() -> None:
    """`PARENT_OF` runs from the parent to the child, and every copy says so.

    The canonical contract (SKILL-SPECS.md) wins over the projection
    (router.md §1), so the sentence has to be in BOTH — and in the projection
    of each routine that writes edges, because the agent loads a routine's
    skill and not the whole contract.

    Falsification: remove the sentence from any of the three files and this
    test fails.
    """
    sources = {
        "specs/harness/SKILL-SPECS.md": "the canonical contract",
        "specs/harness/skills/store-write/SKILL.md": "the write projection",
        "specs/harness/skills/quarterly-plan/SKILL.md": "the quarterly projection",
    }
    missing: list[str] = []
    for relative, what in sources.items():
        path = REPO_ROOT / relative
        if not path.exists():
            missing.append(f"{relative} (missing)")
            continue
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").lower()
        if RELATION_DIRECTION_PHRASE not in text:
            missing.append(f"{relative} ({what})")

    assert not missing, (
        "the direction of the relations is not stated in: " + ", ".join(missing)
    )
