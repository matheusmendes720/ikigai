"""``implement`` node — invoke the chosen AgentAdapter in the worktree.

MVP picks the Claude adapter by default (the only real one). Future waves
will route based on cost / availability — for now the routing decision is
hardcoded so the smoke test can deterministically mock it.

The node:
1. Builds the prompt from the resolved spec + the HIL diff context.
2. Calls ``ClaudeAdapter.run(prompt, worktree_path)``.
3. Optionally runs ``pytest`` in the worktree (best-effort — failures
   are logged but not fatal; the implement loop catches them and
   re-invokes the agent up to MAX_IMPLEMENT_ITERS).
4. Returns ``success`` flag for the routing function to decide.

The test step is best-effort because MVP doesn't enforce a test suite;
the loop just gives the agent a chance to self-correct via the test
output (which lands in ``test_output`` for debugging).

M173-paperclip-cost-gate: before invoking the agent, the node consults
:class:`~src.ikigai.src.agents.paperclip.policy.CostGate`. If today's
spend exceeds the configured USD threshold, the agent is NOT invoked
and the node returns ``error_type="CostGateExceeded"`` with the gate's
reason. The graph routes this to a HIL pause (deferred to a future
wave) or surfaces it to the operator. The gate is fail-open by design
(see ``policy.py``); a missing or malformed ``data/cost-today.json``
does NOT block the graph.
"""

from __future__ import annotations

import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.ikigai.src.agents.paperclip.policy import CostGate, RiskGate, WallClockGate
from src.ikigai.src.agents.paperclip.state import PaperclipStateDict

log = logging.getLogger(__name__)

MAX_IMPLEMENT_ITERS = 3


def _default_adapter() -> Any:
    from src.ikigai.src.agents.paperclip.agents.claude import ClaudeAdapter

    return ClaudeAdapter()


