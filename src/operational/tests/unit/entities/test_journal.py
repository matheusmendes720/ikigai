"""Comprehensive unit tests for ``operational.entities.journal``.

Covers:

* :class:`JournalEntry` — construction, field ranges, validators,
  ``updated_at`` auto-update, mutation, JSON roundtrip, mutation
  triggers timestamp refresh.
* :class:`AutoIndagacao` — construction, ritual-type restriction,
  questions/answers validation, immutability, JSON roundtrip.

The tests are organized as one class per entity, with parametric
descriptors for the multi-case field-range checks. Test isolation is
provided by the built-in ``datetime.now()`` (no clock protocol needed
in these tests).
"""
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from operational.entities.journal import AutoIndagacao, JournalEntry
from operational.enums import Period, RitualType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_journal_kwargs(**overrides: Any) -> dict[str, Any]:
    """Return a baseline :class:`JournalEntry` kwargs dict.

    Args:
        **overrides: Field-level overrides merged on top of the
            baseline.

    Returns:
        :class:`dict` ready to splat into ``JournalEntry(**kwargs)``.
    """
    base: dict[str, Any] = {
        "id": "day_2026_06_07",
        "date": date(2026, 6, 7),
        "entry_text": "Sample narrative.",
        "periods_covered": {Period.MANHA},
        "routines_completed": ["rou_morning_meditation"],
        "energia_nivel": 7,
        "foco_nivel": 8,
        "pomodoros_completos": 4,
        "humor_morning": 4,
        "humor_evening": 5,
        "created_at": datetime(2026, 6, 7, 5, 30, 0),
    }
    base.update(overrides)
    return base


