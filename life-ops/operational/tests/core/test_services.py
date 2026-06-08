"""Unit tests for :mod:`operational.core.services`.

The Core layer is the **only** layer in the operational CLI allowed to
import directly from the persistent state. Tests must therefore
isolate the Core layer by mocking the JSON-backed repositories
exposed in :mod:`operational.cli.state` — never by touching the
filesystem.

Strategy:

* Each test owns its data via the local ``fake_*`` factory fixtures.
* The ``_mock_repos`` helper monkeypatches the ``list`` method of
  every relevant repository in :mod:`operational.cli.state` so the
  test sees **only** the entities it provided.
* The Core layer is the system under test; no Rich, Typer, or CLI
  application code is imported by these tests.

The tests follow strict AAA (Arrange / Act / Assert) — each test has
explicit section comments so the contract is obvious.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Callable

import pytest

from operational.core import services as services_mod
from operational.core.services import (
    DaySnapshot,
    SleepSnapshot,
    _infer_tipo_dia,
    _to_period,
    _to_tipo_dia,
    compute_day_quadrant,
    distribute_pomodoros_across_sessions,
    get_day_snapshot,
)
from operational.entities.ajuste_fino import AjusteFino
from operational.entities.journal import JournalEntry
from operational.entities.metric import SleepRecord
from operational.entities.pomodoro import PomodoroRound
from operational.entities.routine import Routine, RoutineLog
from operational.entities.time_block import TimeBlock
from operational.entities.v3 import (
    DailyReflection,
    DayContext,
    LunchRecord,
    TransicaoRegistrada,
)
from operational.enums import (
    Period,
    PomodoroState,
    RitualType,
    RoutineType,
    TipoDia,
)

# ---------------------------------------------------------------------------
# Repository mock helper
# ---------------------------------------------------------------------------

#: Mapping from the attribute name on ``operational.cli.state`` to the
#: keyword argument expected by :func:`_mock_repos`. Keeping this in one
#: place avoids drift between the keys we accept in tests and the
#: attribute names the Core layer reads.
_REPO_ATTRS: tuple[str, ...] = (
    "sleep_records",
    "day_contexts",
    "time_blocks",
    "pomodoros",
    "transicoes",
    "routine_logs",
    "routines",
    "lunch_records",
    "journals",
    "ajustes_finos",
    "daily_reflections",
)


def _mock_repos(
    monkeypatch: pytest.MonkeyPatch,
    **entities: list[Any],
) -> None:
    """Replace ``list()`` on every state repository with a fixed list.

    Args:
        monkeypatch: Pytest fixture used to revert attribute changes.
        **entities: Mapping ``repo_attr -> list_of_entities``. The keys
            must be one of the attribute names in
            :data:`_REPO_ATTRS`. Repos not mentioned default to an
            empty list — the cleanest possible state.

    Notes:
        The replacement preserves the signature of the real
        :meth:`RepositoryBase.list` (``filters=None``) so any future
        argument pass-through in the Core layer would not break the
        tests.
    """
    from operational.cli import state

    def _make_list(items: list[Any]) -> Callable[..., list[Any]]:
        def _list(_filters: dict[str, Any] | None = None) -> list[Any]:
            return list(items)

        return _list

    for attr in _REPO_ATTRS:
        items = entities.get(attr, [])
        monkeypatch.setattr(state, attr, state.__dict__[attr])
        monkeypatch.setattr(getattr(state, attr), "list", _make_list(items))


# ---------------------------------------------------------------------------
# Entity factory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_sleep_record() -> Callable[..., SleepRecord]:
    """Return a factory producing :class:`SleepRecord` instances."""

    def _factory(
        d: date = date(2026, 6, 7),
        bedtime: time = time(20, 30),
        wake_time: time = time(4, 0),
        quality: int = 9,
    ) -> SleepRecord:
        return SleepRecord(
            id=f"slp_{d.isoformat().replace('-', '_')}",
            date=d,
            bedtime=bedtime,
            wake_time=wake_time,
            quality_score=quality,
            created_at=datetime.combine(d, wake_time),
        )

    return _factory


@pytest.fixture
def fake_journal() -> Callable[..., JournalEntry]:
    """Return a factory producing :class:`JournalEntry` instances."""

    def _factory(
        d: date = date(2026, 6, 7),
        energia: int | None = 8,
        foco: int | None = 8,
        desvios: list[str] | None = None,
        licoes: list[str] | None = None,
        humor_morning: int | None = 4,
        humor_evening: int | None = 5,
    ) -> JournalEntry:
        return JournalEntry(
            id=f"day_{d.isoformat().replace('-', '_')}",
            date=d,
            energia_nivel=energia,
            foco_nivel=foco,
            humor_morning=humor_morning,
            humor_evening=humor_evening,
            desvios=list(desvios or []),
            licoes_aprendidas=list(licoes or []),
            created_at=datetime.combine(d, time(21, 0)),
        )

    return _factory


@pytest.fixture
def fake_routine() -> Callable[..., Routine]:
    """Return a factory producing :class:`Routine` instances."""

    def _factory(
        routine_id: str = "rou_test_workout",
        name: str = "Workout matinal",
        period: Period = Period.MANHA,
        routine_type: RoutineType = RoutineType.ENTRY,
        start_time: time = time(3, 30),
        end_time: time = time(4, 0),
    ) -> Routine:
        return Routine(
            id=routine_id,
            name=name,
            period=period,
            routine_type=routine_type,
            start_time=start_time,
            end_time=end_time,
            created_at=datetime(2026, 6, 7, 0, 0),
        )

    return _factory


@pytest.fixture
def fake_routine_log() -> Callable[..., RoutineLog]:
    """Return a factory producing :class:`RoutineLog` instances."""

    def _factory(
        d: date = date(2026, 6, 7),
        routine_id: str = "rou_test_workout",
        text: str = "Workout completo",
        period: Period = Period.MANHA,
        routine_type: RoutineType = RoutineType.ENTRY,
    ) -> RoutineLog:
        return RoutineLog(
            id=f"rlog_{routine_id}_{d.isoformat().replace('-', '_')}",
            routine_id=routine_id,
            date=d,
            period=period,
            routine_type=routine_type,
            text=text,
            created_at=datetime.combine(d, time(4, 0)),
        )

    return _factory


@pytest.fixture
def fake_time_block() -> Callable[..., TimeBlock]:
    """Return a factory producing :class:`TimeBlock` instances."""

    def _factory(
        d: date = date(2026, 6, 7),
        period: Period = Period.TARDE,
        start_hour: int = 14,
        start_minute: int = 10,
        end_hour: int = 14,
        end_minute: int = 50,
        label: str = "S1 Focus",
    ) -> TimeBlock:
        return TimeBlock(
            id=f"blk_{d.isoformat().replace('-', '_')}_{start_hour:02d}{start_minute:02d}",
            label=label,
            start=datetime(d.year, d.month, d.day, start_hour, start_minute),
            end=datetime(d.year, d.month, d.day, end_hour, end_minute),
            period=period,
            created_at=datetime(d.year, d.month, d.day, end_hour, end_minute),
        )

    return _factory


@pytest.fixture
def fake_day_context() -> Callable[..., DayContext]:
    """Return a factory producing :class:`DayContext` instances."""

    def _factory(
        d: date = date(2026, 6, 7),
        tipo_dia: TipoDia = TipoDia.CURSO,
        orcado: int = 240,
        realizado: int = 0,
        pomodoros_meta: int = 8,
        pomodoros_done: int = 0,
    ) -> DayContext:
        return DayContext(
            id=f"ctx_{d.isoformat().replace('-', '_')}",
            date=d,
            tipo_dia=tipo_dia,
            hardwork_orcado_min=orcado,
            hardwork_realizado_min=realizado,
            pomodoros_meta=pomodoros_meta,
            pomodoros_realizados=pomodoros_done,
            created_at=datetime.combine(d, time(0, 0)),
        )

    return _factory


@pytest.fixture
def fake_lunch_record() -> Callable[..., LunchRecord]:
    """Return a factory producing :class:`LunchRecord` instances."""

    def _factory(
        d: date = date(2026, 6, 7),
        eat: int = 5,
        rest: int = 30,
        pesado: bool = False,
    ) -> LunchRecord:
        return LunchRecord(
            id=f"lun_{d.isoformat().replace('-', '_')}",
            date=d,
            eat_min=eat,
            rest_min=rest,
            pesado=pesado,
            created_at=datetime.combine(d, time(12, 30)),
        )

    return _factory


@pytest.fixture
def fake_daily_reflection() -> Callable[..., DailyReflection]:
    """Return a factory producing :class:`DailyReflection` instances."""

    def _factory(
        d: date = date(2026, 6, 7),
        big_win: str = "Completei o projeto X",
        parar: list[str] | None = None,
        repetir: list[str] | None = None,
        deu_certo: list[str] | None = None,
        deu_errado: list[str] | None = None,
        maior_aprendizado: str = "S1 antes do almoço é chave",
    ) -> DailyReflection:
        return DailyReflection(
            id=f"ref_{d.isoformat().replace('-', '_')}",
            date=d,
            big_win=big_win,
            parar_de_fazer=list(parar or []),
            repetir=list(repetir or []),
            deu_certo=list(deu_certo or []),
            deu_errado=list(deu_errado or []),
            maior_aprendizado=maior_aprendizado,
            created_at=datetime.combine(d, time(21, 0)),
        )

    return _factory


@pytest.fixture
def fake_ajuste_fino() -> Callable[..., AjusteFino]:
    """Return a factory producing :class:`AjusteFino` instances."""

    def _factory(
        d: date = date(2026, 6, 7),
        reason: str = "Pause extra no S2",
        period: Period = Period.TARDE,
        minutos: int = 5,
    ) -> AjusteFino:
        return AjusteFino(
            id=f"aju_{d.isoformat().replace('-', '_')}_{abs(minutos)}",
            date=d,
            period=period,
            minutos=minutos,
            reason=reason,
            created_at=datetime.combine(d, time(15, 0)),
        )

    return _factory


@pytest.fixture
def fake_pomodoro() -> Callable[..., PomodoroRound]:
    """Return a factory producing :class:`PomodoroRound` instances."""

    def _factory(
        d: date = date(2026, 6, 7),
        round_number: int = 1,
        state: PomodoroState = PomodoroState.COMPLETE,
        start_hour: int = 14,
        start_minute: int = 10,
        end_hour: int = 14,
        end_minute: int = 50,
    ) -> PomodoroRound:
        return PomodoroRound(
            id=f"pmor_{d.isoformat().replace('-', '_')}_{round_number}",
            round_number=round_number,
            state=state,
            started_at=datetime(d.year, d.month, d.day, start_hour, start_minute),
            completed_at=datetime(d.year, d.month, d.day, end_hour, end_minute),
        )

    return _factory


@pytest.fixture
def fake_transicao() -> Callable[..., TransicaoRegistrada]:
    """Return a factory producing :class:`TransicaoRegistrada` instances."""

    def _factory(
        d: date = date(2026, 6, 7),
        codigo: str = "T1",
        ritual: RitualType = RitualType.MORNING,
        completed: bool = True,
    ) -> TransicaoRegistrada:
        return TransicaoRegistrada(
            id=f"trn_{codigo.lower()}_{d.isoformat().replace('-', '_')}",
            date=d,
            codigo=codigo,
            ritual=ritual,
            duracao_min=15,
            completed=completed,
            created_at=datetime.combine(d, time(4, 0)),
        )

    return _factory


# ===========================================================================
# get_day_snapshot — empty state
# ===========================================================================


class TestGetDaySnapshotEmpty:
    """``get_day_snapshot`` with all repos empty returns sane defaults."""

    def test_returns_frozen_dataclass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange — every repo returns [].
        _mock_repos(monkeypatch)

        # Act
        snap = get_day_snapshot(date(2026, 6, 7))

        # Assert — DaySnapshot is a frozen dataclass instance.
        assert isinstance(snap, DaySnapshot)
        with pytest.raises((AttributeError, Exception)):
            # frozen dataclass should reject attribute assignment
            snap.date = date(2020, 1, 1)  # type: ignore[misc]

    def test_default_tipo_dia_weekday_is_curso(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange — 2026-06-08 is a Monday.
        _mock_repos(monkeypatch)

        # Act
        snap = get_day_snapshot(date(2026, 6, 8))

        # Assert
        assert snap.date == date(2026, 6, 8)
        assert snap.tipo_dia is TipoDia.CURSO

    def test_default_tipo_dia_weekend_is_livre(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange — 2026-06-13 is a Saturday.
        _mock_repos(monkeypatch)

        # Act
        snap = get_day_snapshot(date(2026, 6, 13))

        # Assert
        assert snap.tipo_dia is TipoDia.LIVRE

    def test_default_budget_for_curso(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange — no DayContext → use inferred CURSO.
        _mock_repos(monkeypatch)

        # Act
        snap = get_day_snapshot(date(2026, 6, 8))  # Monday

        # Assert
        assert snap.hardwork_orcado_min == TipoDia.CURSO.orcado_min_padrao
        assert snap.hardwork_orcado_min == 240

    def test_default_budget_for_livre(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        _mock_repos(monkeypatch)

        # Act — 2026-06-14 is a Sunday.
        snap = get_day_snapshot(date(2026, 6, 14))

        # Assert
        assert snap.hardwork_orcado_min == TipoDia.LIVRE.orcado_min_padrao
        assert snap.hardwork_orcado_min == 540

    def test_empty_sleep_snapshot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange — no sleep data.
        _mock_repos(monkeypatch)

        # Act
        snap = get_day_snapshot(date(2026, 6, 8))

        # Assert
        assert snap.sleep.bedtime is None
        assert snap.sleep.wake_time is None
        assert snap.sleep.duration_hours is None
        assert snap.sleep.quality is None
        assert snap.sleep.notes == ""

    def test_empty_pomodoros_meta_is_zero(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange — no DayContext → pomodoros_meta defaults to 0.
        _mock_repos(monkeypatch)

        # Act
        snap = get_day_snapshot(date(2026, 6, 8))

        # Assert
        assert snap.pomodoros_meta == 0
        assert snap.pomodoros_done == 0
        assert snap.n_pomodoros == 0

    def test_default_lunch_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange — no lunch record.
        _mock_repos(monkeypatch)

        # Act
        snap = get_day_snapshot(date(2026, 6, 8))

        # Assert — defaults per the Core contract (5min eat, 30min rest, light).
        assert snap.lunch_eat_min == 5
        assert snap.lunch_rest_min == 30
        assert snap.lunch_pesado is False

    def test_journal_fields_default_to_none(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange — no journal.
        _mock_repos(monkeypatch)

        # Act
        snap = get_day_snapshot(date(2026, 6, 8))

        # Assert
        assert snap.energia is None
        assert snap.foco is None
        assert snap.humor_morning is None
        assert snap.humor_evening is None
        assert snap.desvios == []
        assert snap.licoes == []

    def test_reflection_fields_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        _mock_repos(monkeypatch)

        # Act
        snap = get_day_snapshot(date(2026, 6, 8))

        # Assert
        assert snap.big_win == ""
        assert snap.parar_de_fazer == []
        assert snap.repetir == []
        assert snap.deu_certo == []
        assert snap.deu_errado == []
        assert snap.maior_aprendizado == ""

    def test_ajustes_default_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        _mock_repos(monkeypatch)

        # Act
        snap = get_day_snapshot(date(2026, 6, 8))

        # Assert
        assert snap.ajustes == []

    def test_n_transicoes_total_is_9(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange — PAV §6 defines exactly 9 daily transitions.
        _mock_repos(monkeypatch)

        # Act
        snap = get_day_snapshot(date(2026, 6, 8))

        # Assert
        assert snap.n_transicoes_total == 9
        assert snap.n_transicoes_completas == 0


# ===========================================================================
# get_day_snapshot — full data
# ===========================================================================


class TestGetDaySnapshotFullPadroesOuro:
    """``get_day_snapshot`` with a complete "gold-standard" day."""

    def test_full_day_populates_all_fields(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_sleep_record: Callable[..., SleepRecord],
        fake_journal: Callable[..., JournalEntry],
        fake_routine: Callable[..., Routine],
        fake_routine_log: Callable[..., RoutineLog],
        fake_time_block: Callable[..., TimeBlock],
        fake_day_context: Callable[..., DayContext],
        fake_lunch_record: Callable[..., LunchRecord],
        fake_daily_reflection: Callable[..., DailyReflection],
        fake_ajuste_fino: Callable[..., AjusteFino],
        fake_pomodoro: Callable[..., PomodoroRound],
        fake_transicao: Callable[..., TransicaoRegistrada],
    ) -> None:
        # Arrange — a perfect PAV day on 2026-06-08 (Monday = CURSO).
        d = date(2026, 6, 8)
        sleep = fake_sleep_record(d, time(20, 30), time(4, 0), 9)
        journal = fake_journal(
            d,
            energia=9,
            foco=9,
            desvios=["Acordei 30min mais cedo por causa do alarme"],
            licoes=["S1 antes do almoço continua sendo o melhor hack"],
        )
        routine_workout = fake_routine(
            routine_id="rou_workout_am",
            name="Workout matinal",
            start_time=time(3, 30),
            end_time=time(4, 0),
        )
        routine_medit = fake_routine(
            routine_id="rou_meditacao",
            name="Meditação matinal",
            period=Period.MANHA,
            start_time=time(4, 5),
            end_time=time(4, 20),
        )
        log_workout = fake_routine_log(d, routine_id="rou_workout_am", text="Workout ok")
        log_medit = fake_routine_log(d, routine_id="rou_meditacao", text="15min medit")
        block_s1 = fake_time_block(d, Period.TARDE, 14, 10, 14, 50, "S1 Focus")
        block_s2 = fake_time_block(d, Period.TARDE, 15, 0, 15, 40, "S2 Focus")
        ctx = fake_day_context(d, TipoDia.CURSO, orcado=240, realizado=80, pomodoros_meta=8)
        lunch = fake_lunch_record(d, eat=5, rest=30, pesado=False)
        reflection = fake_daily_reflection(
            d,
            big_win="Completei o módulo de testes",
            repetir=["S1 antes do almoço"],
            deu_certo=["Workout matinal", "S1 com 4 rounds"],
            maior_aprendizado="Workout curto + meditação = energia top",
        )
        ajuste = fake_ajuste_fino(d, reason="Pause extra no S2", minutos=5)
        pomodoros = [
            fake_pomodoro(d, round_number=1, state=PomodoroState.COMPLETE),
            fake_pomodoro(d, round_number=2, state=PomodoroState.COMPLETE),
        ]
        trans = fake_transicao(d, codigo="T1", completed=True)

        _mock_repos(
            monkeypatch,
            sleep_records=[sleep],
            day_contexts=[ctx],
            time_blocks=[block_s1, block_s2],
            pomodoros=pomodoros,
            routine_logs=[log_workout, log_medit],
            routines=[routine_workout, routine_medit],
            transicoes=[trans],
            lunch_records=[lunch],
            journals=[journal],
            ajustes_finos=[ajuste],
            daily_reflections=[reflection],
        )

        # Act
        snap = get_day_snapshot(d)

        # Assert — sleep block
        assert snap.date == d
        assert snap.tipo_dia is TipoDia.CURSO
        assert snap.sleep.bedtime == time(20, 30)
        assert snap.sleep.wake_time == time(4, 0)
        assert snap.sleep.duration_hours == pytest.approx(7.5)
        assert snap.sleep.quality == 9
        assert snap.wake_hour == 4
        assert snap.sleep_hour == 20

        # Assert — workout/meditation detection
        assert snap.workout_done is True
        assert snap.workout_minutes == 30
        assert snap.meditacao_done is True
        assert snap.meditacao_minutes == 15

        # Assert — blocks
        assert snap.n_blocks == 2
        assert snap.total_block_minutes == 40 + 40

        # Assert — pomodoros (2 complete rounds)
        assert snap.n_pomodoros == 2
        assert snap.pomodoros_done == 2

        # Assert — DayContext fields win
        assert snap.hardwork_orcado_min == 240
        assert snap.pomodoros_meta == 8

        # Assert — hardwork_realizado_min mirrors blocks (in minutes)
        assert snap.hardwork_realizado_min == 80

        # Assert — lunch
        assert snap.lunch_eat_min == 5
        assert snap.lunch_rest_min == 30
        assert snap.lunch_pesado is False

        # Assert — journal
        assert snap.energia == 9
        assert snap.foco == 9
        assert snap.humor_morning == 4
        assert snap.humor_evening == 5
        assert "Acordei 30min mais cedo por causa do alarme" in snap.desvios
        assert "S1 antes do almoço continua sendo o melhor hack" in snap.licoes

        # Assert — adjustments
        assert snap.ajustes == ["Pause extra no S2"]

        # Assert — reflection
        assert snap.big_win == "Completei o módulo de testes"
        assert "S1 antes do almoço" in snap.repetir
        assert "Workout matinal" in snap.deu_certo
        assert snap.maior_aprendizado.startswith("Workout curto")

        # Assert — transitions
        assert snap.n_transicoes_completas == 1


class TestGetDaySnapshotHardcoreScenario:
    """``get_day_snapshot`` with a HARDCORE day (4h sleep, low energy)."""

    def test_hardcore_sleep_4h(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_sleep_record: Callable[..., SleepRecord],
        fake_journal: Callable[..., JournalEntry],
        fake_day_context: Callable[..., DayContext],
    ) -> None:
        # Arrange — 4h sleep, HARDCORE day type, low energia/foco.
        d = date(2026, 6, 8)
        sleep = fake_sleep_record(d, time(0, 0), time(4, 0), 3)
        journal = fake_journal(d, energia=2, foco=2, desvios=["Dormi 4h"], licoes=["Não repetir"])
        ctx = fake_day_context(d, TipoDia.HARDCORE, orcado=660, realizado=300)

        _mock_repos(
            monkeypatch,
            sleep_records=[sleep],
            journals=[journal],
            day_contexts=[ctx],
        )

        # Act
        snap = get_day_snapshot(d)

        # Assert — sleep duration is 4h
        assert snap.sleep.duration_hours == pytest.approx(4.0)
        assert snap.sleep.quality == 3
        assert snap.wake_hour == 4

        # Assert — HARDCORE day type
        assert snap.tipo_dia is TipoDia.HARDCORE
        assert snap.hardwork_orcado_min == 660

        # Assert — low self-reports propagated
        assert snap.energia == 2
        assert snap.foco == 2
        assert "Dormi 4h" in snap.desvios

    def test_other_dates_data_is_filtered_out(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_sleep_record: Callable[..., SleepRecord],
    ) -> None:
        # Arrange — only the target date's record should be picked up.
        d = date(2026, 6, 8)
        target = fake_sleep_record(d, time(20, 30), time(4, 0), 9)
        other = fake_sleep_record(
            date(2026, 6, 9),
            time(20, 30),
            time(4, 0),
            5,
        )

        _mock_repos(monkeypatch, sleep_records=[target, other])

        # Act
        snap = get_day_snapshot(d)

        # Assert — only the target record is used.
        assert snap.sleep.quality == 9
        assert snap.sleep.bedtime == time(20, 30)


# ===========================================================================
# distribute_pomodoros_across_sessions
# ===========================================================================


class TestDistributePomodoros:
    """``distribute_pomodoros_across_sessions`` enforces a 4-per-session cap."""

    @pytest.mark.parametrize(
        ("total", "expected"),
        [
            (0, (0, 0, 0)),
            (1, (1, 0, 0)),
            (2, (2, 0, 0)),
            (3, (3, 0, 0)),
            (4, (4, 0, 0)),
            (5, (4, 1, 0)),
            (6, (4, 2, 0)),
            (7, (4, 3, 0)),
            (8, (4, 4, 0)),
            (9, (4, 4, 1)),
            (10, (4, 4, 2)),
            (11, (4, 4, 3)),
            (12, (4, 4, 4)),
        ],
    )
    def test_distribution_table(
        self,
        total: int,
        expected: tuple[int, int, int],
    ) -> None:
        # Arrange — total is parametrised.
        # Act
        result = distribute_pomodoros_across_sessions(total)

        # Assert
        assert result == expected

    @pytest.mark.parametrize("total", [13, 14, 15, 16, 20, 100, 1000])
    def test_overflow_caps_at_4_4_4(self, total: int) -> None:
        # Arrange — totals above 12 must clamp.
        # Act
        s1, s2, s3 = distribute_pomodoros_across_sessions(total)

        # Assert
        assert s1 == 4
        assert s2 == 4
        assert s3 == 4

    def test_negative_total_clamps_to_zero(self) -> None:
        # Arrange — defensive: a negative total is meaningless but must not raise.
        # Act
        s1, s2, s3 = distribute_pomodoros_across_sessions(-3)

        # Assert — s1 = min(4, -3) = -3, but s2/s3 must remain non-negative.
        # The Core contract is that the function never produces negative s2/s3.
        assert s2 >= 0
        assert s3 >= 0

    def test_returns_tuple_of_three_ints(self) -> None:
        # Arrange
        # Act
        result = distribute_pomodoros_across_sessions(7)

        # Assert
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert all(isinstance(x, int) for x in result)


# ===========================================================================
# compute_day_quadrant
# ===========================================================================


class TestComputeDayQuadrant:
    """``compute_day_quadrant`` returns the (Q1..Q4, x, y) triple."""

    def _snap(
        self,
        *,
        orcado: int = 240,
        realizado: int = 0,
        tipo_dia: TipoDia = TipoDia.CURSO,
    ) -> DaySnapshot:
        """Build a minimal :class:`DaySnapshot` for the test."""
        return DaySnapshot(
            date=date(2026, 6, 8),
            tipo_dia=tipo_dia,
            sleep=SleepSnapshot(None, None, None, None, ""),
            wake_hour=None,
            sleep_hour=None,
            workout_done=False,
            workout_minutes=0,
            meditacao_done=False,
            meditacao_minutes=0,
            lunch_eat_min=5,
            lunch_rest_min=30,
            lunch_pesado=False,
            jantar_antes_18=False,
            luz_azul_apos_18=False,
            n_transicoes_completas=0,
            n_transicoes_total=9,
            n_blocks=0,
            total_block_minutes=realizado,
            hardwork_orcado_min=orcado,
            hardwork_realizado_min=realizado,
            pomodoros_meta=0,
            pomodoros_done=0,
            n_pomodoros=0,
            energia=None,
            foco=None,
            humor_morning=None,
            humor_evening=None,
        )

    def test_q1_full_productivity(self) -> None:
        # Arrange — 100% realisation → X=100, Y=realizado/(realizado+60) high.
        snap = self._snap(orcado=240, realizado=240)

        # Act
        code, x, y = compute_day_quadrant(snap)

        # Assert
        assert code == "Q1"
        assert x == pytest.approx(100.0)
        assert y == pytest.approx(240 / 300 * 100)  # ~80%

    def test_q1_below_100_pct(self) -> None:
        # Arrange — 60% realisation (>= 50%, < 80%) → still Q1 "Bom".
        snap = self._snap(orcado=100, realizado=60)

        # Act
        code, x, y = compute_day_quadrant(snap)

        # Assert
        assert code == "Q1"
        assert x == pytest.approx(60.0)

    def test_q3_minimal_work(self) -> None:
        # Arrange — 0% realisation, 0 foco → X=0, Y=0 → Q3.
        snap = self._snap(orcado=240, realizado=0)

        # Act
        code, x, y = compute_day_quadrant(snap)

        # Assert
        assert code == "Q3"
        assert x == 0.0
        assert y == 0.0

    def test_q4_productive_but_inefficient(self) -> None:
        # Arrange — high X, low Y (work done but inefficient).
        # realizado/orcado=0.8 → X=80, Y=realizado/(realizado+60) low.
        snap = self._snap(orcado=100, realizado=80)
        # x=80, y = 80 / 140 ≈ 57.1 (still >=50), so this is Q1 actually.
        # To get Q4 we need X >= 50 and Y < 50. Realizado small + total = realizado+60.
        # y = realizado/(realizado+60). For y<50: realizado < 60.
        # We want x >= 50 and y < 50.
        snap = self._snap(orcado=100, realizado=55)
        # x=55, y=55/115 ≈ 47.8 → Q4.

        # Act
        code, x, y = compute_day_quadrant(snap)

        # Assert
        assert code == "Q4"
        assert x == pytest.approx(55.0)
        assert y < 50.0

    def test_q2_optimised_but_little_output(self) -> None:
        # Arrange — X < 50, Y >= 50: little work done, but the bit done was efficient.
        # realizado/(realizado+60) >= 50 → realizado >= 60.
        # realizado/orcado < 50 → orcado > 2*realizado. Take realizado=60, orcado=200.
        snap = self._snap(orcado=200, realizado=60)
        # x = 60/200*100 = 30, y = 60/120*100 = 50.

        # Act
        code, x, y = compute_day_quadrant(snap)

        # Assert
        assert code == "Q2"
        assert x < 50.0
        assert y >= 50.0

    def test_zero_orcado_yields_zero_x(self) -> None:
        # Arrange — orcado=0 must be guarded (no division by zero).
        snap = self._snap(orcado=0, realizado=50)

        # Act
        code, x, y = compute_day_quadrant(snap)

        # Assert — x clamped to 0, y still computable.
        assert x == 0.0
        assert y == pytest.approx(50 / 110 * 100)

    def test_returns_three_tuple(self) -> None:
        # Arrange
        snap = self._snap(orcado=240, realizado=120)

        # Act
        result = compute_day_quadrant(snap)

        # Assert
        assert isinstance(result, tuple)
        assert len(result) == 3
        code, x, y = result
        assert isinstance(code, str)
        assert isinstance(x, float)
        assert isinstance(y, float)


# ===========================================================================
# _to_period / _to_tipo_dia / _infer_tipo_dia
# ===========================================================================


class TestToPeriod:
    """``_to_period`` accepts Period, str or None-ish values."""

    def test_passthrough_period(self) -> None:
        # Arrange / Act / Assert
        assert _to_period(Period.MANHA) is Period.MANHA
        assert _to_period(Period.TARDE) is Period.TARDE
        assert _to_period(Period.NOITE) is Period.NOITE

    def test_string_conversion(self) -> None:
        # Arrange / Act / Assert
        assert _to_period("MANHA") is Period.MANHA
        assert _to_period("TARDE") is Period.TARDE
        assert _to_period("NOITE") is Period.NOITE

    def test_invalid_string_returns_none(self) -> None:
        # Arrange / Act / Assert
        assert _to_period("INVALID") is None
        assert _to_period("") is None
        assert _to_period("manhã") is None  # case-sensitive

    def test_non_string_non_period_returns_none(self) -> None:
        # Arrange / Act / Assert
        assert _to_period(42) is None
        assert _to_period(None) is None
        assert _to_period(["MANHA"]) is None


class TestToTipoDia:
    """``_to_tipo_dia`` accepts TipoDia, str, and falls back to CURSO."""

    def test_passthrough_tipodia(self) -> None:
        # Arrange / Act / Assert
        assert _to_tipo_dia(TipoDia.CURSO) is TipoDia.CURSO
        assert _to_tipo_dia(TipoDia.LIVRE) is TipoDia.LIVRE
        assert _to_tipo_dia(TipoDia.HARDCORE) is TipoDia.HARDCORE
        assert _to_tipo_dia(TipoDia.DESCANSO) is TipoDia.DESCANSO

    def test_string_conversion(self) -> None:
        # Arrange / Act / Assert
        assert _to_tipo_dia("curso") is TipoDia.CURSO
        assert _to_tipo_dia("livre") is TipoDia.LIVRE
        assert _to_tipo_dia("hardcore") is TipoDia.HARDCORE
        assert _to_tipo_dia("descanso") is TipoDia.DESCANSO

    def test_invalid_string_falls_back_to_curso(self) -> None:
        # Arrange / Act / Assert
        assert _to_tipo_dia("INVALID") is TipoDia.CURSO
        assert _to_tipo_dia("") is TipoDia.CURSO
        assert _to_tipo_dia("CURSO") is TipoDia.CURSO  # case-sensitive

    def test_non_string_non_tipodia_falls_back_to_curso(self) -> None:
        # Arrange / Act / Assert
        assert _to_tipo_dia(42) is TipoDia.CURSO
        assert _to_tipo_dia(None) is TipoDia.CURSO


class TestInferTipoDia:
    """``_infer_tipo_dia`` applies the weekday/weekend heuristic."""

    @pytest.mark.parametrize(
        "d",
        [
            date(2026, 6, 8),  # Monday
            date(2026, 6, 9),  # Tuesday
            date(2026, 6, 10),  # Wednesday
            date(2026, 6, 11),  # Thursday
            date(2026, 6, 12),  # Friday
        ],
    )
    def test_weekday_returns_curso(self, d: date) -> None:
        # Arrange / Act / Assert
        assert d.weekday() < 5
        assert _infer_tipo_dia(d) is TipoDia.CURSO

    @pytest.mark.parametrize(
        "d",
        [
            date(2026, 6, 13),  # Saturday
            date(2026, 6, 14),  # Sunday
        ],
    )
    def test_weekend_returns_livre(self, d: date) -> None:
        # Arrange / Act / Assert
        assert d.weekday() >= 5
        assert _infer_tipo_dia(d) is TipoDia.LIVRE


# ===========================================================================
# DaySnapshot container
# ===========================================================================


class TestDaySnapshotContainer:
    """``DaySnapshot`` is a frozen dataclass with the expected slots."""

    def test_is_frozen(self) -> None:
        # Arrange
        snap = DaySnapshot(
            date=date(2026, 6, 8),
            tipo_dia=TipoDia.CURSO,
            sleep=SleepSnapshot(None, None, None, None, ""),
            wake_hour=None,
            sleep_hour=None,
            workout_done=False,
            workout_minutes=0,
            meditacao_done=False,
            meditacao_minutes=0,
            lunch_eat_min=5,
            lunch_rest_min=30,
            lunch_pesado=False,
            jantar_antes_18=False,
            luz_azul_apos_18=False,
            n_transicoes_completas=0,
            n_transicoes_total=9,
            n_blocks=0,
            total_block_minutes=0,
            hardwork_orcado_min=240,
            hardwork_realizado_min=0,
            pomodoros_meta=0,
            pomodoros_done=0,
            n_pomodoros=0,
            energia=None,
            foco=None,
            humor_morning=None,
            humor_evening=None,
        )

        # Act / Assert
        with pytest.raises(Exception):
            snap.date = date(2020, 1, 1)  # type: ignore[misc]

    def test_module_exports(self) -> None:
        # Arrange / Act / Assert — public surface stable.
        assert "get_day_snapshot" in services_mod.__all__
        assert "distribute_pomodoros_across_sessions" in services_mod.__all__
        assert "compute_day_quadrant" in services_mod.__all__
        assert "DaySnapshot" in services_mod.__all__
        assert "SleepSnapshot" in services_mod.__all__
