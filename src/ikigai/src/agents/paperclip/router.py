"""Paperclip ``router`` — pick the best available AI adapter for a spec.

M174-paperclip-auto-spawner introduces the **adapter router** as the
single point where Paperclip decides *which* AI agent to invoke. Before
M174, the implement node hard-coded ``claude`` (the only real adapter).
With the M170-M172 wave shipping real ``pi``, ``omo``, and ``openclaw``
adapters, the choice now belongs to a policy that respects:

* **Cost** — cheapest healthy adapter wins (``pi`` > ``omo`` >
  ``openclaw`` > ``claude``). Locked in by ``ADAPTER_PRIORITY`` and the
  unit test ``test_router_picks_cheapest_healthy``.
* **Health** — adapter must be ``on_path=True``. Off-path adapters are
  skipped without raising (operator may have uninstalled a binary mid-
  week). Raises ``AdapterUnavailableError`` only when **zero** adapters
  are healthy.
* **Budget** — daily cost cap (``COST_THRESHOLD_USD`` env var, default
  ``$5.00``). When ``spec.cost_today_usd`` exceeds the threshold, raise
  ``CostThresholdExceeded`` (fail-CLOSED — the auto-spawner MUST refuse
  to dispatch when the budget is blown). Mirrors the M173 ``CostGate``
  policy but lives in the router so the auto-spawner path can short-
  circuit without instantiating a full ``CostGate``.

Design notes:

* **Pure stdlib + Pydantic v2** — no MCP, no subprocess, no filesystem
  I/O. The router is a pure function over an in-memory health dict.
* **Pydantic v2 strict** on all models: ``frozen=True, extra="forbid"``
  per the project-wide invariant.
* **Sequential queue, not parallel** — the router returns a single
  ``RouterDecision``. Multi-graph fan-out is explicitly deferred to
  Wave N+5 (per M169 spec). The companion helper ``rank_adapters``
  surfaces the full priority-ordered list for observability + future
  fan-out.
* **No background polling** — health is passed in by the caller (the
  auto-spawner shell script reads ``which <adapter>`` and timestamps
  from the cost-dashboard's JSON sidecar). This keeps the router cheap
  to test and free of clock-skew edge cases.
* **Source-agnostic** — the router does NOT inspect the spec text
  beyond carrying it for downstream log scoping. Severity / role / fork-tag
  routing belongs to Wave N+2 (risk gate / D5 keyword list pending).

Public surface (locked by ``test_paperclip_router_importable``):

* :class:`AdapterHealth` — Pydantic model of one adapter's status.
* :class:`SpecContext` — Pydantic model of the spec being routed.
* :class:`RouterDecision` — Pydantic model of the chosen adapter + reason.
* :func:`pick_adapter` — primary entry point.
* :func:`rank_adapters` — observability helper (returns full priority
  list).
* :class:`AdapterUnavailableError` — raised when zero adapters are healthy.
* :class:`CostThresholdExceeded` — raised when ``cost_today_usd`` exceeds
  the threshold.

Constants:

* :data:`ADAPTER_PRIORITY` — ``("pi", "omo", "openclaw", "claude")``.
  Tuple (not list) to make the lock-in loud in tests.
* :data:`COST_THRESHOLD_USD` — ``$5.00`` default; override via
  ``PAPERCLIP_COST_THRESHOLD_USD`` (mirrors M173 ``policy.py`` env var).

This module is a leaf — it does NOT import any Paperclip node or agent
adapter (zero risk of circular imports). It MAY be imported by the
implement node in Wave N+3 (per M174 spec); for now the auto-spawner
shell script is the only consumer.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from pydantic import BaseModel, ConfigDict

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Priority order — cheapest healthy adapter wins.
#: Tuple (not list) to make the lock-in loud in unit tests. The order
#: encodes the M174 design decision: prefer the free / cheap local
#: adapters first, fall back to Claude (the most expensive) only when
#: nothing else is available.
ADAPTER_PRIORITY: tuple[str, ...] = ("pi", "omo", "openclaw", "claude")

#: Default daily cost ceiling in USD. Mirrors :data:`policy.DEFAULT_THRESHOLD_USD`
#: but lives here so the router can fail-CLOSED without instantiating a
#: ``CostGate``. Override via :data:`ENV_COST_THRESHOLD`.
DEFAULT_COST_THRESHOLD_USD: float = 5.00

#: Module-level daily cost ceiling in USD (frozen at import). Mirrors
#: ``policy.COST_THRESHOLD_USD`` (M174 spec contract). ``pick_adapter``
#: consults the runtime resolver too so post-import env var changes
#: are still honoured.
COST_THRESHOLD_USD: float = DEFAULT_COST_THRESHOLD_USD

#: Environment-variable name consulted by :func:`_resolve_cost_threshold`.
ENV_COST_THRESHOLD: str = "PAPERCLIP_COST_THRESHOLD_USD"


# ---------------------------------------------------------------------------
# Models (Pydantic v2 strict per project invariant)
# ---------------------------------------------------------------------------


class AdapterHealth(BaseModel):
    """Snapshot of one adapter's health at decision time.

    The auto-spawner shell script (``scripts/paperclip-spawner.sh``)
    builds these objects from ``which <adapter>`` exit codes and the
    cost-dashboard JSON sidecar.

    Attributes:
        name: short adapter identifier (``"pi"``, ``"omo"``,
            ``"openclaw"``, ``"claude"``). Must match a key in
            :data:`ADAPTER_PRIORITY` for ``pick_adapter`` to consider
            it; off-list names are ignored (no warning — silent skip
            keeps the contract simple).
        on_path: whether the binary is currently on ``PATH``. The
            auto-spawner sets this from ``which <adapter>`` exit code.
        last_invoked_at: when this adapter was last invoked (UTC). May
            be ``None`` if never used. Used by future-wave heuristics
            (least-recently-used fallback); not consulted by M174
            router.
        last_success: whether the last invocation succeeded. Same
            future-use caveat as ``last_invoked_at``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    on_path: bool
    last_invoked_at: datetime | None = None
    last_success: bool | None = None