def _run_tests(worktree: Path) -> tuple[bool, str]:
    """Best-effort test runner. Returns (ok, tail_output).

    Looks for ``pytest.ini`` or ``pyproject.toml`` with ``[tool.pytest]``;
    if neither, treats the worktree as test-less and returns (True, "").
    """
    if not (worktree / "pytest.ini").exists() and not (worktree / "pyproject.toml").exists():
        return True, "(no pytest config — skipping tests)"
    try:
        proc = subprocess.run(
            ["uv", "run", "pytest", "-x", "--tb=short", "-q"],
            cwd=str(worktree),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, "pytest timeout after 120s"
    except FileNotFoundError:
        return False, "uv not on PATH — cannot run pytest"
    tail = (proc.stdout + proc.stderr)[-2000:]
    return proc.returncode == 0, tail


def implement_node(
    state: PaperclipStateDict,
    *,
    adapter: Any = None,
) -> dict[str, object]:
    """Invoke the agent adapter in the worktree; run tests; report success.

    ``adapter`` is injectable for tests (defaults to ``ClaudeAdapter()``).
    """
    if adapter is None:
        adapter = _default_adapter()

    worktree_str = state.get("worktree_path")
    if not worktree_str:
        return {
            "originating_node": "implement",
            "error_type": "WorktreeMissing",
            "error_message": "worktree_path missing — worktree_create must run first",
            "last_step": "implement",
        }
    worktree = Path(worktree_str)
    if not worktree.exists():
        return {
            "originating_node": "implement",
            "error_type": "WorktreeMissing",
            "error_message": f"worktree {worktree} does not exist",
            "last_step": "implement",
        }

    iteration = int(state.get("implement_iteration") or 0)
    if iteration >= MAX_IMPLEMENT_ITERS:
        return {
            "originating_node": "implement",
            "error_type": "ImplementMaxIters",
            "error_message": f"implement failed after {MAX_IMPLEMENT_ITERS} iterations",
            "implement_iteration": iteration,
            "last_step": "implement",
        }

    # M173-paperclip-cost-gate: consult the daily-spend gate BEFORE invoking
    # the agent. Fail-open semantics in ``CostGate.check()`` ensure a missing
    # or malformed ``data/cost-today.json`` does not break the graph; only
    # an explicit over-threshold reading blocks the call.
    cost_gate = CostGate()
    cost_allowed, cost_reason = cost_gate.check()
    if not cost_allowed:
        log.warning("paperclip implement: cost gate closed — %s", cost_reason)
        return {
            "originating_node": "implement",
            "error_type": "CostGateExceeded",
            "error_message": cost_reason,
            "implement_iteration": iteration,
            "last_step": "implement",
        }

    # M175-paperclip-wall-clock-gate: consult the elapsed-time gate AFTER the
    # cost gate but BEFORE invoking the agent. ``task_started_at`` is set by
    # ``read_spec_node`` on first invocation; if missing (older clients /
    # replayed checkpoints), the gate is fail-open (allowed=True) so the
    # graph does not break. ``datetime.now(timezone.utc).isoformat()`` is
    # used instead of ``time.gmtime()`` because we want sub-second precision
    # and a clean ISO 8601 string that round-trips through ``fromisoformat``.
    started_at = state.get("task_started_at")
    wall_gate = WallClockGate(
        task_started_at=started_at,
        now_iso=datetime.now(UTC).isoformat(),
    )
    wall_ok, wall_reason = wall_gate.check()
    if not wall_ok:
        log.warning("paperclip implement: wall-clock gate closed — %s", wall_reason)
        return {
            "originating_node": "implement",
            "error_type": "WallClockGateExceeded",
            "error_message": wall_reason,
            "implement_iteration": iteration,
            "last_step": "implement",
        }

    # M176-paperclip-risk-gate: scan the spec + prompt concatenation for
    # dangerous keywords (rm -rf, git push --force, .env, api_key=, etc.).
    # Unlike M173/M175 which fail-OPEN, the risk gate fails-CLOSED — any
    # match refuses the call. ``error_type="RiskGateExceeded"`` so the
    # operator (or future HIL pause) can route to a "rewrite spec" path.
    spec_text = state.get("spec_text") or ""
    prompt_preview = (
        f"You are working inside an isolated git worktree at {worktree}.\n"
        "Implement the following spec exactly. After writing code, run the "
        "test suite (uv run pytest) and ensure it passes before exiting."
    )
    risk_gate = RiskGate(
        text_to_check=(spec_text + "\n" + prompt_preview),
    )
    risk_ok, risk_reason = risk_gate.check()
    if not risk_ok:
        log.warning("paperclip implement: risk gate closed — %s", risk_reason)
        return {
            "originating_node": "implement",
            "error_type": "RiskGateExceeded",
            "error_message": risk_reason,
            "implement_iteration": iteration,
            "last_step": "implement",
        }

    prompt = (
        f"You are working inside an isolated git worktree at {worktree}.\n"
        "Implement the following spec exactly. After writing code, run the "
        "test suite (uv run pytest) and ensure it passes before exiting.\n\n"
        "SPEC:\n"
        f"{spec_text}\n\n"
        "Reply with a one-paragraph summary of changes you made."
    )

    try:
        result = adapter.run(prompt, worktree)
    except NotImplementedError as exc:
        return {
            "originating_node": "implement",
            "error_type": "AdapterUnavailable",
            "error_message": str(exc),
            "implement_iteration": iteration + 1,
            "last_step": "implement",
        }

    if not result.success:
        return {
            "originating_node": "implement",
            "error_type": "AdapterFailed",
            "error_message": result.error or "agent returned failure",
            "implement_iteration": iteration + 1,
            "last_step": "implement",
            "test_output": result.output[-2000:] if result.output else "",
        }

    tests_ok, test_tail = _run_tests(worktree)
    log.info(
        "paperclip implement: iter=%d adapter_ok=True tests_ok=%s duration=%.1fs",
        iteration + 1,
        tests_ok,
        result.duration_s,
    )
    return {
        "implement_iteration": iteration + 1,
        "test_output": test_tail,
        "tests_ok": tests_ok,
        # Routing: if tests fail we loop back to implement (re-invoke with
        # test_output as additional prompt context); if pass or no tests
        # configured, we proceed to commit.
        "last_step": "implement",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"paperclip: implement iter={iteration + 1} adapter_ok=True tests_ok={tests_ok}"
                ),
            }
        ],
    }