def _base_indagacao_kwargs(**overrides: Any) -> dict[str, Any]:
    """Return a baseline :class:`AutoIndagacao` kwargs dict.

    Args:
        **overrides: Field-level overrides merged on top of the
            baseline.

    Returns:
        :class:`dict` ready to splat into ``AutoIndagacao(**kwargs)``.
    """
    base: dict[str, Any] = {
        "id": "ind_2026_06_07_morning",
        "journal_entry_id": "day_2026_06_07",
        "ritual_type": RitualType.MORNING,
        "questions_answered": {
            "What is my plan today?": "Deep work on PRD-02.",
            "What's my top priority?": "Ship the journal entity.",
        },
        "insights": ["I work best in the morning."],
        "action_items": ["Open with the hardest task."],
        "created_at": datetime(2026, 6, 7, 6, 0, 0),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# JournalEntry — construction
# ---------------------------------------------------------------------------


class TestJournalEntryConstruction:
    """Build a :class:`JournalEntry` from valid kwargs."""

    def test_create_minimal_journal_entry(self) -> None:
        """A minimal entry with only required fields is valid."""
        entry = JournalEntry(
            id="day_2026_06_07",
            date=date(2026, 6, 7),
            created_at=datetime(2026, 6, 7, 5, 30, 0),
        )
        assert entry.id == "day_2026_06_07"
        assert entry.date == date(2026, 6, 7)
        assert entry.entry_text == ""
        assert entry.periods_covered == set()
        assert entry.routines_completed == []
        assert entry.desvios == []
        assert entry.licoes_aprendidas == []
        assert entry.energia_nivel is None
        assert entry.foco_nivel is None
        assert entry.pomodoros_completos == 0
        assert entry.humor_morning is None
        assert entry.humor_evening is None
        assert entry.created_at == datetime(2026, 6, 7, 5, 30, 0)
        assert entry.updated_at is not None

    def test_create_full_journal_entry(self) -> None:
        """All fields populated at once are accepted."""
        entry = JournalEntry(**_base_journal_kwargs())
        assert entry.energia_nivel == 7
        assert entry.foco_nivel == 8
        assert entry.pomodoros_completos == 4
        assert entry.periods_covered == {Period.MANHA}
        assert entry.routines_completed == ["rou_morning_meditation"]

    def test_periods_covered_accepts_all_three_periods(self) -> None:
        """All three :class:`Period` members are accepted."""
        entry = JournalEntry(
            **_base_journal_kwargs(
                periods_covered={Period.MANHA, Period.TARDE, Period.NOITE},
            ),
        )
        assert len(entry.periods_covered) == 3

    def test_periods_covered_deduplicates(self) -> None:
        """Repeated periods collapse to a set."""
        entry = JournalEntry(
            **_base_journal_kwargs(
                periods_covered={Period.MANHA, Period.MANHA, Period.TARDE},
            ),
        )
        assert entry.periods_covered == {Period.MANHA, Period.TARDE}

    def test_routines_completed_preserves_order(self) -> None:
        """The order of ``routines_completed`` is preserved (list, not set)."""
        entry = JournalEntry(
            **_base_journal_kwargs(
                routines_completed=["rou_b", "rou_a", "rou_c"],
            ),
        )
        assert entry.routines_completed == ["rou_b", "rou_a", "rou_c"]

    def test_to_dict_returns_sorted_periods(self) -> None:
        """``to_dict()`` sorts ``periods_covered`` for determinism."""
        entry = JournalEntry(
            **_base_journal_kwargs(
                periods_covered={Period.NOITE, Period.MANHA, Period.TARDE},
            ),
        )
        out = entry.to_dict()
        assert out["periods_covered"] == ["MANHA", "NOITE", "TARDE"]


# ---------------------------------------------------------------------------
# JournalEntry — field constraints
# ---------------------------------------------------------------------------


class TestJournalEntryFieldConstraints:
    """Range / length constraints on :class:`JournalEntry` fields."""

    def test_journal_entry_text_max_length(self) -> None:
        """``entry_text`` accepts exactly 5000 chars, rejects 5001."""
        boundary = JournalEntry(
            **_base_journal_kwargs(entry_text="x" * 5000),
        )
        assert len(boundary.entry_text) == 5000
        with pytest.raises(ValidationError):
            JournalEntry(**_base_journal_kwargs(entry_text="x" * 5001))

    def test_journal_entry_text_default_is_empty(self) -> None:
        """Default ``entry_text`` is the empty string."""
        entry = JournalEntry(
            **_base_journal_kwargs(entry_text=""),
        )
        assert entry.entry_text == ""

    @pytest.mark.parametrize("nivel", [1, 5, 10])
    def test_journal_entry_energia_nivel_range(self, nivel: int) -> None:
        """``energia_nivel`` accepts 1, 5, 10 (boundary cases)."""
        entry = JournalEntry(
            **_base_journal_kwargs(energia_nivel=nivel),
        )
        assert entry.energia_nivel == nivel

    @pytest.mark.parametrize("nivel", [0, 11, -1, 100])
    def test_journal_entry_energia_nivel_out_of_range(self, nivel: int) -> None:
        """``energia_nivel`` rejects 0, 11, negatives, etc."""
        with pytest.raises(ValidationError):
            JournalEntry(**_base_journal_kwargs(energia_nivel=nivel))

    def test_journal_entry_energia_nivel_optional(self) -> None:
        """``energia_nivel`` is optional (``None`` by default)."""
        entry = JournalEntry(
            id="day_2026_06_08",
            date=date(2026, 6, 8),
            created_at=datetime(2026, 6, 8, 5, 30, 0),
        )
        assert entry.energia_nivel is None

    @pytest.mark.parametrize("nivel", [1, 5, 10])
    def test_journal_entry_foco_nivel_range(self, nivel: int) -> None:
        """``foco_nivel`` accepts 1, 5, 10."""
        entry = JournalEntry(
            **_base_journal_kwargs(foco_nivel=nivel),
        )
        assert entry.foco_nivel == nivel

    @pytest.mark.parametrize("nivel", [0, 11, -5])
    def test_journal_entry_foco_nivel_out_of_range(self, nivel: int) -> None:
        """``foco_nivel`` rejects 0, 11, negatives."""
        with pytest.raises(ValidationError):
            JournalEntry(**_base_journal_kwargs(foco_nivel=nivel))

    @pytest.mark.parametrize("pomodoros", [0, 6, 12])
    def test_journal_entry_pomodoros_range(self, pomodoros: int) -> None:
        """``pomodoros_completos`` accepts 0, 6, 12 (boundaries)."""
        entry = JournalEntry(
            **_base_journal_kwargs(pomodoros_completos=pomodoros),
        )
        assert entry.pomodoros_completos == pomodoros

    @pytest.mark.parametrize("pomodoros", [-1, 13, 100])
    def test_journal_entry_pomodoros_out_of_range(self, pomodoros: int) -> None:
        """``pomodoros_completos`` rejects < 0 or > 12."""
        with pytest.raises(ValidationError):
            JournalEntry(**_base_journal_kwargs(pomodoros_completos=pomodoros))

    @pytest.mark.parametrize("humor", [1, 3, 5])
    def test_journal_entry_humor_range(self, humor: int) -> None:
        """``humor_morning``/``humor_evening`` accept 1, 3, 5."""
        entry = JournalEntry(
            **_base_journal_kwargs(humor_morning=humor, humor_evening=humor),
        )
        assert entry.humor_morning == humor
        assert entry.humor_evening == humor

    @pytest.mark.parametrize("humor", [0, 6, -1])
    def test_journal_entry_humor_out_of_range(self, humor: int) -> None:
        """``humor_*`` reject 0, 6, negatives."""
        with pytest.raises(ValidationError):
            JournalEntry(**_base_journal_kwargs(humor_morning=humor))

    def test_journal_entry_desvios_optional(self) -> None:
        """``desvios`` defaults to an empty list and accepts entries."""
        entry = JournalEntry(
            **_base_journal_kwargs(desvios=["slept late", "skipped water"]),
        )
        assert entry.desvios == ["slept late", "skipped water"]

    def test_journal_entry_licoes_optional(self) -> None:
        """``licoes_aprendidas`` defaults to empty, accepts entries."""
        entry = JournalEntry(
            **_base_journal_kwargs(
                licoes_aprendidas=["wake up is everything"],
            ),
        )
        assert entry.licoes_aprendidas == ["wake up is everything"]

    def test_journal_entry_desvios_max_length(self) -> None:
        """``desvios`` items capped at 200 chars."""
        entry = JournalEntry(
            **_base_journal_kwargs(desvios=["x" * 200]),
        )
        assert len(entry.desvios[0]) == 200
        with pytest.raises(ValidationError):
            JournalEntry(**_base_journal_kwargs(desvios=["x" * 201]))

    def test_journal_entry_licoes_max_length(self) -> None:
        """``licoes_aprendidas`` items capped at 500 chars."""
        entry = JournalEntry(
            **_base_journal_kwargs(licoes_aprendidas=["x" * 500]),
        )
        assert len(entry.licoes_aprendidas[0]) == 500
        with pytest.raises(ValidationError):
            JournalEntry(**_base_journal_kwargs(licoes_aprendidas=["x" * 501]))

    def test_journal_entry_text_strips_whitespace(self) -> None:
        """``str_strip_whitespace=True`` strips leading/trailing whitespace."""
        entry = JournalEntry(
            **_base_journal_kwargs(entry_text="  hello  "),
        )
        assert entry.entry_text == "hello"


# ---------------------------------------------------------------------------
# JournalEntry — validators
# ---------------------------------------------------------------------------


class TestJournalEntryValidators:
    """Custom validators on :class:`JournalEntry`."""

    def test_journal_entry_routines_unique_accepts_unique(self) -> None:
        """Unique routine IDs are accepted as-is."""
        entry = JournalEntry(
            **_base_journal_kwargs(
                routines_completed=["rou_a", "rou_b", "rou_c"],
            ),
        )
        assert entry.routines_completed == ["rou_a", "rou_b", "rou_c"]

    def test_journal_entry_routines_unique_rejects_duplicates(self) -> None:
        """Duplicate routine IDs raise :class:`ValidationError`."""
        with pytest.raises(ValidationError) as exc_info:
            JournalEntry(
                **_base_journal_kwargs(
                    routines_completed=["rou_a", "rou_b", "rou_a"],
                ),
            )
        assert "routines_completed" in str(exc_info.value)
        assert "unique" in str(exc_info.value).lower()

    def test_journal_entry_rejects_unknown_fields(self) -> None:
        """``extra="forbid"`` rejects unknown field names."""
        with pytest.raises(ValidationError) as exc_info:
            JournalEntry(
                **_base_journal_kwargs(unknown_field="boom"),
            )
        assert "unknown_field" in str(exc_info.value)

    def test_journal_entry_id_pattern_enforced(self) -> None:
        """``id`` must match the :data:`UEID` pattern (prefix_slug)."""
        with pytest.raises(ValidationError):
            JournalEntry(
                **_base_journal_kwargs(id="InvalidID"),
            )


# ---------------------------------------------------------------------------
# JournalEntry — updated_at and mutation
# ---------------------------------------------------------------------------


class TestJournalEntryUpdatedAt:
    """The ``updated_at`` auto-management contract."""

    def test_journal_entry_auto_update_timestamp_on_construction(self) -> None:
        """``updated_at`` is set to ``datetime.now()`` at construction."""
        before = datetime.now(tz=UTC) - timedelta(seconds=1)
        entry = JournalEntry(
            id="day_2026_06_07",
            date=date(2026, 6, 7),
            created_at=datetime(2026, 6, 7, 5, 30, 0),
        )
        after = datetime.now(tz=UTC) + timedelta(seconds=1)
        assert entry.updated_at is not None
        assert before <= entry.updated_at <= after

    def test_journal_entry_mutation_refreshes_updated_at(self) -> None:
        """Field assignment triggers ``updated_at`` refresh."""
        entry = JournalEntry(**_base_journal_kwargs())
        first = entry.updated_at
        assert first is not None
        # Force a measurable time gap
        entry.entry_text = "Revised narrative."
        assert entry.updated_at is not None
        assert entry.updated_at >= first

    def test_journal_entry_touch_method(self) -> None:
        """``touch()`` refreshes ``updated_at`` to ``datetime.now()``."""
        entry = JournalEntry(**_base_journal_kwargs())
        first = entry.updated_at
        entry.touch()
        second = entry.updated_at
        assert second is not None
        assert first is not None
        assert second >= first

    def test_journal_entry_touch_returns_self(self) -> None:
        """``touch()`` returns the same instance (chainable)."""
        entry = JournalEntry(**_base_journal_kwargs())
        assert entry.touch() is entry


# ---------------------------------------------------------------------------
# JournalEntry — JSON roundtrip
# ---------------------------------------------------------------------------


class TestJournalEntryJson:
    """JSON serialization roundtrip for :class:`JournalEntry`."""

    def test_journal_entry_json_roundtrip(self) -> None:
        """``model_dump_json()`` → ``model_validate_json()`` is lossless."""
        original = JournalEntry(**_base_journal_kwargs())
        payload = original.model_dump_json()
        restored = JournalEntry.model_validate_json(payload)
        assert restored.id == original.id
        assert restored.date == original.date
        assert restored.entry_text == original.entry_text
        assert restored.periods_covered == original.periods_covered
        assert restored.routines_completed == original.routines_completed
        assert restored.energia_nivel == original.energia_nivel
        assert restored.pomodoros_completos == original.pomodoros_completos

    def test_journal_entry_to_dict_is_json_serialisable(self) -> None:
        """``to_dict()`` output is JSON-serialisable (no ``set`` leak)."""
        entry = JournalEntry(
            **_base_journal_kwargs(
                periods_covered={Period.MANHA, Period.TARDE, Period.NOITE},
            ),
        )
        out = entry.to_dict()
        # Must not raise — this is the test.
        encoded = json.dumps(out)
        assert "MANHA" in encoded
        assert "TARDE" in encoded
        assert "NOITE" in encoded


# ---------------------------------------------------------------------------
# AutoIndagacao — construction
# ---------------------------------------------------------------------------


class TestAutoIndagacaoConstruction:
    """Build :class:`AutoIndagacao` from valid kwargs."""

    def test_create_auto_indagacao_minimal(self) -> None:
        """Minimal required fields are accepted."""
        ind = AutoIndagacao(
            id="ind_2026_06_07_morning",
            journal_entry_id="day_2026_06_07",
            ritual_type=RitualType.MORNING,
            questions_answered={"Q?": "A."},
            created_at=datetime(2026, 6, 7, 6, 0, 0),
        )
        assert ind.ritual_type == RitualType.MORNING
        assert ind.questions_answered == {"Q?": "A."}
        assert ind.insights == []
        assert ind.action_items == []

    def test_auto_indagacao_with_insights_and_actions(self) -> None:
        """Insights and action items are preserved."""
        ind = AutoIndagacao(**_base_indagacao_kwargs())
        assert ind.insights == ["I work best in the morning."]
        assert ind.action_items == ["Open with the hardest task."]


# ---------------------------------------------------------------------------
# AutoIndagacao — ritual_type restriction
# ---------------------------------------------------------------------------


class TestAutoIndagacaoRitualType:
    """The :class:`RitualType` is restricted to the 3 journal-level values."""

    @pytest.mark.parametrize(
        "ritual_type",
        [RitualType.MORNING, RitualType.EVENING, RitualType.REVIEW],
    )
    def test_auto_indagacao_accepts_journal_rituals(self, ritual_type: RitualType) -> None:
        """All 3 journal-level rituals are accepted."""
        ind = AutoIndagacao(
            **_base_indagacao_kwargs(ritual_type=ritual_type),
        )
        assert ind.ritual_type == ritual_type

    @pytest.mark.parametrize(
        "ritual_type",
        [RitualType.HYDRATION, RitualType.MEDITATION, RitualType.SHUTDOWN],
    )
    def test_auto_indagacao_rejects_routine_rituals(
        self,
        ritual_type: RitualType,
    ) -> None:
        """Routine-internal rituals are rejected at construction."""
        with pytest.raises(ValidationError) as exc_info:
            AutoIndagacao(
                **_base_indagacao_kwargs(ritual_type=ritual_type),
            )
        assert "ritual_type" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AutoIndagacao — questions_answered validation
# ---------------------------------------------------------------------------


class TestAutoIndagacaoQuestions:
    """The ``questions_answered`` dict constraints."""

    def test_auto_indagacao_questions_answered_not_empty(self) -> None:
        """Empty dict raises :class:`ValidationError`."""
        with pytest.raises(ValidationError) as exc_info:
            AutoIndagacao(
                **_base_indagacao_kwargs(questions_answered={}),
            )
        assert "questions_answered" in str(exc_info.value)
        assert "empty" in str(exc_info.value).lower()

    def test_auto_indagacao_questions_answered_single(self) -> None:
        """A single question/answer pair is accepted."""
        ind = AutoIndagacao(
            **_base_indagacao_kwargs(
                questions_answered={"Single Q": "Single A."},
            ),
        )
        assert len(ind.questions_answered) == 1

    def test_auto_indagacao_questions_answered_eleven(self) -> None:
        """11 questions (canonical socratic count) are accepted."""
        qa = {f"Q{i}": f"A{i}" for i in range(11)}
        ind = AutoIndagacao(
            **_base_indagacao_kwargs(questions_answered=qa),
        )
        assert len(ind.questions_answered) == 11

    def test_auto_indagacao_questions_answered_max_20(self) -> None:
        """20 questions are accepted (boundary)."""
        qa = {f"q{i:02d}": f"a{i:02d}" for i in range(20)}
        ind = AutoIndagacao(
            **_base_indagacao_kwargs(questions_answered=qa),
        )
        assert len(ind.questions_answered) == 20

    def test_auto_indagacao_questions_answered_over_20_rejected(self) -> None:
        """21 questions raise :class:`ValidationError`."""
        qa = {f"q{i:02d}": f"a{i:02d}" for i in range(21)}
        with pytest.raises(ValidationError) as exc_info:
            AutoIndagacao(
                **_base_indagacao_kwargs(questions_answered=qa),
            )
        assert "questions_answered" in str(exc_info.value)
        assert "20" in str(exc_info.value)

    def test_auto_indagacao_question_max_length(self) -> None:
        """A question text of 200 chars is accepted; 201 is not."""
        ind = AutoIndagacao(
            **_base_indagacao_kwargs(
                questions_answered={"x" * 200: "A"},
            ),
        )
        assert len(next(iter(ind.questions_answered))) == 200
        with pytest.raises(ValidationError):
            AutoIndagacao(
                **_base_indagacao_kwargs(
                    questions_answered={"x" * 201: "A"},
                ),
            )

    def test_auto_indagacao_answer_max_length(self) -> None:
        """An answer text of 1000 chars is accepted; 1001 is not."""
        ind = AutoIndagacao(
            **_base_indagacao_kwargs(
                questions_answered={"Q": "x" * 1000},
            ),
        )
        assert len(next(iter(ind.questions_answered.values()))) == 1000
        with pytest.raises(ValidationError):
            AutoIndagacao(
                **_base_indagacao_kwargs(
                    questions_answered={"Q": "x" * 1001},
                ),
            )

    def test_auto_indagacao_insights_optional(self) -> None:
        """``insights`` defaults to ``[]``."""
        ind = AutoIndagacao(
            **_base_indagacao_kwargs(insights=[]),
        )
        assert ind.insights == []

    def test_auto_indagacao_insights_max_length(self) -> None:
        """Insight items capped at 500 chars."""
        ind = AutoIndagacao(
            **_base_indagacao_kwargs(insights=["x" * 500]),
        )
        assert len(ind.insights[0]) == 500
        with pytest.raises(ValidationError):
            AutoIndagacao(
                **_base_indagacao_kwargs(insights=["x" * 501]),
            )

    def test_auto_indagacao_action_items_max_length(self) -> None:
        """Action items capped at 200 chars."""
        ind = AutoIndagacao(
            **_base_indagacao_kwargs(action_items=["x" * 200]),
        )
        assert len(ind.action_items[0]) == 200
        with pytest.raises(ValidationError):
            AutoIndagacao(
                **_base_indagacao_kwargs(action_items=["x" * 201]),
            )


# ---------------------------------------------------------------------------
# AutoIndagacao — extras and JSON
# ---------------------------------------------------------------------------


class TestAutoIndagacaoExtras:
    """Extra-field rejection, immutability, and JSON roundtrip."""

    def test_auto_indagacao_rejects_unknown_fields(self) -> None:
        """``extra="forbid"`` rejects unknown field names."""
        with pytest.raises(ValidationError) as exc_info:
            AutoIndagacao(
                **_base_indagacao_kwargs(unknown_field="boom"),
            )
        assert "unknown_field" in str(exc_info.value)

    def test_auto_indagacao_is_frozen(self) -> None:
        """An :class:`AutoIndagacao` instance is frozen."""
        ind = AutoIndagacao(**_base_indagacao_kwargs())
        with pytest.raises(ValidationError):
            ind.ritual_type = RitualType.EVENING  # type: ignore[misc]

    def test_auto_indagacao_json_roundtrip(self) -> None:
        """JSON dump → load is lossless."""
        original = AutoIndagacao(**_base_indagacao_kwargs())
        payload = original.model_dump_json()
        restored = AutoIndagacao.model_validate_json(payload)
        assert restored.id == original.id
        assert restored.journal_entry_id == original.journal_entry_id
        assert restored.ritual_type == original.ritual_type
        assert restored.questions_answered == original.questions_answered
        assert restored.insights == original.insights
        assert restored.action_items == original.action_items
        assert restored.created_at == original.created_at

    def test_auto_indagacao_id_pattern_enforced(self) -> None:
        """``id`` must match the :data:`UEID` pattern."""
        with pytest.raises(ValidationError):
            AutoIndagacao(
                **_base_indagacao_kwargs(id="InvalidID"),
            )

    def test_auto_indagacao_journal_id_pattern_enforced(self) -> None:
        """``journal_entry_id`` must match the :data:`UEID` pattern."""
        with pytest.raises(ValidationError):
            AutoIndagacao(
                **_base_indagacao_kwargs(journal_entry_id="BadID"),
            )


# ---------------------------------------------------------------------------
# Cross-entity — JSON in a dict
# ---------------------------------------------------------------------------


class TestJournalJsonInContainer:
    """Entities survive a JSON encode/decode through a container."""

    def test_journal_and_indagacao_round_trip(self) -> None:
        """A bundle of both entities round-trips through JSON."""
        entry = JournalEntry(**_base_journal_kwargs())
        ind = AutoIndagacao(**_base_indagacao_kwargs())
        bundle = json.dumps(
            {
                "entry": entry.model_dump(mode="json"),
                "indagacao": ind.model_dump(mode="json"),
            },
        )
        loaded = json.loads(bundle)
        assert JournalEntry.model_validate(loaded["entry"]).id == entry.id
        assert (
            AutoIndagacao.model_validate(loaded["indagacao"]).id == ind.id
        )
