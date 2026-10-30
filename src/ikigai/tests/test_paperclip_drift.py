"""Paperclip drift-net invariants (M169-paperclip).

Two new invariants added to the drift net:

* ``test_paperclip_graph_registered`` — ``langgraph.json`` must register
  ``ikigai_paperclip`` pointing to ``make_paperclip_graph``. Locks the
  factory signature + graph name from accidental rename.
* ``test_paperclip_agents_have_adapters`` — all 6 declared agent adapters
  (``claude``, ``pi``, ``mcode``, ``omo``, ``hermes``, ``openclaw``) must
  exist as Python files under ``paperclip/agents/``. Stubs are fine; the
  test asserts presence + parseability, not implementation completeness.

These 2 tests grow the drift count by +2 (68 → 70). Per the drift net
mechanic (each ``def test_X() -> None`` is +1), the invariant total grows
linearly with this file's functions.

Follows the static-AST-walk pattern from
``test_drift_extended_invariants.py:214-239`` rather than spawning
subprocesses — keeps the drift net fast (single pytest pass) and avoids
import-time side effects.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

# Module-level resolution — mirrors ``test_drift_extended_invariants``.
THIS_FILE = Path(__file__).resolve()
IKIGAI_TESTS = THIS_FILE.parent
IKIGAI_PKG = IKIGAI_TESTS.parent
IKIGAI_SRC = IKIGAI_PKG / "src"
REPO_ROOT = IKIGAI_PKG.parent.parent  # tests/ -> ikigai/ -> src/ -> repo/
PAPERCLIP_DIR = IKIGAI_SRC / "agents" / "paperclip"
AGENTS_DIR = PAPERCLIP_DIR / "agents"
LANGGRAPH_JSON = REPO_ROOT / "langgraph.json"

DECLARED_ADAPTERS = ("claude", "pi", "mcode", "omo", "hermes", "openclaw")


def test_paperclip_graph_registered() -> None:
    """``ikigai_paperclip`` must be in ``langgraph.json`` and point to
    ``make_paperclip_graph``.

    Drift-net guard against accidental rename / removal of the Paperclip
    graph from the LangGraph registry.
    """
    assert LANGGRAPH_JSON.exists(), f"langgraph.json missing at {LANGGRAPH_JSON}"
    data = json.loads(LANGGRAPH_JSON.read_text(encoding="utf-8"))
    graphs = data.get("graphs") or {}
    assert "ikigai_paperclip" in graphs, (
        "ikigai_paperclip missing from langgraph.json graphs — was the "
        "registration removed? Re-add per M169-paperclip."
    )
    entry = graphs["ikigai_paperclip"]
    assert entry.endswith("make_paperclip_graph"), (
        f"ikigai_paperclip must point to make_paperclip_graph factory, got: {entry}"
    )
    assert "paperclip" in entry.lower(), (
        f"ikigai_paperclip path should mention paperclip, got: {entry}"
    )


def test_paperclip_agents_have_adapters() -> None:
    """All 6 declared agent adapters must exist as parseable Python modules
    with at least one class or function.

    Drift-net guard against silent removal of a stub adapter. Stubs are
    intentional for the future-wave agents (pi/mcode/omo/hermes/openclaw);
    removing the stub file would break the contract even though the
    adapter raises NotImplementedError.
    """
    assert AGENTS_DIR.exists(), f"paperclip/agents/ missing at {AGENTS_DIR}"
    missing: list[str] = []
    empty: list[str] = []
    for name in DECLARED_ADAPTERS:
        path = AGENTS_DIR / f"{name}.py"
        if not path.exists():
            missing.append(f"{name}.py")
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            empty.append(f"{name}.py (syntax error: {exc})")
            continue
        has_def = any(
            isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.FunctionDef))
            for node in ast.walk(tree)
        )
        if not has_def:
            empty.append(f"{name}.py (no class/function)")

    assert not missing, f"missing paperclip agent adapters: {missing}"
    assert not empty, f"empty/broken paperclip agent adapters: {empty}"


def test_paperclip_router_importable() -> None:
    """``src/ikigai/src/agents/paperclip/router.py`` must exist, parse,
    and export the M174 router contract.

    Drift-net guard against accidental removal / rename of the router
    surface that the M174 auto-spawner depends on. Required exports:

    * ``AdapterHealth`` — Pydantic model of one adapter's status.
    * ``SpecContext`` — Pydantic model of the spec being routed.
    * ``RouterDecision`` — Pydantic model of the chosen adapter + reason.
    * ``pick_adapter`` — primary entry point.
    * ``AdapterUnavailableError`` — raised when zero adapters are healthy.
    * ``CostThresholdExceeded`` — raised when daily spend > threshold.

    Adding the file alone is insufficient — every named export must
    remain importable. A refactor that drops, say, ``rank_adapters`` from
    ``__all__`` (or renames ``AdapterHealth``) would break the
    auto-spawner without breaking this test, so we explicitly assert
    each name is present.
    """
    router_path = IKIGAI_SRC / "agents" / "paperclip" / "router.py"
    assert router_path.exists(), f"paperclip router.py missing at {router_path}"
    try:
        tree = ast.parse(router_path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        raise AssertionError(f"paperclip router.py has syntax error: {exc}") from exc

    # Collect every top-level binding name (classes, functions, constants).
    binding_names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            binding_names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    binding_names.add(target.id)

    # Also include names re-exported via ``__all__`` (the project-wide
    # convention — router.py uses ``__all__ = [...]`` for its surface).
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                binding_names.add(elt.value)

    required = {
        "AdapterHealth",
        "SpecContext",
        "RouterDecision",
        "pick_adapter",
        "AdapterUnavailableError",
        "CostThresholdExceeded",
    }
    missing = required - binding_names
    assert not missing, (
        f"paperclip router.py missing required exports: {sorted(missing)} — "
        f"present: {sorted(binding_names)}"
    )


def test_paperclip_spawner_script_exists() -> None:
    """``scripts/paperclip-spawner.sh`` must exist, be executable, and
    start with ``#!/usr/bin/env bash``.

    Drift-net guard against accidental removal of the M174 auto-spawner
    shell entry point. The script is the ONLY public surface between
    the ``.claude/loop/schedules.json`` schedule (300m tick) and the
    Paperclip graph — dropping it would silently kill the auto-spawner
    pipeline without raising any error in the loop.

    Three checks:

    1. **Path exists** — file is on disk at ``scripts/paperclip-spawner.sh``.
    2. **Executable bit** — ``os.access(path, os.X_OK)`` is true. On
       Windows the bit is set via ``git`` when ``core.fileMode`` is
       enabled; CI's POSIX runner respects it. A file with mode ``0644``
       (not ``0755``) would fail this guard.
    3. **Shebang line** — the file MUST start with ``#!/usr/bin/env bash``
       so ``bash scripts/paperclip-spawner.sh`` works in any subshell,
       regardless of the calling shell.
    """
    import os

    spawner_path = REPO_ROOT / "scripts" / "paperclip-spawner.sh"
    assert spawner_path.exists(), f"paperclip-spawner.sh missing at {spawner_path}"
    assert os.access(str(spawner_path), os.X_OK), (
        f"paperclip-spawner.sh at {spawner_path} is not executable "
        f"(chmod +x scripts/paperclip-spawner.sh)"
    )
    first_line = spawner_path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "#!/usr/bin/env bash", (
        f"paperclip-spawner.sh shebang must be '#!/usr/bin/env bash', got: {first_line!r}"
    )


def test_paperclip_wall_clock_gate_exists() -> None:
    """``WallClockGate`` is exported from ``policy.py`` and parses.

    Drift-net guard against accidental removal / rename of the M175
    wall-clock gate — the **second auto-throttle** in the Paperclip
    architecture (after ``CostGate`` from M173). A refactor that drops
    ``WallClockGate`` from ``policy.py`` would silently re-open the
    auto-throttle chain, allowing runaway implement tasks to keep
    burning through the agent loop without any elapsed-time guard.

    The test asserts:

    1. ``WallClockGate`` is importable from the canonical path
       (``src.ikigai.src.agents.paperclip.policy``).
    2. The default ``threshold_seconds`` matches ``DEFAULT_THRESHOLD_S``
       (3600s = 1 hour), so a builder who forgets to pass a threshold
       gets the documented default — not the previous ``CostGate``'s
       $5.00 numeric coercion or a sentinel error.
    3. The gate is constructible without explicit ``now_iso`` (the
       production path lets ``check()`` call ``datetime.now(UTC)``).
    """
    from src.ikigai.src.agents.paperclip.policy import WallClockGate

    gate = WallClockGate(task_started_at=None)
    assert gate.threshold_seconds == 3600, (
        f"expected default threshold_seconds=3600 (1h), got {gate.threshold_seconds}"
    )
    allowed, reason = gate.check()
    assert allowed is True, (
        f"expected fail-open when task_started_at is None, got: allowed={allowed} reason={reason!r}"
    )


def test_paperclip_risk_gate_exists() -> None:
    """``RiskGate`` is exported from ``policy.py`` with the correct shape.

    Drift-net guard against accidental removal / rename of the M176
    risk gate — the **third auto-throttle** and the **first fail-CLOSED
    gate** in the Paperclip architecture. A refactor that drops
    ``RiskGate`` from ``policy.py`` (or empties ``DEFAULT_RISK_KEYWORDS``
    by accident) would silently re-open the dangerous-keyword guard,
    letting ``rm -rf /`` or ``git push --force`` through the agent
    loop. This invariant is +1 (73 → 74).

    The test asserts:

    1. ``RiskGate`` is importable from the canonical path
       (``src.ikigai.src.agents.paperclip.policy``).
    2. The default ``keywords`` is a non-empty tuple/list — empty
       defaults would silently disable the gate.
    3. The gate is constructible with a clean spec text and returns
       ``allowed=True`` (sanity check on the happy path).
    """
    from src.ikigai.src.agents.paperclip.policy import RiskGate

    gate = RiskGate(text_to_check="safe text")
    allowed, reason = gate.check()
    assert allowed is True, (
        f"expected allowance on safe text, got: allowed={allowed} reason={reason!r}"
    )
    assert isinstance(gate.keywords, (tuple, list)), (
        f"expected keywords to be tuple/list, got {type(gate.keywords).__name__}"
    )
    assert len(gate.keywords) > 0, (
        f"default keywords list is empty — would silently disable the gate; got {gate.keywords!r}"
    )


def test_paperclip_worktree_path_helper_exists() -> None:
    """``_to_posix_path`` is exported from ``worktree.py`` and handles
    non-Windows gracefully.

    Drift-net guard against accidental removal of the M178
    ``_to_posix_path`` helper — the M178 fix for ``paperclip run`` on
    Windows where MSYS bash couldn't resolve backslash-separated paths.
    Without this helper, ``paperclip run --spec ...`` fails on Windows
    with ``WorktreeCreateError`` pointing at the mangled path.

    The test asserts:

    1. ``_to_posix_path`` is importable from the canonical path
       (``src.ikigai.src.agents.paperclip.nodes.worktree``).
    2. The return type is ``str`` — the helper's contract for callers
       (``subprocess.run`` argv). The exact string content is
       platform-dependent (``/tmp/test`` on Linux/macOS, ``/c/tmp/test``
       on Windows Git Bash after ``cygpath -u``), so we don't pin a
       specific value — only that *something* came back.
    """
    from src.ikigai.src.agents.paperclip.nodes.worktree import _to_posix_path

    result = _to_posix_path(Path("/tmp/test"))
    assert isinstance(result, str), (
        f"_to_posix_path must return str (subprocess argv); got {type(result).__name__}"
    )
    assert len(result) > 0, "_to_posix_path returned empty string"


def test_paperclip_persistence_module_exists() -> None:
    """``persist_run`` and ``list_recent_runs`` are importable from ``agents.paperclip.persistence``.

    Drift-net guard against accidental removal of the M183 run-state
    persistence layer. The paperclip ``run`` CLI subcommand calls
    ``persist_run`` after every invocation (success OR failure); the
    ``runs`` subcommand + ``M174 auto-spawner`` both rely on
    ``list_recent_runs`` to enumerate prior runs. Dropping the module
    silently breaks post-mortem debugging + spawner history without
    raising any error in the graph loop.

    Asserts:

    1. ``persist_run`` is importable from the canonical path
       (``src.ikigai.src.agents.paperclip.persistence``).
    2. ``list_recent_runs`` is importable from the same path.
    3. ``RunRecord`` dataclass is importable (so callers can build records).
    4. ``MAX_RUNS`` constant is positive (zero would silently disable GC).
    5. ``DEFAULT_RUNS_DIR`` is a :class:`Path` ending in ``runs``.
    """
    from src.ikigai.src.agents.paperclip.persistence import (
        DEFAULT_RUNS_DIR,
        MAX_RUNS,
        RunRecord,
        list_recent_runs,
        persist_run,
    )

    assert callable(persist_run), "persist_run must be callable"
    assert callable(list_recent_runs), "list_recent_runs must be callable"
    assert isinstance(RunRecord, type), "RunRecord must be a class"
    assert MAX_RUNS > 0, f"MAX_RUNS must be >0, got {MAX_RUNS}"
    assert isinstance(DEFAULT_RUNS_DIR, Path), (
        f"DEFAULT_RUNS_DIR must be Path, got {type(DEFAULT_RUNS_DIR).__name__}"
    )
    assert str(DEFAULT_RUNS_DIR).endswith("runs"), (
        f"DEFAULT_RUNS_DIR must end with 'runs', got {DEFAULT_RUNS_DIR}"
    )


def test_paperclip_canonical_http_adapter_exists() -> None:
    """``scripts/paperclip_heartbeat_http.py`` exists and exposes a heartbeat endpoint.

    Drift-net guard against accidental removal of the M190 canonical
    Paperclip HTTP adapter — the first concrete step of the migration
    path documented in ``paperclip-orchestrator-specs.md`` §9.3. The
    file is the load-bearing bridge between the canonical Paperclip
    platform (control plane, port 3100) and our M169 LangGraph Paperclip
    graph (employee). Without it, the canonical Paperclip can't POST
    heartbeats to us and the Phase 1 parallel run cannot start.

    The test asserts:

    1. **Path exists** — file is on disk at ``scripts/paperclip_heartbeat_http.py``.
    2. **Has a POST handler** — the substring ``POST`` must appear
       (we use stdlib ``do_POST`` per the SPEC's "stdlib only" choice).
    3. **Exposes the heartbeat route** — the substring ``/heartbeat``
       must appear (canonical Paperclip's §6.4 HTTP adapter contract).
    """
    # Repo-root-relative (not CWD-relative): CI runs pytest from
    # ``src/ikigai``, so a bare ``Path("scripts/...")`` would resolve
    # against the wrong root. Sibling tests in this file use REPO_ROOT.
    script = REPO_ROOT / "scripts" / "paperclip_heartbeat_http.py"
    assert script.exists(), f"paperclip_heartbeat_http.py missing at {script}"
    text = script.read_text(encoding="utf-8")
    assert "POST" in text, (
        "scripts/paperclip_heartbeat_http.py must declare a POST handler "
        "(stdlib BaseHTTPRequestHandler.do_POST)"
    )
    assert "/heartbeat" in text, (
        "scripts/paperclip_heartbeat_http.py must expose a /heartbeat route "
        "per paperclip-orchestrator-specs.md §6.4"
    )


def test_paperclip_hil_apply_user_resolution_node_exists() -> None:
    """``hil_apply_user_resolution_node`` is importable from
    ``src.ikigai.src.agents.paperclip.nodes.hil_pause`` and is callable.

    Drift-net guard against accidental removal of the M180 audit-trail node.
    Without this invariant, a refactor could silently drop the
    ``hil_apply_user_resolution`` step from the HIL pipeline and resume
    audit counts would never get bumped — but unit tests for the node
    itself could still pass if they were also deleted in the same
    refactor. The drift test guards against the deletion-by-omission
    class of bug.

    The test asserts:

    1. The node is importable from the canonical path.
    2. The node is callable (so ``graph.py`` can wrap it with ``_safe_node``).
    3. The node accepts a partial ``PaperclipStateDict`` (does NOT require
       ``hil_resume_count`` to be pre-set) — guards against an off-by-one
       regression where the node assumes ``hil_resume_count`` exists and
       crashes with ``TypeError`` on first resume.
    """
    from src.ikigai.src.agents.paperclip.nodes.hil_pause import hil_apply_user_resolution_node

    assert callable(hil_apply_user_resolution_node), (
        "hil_apply_user_resolution_node must be callable (graph._safe_node wraps it)"
    )

    # Smoke: invoke with a partial state (no hil_resume_count set) — must
    # not raise. This locks in the "missing -> start at 0" behavior so a
    # future refactor that requires hil_resume_count to be pre-set would
    # break this drift test (correct behavior: bump on every call).
    from src.ikigai.src.agents.paperclip.state import PaperclipStateDict

    state: PaperclipStateDict = {
        "task_id": "drift-smoke",
        "spec_text": "any",
        "user_resolution": {"answer": "ok", "rewritten_spec": ""},
        "gap_iteration": 1,
    }
    result = hil_apply_user_resolution_node(state)
    assert result["hil_resume_count"] == 1
    assert result["last_step"] == "hil_apply_user_resolution"
    assert isinstance(result["hil_last_resume_at"], str)
    assert result["hil_last_resume_at"]  # non-empty ISO timestamp


def test_paperclip_stacks_comparison_exists() -> None:
    """The 8-stacks comparison matrix is documented (M193).

    Drift-net guard against accidental deletion of the side-by-side
    comparison between life-oss loop engineering and the 8 families
    documented in ``meta-analysis-loop-engineering-stacks.md``. The
    matrix is the canonical answer to "why didn't we just adopt Family
    N?" — losing the document would lose the rationale when a future
    contributor asks.

    The test asserts:

    1. The SPEC file exists at ``specs/M193-paperclip-stacks-comparison/SPEC.md``.
    2. All 8 family names appear in the body (Ralph, Karpathy,
       TheBotCompany, AOrchestra, LangChain, Osmani, Gas Town, SDD).
    3. The string ``life-oss`` appears at least once (the
       comparison's "where do we sit" column).
    4. The YAML frontmatter declares ``status: DONE`` — the SPEC is
       documentation, not a stub.
    """
    # Repo-root-relative (not CWD-relative) — see the note in
    # ``test_paperclip_canonical_http_adapter_exists``.
    spec = REPO_ROOT / "specs" / "M193-paperclip-stacks-comparison" / "SPEC.md"
    assert spec.exists(), f"M193 SPEC missing at {spec}"
    text = spec.read_text(encoding="utf-8")

    families = [
        "Ralph",
        "Karpathy",
        "TheBotCompany",
        "AOrchestra",
        "LangChain",
        "Osmani",
        "Gas Town",
        "SDD",
    ]
    for family in families:
        assert family in text, f"M193 must reference family: {family}"

    assert "life-oss" in text, "M193 must reference life-oss"
    assert "status: DONE" in text, "M193 SPEC frontmatter must declare status: DONE"


def test_paperclip_dynamic_graph_registered() -> None:
    """``ikigai_dynamic`` is in ``langgraph.json`` and points to the
    ``make_dynamic_graph`` factory.

    Drift-net guard against accidental rename / removal of the M191
    Paperclip Dynamic graph from the LangGraph registry. The dynamic
    graph is the **second** Paperclip graph (alongside
    ``ikigai_paperclip``) and is registered as the 5th graph in
    ``langgraph.json``.

    This invariant is +1. The test asserts:

    1. ``langgraph.json`` exists at the repo root.
    2. ``ikigai_dynamic`` is registered under the ``graphs`` dict.
    3. The factory path ends with ``make_dynamic_graph`` (locks the
       factory symbol name).
    4. The factory path mentions ``paperclip_dynamic`` (locks the
       package location).
    """
    assert LANGGRAPH_JSON.exists(), f"langgraph.json missing at {LANGGRAPH_JSON}"
    data = json.loads(LANGGRAPH_JSON.read_text(encoding="utf-8"))
    graphs = data.get("graphs") or {}
    assert "ikigai_dynamic" in graphs, (
        "ikigai_dynamic missing from langgraph.json graphs — was the "
        "M191 Paperclip Dynamic registration removed? Re-add per "
        "specs/M191-paperclip-dynamic-workflows/SPEC.md."
    )
    entry = graphs["ikigai_dynamic"]
    assert entry.endswith("make_dynamic_graph"), (
        f"ikigai_dynamic must point to make_dynamic_graph factory, got: {entry}"
    )
    assert "paperclip_dynamic" in entry.lower(), (
        f"ikigai_dynamic path should mention paperclip_dynamic, got: {entry}"
    )


def test_paperclip_adr_036_exists() -> None:
    """ADR-036 documents life-oss's adoption of the LangChain 4 nested loops framework.

    Drift-net guard against silent removal / rename of the Paperclip
    framework-codification ADR. The file documents which cron / daemon /
    gate maps to which of the 4 loops (Agent / Verification / Event-driven /
    Hill-climbing) + the 5 risks matrix from Ronacher + Osmani. Removing
    or renaming the file would silently invalidate the framework-mapping
    assertions made throughout M169 / M173 / M175 / M176 / M174 / M183
    spec docs without breaking any structural test.

    This invariant is +1 to the drift net (was 12 in test_paperclip_drift.py
    before M192; becomes 13 after). Per the M192 acceptance criteria:

    1. The ADR exists at the canonical path. The M192 spec originally
       requested ``ADR-026`` but that number was already ACCEPTED (the
       Sub-Agent Dispatch Protocol, 2026-09-05). Per
       ``code-docs/adr/README.md §Maintenance`` numbering rule, the next
       available slot was ``ADR-036`` — the file is authored there.
    2. The body MUST reference each of the 4 loops by their canonical
       name (``Loop 1`` ... ``Loop 4``) and by their descriptive role
       (``Agent``, ``Verification``, ``Event-driven``, ``Hill-climbing``).
       If the framework mapping section is removed without an ADR
       amendment, CI fails.
    3. The body MUST reference each of the 5 risks matrix risks
       (``cognitive surrender``, ``loop brittleness``, ``HITL fatigue``,
       ``runaway cost``). ``verifier mis-grades`` (#3) and a 5th risk
       aside from ``runaway cost`` are also present but the spec pinned
       these 4 as the minimum drift surface; the other two are documented
       in the ADR body but not asserted (kept lax to allow future
       rephrasing of the matrix headings).
    """
    # Repo-root-relative (not CWD-relative) — see the note in
    # ``test_paperclip_canonical_http_adapter_exists``.
    adr = REPO_ROOT / "code-docs" / "adr" / "ADR-036-paperclip-four-nested-loops.md"
    assert adr.exists(), (
        f"ADR-036 must exist at {adr} — was it removed? Per M192 (2026-10-12) "
        "this ADR documents life-oss's adoption of the LangChain 4 nested "
        "loops framework."
    )
    text = adr.read_text(encoding="utf-8")
    # Must reference the 4 loops by name + by descriptive role
    for loop_name in [
        "Loop 1",
        "Loop 2",
        "Loop 3",
        "Loop 4",
        "Agent",
        "Verification",
        "Event-driven",
        "Hill-climbing",
    ]:
        assert loop_name in text, f"ADR-036 must reference {loop_name}"
    # Must reference the 5 risks (4 anchored as minimum drift surface)
    for risk in [
        "cognitive surrender",
        "loop brittleness",
        "HITL fatigue",
        "runaway cost",
    ]:
        assert risk.lower() in text.lower(), f"ADR-036 must reference {risk}"
