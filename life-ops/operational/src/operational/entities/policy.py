"""Policy governance entities (PRD-06, Points_of_premisses §4, ikigai_meta_heuristics §1).

This module defines the three Pydantic entities that make up the **policy
governance layer** of the cybernetic loop. They are pure data containers
with invariants — no business logic, no I/O, no state-machine evaluation
(the latter lives in ``operational.core`` and is wired up in Sprint 2E).

Three entities are exposed:

* :class:`PolicySetpoints` — the **operational regime** parameters for a
  given :class:`operational.enums.PolicyState`. Each of the four states
  (PUSH, MAINTAIN, REDUCE, RECOVER) has a canonical set of setpoints
  (work-hour budget, pomodoro cap, sleep target, Q_HE target, break
  duration, allowed phases, description). Use
  :meth:`PolicySetpoints.from_pav_defaults` to construct the canonical
  version without repeating the magic numbers.
* :class:`PolicyDecision` — a **decision record** for a specific date:
  the chosen state, severity, rationale, the active setpoints, and the
  inputs that drove the decision (Q_HE, energy, infraction count).
  Mutable (``frozen=False``) because ``applied`` / ``applied_at`` are
  flipped in a second step after the decision is constructed.
* :class:`DecisionRecord` — an **append-only audit log** entry for state
  transitions. Immutable (``frozen=True``). The
  ``from_state != to_state`` invariant is enforced at construction.

Source documents:

* **PRD-06** — Policy governance (the four-state regime, histerese, the
  canonical setpoint table reproduced in :meth:`PolicySetpoints.from_pav_defaults`).
* **Points_of_premisses §4** — Asymmetric histerese (3 days up, 2 days
  down, 1 day into ``RECOVER``); thresholds ``QHE_PUSH >= 0.85`` and
  ``QHE_RECOVER < 0.60``.
* **ikigai_meta_heuristics §1** — The four regimes and their
  product/preserve trade-offs.

Conventions:

* Pydantic v2 strict mode (``frozen`` / ``extra="forbid"`` /
  ``validate_assignment``).
* Google-style docstrings, line-length 100, ``__all__`` explicit.
* All constraints enforced via ``Field`` (max_length, ge, le) and
  explicit ``model_validator`` methods.
* No business logic — pure data containers with invariants.
"""
from __future__ import annotations

import datetime as _dt
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from operational.enums import EnergyLevel, PolicyState
from operational.types import UEID  # noqa: TC001

__all__ = ["DecisionRecord", "PolicyDecision", "PolicySetpoints"]


# ---------------------------------------------------------------------------
# Module-level validation constants
# ---------------------------------------------------------------------------

#: Maximum length of ``PolicySetpoints.description`` (PRD-06 §3).
_SETPOINTS_DESCRIPTION_MAX: int = 200

#: Maximum length of ``PolicyDecision.rationale`` (PRD-06 — short prose).
_RATIONALE_MAX: int = 500

#: Maximum length of ``DecisionRecord.trigger`` (PRD-06 — short prose).
_TRIGGER_MAX: int = 200

#: Allowed phase values for ``PolicySetpoints.allowed_phases``.
_ALLOWED_PHASE: Literal["DEEP_WORK", "SHALLOW_WORK", "RECOVERY"] = "DEEP_WORK"

#: Canonical :data:`UEID` prefix for setpoints. The full ID is composed
#: as ``set_<12 hex>`` for uniqueness.
_SETPOINTS_ID_PREFIX: str = "set_"

#: Canonical :data:`UEID` prefix for policy decisions.
_DECISION_ID_PREFIX: str = "pol_"

#: Canonical :data:`UEID` prefix for decision records (audit log).
_RECORD_ID_PREFIX: str = "rec_"

#: UUID hex-truncation length (matches other entities in this package).
_UEID_HEX_LEN: int = 12


# ---------------------------------------------------------------------------
# PolicySetpoints
# ---------------------------------------------------------------------------


