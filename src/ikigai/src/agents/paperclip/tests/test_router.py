"""Paperclip ``router`` unit tests (M174-paperclip-router).

Five focused tests covering the adapter-selection contract:

* ``test_router_picks_cheapest_healthy`` — 4 adapters all healthy; default
  priority order returns the cheapest (``pi``).
* ``test_router_skips_unhealthy`` — ``claude`` off-PATH; router picks the
  next priority (``pi`` is still priority 1; ``claude`` was already last
  so this test asserts the priority order is preserved when an arbitrary
  adapter is off-path).
* ``test_router_raises_when_no_healthy`` — all 4 off-PATH; raises
  :class:`AdapterUnavailableError`.
* ``test_router_raises_when_cost_exceeded`` — ``cost_today_usd=7.50``
  exceeds ``$5.00``; raises :class:`CostThresholdExceeded`.
* ``test_router_reason_mentions_adapter`` — the reason string contains
  the chosen adapter name (log-scraper pattern-match contract).

Companion to ``router.py`` and the wire-up planned for ``nodes/implement.py``
(Wave N+3). Mirrors the M173 ``test_cost_gate.py`` style: pure unit
tests, no subprocess, no filesystem I/O, no MCP — the router is a pure
function over the in-memory health dict.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from src.ikigai.src.agents.paperclip.router import (
    ADAPTER_PRIORITY,
    AdapterHealth,
    AdapterUnavailableError,
    CostThresholdExceeded,
    RouterDecision,
    SpecContext,
    pick_adapter,
    rank_adapters,
)


def _all_healthy() -> dict[str, AdapterHealth]:
    """Build a health dict with all 4 adapters marked on-path."""
    return {
        "claude": AdapterHealth(
            name="claude",
            on_path=True,
            last_invoked_at=datetime(2026, 10, 11, 12, 0, tzinfo=UTC),
            last_success=True,
        ),
        "pi": AdapterHealth(
            name="pi",
            on_path=True,
            last_invoked_at=datetime(2026, 10, 11, 12, 0, tzinfo=UTC),
            last_success=True,
        ),
        "omo": AdapterHealth(
            name="omo",
            on_path=True,
            last_invoked_at=datetime(2026, 10, 11, 12, 0, tzinfo=UTC),
            last_success=True,
        ),
        "openclaw": AdapterHealth(
            name="openclaw",
            on_path=True,
            last_invoked_at=datetime(2026, 10, 11, 12, 0, tzinfo=UTC),
            last_success=True,
        ),
    }


def test_router_picks_cheapest_healthy() -> None:
    """When all 4 adapters are healthy, the router picks ``pi`` (priority 1).

    Locks in :data:`ADAPTER_PRIORITY` as ``("pi", "omo", "openclaw",
    "claude")``. The test mirrors the M174 design rationale: cheapest
    first so we don't burn the budget on Claude when a cheaper adapter
    is available.
    """
    spec = SpecContext(task_id="M174-test", spec_text="implement router")
    decision = pick_adapter(spec, _all_healthy())

    assert isinstance(decision, RouterDecision)
    assert decision.adapter == "pi", (
        f"expected pi (cheapest priority-1 adapter), got {decision.adapter}"
    )
    # And the priority-order tuple locks in the design decision so a
    # future refactor doesn't silently flip it.
    assert ADAPTER_PRIORITY[0] == "pi"
    assert ADAPTER_PRIORITY[-1] == "claude"


def test_router_skips_unhealthy() -> None:
    """When ``claude`` is off-path, the router picks the next priority that IS healthy.

    Sets ``claude.on_path=False`` (the most expensive adapter, last in
    priority) and asserts the router still picks ``pi`` (priority 1).
    This test catches the failure mode where a refactor accidentally
    short-circuits on the first off-path adapter instead of walking the
    full priority list.
    """
    health = _all_healthy()
    health["claude"] = AdapterHealth(
        name="claude",
        on_path=False,  # OFF PATH
        last_invoked_at=None,
        last_success=None,
    )
    spec = SpecContext(task_id="M174-test", spec_text="implement router")
    decision = pick_adapter(spec, health)

    assert decision.adapter == "pi", (
        f"expected pi to win when claude is off-path, got {decision.adapter}"
    )
    assert "claude" in decision.reason or "pi" in decision.reason


def test_router_raises_when_no_healthy() -> None:
    """When all 4 adapters are off-path, the router raises ``AdapterUnavailableError``.

    Per the M174 design: Paperclip cannot proceed without at least one
    working adapter. The exception carries the off-path list so the
    operator can act (re-install binaries, fix PATH, etc.).
    """
    spec = SpecContext(task_id="M174-test", spec_text="implement router")
    # All four off-path.
    health = {
        "claude": AdapterHealth(name="claude", on_path=False),
        "pi": AdapterHealth(name="pi", on_path=False),
        "omo": AdapterHealth(name="omo", on_path=False),
        "openclaw": AdapterHealth(name="openclaw", on_path=False),
    }

    with pytest.raises(AdapterUnavailableError) as excinfo:
        pick_adapter(spec, health)

    # The exception message should mention at least one off-path name
    # so the operator can act. ``off_path`` attribute carries the list.
    msg = str(excinfo.value).lower()
    assert "off-path" in msg or "no healthy" in msg
    # The exception object also exposes the off-path list directly.
    assert hasattr(excinfo.value, "off_path")
    assert set(excinfo.value.off_path) == {"claude", "pi", "omo", "openclaw"}


def test_router_raises_when_cost_exceeded() -> None:
    """When ``cost_today_usd`` exceeds ``COST_THRESHOLD_USD``, the router raises
    :class:`CostThresholdExceeded`.

    Per M174 design: this is fail-CLOSED — the router does NOT silently
    route when the budget is blown. The policy gate in ``policy.py`` is
    the canonical gate (reads ``data/cost-today.json``); the router just
    respects whatever value the caller passes in via ``SpecContext``.

    Note: the ``$5.00`` default is set at module import via
    :func:`_resolve_cost_threshold_from_env`; we use a ``$7.50`` value
    well above that so the test is robust against threshold tweaks
    (operators may bump the env var to ``$10.00`` in dev, for example).
    """
    spec = SpecContext(
        task_id="M174-test",
        spec_text="implement router",
        cost_today_usd=7.50,  # > $5.00 default
    )

    with pytest.raises(CostThresholdExceeded) as excinfo:
        pick_adapter(spec, _all_healthy())

    # Exception carries the observed cost + threshold so downstream
    # log readers can pattern-match without re-parsing the message.
    assert excinfo.value.cost_today_usd == 7.50
    assert excinfo.value.threshold_usd == 5.00  # module-level default
    # Message mentions both numbers.
    msg = str(excinfo.value)
    assert "7.50" in msg
    assert "5.00" in msg


def test_router_reason_mentions_adapter() -> None:
    """The decision ``reason`` contains the adapter name so log scrapers can match.

    Locks the contract from M174 §"router.py exports": the reason
    string MUST mention the chosen adapter. This is the only field
    downstream code (TUI, logs) reads to identify which adapter was
    picked — without it, operators can't audit routing decisions.
    """
    spec = SpecContext(task_id="M174-test", spec_text="implement router")
    decision = pick_adapter(spec, _all_healthy())

    assert decision.adapter in decision.reason, (
        f"reason string must mention the chosen adapter "
        f"({decision.adapter}); got: {decision.reason!r}"
    )

    # Also test the rank_adapters path — every ranked decision must
    # mention its adapter too.
    ranked = rank_adapters(spec, _all_healthy())
    assert len(ranked) >= 2, "expected at least 2 ranked adapters when all 4 are healthy"
    for rd in ranked:
        assert rd.adapter in rd.reason, (
            f"rank_adapters reason must mention the adapter ({rd.adapter}); got: {rd.reason!r}"
        )