class SpecContext(BaseModel):
    """The spec being routed.

    Carries enough context for ``pick_adapter`` to make a deterministic
    decision without touching the filesystem.

    Attributes:
        task_id: short identifier of the spec / task. Surfaces in
            log lines so operators can correlate routing decisions
            with taskdog rows.
        spec_text: full spec body. The router does NOT parse this in
            M174 (D5 keyword list deferred); included now so future
            severity-based routing does not need a model bump.
        cost_today_usd: today's accumulated spend. ``None`` skips the
            budget check (lets unit tests bypass the gate without
            monkeypatching env vars). The auto-spawner fills this from
            ``data/cost-today.json``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: str
    spec_text: str
    cost_today_usd: float | None = None


class RouterDecision(BaseModel):
    """The chosen adapter + human-readable explanation.

    Attributes:
        adapter: chosen adapter name (must be in
            :data:`ADAPTER_PRIORITY` when returned by ``pick_adapter``).
        reason: short explanation. **Must contain the adapter name**
            (locked by ``test_router_reason_mentions_adapter``) so
            log scrapers can pattern-match without parsing the model.
        rank: position in the priority list (1-indexed). The chosen
            adapter has ``rank=1``; subsequent ranks appear in
            ``rank_adapters`` output.
        skipped: adapters that were skipped (and why). Empty for the
            primary ``pick_adapter`` decision; populated by
            ``rank_adapters``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter: str
    reason: str
    rank: int = 1
    skipped: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AdapterUnavailableError(RuntimeError):
    """Raised when **zero** adapters are on-path.

    The exception message lists the off-path adapter names so the
    operator can act (re-install binaries, fix PATH, etc.). The
    auto-spawner catches this and posts an alert to ``data/spawner.log``
    rather than crashing the loop.
    """

    def __init__(self, off_path: list[str]) -> None:
        self.off_path: list[str] = list(off_path)
        super().__init__(
            f"no healthy paperclip adapter (off-path: {', '.join(self.off_path) or 'none'})"
        )