class PolicySetpoints(BaseModel):
    """Operational setpoints for a policy state (PRD-06 §3).

    Each :class:`operational.enums.PolicyState` (PUSH, MAINTAIN, REDUCE,
    RECOVER) has its own setpoints that govern workload, recovery and
    quality targets for the day. The setpoints are the **envelope** that
    the daily handler must respect: a hard ceiling on focused hours, a
    cap on pomodoros, a sleep target, the Q_HE target to maintain, the
    break length, and the list of phases the user is allowed to enter.

    Use :meth:`from_pav_defaults` to build a canonical instance for any
    of the four states without having to repeat the magic numbers; use
    the regular constructor to express a custom (still validated)
    regime.

    Attributes:
        id: :data:`UEID` (e.g. ``"set_a1b2c3d4e5f6"``).
        state: The :class:`PolicyState` these setpoints govern.
        hardwork_budget_hours: Maximum focused work hours per day
            (float, ``[0.0, 16.0]``).
        max_pomodoros_per_day: Maximum pomodoros per day
            (int, ``[0, 12]``).
        sleep_target_hours: Target sleep duration in hours
            (float, ``[4.0, 10.0]``).
        qhe_target: Target Q_HE value to maintain (float, ``[0.0, 1.0]``).
        break_minutes: Break length between work blocks
            (int, ``[1, 30]``).
        allowed_phases: Phases the user is allowed to enter while this
            state is active. Restricts the daily handler.
        description: Human-readable description, 0-200 characters.
        created_at: Wall-clock timestamp of construction.

    Raises:
        ValidationError: If any constraint is violated.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    id: UEID
    state: PolicyState
    hardwork_budget_hours: Annotated[float, Field(ge=0.0, le=16.0)]
    max_pomodoros_per_day: Annotated[int, Field(ge=0, le=12)]
    sleep_target_hours: Annotated[float, Field(ge=4.0, le=10.0)]
    qhe_target: Annotated[float, Field(ge=0.0, le=1.0)]
    break_minutes: Annotated[int, Field(ge=1, le=30)]
    allowed_phases: list[Literal["DEEP_WORK", "SHALLOW_WORK", "RECOVERY"]]
    description: Annotated[str, Field(default="", max_length=_SETPOINTS_DESCRIPTION_MAX)]
    created_at: datetime

    @model_validator(mode="after")
    def _validate_phases(self) -> PolicySetpoints:
        """Cross-field invariants for the allowed-phases list.

        A non-empty list is required so the daily handler always has a
        well-defined set of phases to choose from. Empty or
        ``None``-only lists are rejected at construction time.

        Returns:
            The model instance (unchanged on success).

        Raises:
            ValueError: If ``allowed_phases`` is empty.
        """
        if len(self.allowed_phases) == 0:
            msg = (
                f"allowed_phases must be non-empty for state {self.state!r}, "
                "got empty list"
            )
            raise ValueError(msg)
        return self

    @classmethod
    def from_pav_defaults(
        cls,
        state: PolicyState,
        **overrides: Any,  # noqa: ANN401
    ) -> PolicySetpoints:
        """Build a :class:`PolicySetpoints` from PRD-06 canonical defaults.

        The canonical values for each :class:`PolicyState` are
        hard-coded in this method (single source of truth for the
        policy setpoint table). Any field can be overridden through
        keyword arguments — useful for tests, ad-hoc regimes, or
        future A/B experiments.

        Args:
            state: The :class:`PolicyState` whose canonical setpoints
                are requested.
            **overrides: Field overrides. Allowed keys: ``id``,
                ``hardwork_budget_hours``, ``max_pomodoros_per_day``,
                ``sleep_target_hours``, ``qhe_target``,
                ``break_minutes``, ``allowed_phases``, ``description``,
                ``created_at``. Unknown keys raise :class:`ValueError`
                (Pydantic ``extra="forbid"``).

        Returns:
            A fully-validated :class:`PolicySetpoints`.

        Example:
            >>> from operational.enums import PolicyState
            >>> s = PolicySetpoints.from_pav_defaults(PolicyState.PUSH)
            >>> s.hardwork_budget_hours
            8.0
            >>> s.allowed_phases
            ['DEEP_WORK', 'SHALLOW_WORK']
        """
        canonical: dict[PolicyState, dict[str, object]] = {
            PolicyState.PUSH: {
                "hardwork_budget_hours": 8.0,
                "max_pomodoros_per_day": 10,
                "sleep_target_hours": 7.0,
                "qhe_target": 0.85,
                "break_minutes": 10,
                "allowed_phases": ["DEEP_WORK", "SHALLOW_WORK"],
                "description": (
                    "PUSH regime: maximum focus. 8h hard work, 10 "
                    "pomodoros, sleep 7h, Q_HE target 0.85."
                ),
            },
            PolicyState.MAINTAIN: {
                "hardwork_budget_hours": 6.0,
                "max_pomodoros_per_day": 8,
                "sleep_target_hours": 8.0,
                "qhe_target": 0.75,
                "break_minutes": 10,
                "allowed_phases": ["DEEP_WORK", "SHALLOW_WORK"],
                "description": (
                    "MAINTAIN regime: steady cadence. 6h hard work, 8 "
                    "pomodoros, sleep 8h, Q_HE target 0.75."
                ),
            },
            PolicyState.REDUCE: {
                "hardwork_budget_hours": 4.0,
                "max_pomodoros_per_day": 5,
                "sleep_target_hours": 8.0,
                "qhe_target": 0.65,
                "break_minutes": 15,
                "allowed_phases": ["SHALLOW_WORK", "RECOVERY"],
                "description": (
                    "REDUCE regime: protect recovery. 4h hard work, 5 "
                    "pomodoros, sleep 8h, Q_HE target 0.65."
                ),
            },
            PolicyState.RECOVER: {
                "hardwork_budget_hours": 2.0,
                "max_pomodoros_per_day": 2,
                "sleep_target_hours": 9.0,
                "qhe_target": 0.50,
                "break_minutes": 20,
                "allowed_phases": ["RECOVERY"],
                "description": (
                    "RECOVER regime: hard stop. 2h hard work, 2 "
                    "pomodoros, sleep 9h, Q_HE target 0.50."
                ),
            },
        }
        base: dict[str, object] = {
            "id": f"{_SETPOINTS_ID_PREFIX}{uuid4().hex[:_UEID_HEX_LEN]}",
            "state": state,
            "created_at": datetime.now(),  # noqa: DTZ005
        }
        base.update(canonical[state])
        base.update(overrides)
        return cls(**base)


# ---------------------------------------------------------------------------
# PolicyDecision
# ---------------------------------------------------------------------------


class PolicyDecision(BaseModel):
    """A policy decision for a given date (PRD-06).

    A :class:`PolicyDecision` is the **output of the PolicyEngine** for a
    specific date: the chosen :class:`PolicyState`, its severity, the
    active :class:`PolicySetpoints`, and the inputs that drove the
    decision (Q_HE value, energy level, infraction count).

    The model is **mutable** (``frozen=False``) because ``applied`` /
    ``applied_at`` are flipped in a second step after the decision is
    constructed (the orchestrator builds the decision, then later marks
    it as applied once the setpoints are actually pushed to the daily
    handler). Setting ``applied=True`` without ``applied_at`` is allowed:
    the auto-timestamp validator fills in :func:`datetime.now`.

    Attributes:
        id: :data:`UEID` (e.g. ``"pol_a1b2c3d4e5f6"``).
        date: The calendar date this decision applies to.
        state: The chosen :class:`PolicyState`.
        severity: ``"INFO"`` / ``"WARNING"`` / ``"CRITICAL"``. Defaults
            to ``"INFO"`` for routine decisions.
        rationale: Short prose (0-500 chars) explaining why this state
            was chosen. Surfaced in the daily report.
        setpoints: The active :class:`PolicySetpoints`. Must match
            :attr:`state` (validated).
        days_in_state: Number of consecutive days spent in the current
            state. Defaults to ``0``.
        previous_state: The :class:`PolicyState` we transitioned from,
            or ``None`` for the first decision on record.
        qhe_input: Q_HE value at the moment of the decision
            (float, ``[0.0, 1.0]``). ``None`` when the engine ran
            without a Q_HE reading.
        energy_input: Self-reported :class:`EnergyLevel` at the moment
            of the decision. ``None`` if not reported.
        infraction_count: Number of policy violations that triggered
            this decision. Defaults to ``0``.
        created_at: Wall-clock timestamp of construction.
        applied: Whether this decision has been pushed to the daily
            handler. Defaults to ``False``.
        applied_at: Wall-clock timestamp of the application. ``None``
            until :attr:`applied` is set to ``True``.

    Raises:
        ValidationError: If any constraint or invariant is violated
            (``setpoints.state != state`` or out-of-range values).
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    id: UEID
    date: _dt.date
    state: PolicyState
    severity: Literal["INFO", "WARNING", "CRITICAL"] = "INFO"
    rationale: Annotated[str, Field(default="", max_length=_RATIONALE_MAX)]
    setpoints: PolicySetpoints
    days_in_state: Annotated[int, Field(ge=0)] = 0
    previous_state: PolicyState | None = None
    qhe_input: Annotated[float, Field(ge=0.0, le=1.0)] | None = None
    energy_input: EnergyLevel | None = None
    infraction_count: Annotated[int, Field(ge=0)] = 0
    created_at: datetime
    applied: bool = False
    applied_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_setpoints_match_state(self) -> PolicyDecision:
        """Verify ``setpoints.state`` matches the decision's ``state``.

        A :class:`PolicyDecision` is meaningless if its
        :class:`PolicySetpoints` describe a different state than the
        one recorded in :attr:`state`. This invariant guards against
        accidental state/setpoint mix-ups (e.g. constructing a PUSH
        decision with the canonical MAINTAIN setpoints).

        Returns:
            The model instance (unchanged on success).

        Raises:
            ValueError: If ``self.setpoints.state != self.state``.
        """
        if self.setpoints.state is not self.state:
            msg = (
                f"setpoints.state ({self.setpoints.state!r}) must match "
                f"decision state ({self.state!r})"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _validate_applied_at(self) -> PolicyDecision:
        """Auto-fill :attr:`applied_at` when :attr:`applied` flips to ``True``.

        The orchestrator typically constructs a decision with
        ``applied=False`` and then later assigns ``applied=True``.
        When the user sets ``applied=True`` without supplying an
        explicit timestamp, we set :attr:`applied_at` to
        :func:`datetime.now` so the audit trail always carries a
        monotonic ordering.

        Returns:
            The model instance (with :attr:`applied_at` filled in
            when applicable).
        """
        if self.applied and self.applied_at is None:
            self.applied_at = datetime.now()  # noqa: DTZ005
        return self

    @classmethod
    def from_state(  # noqa: PLR0913
        cls,
        decision_date: _dt.date,
        state: PolicyState,
        rationale: str = "",
        severity: Literal["INFO", "WARNING", "CRITICAL"] = "INFO",
        previous_state: PolicyState | None = None,
        qhe_input: float | None = None,
        energy_input: EnergyLevel | None = None,
        infraction_count: int = 0,
        days_in_state: int = 0,
        **overrides: Any,  # noqa: ANN401
    ) -> PolicyDecision:
        """Build a :class:`PolicyDecision` from canonical setpoints.

        Convenience constructor that wires up the matching
        :class:`PolicySetpoints` for the chosen :class:`PolicyState`
        automatically (no need to call
        :meth:`PolicySetpoints.from_pav_defaults` separately). Useful
        in the orchestrator and in tests.

        Args:
            decision_date: Calendar date the decision applies to.
            state: The chosen :class:`PolicyState`.
            rationale: Short prose (0-500 chars).
            severity: ``"INFO"`` / ``"WARNING"`` / ``"CRITICAL"``.
            previous_state: Prior :class:`PolicyState`, or ``None``.
            qhe_input: Q_HE value (``[0.0, 1.0]``) or ``None``.
            energy_input: :class:`EnergyLevel` or ``None``.
            infraction_count: Number of violations. Defaults to ``0``.
            days_in_state: Consecutive days in the current state.
                Defaults to ``0``.
            **overrides: Field overrides for the decision. The
                ``setpoints`` key is ignored (it is derived from
                ``state``).

        Returns:
            A fully-validated :class:`PolicyDecision`.
        """
        setpoints: PolicySetpoints = PolicySetpoints.from_pav_defaults(state)
        # ``setpoints`` is derived from ``state``; never accept an override.
        overrides.pop("setpoints", None)
        base: dict[str, object] = {
            "id": f"{_DECISION_ID_PREFIX}{uuid4().hex[:_UEID_HEX_LEN]}",
            "date": decision_date,
            "state": state,
            "severity": severity,
            "rationale": rationale,
            "setpoints": setpoints,
            "days_in_state": days_in_state,
            "previous_state": previous_state,
            "qhe_input": qhe_input,
            "energy_input": energy_input,
            "infraction_count": infraction_count,
            "created_at": datetime.now(),  # noqa: DTZ005
            "applied": False,
            "applied_at": None,
        }
        base.update(overrides)
        return cls(**base)


# ---------------------------------------------------------------------------
# DecisionRecord
# ---------------------------------------------------------------------------


class DecisionRecord(BaseModel):
    """An audit log of policy state transitions (PRD-06).

    A :class:`DecisionRecord` is an **append-only** entry that records a
    transition between two :class:`PolicyState` values. Every successful
    state change in the policy engine produces exactly one record. The
    record is immutable (``frozen=True``) — corrections are made by
    writing a *new* record, never by editing an existing one.

    Attributes:
        id: :data:`UEID` (e.g. ``"rec_a1b2c3d4e5f6"``).
        from_state: The :class:`PolicyState` we transitioned from, or
            ``None`` for the very first decision on record.
        to_state: The :class:`PolicyState` we transitioned to.
        transition_date: Calendar date the transition took effect.
        days_in_previous_state: How many days were spent in
            :attr:`from_state` before the transition fired. ``0`` for
            the first decision on record.
        trigger: Short prose (0-200 chars) explaining what triggered
            the transition (Q_HE threshold breach, energy drop, …).
        qhe_at_transition: Q_HE value at the moment of the transition
            (float, ``[0.0, 1.0]``). ``None`` when the engine ran
            without a Q_HE reading.
        created_at: Wall-clock timestamp the record was written.

    Raises:
        ValidationError: If any constraint or invariant is violated
            (e.g. ``from_state == to_state``).
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    id: UEID
    from_state: PolicyState | None = None
    to_state: PolicyState
    transition_date: _dt.date
    days_in_previous_state: Annotated[int, Field(ge=0)]
    trigger: Annotated[str, Field(default="", max_length=_TRIGGER_MAX)]
    qhe_at_transition: Annotated[float, Field(ge=0.0, le=1.0)] | None = None
    created_at: datetime

    @model_validator(mode="after")
    def _validate_transition(self) -> DecisionRecord:
        """Verify ``from_state`` and ``to_state`` are distinct.

        A :class:`DecisionRecord` exists to record a **change** of
        state. If ``from_state`` and ``to_state`` are the same, the
        record carries no information and is rejected at construction.

        Returns:
            The model instance (unchanged on success).

        Raises:
            ValueError: If ``self.from_state == self.to_state``.
        """
        if self.from_state is not None and self.from_state is self.to_state:
            msg = (
                f"from_state and to_state must differ for a "
                f"DecisionRecord, both are {self.to_state!r}"
            )
            raise ValueError(msg)
        return self

    @classmethod
    def from_states(  # noqa: PLR0913
        cls,
        from_state: PolicyState | None,
        to_state: PolicyState,
        transition_date: _dt.date,
        days_in_previous_state: int = 0,
        trigger: str = "",
        qhe_at_transition: float | None = None,
        **overrides: Any,  # noqa: ANN401
    ) -> DecisionRecord:
        """Build a :class:`DecisionRecord` with a generated ``id``.

        Convenience constructor for the orchestrator. Auto-generates
        the :attr:`id` and the :attr:`created_at` timestamp.

        Args:
            from_state: Prior :class:`PolicyState`, or ``None``.
            to_state: The new :class:`PolicyState`.
            transition_date: Calendar date of the transition.
            days_in_previous_state: Days spent in ``from_state``.
                Defaults to ``0`` (use ``0`` for the first record).
            trigger: Short prose (0-200 chars).
            qhe_at_transition: Q_HE at the moment of the transition.
            **overrides: Field overrides. The ``id`` and
                ``created_at`` keys are ignored (auto-generated).

        Returns:
            A fully-validated :class:`DecisionRecord`.

        Raises:
            ValueError: If ``from_state == to_state``.
        """
        base: dict[str, object] = {
            "id": f"{_RECORD_ID_PREFIX}{uuid4().hex[:_UEID_HEX_LEN]}",
            "from_state": from_state,
            "to_state": to_state,
            "transition_date": transition_date,
            "days_in_previous_state": days_in_previous_state,
            "trigger": trigger,
            "qhe_at_transition": qhe_at_transition,
            "created_at": datetime.now(),  # noqa: DTZ005
        }
        overrides.pop("id", None)
        overrides.pop("created_at", None)
        base.update(overrides)
        return cls(**base)
