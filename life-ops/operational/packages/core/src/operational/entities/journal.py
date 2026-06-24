"""Journal domain entities (PAV §10, PRD-06, Análise Tática §11).

This module defines the **leaf Pydantic models** that capture the daily
narrative of the user. They are part of the ``operational.entities`` package
and are intentionally **leaves** of the import graph — no other operational
module imports from them, and they import only from ``operational.enums``
and ``operational.types``.

Two entities are exposed:

* :class:`JournalEntry` — the raw daily narrative. Mutable model
  (``frozen=False``) because ``updated_at`` is auto-managed on every
  assignment through ``validate_assignment=True``.
* :class:`AutoIndagacao` — the socratic self-inquiry ritual (11 questions
  for MORNING / EVENING / REVIEW). Immutable (``frozen=True``).

Source documents:

* **PAV §10** — journal structure (date, periods, routines, desvios,
  lições, energia, foco, pomodoros, humor).
* **PRD-06** — the four ritual types; :class:`AutoIndagacao` is bound to
  ``MORNING``, ``EVENING`` or ``REVIEW``.
* **Análise (Tático e Operacional).md** §11 — the 11 socratic questions
  used by :class:`AutoIndagacao`.
* **Cluster PLAN drilldown** — the relationship between routines and
  journal entries.

Conventions:

* Pydantic v2 strict mode (``frozen`` / ``extra="forbid"`` /
  ``validate_assignment``).
* Google-style docstrings, line-length 100, ``__all__`` explicit.
* All constraints enforced via ``Field`` (max_length, ge, le) and
  explicit ``field_validator`` / ``model_validator`` methods.
* No business logic — pure data containers with invariants.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from operational.entities.ajuste_fino import AjusteFino  # noqa: TC001
from operational.enums import Period, RitualType
from operational.types import UEID  # noqa: TC001  (used as Pydantic field type at runtime)

__all__ = ["AutoIndagacao", "JournalEntry"]


# ---------------------------------------------------------------------------
# Module-level validation constants
# ---------------------------------------------------------------------------

#: Maximum length of the free-form journal narrative. PAV §10 row 2.
_JOURNAL_ENTRY_TEXT_MAX: int = 5000

#: Maximum length of a single deviation / "ajuste fino". PAV §10 row 5.
_JOURNAL_DESVIO_MAX: int = 200

#: Maximum length of a single lesson learned. PAV §10 row 6.
_JOURNAL_LICAO_MAX: int = 500

#: Maximum number of pomodoros a day can hold. PAV §1 + §9.
_JOURNAL_POMODOROS_MAX: int = 12

#: Maximum number of ``questions_answered`` entries on a single
#: :class:`AutoIndagacao` ritual (Análise Tática §11 — 11 questions, plus
#: 9 of headroom for custom prompts).
_AUTO_INDAGACAO_QUESTIONS_MAX: int = 20

#: Maximum length of a socratic question text.
_AUTO_INDAGACAO_QUESTION_MAX: int = 200

#: Maximum length of a socratic answer text.
_AUTO_INDAGACAO_ANSWER_MAX: int = 1000

#: Maximum length of an insight extracted from a ritual.
_AUTO_INDAGACAO_INSIGHT_MAX: int = 500

#: Maximum length of a concrete action item.
_AUTO_INDAGACAO_ACTION_MAX: int = 200


# ---------------------------------------------------------------------------
# JournalEntry
# ---------------------------------------------------------------------------


class JournalEntry(BaseModel):
    """A daily journal entry (PAV §10).

    Captures the narrative of a single day, including the periods covered,
    routines completed (as a list of :data:`UEID` references), deviations
    from plan, lessons learned, energy / focus levels, completed
    pomodoros, and self-reported mood at start and end of day.

    This model is **mutable** (``frozen=False``) because ``updated_at`` is
    auto-managed on every assignment. The model is also
    ``validate_assignment=True`` so that any subsequent edit re-runs the
    full validation pipeline (including the ``updated_at`` auto-update).

    Attributes:
        id: Universal Entity ID (:data:`UEID`). Convention:
            ``"day_YYYY_MM_DD"``.
        date: Calendar date the entry refers to (local time).
        entry_text: Free-form narrative. Max 5000 chars (PAV §10).
        periods_covered: Set of :class:`Period` values touched by the day.
        routines_completed: Ordered list of routine :data:`UEID` references
            that were actually completed on this date. Must be unique.
        desvios: Deviations from plan / "ajustes finos".
            Each max 200 chars.
        licoes_aprendidas: Lessons learned. Each max 500 chars.
        energia_nivel: Subjective energy (1-10) at end of day. Optional.
        foco_nivel: Subjective focus (1-10) at end of day. Optional.
        pomodoros_completos: Number of pomodoros completed (0-12).
        humor_morning: Self-reported morning mood (1-5). Optional.
        humor_evening: Self-reported evening mood (1-5). Optional.
        created_at: Wall-clock timestamp at construction. Required.
        updated_at: Wall-clock timestamp at last edit. Auto-managed.

    Raises:
        ValidationError: If any constraint is violated. Pydantic v2 raises
            :class:`pydantic.ValidationError` automatically for field
            constraints; custom validators raise :class:`ValueError` for
            semantic invariants (e.g. duplicate routine references).
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    id: UEID
    date: date
    entry_text: Annotated[str, Field(default="", max_length=_JOURNAL_ENTRY_TEXT_MAX)]
    periods_covered: set[Period] = Field(default_factory=set)
    routines_completed: list[UEID] = Field(default_factory=list)
    desvios: list[Annotated[str, Field(max_length=_JOURNAL_DESVIO_MAX)]] = Field(
        default_factory=list,
        description=(
            "Free-form list of natural-language deviation descriptions "
            "(PAV §2 — 'desviosRotina: string[]'). Example: "
            "'Dormi 1h mais tarde por causa do alarme.'"
        ),
    )
    ajustes_finos: list[AjusteFino] = Field(
        default_factory=list,
        description=(
            "Structured fine-grained adjustments (PAV §2 — 'ajusteFinos: "
            "{periodo, minutos}[]'). Each entry is an AjusteFino entity "
            "with period, signed minutos, and NL reason."
        ),
    )
    rotinas_logs: list[UEID] = Field(
        default_factory=list,
        description=(
            "UEIDs of :class:`RoutineLog` entities that anchor NL "
            "descriptions to specific routine executions. Linked to "
            "this journal by date+period. The actual RoutineLog "
            "entities are stored separately."
        ),
    )
    licoes_aprendidas: list[Annotated[str, Field(max_length=_JOURNAL_LICAO_MAX)]] = Field(
        default_factory=list,
    )
    energia_nivel: Annotated[int, Field(ge=1, le=10)] | None = None
    foco_nivel: Annotated[int, Field(ge=1, le=10)] | None = None
    pomodoros_completos: Annotated[int, Field(ge=0, le=_JOURNAL_POMODOROS_MAX)] = 0
    humor_morning: Annotated[int, Field(ge=1, le=5)] | None = None
    humor_evening: Annotated[int, Field(ge=1, le=5)] | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @field_validator("routines_completed")
    @classmethod
    def _validate_unique_routines(cls, value: list[UEID]) -> list[UEID]:
        """Reject duplicate routine references in ``routines_completed``.

        Args:
            value: The list of routine UEIDs supplied by the caller.

        Returns:
            The same list, validated.

        Raises:
            ValueError: If the list contains duplicate UEIDs.
        """
        if len(value) != len(set(value)):
            msg = "routines_completed must contain unique UEIDs (no duplicates)"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _auto_set_updated_at(self) -> JournalEntry:
        """Auto-set ``updated_at`` to ``datetime.now()`` on every change.

        Because ``validate_assignment=True`` is enabled, this validator
        re-runs whenever any field is assigned post-construction,
        keeping ``updated_at`` fresh without explicit caller action.

        Implementation note: we use :func:`object.__setattr__` to bypass
        Pydantic's ``validate_assignment`` setter (a plain
        ``self.updated_at = ...`` would re-trigger this very validator
        and cause infinite recursion).

        Returns:
            The model itself, with ``updated_at`` refreshed.
        """
        object.__setattr__(self, "updated_at", datetime.now(tz=UTC))
        return self

    def touch(self) -> JournalEntry:
        """Refresh ``updated_at`` to ``datetime.now()``.

        Returns:
            The same instance, with ``updated_at`` updated. Useful in
            read-modify-write loops where the caller has built a
            replacement model and wants to mark it as fresh.
        """
        object.__setattr__(self, "updated_at", datetime.now(tz=UTC))
        return self

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable :class:`dict` view of the model.

        ``periods_covered`` (a :class:`set`) is converted to a sorted
        list so the output is deterministic across runs.

        Returns:
            Plain :class:`dict` ready for ``json.dumps``.
        """
        data: dict[str, Any] = self.model_dump(mode="json")
        # ``mode="json"`` serialises the ``set[Period]`` to a list; we
        # sort it so the order is reproducible regardless of set
        # iteration order.
        data["periods_covered"] = sorted(data["periods_covered"])
        return data


# ---------------------------------------------------------------------------
# AutoIndagacao
# ---------------------------------------------------------------------------


class AutoIndagacao(BaseModel):
    """Socratic self-inquiry ritual (PRD-06, Análise Tática §11).

    An :class:`AutoIndagacao` binds a set of structured questions / answers
    to a :class:`JournalEntry`. The 11 canonical questions, grouped by
    ritual type, are documented in Análise Tática §11 (MORNING / EVENING
    / REVIEW).

    The questions are stored as a free-form ``dict[str, str]`` mapping
    question text to answer text. This model is **frozen** — once written,
    an :class:`AutoIndagacao` is immutable. To capture a new reflection,
    create a new instance.

    Attributes:
        id: Universal Entity ID (:data:`UEID`). Convention: ``"ind_..."``.
        journal_entry_id: :data:`UEID` of the parent
            :class:`JournalEntry`. Cross-entity reference.
        ritual_type: One of ``MORNING`` / ``EVENING`` / ``REVIEW``.
            Other :class:`RitualType` members (``HYDRATION``,
            ``MEDITATION``, ``SHUTDOWN``) are reserved for
            in-routine tags, not journal-level rituals.
        questions_answered: Question text → answer text. Max 20 entries.
            Question text max 200 chars, answer text max 1000 chars.
        insights: Extracted insights from the ritual. Each max 500 chars.
        action_items: Concrete next steps. Each max 200 chars.
        created_at: Wall-clock timestamp at construction. Required.

    Raises:
        ValidationError: If any constraint is violated.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    id: UEID
    journal_entry_id: UEID
    ritual_type: RitualType
    questions_answered: dict[
        Annotated[str, Field(max_length=_AUTO_INDAGACAO_QUESTION_MAX)],
        Annotated[str, Field(max_length=_AUTO_INDAGACAO_ANSWER_MAX)],
    ]
    insights: list[Annotated[str, Field(max_length=_AUTO_INDAGACAO_INSIGHT_MAX)]] = Field(
        default_factory=list,
    )
    action_items: list[Annotated[str, Field(max_length=_AUTO_INDAGACAO_ACTION_MAX)]] = Field(
        default_factory=list,
    )
    created_at: datetime

    @field_validator("ritual_type")
    @classmethod
    def _validate_ritual_type(cls, value: RitualType) -> RitualType:
        """Restrict ``ritual_type`` to the 3 journal-level rituals.

        The full :class:`RitualType` enum contains 6 members, but only
        ``MORNING``, ``EVENING`` and ``REVIEW`` make sense at the
        journal level (``HYDRATION`` / ``MEDITATION`` / ``SHUTDOWN`` are
        routine-internal tags).

        Args:
            value: The :class:`RitualType` value supplied by the caller.

        Returns:
            The validated :class:`RitualType` value, unchanged.

        Raises:
            ValueError: If the ritual type is not one of the 3 allowed
                journal-level rituals.
        """
        allowed: frozenset[RitualType] = frozenset(
            {RitualType.MORNING, RitualType.EVENING, RitualType.REVIEW},
        )
        if value not in allowed:
            msg = (
                "ritual_type must be MORNING/EVENING/REVIEW for an "
                f"AutoIndagacao, got {value!r}"
            )
            raise ValueError(msg)
        return value

    @field_validator("questions_answered")
    @classmethod
    def _validate_questions_answered(
        cls,
        value: dict[str, str],
    ) -> dict[str, str]:
        """Ensure the questions dict is non-empty and bounded.

        Args:
            value: The questions/answers dict supplied by the caller.

        Returns:
            The validated dict, unchanged.

        Raises:
            ValueError: If the dict is empty or exceeds the cap.
        """
        if not value:
            msg = "questions_answered cannot be empty"
            raise ValueError(msg)
        if len(value) > _AUTO_INDAGACAO_QUESTIONS_MAX:
            msg = (
                f"questions_answered cannot have more than "
                f"{_AUTO_INDAGACAO_QUESTIONS_MAX} entries, got {len(value)}"
            )
            raise ValueError(msg)
        return value
