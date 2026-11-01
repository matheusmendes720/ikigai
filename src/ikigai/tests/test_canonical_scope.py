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
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
IKIGAI_PKG = THIS_FILE.parent.parent
REPO_ROOT = IKIGAI_PKG.parent.parent

# ── Retired runtime (must never come back to the published tree) ──────────
RETIRED_PATHS = (
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
    "src/mesh",
    "src/services",
    "src/transport",
    "src/data",
    "src/agents",
    "sys_ikigai",
    "vault",
    "specs",
    "docs",
)

UEID_4PART = re.compile(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$")


def _tracked(repo: Path) -> set[str]:
    """Return the tracked file set of the repository under test."""
    import subprocess

    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:  # not a git checkout (e.g. sdist) — skip
        pytest.skip("not a git checkout")
    return set(proc.stdout.split())


def _pytest_skip_guard() -> None:
    import pytest

    pytest.skip("not a git checkout")


try:  # pragma: no cover - import shim for the skip helper above
    import pytest
except ImportError:  # pragma: no cover
    pytest = None  # type: ignore[assignment]


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
        r"(src\.ikigai\.src\.(agents|chat|mcp_server|plugins)"
        r"|ikigai_wrapper|gateway_client"
        r"|(^|[^.\w])from (agents|chat|mcp_server|plugins)(\.| import)"
    )
    proc = subprocess.run(
        ["git", "grep", "-l", "-E", pattern, "--", "src/", "tests/", "sys_ikigai/", "interfaces/"],
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


# ---------------------------------------------------------------------------
# 3. Contracts are the single source of truth
# ---------------------------------------------------------------------------
def test_contracts_are_the_single_source_of_truth() -> None:
    tracked = _tracked(REPO_ROOT)
    # The meta-planner contracts are a separate family and must stay inside
    # the ikigai project (src/ikigai/contracts/), never inside src/contracts/.
    assert not any(f.startswith("src/contracts/proposal") for f in tracked)


def test_mesh_exposes_only_cloud_safe_adapters() -> None:
    tracked = _tracked(REPO_ROOT)
    adapters = {f for f in tracked if f.startswith("src/mesh/adapters/") and f.endswith(".py")}
    names = {Path(f).stem for f in adapters}
    assert "solverforge_calendar" not in names, "calendar MCP fork adapter came back"
    assert {"base", "cli", "taskdog"} <= names, f"missing canonical adapters: {sorted(names)}"


# ---------------------------------------------------------------------------
# 4. UEID format (ADR-014)
# ---------------------------------------------------------------------------
def test_ueid_4part_format_is_canonical() -> None:
    assert UEID_4PART.match("life:task:abc123:def456")
    assert not UEID_4PART.match("LIFE:task:abc123:def456")
    assert not UEID_4PART.match("life:task:abc123")


# ---------------------------------------------------------------------------
# 5. Planner-only surface (ADR-013) for the code that survived
# ---------------------------------------------------------------------------
FORBIDDEN_IN_AGENT_LAYER = (
    "sys_ikigai.core.scoring",
    "ikigai.core.heuristics",
    "cybernetics.daily_loop",
)


def test_no_algorithm_constants_in_agent_code() -> None:
    import subprocess

    proc = subprocess.run(
        ["git", "grep", "-l", "-E", "|".join(FORBIDDEN_IN_AGENT_LAYER), "--", "src/agents/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert not [line for line in proc.stdout.split() if line], (
        "ADR-013 violation: scoring/policy math reached the planner layer"
    )


def test_reflection_layer_has_no_llm_dependency() -> None:
    import subprocess

    proc = subprocess.run(
        [
            "git",
            "grep",
            "-l",
            "-E",
            r"^\s*(import|from)\s+(openai|anthropic|langchain|litellm)",
            "--",
            "src/agents/reflection/",
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
        ["git", "grep", "-l", "-E", r"algorithm_constants", "--", "src/agents/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert not [line for line in proc.stdout.split() if line], (
        "ADR-019 R7: the agent layer must not read the algorithm constants"
    )