class CostThresholdExceeded(RuntimeError):  # noqa: N818 — M174 spec mandates this exact name
    """Raised when ``cost_today_usd`` exceeds :data:`COST_THRESHOLD_USD`.

    Attributes carried on the exception (not just the message) so
    downstream log readers / TUI panels can pattern-match without
    re-parsing the message text. Mirrors ``CostGate`` style.

    Attributes:
        cost_today_usd: the observed spend.
        threshold_usd: the threshold that was exceeded.
    """

    def __init__(self, cost_today_usd: float, threshold_usd: float) -> None:
        self.cost_today_usd: float = cost_today_usd
        self.threshold_usd: float = threshold_usd
        super().__init__(
            f"paperclip cost threshold exceeded: "
            f"${cost_today_usd:.2f} today > ${threshold_usd:.2f} threshold"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_cost_threshold_from_env() -> float:
    """Read :data:`ENV_COST_THRESHOLD`; fall back to default.

    Mirrors ``policy.CostGate._resolve_threshold_from_env``: invalid or
    negative values fall back silently to the default. Fail-open on
    parse errors — the cost gate is a guardrail, not a security
    boundary; misconfiguration should not break Paperclip dispatch.
    """
    raw = os.environ.get(ENV_COST_THRESHOLD)
    if raw is None or raw.strip() == "":
        return DEFAULT_COST_THRESHOLD_USD
    try:
        value = float(raw)
    except ValueError:
        log.warning(
            "paperclip router: %s=%r is not a float; using default $%.2f",
            ENV_COST_THRESHOLD,
            raw,
            DEFAULT_COST_THRESHOLD_USD,
        )
        return DEFAULT_COST_THRESHOLD_USD
    if value < 0:
        log.warning(
            "paperclip router: %s=%r is negative; using default $%.2f",
            ENV_COST_THRESHOLD,
            raw,
            DEFAULT_COST_THRESHOLD_USD,
        )
        return DEFAULT_COST_THRESHOLD_USD
    return value


def _build_reason(adapter: str, rank: int, skipped: tuple[str, ...]) -> str:
    """Compose a human-readable ``reason`` string for the decision.

    The output MUST mention ``adapter`` (locked by
    ``test_router_reason_mentions_adapter``). Format::

        "pi (priority 1) — healthy; skipped omo (off-path)"

    Skipped entries appear in priority order. An empty skip list
    yields ``"pi (priority 1) — healthy"``.
    """
    skip_clause = ""
    if skipped:
        names = ", ".join(skipped)
        skip_clause = f"; skipped {names}"
    return f"{adapter} (priority {rank}) — healthy{skip_clause}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def pick_adapter(
    spec: SpecContext,
    health: dict[str, AdapterHealth],
) -> RouterDecision:
    """Pick the best healthy adapter for ``spec``.

    Walks :data:`ADAPTER_PRIORITY` in order, skipping off-path
    adapters, and returns the first healthy one. Raises
    :class:`CostThresholdExceeded` if ``spec.cost_today_usd`` exceeds
    :data:`COST_THRESHOLD_USD`. Raises :class:`AdapterUnavailableError`
    if zero adapters in the priority list are healthy.

    Args:
        spec: the spec being routed. ``cost_today_usd`` is consulted
            for the budget gate.
        health: map from adapter name to its current health. Names not
            in :data:`ADAPTER_PRIORITY` are ignored.

    Returns:
        A frozen :class:`RouterDecision` describing the chosen adapter
        and which earlier-priority adapters were skipped.

    Raises:
        CostThresholdExceeded: ``spec.cost_today_usd`` exceeds the
            threshold. **Fail-CLOSED** — the auto-spawner MUST
            surface this and refuse to dispatch.
        AdapterUnavailableError: zero healthy adapters in the
            priority list. Message lists the off-path names.
    """
    # Budget gate first — fail-CLOSED when over threshold. ``None`` skips.
    threshold = _resolve_cost_threshold_from_env()
    if spec.cost_today_usd is not None and spec.cost_today_usd > threshold:
        raise CostThresholdExceeded(
            cost_today_usd=spec.cost_today_usd,
            threshold_usd=threshold,
        )

    off_path: list[str] = []
    skipped: list[str] = []

    for rank, name in enumerate(ADAPTER_PRIORITY, start=1):
        h = health.get(name)
        if h is None:
            # Adapter wasn't probed — treat as off-path. Surface in
            # the error if EVERY priority is missing.
            off_path.append(name)
            skipped.append(f"{name} (not probed)")
            continue
        if not h.on_path:
            off_path.append(name)
            skipped.append(f"{name} (off-path)")
            continue

        # First healthy adapter wins.
        return RouterDecision(
            adapter=name,
            reason=_build_reason(name, rank, tuple(skipped)),
            rank=rank,
            skipped=tuple(skipped),
        )

    # Walked the whole priority list — no healthy adapter.
    raise AdapterUnavailableError(off_path)


def rank_adapters(
    spec: SpecContext,
    health: dict[str, AdapterHealth],
) -> list[RouterDecision]:
    """Return the full priority-ordered list of healthy adapters.

    Unlike :func:`pick_adapter`, this does NOT raise on zero healthy
    adapters — it returns an empty list. Useful for the TUI /
    ``data/spawner.log`` observability layer where the operator wants
    to see "which adapters were available" rather than crash the render.

    The returned list is in priority order (cheapest first). Each entry
    carries the cumulative ``skipped`` list at the time of its decision
    so log readers can reconstruct the walk.

    Args:
        spec: same as :func:`pick_adapter`. ``cost_today_usd`` is
            ignored here — this is an observability helper, not a
            gating decision.
        health: same as :func:`pick_adapter`.

    Returns:
        List of :class:`RouterDecision` in priority order. Empty when
        no adapters are healthy.
    """
    decisions: list[RouterDecision] = []
    skipped: list[str] = []

    for rank, name in enumerate(ADAPTER_PRIORITY, start=1):
        h = health.get(name)
        if h is None:
            skipped.append(f"{name} (not probed)")
            continue
        if not h.on_path:
            skipped.append(f"{name} (off-path)")
            continue

        decisions.append(
            RouterDecision(
                adapter=name,
                reason=_build_reason(name, rank, tuple(skipped)),
                rank=rank,
                skipped=tuple(skipped),
            )
        )

    return decisions


__all__ = [
    "ADAPTER_PRIORITY",
    "COST_THRESHOLD_USD",
    "DEFAULT_COST_THRESHOLD_USD",
    "ENV_COST_THRESHOLD",
    "AdapterHealth",
    "AdapterUnavailableError",
    "CostThresholdExceeded",
    "RouterDecision",
    "SpecContext",
    "pick_adapter",
    "rank_adapters",
]
