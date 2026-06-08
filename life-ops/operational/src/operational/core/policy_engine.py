"""Policy engine — 4-state FSM with histerese (PRD-06, Points_of_premisses §4).

This module implements the **Target-Sensor-Adjuster** cybernetic loop that
governs the user's operational regime. The four states are::

    PUSH     → MAINTAIN   (UPGRADE, requires QHE >= push threshold for
                           POLICY_UPGRADE_DAYS consecutive days)
    MAINTAIN → PUSH       (UPGRADE, same histerese)
    MAINTAIN → REDUCE     (DOWNGRADE, requires QHE < recover threshold for
                           POLICY_DOWNGRADE_DAYS consecutive days)
    REDUCE   → MAINTAIN   (UPGRADE, same as MAINTAIN→PUSH)
    REDUCE   → RECOVER    (DOWNGRADE, same as MAINTAIN→REDUCE)
    RECOVER  → REDUCE     (EXIT, requires QHE >= recover threshold for
                           POLICY_UPGRADE_DAYS consecutive days)
    *any*    → RECOVER    (EMERGENCY ENTRY, triggered immediately if
                           infraction_count >= 3 or QHE < 0.30)

Source documents:

* **PRD-06** — the four-state regime and histerese rules.
* **Points_of_premisses §4** — asymmetric histerese (3 days up, 2 days
  down) and the QHE thresholds ``QHE_PUSH_THRESHOLD = 0.85`` and
  ``QHE_RECOVER_THRESHOLD = 0.60``.
* **ikigai_meta_heuristics §1** — the four regimes and their
  product/preserve trade-offs.

Design rules:

* **Pure functions** for the FSM evaluation logic (:func:`evaluate_policy`,
  :func:`is_recover_entry_condition`, :func:`consecutive_days_*`). They
  take a current state, a QHE snapshot, and a history of decisions —
  no I/O, no side effects.
* **Stateful** :class:`PolicyEngine` for production use: it holds the
  decision history and the transition log internally and exposes a
  small API (:meth:`PolicyEngine.evaluate`, :meth:`PolicyEngine.reset`).
* The engine respects the **asymmetric histerese** — a faster decay
  (2 days) than upgrade (3 days) — to avoid oscillation under noisy
  QHE readings.
* The **emergency entry** to :attr:`operational.enums.PolicyState.RECOVER`
  fires immediately (no histerese) on either ``infraction_count >= 3``
  or ``QHE < 0.30``. The user is protected even if the data is
  degraded for a single day.
* The severity tier of the decision (:attr:`Severity.INFO` /
  :attr:`Severity.WARNING` / :attr:`Severity.CRITICAL`) is derived
  deterministically from the transition path — every entry into
  :attr:`operational.enums.PolicyState.RECOVER` is
  :attr:`Severity.CRITICAL`, every entry into
  :attr:`operational.enums.PolicyState.REDUCE` is
  :attr:`Severity.WARNING`, and the rest are
  :attr:`Severity.INFO`.

Public surface
--------------

* :class:`PolicyEngine` — stateful engine with history.
* :func:`evaluate_policy` — pure FSM evaluation (used by
  :class:`PolicyEngine` and by tests / orchestrators).
* :func:`is_recover_entry_condition` — predicate for emergency entry.
* :func:`consecutive_days_above_threshold` /
  :func:`consecutive_days_below_threshold` — histerese helpers.
* :class:`PolicyEvaluation` — frozen result of :func:`evaluate_policy`.
* :class:`Severity` — :class:`enum.StrEnum` mirroring
  :class:`operational.exceptions.Severity` (subset: ``INFO``,
  ``WARNING``, ``CRITICAL``).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Final
from uuid import uuid4

from operational.constants import DEFAULT
from operational.entities.habit import QHEMetrics  # noqa: TC001
from operational.entities.policy import (
    DecisionRecord,
    PolicyDecision,
    PolicySetpoints,
)
from operational.enums import EnergyLevel, PolicyState

__all__ = [
    "PolicyEngine",
    "PolicyEvaluation",
    "Severity",
    "consecutive_days_above_threshold",
    "consecutive_days_below_threshold",
    "evaluate_policy",
    "is_recover_entry_condition",
]


# ---------------------------------------------------------------------------
# Module-level constants (ruff PLR2004 — magic values extracted)
# ---------------------------------------------------------------------------

#: Critical QHE cutoff below which the engine enters RECOVER immediately
#: (Points_of_premisses §4 — emergency entry threshold).
_RECOVER_QHE_CRITICAL: Final[float] = 0.30

#: Number of infractions that triggers immediate RECOVER entry
#: (Points_of_premisses §4).
_RECOVER_INFRACTION_THRESHOLD: Final[int] = 3

#: Number of infractions that triggers an early warning from PUSH to REDUCE
#: (Points_of_premisses §4 — secondary PUSH down-channel).
_PUSH_EARLY_WARNING_INFRACTIONS: Final[int] = 2

#: ID prefix for policy decisions emitted by :class:`PolicyEngine`.
#: The 3-letter prefix is required by the
#: :data:`operational.types.UEID` regex (``^[a-z]{{3,5}}_[a-z0-9_]+$``).
_DECISION_ID_PREFIX: Final[str] = "pcs_"

#: ID prefix for transition records emitted by :class:`PolicyEngine`.
_RECORD_ID_PREFIX: Final[str] = "dtr_"

#: UUID hex-truncation length (matches other entities in this package).
_UEID_HEX_LEN: Final[int] = 12

#: Minimum allowed ``max_history`` for :class:`PolicyEngine`.
_MIN_HISTORY: Final[int] = 1

#: Upper bound for the :class:`PolicyDecision` ``qhe_input`` field
#: (Pydantic constraint ``le=1.0``). Values above this are clamped
#: before storage. The raw QHE formula can briefly exceed 1.0 (the
#: ``1 + eta * streak_bonus`` multiplier), but the storage and the
#: FSM evaluation threshold are both ``>= 0.85`` (PUSH) and
## ``< 0.60`` (RECOVER) — both well within the formula's natural
#: range, so the clamp is a no-op for the FSM boolean comparisons.
_QHE_INPUT_MAX: Final[float] = 1.0

#: Lower bound for the :class:`PolicyDecision` ``qhe_input`` field.
_QHE_INPUT_MIN: Final[float] = 0.0


def _clamp_qhe_for_storage(qhe: float) -> float:
    """Clamp a QHE value to the storage range ``[0.0, 1.0]``.

    The pure :class:`QHEMetrics` formula can produce values slightly
    above 1.0 when the streak bonus pushes the multiplier up. The
    :class:`PolicyDecision` storage schema constrains ``qhe_input``
    to ``[0.0, 1.0]``, so the engine clamps before persisting.

    The clamp is a **no-op for the FSM evaluation** because both
    threshold comparisons (``QHE >= 0.85`` for PUSH and
    ``QHE < 0.60`` for RECOVER) are invariant under clamping:
    clamping only affects values above 1.0, and every such value
    also satisfies the PUSH predicate on the raw scale.

    Args:
        qhe: The raw QHE value (possibly outside ``[0.0, 1.0]``).

    Returns:
        The value clipped to ``[0.0, 1.0]``.
    """
    if qhe < _QHE_INPUT_MIN:
        return _QHE_INPUT_MIN
    if qhe > _QHE_INPUT_MAX:
        return _QHE_INPUT_MAX
    return qhe


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------


class Severity(StrEnum):
    """Severity of a policy transition (PRD-06).

    This is a **subset** of :class:`operational.exceptions.Severity`
    that captures the three tiers the policy FSM uses. The two extra
    tiers of the broader ``Severity`` enum (``LOW`` / ``MEDIUM``) do
    not apply to policy transitions: there is no meaningful distinction
    between a *low* down-channel and a *medium* down-channel for a
    state machine with a single protective state pair (REDUCE /
    RECOVER).

    Mapping:

    * ``INFO`` — routine transition or stay-in-state. The user does
      not need to take action.
    * ``WARNING`` — protective downgrade (any path into
      :attr:`operational.enums.PolicyState.REDUCE`). The user should
      consider lowering their workload.
    * ``CRITICAL`` — any path into
      :attr:`operational.enums.PolicyState.RECOVER`. Hard stop:
      ``hardwork_budget_hours = 2.0`` and
      ``max_pomodoros_per_day = 2`` per the canonical setpoints.
    """

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# PolicyEvaluation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    """Result of evaluating the policy FSM for one decision.

    This is the **pure-function** return shape of
    :func:`evaluate_policy`. The stateful :class:`PolicyEngine` wraps
    this with a freshly-built :class:`PolicyDecision` and (if
    applicable) a :class:`DecisionRecord` for the transition log.

    Attributes:
        new_state: The :class:`operational.enums.PolicyState` the FSM
            selects as the next state. May equal :attr:`previous_state`
            for a stay-in-state result.
        severity: :class:`Severity` of the transition. ``CRITICAL`` for
            any RECOVER entry, ``WARNING`` for any REDUCE entry, and
            ``INFO`` for upgrades or stays.
        rationale: Short prose (≤ 200 chars in practice) explaining
            why the FSM chose this transition. Surfaced verbatim in
            the :class:`operational.entities.policy.PolicyDecision.rationale`.
        days_in_state: Number of consecutive days spent in
            :attr:`previous_state` *before* this evaluation. ``0`` for
            the first call (no prior history).
        is_transition: ``True`` iff :attr:`new_state != previous_state`.
            ``False`` for stays (including the initial state).
        previous_state: The state we were in before this evaluation.
            ``None`` for the first call.
    """

    new_state: PolicyState
    severity: Severity
    rationale: str
    days_in_state: int
    is_transition: bool
    previous_state: PolicyState | None


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def is_recover_entry_condition(qhe: float, infraction_count: int) -> bool:
    """Return ``True`` if emergency RECOVER entry conditions are met.

    Emergency entry is triggered if **either**:

    * ``infraction_count >= 3`` (too many policy violations) — see
      :data:`_RECOVER_INFRACTION_THRESHOLD`.
    * ``qhe < 0.30`` (extreme low QHE) — see
      :data:`_RECOVER_QHE_CRITICAL` and Points_of_premisses §4.

    The check is a **predicate** (no side effects) and is used by
    :func:`evaluate_policy` to short-circuit the FSM evaluation
    before the regular transition rules. A ``True`` result forces
    the next state to :attr:`operational.enums.PolicyState.RECOVER`
    regardless of the current state.

    Args:
        qhe: Current QHE value in ``[0.0, 1.0]`` (or the value of
            :attr:`operational.entities.habit.QHEMetrics.qhe`).
        infraction_count: Number of routine violations in the
            current window. ``>= 0``.

    Returns:
        ``True`` if the engine should enter :attr:`PolicyState.RECOVER`
        immediately.
    """
    return infraction_count >= _RECOVER_INFRACTION_THRESHOLD or qhe < _RECOVER_QHE_CRITICAL


def consecutive_days_below_threshold(
    history: list[PolicyDecision] | tuple[PolicyDecision, ...],
    threshold: float,
) -> int:
    """Count consecutive days (most recent first) below ``threshold``.

    The function sorts the history by :attr:`PolicyDecision.date`
    **descending** and walks forward, counting decisions whose
    :attr:`PolicyDecision.qhe_input` is strictly less than
    ``threshold``. The walk stops at the first decision that does not
    satisfy the predicate, or at the first decision with a ``None``
    :attr:`PolicyDecision.qhe_input` (treated as a "broken streak").

    The result is the **prefix length** of the most-recent streak,
    not the total count of days below the threshold.

    Args:
        history: Sequence of past :class:`PolicyDecision` records in
            any order. The function sorts internally.
        threshold: The strict upper bound (``qhe_input < threshold``
            counts as a streak day).

    Returns:
        ``int >= 0`` — the number of consecutive days ending at the
        most recent decision that satisfy the predicate. ``0`` if
        ``history`` is empty or if the most recent decision does not
        satisfy the predicate.
    """
    if not history:
        return 0
    sorted_history = sorted(history, key=lambda d: d.date, reverse=True)
    count = 0
    for decision in sorted_history:
        if decision.qhe_input is None:
            break
        if decision.qhe_input < threshold:
            count += 1
        else:
            break
    return count


def consecutive_days_above_threshold(
    history: list[PolicyDecision] | tuple[PolicyDecision, ...],
    threshold: float,
) -> int:
    """Count consecutive days (most recent first) at/above ``threshold``.

    Mirror of :func:`consecutive_days_below_threshold` with an
    **inclusive** comparison (``qhe_input >= threshold`` counts).

    Args:
        history: Sequence of past :class:`PolicyDecision` records in
            any order. The function sorts internally.
        threshold: The lower bound (``qhe_input >= threshold`` counts
            as a streak day).

    Returns:
        ``int >= 0`` — the number of consecutive days ending at the
        most recent decision that satisfy the predicate. ``0`` if
        ``history`` is empty or if the most recent decision does not
        satisfy the predicate.
    """
    if not history:
        return 0
    sorted_history = sorted(history, key=lambda d: d.date, reverse=True)
    count = 0
    for decision in sorted_history:
        if decision.qhe_input is None:
            break
        if decision.qhe_input >= threshold:
            count += 1
        else:
            break
    return count


def _count_days_in_state(
    history: list[PolicyDecision] | tuple[PolicyDecision, ...],
    state: PolicyState,
) -> int:
    """Count consecutive days (most recent first) spent in ``state``.

    Args:
        history: Sequence of past :class:`PolicyDecision` records in
            any order.
        state: The state to look for in the streak.

    Returns:
        ``int >= 0`` — the number of consecutive days ending at the
        most recent decision that match ``state``. ``0`` if no match.
    """
    if not history:
        return 0
    sorted_history = sorted(history, key=lambda d: d.date, reverse=True)
    count = 0
    for decision in sorted_history:
        if decision.state == state:
            count += 1
        else:
            break
    return count


# ---------------------------------------------------------------------------
# Pure FSM evaluation
# ---------------------------------------------------------------------------


def evaluate_policy(  # noqa: C901, PLR0911
    current_state: PolicyState | None,
    qhe_metrics: QHEMetrics,
    history: list[PolicyDecision] | tuple[PolicyDecision, ...] = (),
    infraction_count: int = 0,
) -> PolicyEvaluation:
    """Evaluate the next policy state (pure function, PRD-06).

    Implements the **deterministic 4-state FSM with histerese** from
    PRD-06 + Points_of_premisses §4. The function takes the current
    state, the latest :class:`QHEMetrics`, the history of recent
    :class:`PolicyDecision` records, and the current infraction
    count; it returns a :class:`PolicyEvaluation` describing the
    next state, the severity of the transition, and the rationale.

    The decision rules are evaluated in a fixed priority order:

    1. **Emergency RECOVER entry** — if
       :func:`is_recover_entry_condition` returns ``True``, the
       function short-circuits to RECOVER (CRITICAL).
    2. **RECOVER exit** — if the current state is RECOVER and the
       history shows ``QHE >= QHE_RECOVER_THRESHOLD`` for
       ``POLICY_UPGRADE_DAYS`` consecutive days, exit to REDUCE
       (INFO). Otherwise stay in RECOVER (CRITICAL).
    3. **REDUCE transitions** — UPGRADE to MAINTAIN on
       ``POLICY_UPGRADE_DAYS`` days above
       ``QHE_PUSH_THRESHOLD``; DOWNGRADE to RECOVER on
       ``POLICY_DOWNGRADE_DAYS`` days below
       ``QHE_RECOVER_THRESHOLD``; otherwise stay (WARNING).
    4. **MAINTAIN transitions** — UPGRADE to PUSH on
       ``POLICY_UPGRADE_DAYS`` days above
       ``QHE_PUSH_THRESHOLD``; DOWNGRADE to REDUCE on
       ``POLICY_DOWNGRADE_DAYS`` days below
       ``QHE_RECOVER_THRESHOLD``; otherwise stay (INFO).
    5. **PUSH transitions** — DOWNGRADE to MAINTAIN on
       ``POLICY_DOWNGRADE_DAYS`` days below
       ``QHE_RECOVER_THRESHOLD``; **early warning** DOWNGRADE to
       REDUCE if ``infraction_count >= 2``; otherwise stay (INFO).
    6. **Initial state** — if ``current_state`` is ``None`` and there
       is no history, the FSM seeds at MAINTAIN (INFO).

    Args:
        current_state: The :class:`operational.enums.PolicyState` the
            FSM is in. ``None`` for the very first call (no prior
            decision).
        qhe_metrics: The current :class:`operational.entities.habit.QHEMetrics`
            snapshot. The QHE value used internally is
            :attr:`QHEMetrics.qhe`.
        history: Recent :class:`operational.entities.policy.PolicyDecision`
            records, in any order. Used by the histerese helpers to
            count consecutive days. Pass ``()`` for the first call.
        infraction_count: Number of routine violations. Defaults to
            ``0``. ``>= 3`` triggers emergency RECOVER entry;
            ``>= 2`` triggers an early PUSH → REDUCE warning.

    Returns:
        A :class:`PolicyEvaluation` with the new state, the severity
        of the transition, the rationale, the days-in-state count,
        and the ``is_transition`` flag.
    """
    qhe = qhe_metrics.qhe

    # Compute the "days in current state" prefix length.
    days_in_state = (
        _count_days_in_state(history, current_state) if current_state is not None else 0
    )

    # ----------------------------------------------------------------------
    # 1. Emergency RECOVER entry (highest priority, no histerese).
    # ----------------------------------------------------------------------
    if current_state != PolicyState.RECOVER and is_recover_entry_condition(
        qhe, infraction_count
    ):
        return PolicyEvaluation(
            new_state=PolicyState.RECOVER,
            severity=Severity.CRITICAL,
            rationale=(
                f"RECOVER entry: qhe={qhe:.3f}, infractions={infraction_count}"
            ),
            days_in_state=days_in_state,
            is_transition=True,
            previous_state=current_state,
        )

    # ----------------------------------------------------------------------
    # 2. RECOVER exit (RECOVER -> REDUCE on stable QHE).
    # ----------------------------------------------------------------------
    if current_state == PolicyState.RECOVER:
        days_above = consecutive_days_above_threshold(history, DEFAULT.QHE_RECOVER_THRESHOLD)
        if days_above >= DEFAULT.POLICY_UPGRADE_DAYS:
            return PolicyEvaluation(
                new_state=PolicyState.REDUCE,
                severity=Severity.INFO,
                rationale=(
                    f"RECOVER exit: qhe >= {DEFAULT.QHE_RECOVER_THRESHOLD} "
                    f"for {days_above} days"
                ),
                days_in_state=days_in_state,
                is_transition=True,
                previous_state=current_state,
            )
        return PolicyEvaluation(
            new_state=PolicyState.RECOVER,
            severity=Severity.CRITICAL,
            rationale=f"RECOVER continues: qhe={qhe:.3f}",
            days_in_state=days_in_state,
            is_transition=False,
            previous_state=current_state,
        )

    # ----------------------------------------------------------------------
    # 3. REDUCE transitions.
    # ----------------------------------------------------------------------
    if current_state == PolicyState.REDUCE:
        days_above_push = consecutive_days_above_threshold(
            history, DEFAULT.QHE_PUSH_THRESHOLD
        )
        days_below_recover = consecutive_days_below_threshold(
            history, DEFAULT.QHE_RECOVER_THRESHOLD
        )
        if days_above_push >= DEFAULT.POLICY_UPGRADE_DAYS:
            return PolicyEvaluation(
                new_state=PolicyState.MAINTAIN,
                severity=Severity.INFO,
                rationale=(
                    f"REDUCE->MAINTAIN: qhe >= {DEFAULT.QHE_PUSH_THRESHOLD} "
                    f"for {days_above_push} days"
                ),
                days_in_state=days_in_state,
                is_transition=True,
                previous_state=current_state,
            )
        if days_below_recover >= DEFAULT.POLICY_DOWNGRADE_DAYS:
            return PolicyEvaluation(
                new_state=PolicyState.RECOVER,
                severity=Severity.WARNING,
                rationale=(
                    f"REDUCE->RECOVER: qhe < {DEFAULT.QHE_RECOVER_THRESHOLD} "
                    f"for {days_below_recover} days"
                ),
                days_in_state=days_in_state,
                is_transition=True,
                previous_state=current_state,
            )
        return PolicyEvaluation(
            new_state=PolicyState.REDUCE,
            severity=Severity.WARNING,
            rationale=f"REDUCE continues: qhe={qhe:.3f}",
            days_in_state=days_in_state,
            is_transition=False,
            previous_state=current_state,
        )

    # ----------------------------------------------------------------------
    # 4. MAINTAIN transitions.
    # ----------------------------------------------------------------------
    if current_state == PolicyState.MAINTAIN:
        days_above_push = consecutive_days_above_threshold(
            history, DEFAULT.QHE_PUSH_THRESHOLD
        )
        days_below_recover = consecutive_days_below_threshold(
            history, DEFAULT.QHE_RECOVER_THRESHOLD
        )
        if days_above_push >= DEFAULT.POLICY_UPGRADE_DAYS:
            return PolicyEvaluation(
                new_state=PolicyState.PUSH,
                severity=Severity.INFO,
                rationale=(
                    f"MAINTAIN->PUSH: qhe >= {DEFAULT.QHE_PUSH_THRESHOLD} "
                    f"for {days_above_push} days"
                ),
                days_in_state=days_in_state,
                is_transition=True,
                previous_state=current_state,
            )
        if days_below_recover >= DEFAULT.POLICY_DOWNGRADE_DAYS:
            return PolicyEvaluation(
                new_state=PolicyState.REDUCE,
                severity=Severity.WARNING,
                rationale=(
                    f"MAINTAIN->REDUCE: qhe < {DEFAULT.QHE_RECOVER_THRESHOLD} "
                    f"for {days_below_recover} days"
                ),
                days_in_state=days_in_state,
                is_transition=True,
                previous_state=current_state,
            )
        return PolicyEvaluation(
            new_state=PolicyState.MAINTAIN,
            severity=Severity.INFO,
            rationale=f"MAINTAIN continues: qhe={qhe:.3f}",
            days_in_state=days_in_state,
            is_transition=False,
            previous_state=current_state,
        )

    # ----------------------------------------------------------------------
    # 5. PUSH transitions.
    # ----------------------------------------------------------------------
    if current_state == PolicyState.PUSH:
        days_below_recover = consecutive_days_below_threshold(
            history, DEFAULT.QHE_RECOVER_THRESHOLD
        )
        if days_below_recover >= DEFAULT.POLICY_DOWNGRADE_DAYS:
            return PolicyEvaluation(
                new_state=PolicyState.MAINTAIN,
                severity=Severity.WARNING,
                rationale=(
                    f"PUSH->MAINTAIN: qhe < {DEFAULT.QHE_RECOVER_THRESHOLD} "
                    f"for {days_below_recover} days"
                ),
                days_in_state=days_in_state,
                is_transition=True,
                previous_state=current_state,
            )
        if infraction_count >= _PUSH_EARLY_WARNING_INFRACTIONS:
            return PolicyEvaluation(
                new_state=PolicyState.REDUCE,
                severity=Severity.WARNING,
                rationale=(
                    f"PUSH->REDUCE: early warning, {infraction_count} infractions"
                ),
                days_in_state=days_in_state,
                is_transition=True,
                previous_state=current_state,
            )
        return PolicyEvaluation(
            new_state=PolicyState.PUSH,
            severity=Severity.INFO,
            rationale=f"PUSH continues: qhe={qhe:.3f}",
            days_in_state=days_in_state,
            is_transition=False,
            previous_state=current_state,
        )

    # ----------------------------------------------------------------------
    # 6. Initial state (no history) -> seed at MAINTAIN.
    # ----------------------------------------------------------------------
    return PolicyEvaluation(
        new_state=PolicyState.MAINTAIN,
        severity=Severity.INFO,
        rationale="Initial state: starting at MAINTAIN",
        days_in_state=0,
        is_transition=False,
        previous_state=None,
    )


# ---------------------------------------------------------------------------
# PolicyEngine — stateful wrapper
# ---------------------------------------------------------------------------


class PolicyEngine:
    """Stateful 4-state policy engine with history tracking (PRD-06).

    Unlike the pure :func:`evaluate_policy` function, this class
    holds the decision history and the transition log internally so
    the caller can invoke :meth:`evaluate` with just the current
    :class:`QHEMetrics` snapshot and the current infraction count.

    The engine is **not thread-safe** — the histerese counters rely
    on a consistent view of the decision history. Use one engine per
    user/session.

    Attributes (read-only via properties):
        current_state: The :class:`operational.enums.PolicyState` the
            engine is currently in. ``None`` before the first
            :meth:`evaluate` call (or after :meth:`reset`).
        history: **Defensive copy** of the decision log (most recent
            last). Trimmed to the last ``max_history`` entries.
        transitions: **Defensive copy** of the transition log
            (:class:`operational.entities.policy.DecisionRecord`
            entries, one per state change). Capped at ``max_history``
            entries.
        max_history: Maximum number of decisions kept in memory.
    """

    def __init__(self, max_history: int = 30) -> None:
        """Initialise the engine.

        Args:
            max_history: Maximum number of decisions to retain in the
                in-memory history. Defaults to ``30`` (a calendar
                month). Must be ``>= 1``.

        Raises:
            ValueError: If ``max_history < 1``.
        """
        if max_history < _MIN_HISTORY:
            msg = f"max_history must be >= {_MIN_HISTORY}, got {max_history}"
            raise ValueError(msg)
        self._max_history: int = max_history
        self._history: list[PolicyDecision] = []
        self._transitions: list[DecisionRecord] = []
        self._current_state: PolicyState | None = None

    @property
    def current_state(self) -> PolicyState | None:
        """Return the current :class:`PolicyState` (``None`` if not yet started)."""
        return self._current_state

    @property
    def max_history(self) -> int:
        """Return the maximum number of decisions retained in memory."""
        return self._max_history

    @property
    def history(self) -> list[PolicyDecision]:
        """Return a **defensive copy** of the decision log.

        The returned list is ordered oldest-first (insertion order);
        callers may freely sort, slice, or filter it without
        affecting the engine's internal state.
        """
        return list(self._history)

    @property
    def transitions(self) -> list[DecisionRecord]:
        """Return a **defensive copy** of the transition log.

        The list contains one :class:`DecisionRecord` per state
        change, ordered oldest-first. The initial state (None →
        MAINTAIN on the first call) does **not** generate a
        transition record — there is no ``from_state`` to record
        against.

        Empty until the second :meth:`evaluate` call.
        """
        return list(self._transitions)

    @property
    def days_in_current_state(self) -> int:
        """Return the number of consecutive decisions in the current state.

        Returns ``0`` before the first :meth:`evaluate` call or
        immediately after :meth:`reset`.
        """
        if self._current_state is None:
            return 0
        return _count_days_in_state(self._history, self._current_state)

    # --- Core API ----------------------------------------------------------

    def evaluate(
        self,
        qhe_metrics: QHEMetrics,
        infraction_count: int = 0,
        energy_level: EnergyLevel | None = None,
        on_date: date | None = None,
    ) -> PolicyDecision:
        """Evaluate the next state and record the decision.

        The engine:

        1. Calls :func:`evaluate_policy` with the current state, the
           supplied QHE snapshot, the in-memory history, and the
           infraction count.
        2. Builds a fully-validated :class:`PolicyDecision` (with
           canonical :class:`PolicySetpoints` for the new state) and
           appends it to :attr:`history`.
        3. If the FSM transitioned, builds a
           :class:`DecisionRecord` and appends it to
           :attr:`transitions`.
        4. Trims both logs to the last ``max_history`` entries.
        5. Updates :attr:`current_state`.

        Args:
            qhe_metrics: The current :class:`QHEMetrics` snapshot.
            infraction_count: Number of routine violations. Defaults
                to ``0``.
            energy_level: Self-reported :class:`EnergyLevel` at the
                moment of the decision. Optional — ``None`` if the
                caller does not have a reading. Stored on
                :attr:`PolicyDecision.energy_input` for downstream
                reporting.
            on_date: Calendar date the decision applies to. Defaults
                to :func:`date.today` for ad-hoc invocations; tests
                and orchestrators should pass an explicit date for
                determinism.

        Returns:
            The newly-constructed :class:`PolicyDecision` (also
            appended to :attr:`history`).
        """
        eval_result = evaluate_policy(
            self._current_state, qhe_metrics, self._history, infraction_count
        )
        decision_date = on_date if on_date is not None else date.today()  # noqa: DTZ011
        decision = PolicyDecision(
            id=f"{_DECISION_ID_PREFIX}{uuid4().hex[:_UEID_HEX_LEN]}",
            date=decision_date,
            state=eval_result.new_state,
            severity=eval_result.severity.value,
            rationale=eval_result.rationale,
            setpoints=PolicySetpoints.from_pav_defaults(eval_result.new_state),
            days_in_state=eval_result.days_in_state,
            previous_state=eval_result.previous_state,
            qhe_input=_clamp_qhe_for_storage(qhe_metrics.qhe),
            energy_input=energy_level,
            infraction_count=infraction_count,
            created_at=datetime.now(),  # noqa: DTZ005
        )
        # Record the transition (only when state actually changed from
        # a known previous state — the initial seed at MAINTAIN does
        # not produce a DecisionRecord).
        if (
            eval_result.is_transition
            and self._current_state is not None
            and self._current_state != eval_result.new_state
        ):
            record = DecisionRecord(
                id=f"{_RECORD_ID_PREFIX}{uuid4().hex[:_UEID_HEX_LEN]}",
                from_state=self._current_state,
                to_state=eval_result.new_state,
                transition_date=decision_date,
                days_in_previous_state=eval_result.days_in_state,
                trigger=eval_result.rationale,
                qhe_at_transition=_clamp_qhe_for_storage(qhe_metrics.qhe),
                created_at=datetime.now(),  # noqa: DTZ005
            )
            self._transitions.append(record)
            if len(self._transitions) > self._max_history:
                self._transitions = self._transitions[-self._max_history :]
        # Append the decision and trim.
        self._history.append(decision)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]
        # Update state.
        self._current_state = eval_result.new_state
        return decision

    def reset(self) -> None:
        """Reset the engine to its initial state.

        Clears the decision log, the transition log, and the current
        state. The engine is then indistinguishable from a freshly
        constructed one.
        """
        self._history = []
        self._transitions = []
        self._current_state = None
