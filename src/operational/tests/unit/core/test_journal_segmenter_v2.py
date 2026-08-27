"""Unit tests for :mod:`operational.core.journal_segmenter` v2 — with NL logs.

These tests cover the integration of ``RoutineLog`` and
``AjusteFino`` into the per-period segment rendering.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from operational.core.journal_segmenter import (
    render_full_day_report,
    render_natural_language_report,
    render_period_summary,
    segment_journal_by_period,
)
from operational.entities.ajuste_fino import AjusteFino
from operational.entities.journal import JournalEntry
from operational.entities.routine import RoutineLog
from operational.enums import Period, RoutineType


def _make_journal(
    text: str = "",
    periods_covered: set[Period] | None = None,
    energia_nivel: int | None = None,
    foco_nivel: int | None = None,
    pomodoros: int = 0,
) -> JournalEntry:
    return JournalEntry(
        id=f"jnl_{hash(text) & 0xFFFFFFFF:08x}",
        date=date(2026, 6, 7),
        entry_text=text,
        periods_covered=periods_covered or set(),
        energia_nivel=energia_nivel,
        foco_nivel=foco_nivel,
        pomodoros_completos=pomodoros,
        created_at=datetime(2026, 6, 7, 20, 0),
    )


def _make_routine_log(
    log_id: str,
    routine_id: str,
    period: Period,
    routine_type: RoutineType,
    text: str,
    date_: date = date(2026, 6, 7),
    energia: int | None = None,
    foco: int | None = None,
) -> RoutineLog:
    return RoutineLog(
        id=log_id if "_" in log_id else f"rlog_{log_id}",
        routine_id=routine_id if "_" in routine_id else f"rou_{routine_id}",
        date=date_,
        period=period,
        routine_type=routine_type,
        text=text,
        energia_nivel=energia,
        foco_nivel=foco,
        created_at=datetime(2026, 6, 7, 4, 5),
    )


def _make_ajuste(
    ajuste_id: str,
    period: Period,
    minutos: int,
    reason: str,
    date_: date = date(2026, 6, 7),
) -> AjusteFino:
    return AjusteFino(
        id=ajuste_id if "_" in ajuste_id else f"aju_{ajuste_id}",
        date=date_,
        period=period,
        minutos=minutos,
        reason=reason,
        created_at=datetime(2026, 6, 7, 5, 30),
    )


# ---------------------------------------------------------------------------
# segment_journal_by_period with routine_logs
# ---------------------------------------------------------------------------


class TestSegmentWithRoutineLogs:
    """Tests for segment_journal_by_period with NL routine logs."""

    def test_segment_attaches_routine_logs(self) -> None:
        log = _make_routine_log(
            "rlog_1", "rou_acordar", Period.MANHA, RoutineType.ENTRY,
            "Acordei bem, 7h sono",
        )
        journal = _make_journal(
            "Manhã: acordei.",
            periods_covered={Period.MANHA},
        )
        report = segment_journal_by_period(journal, routine_logs=[log])
        assert len(report.segments) == 1
        assert len(report.segments[0].routine_logs) == 1
        assert report.segments[0].routine_logs[0].text == "Acordei bem, 7h sono"

    def test_segment_filters_routine_logs_by_date(self) -> None:
        # Log on a different date should NOT be attached
        log_other_date = _make_routine_log(
            "rlog_x", "rou_x", Period.MANHA, RoutineType.ENTRY,
            "Yesterday's log",
            date_=date(2026, 6, 6),  # different date
        )
        log_today = _make_routine_log(
            "rlog_y", "rou_y", Period.MANHA, RoutineType.ENTRY,
            "Today's log",
        )
        journal = _make_journal("Manhã: x", {Period.MANHA})
        report = segment_journal_by_period(
            journal, routine_logs=[log_other_date, log_today],
        )
        assert len(report.segments[0].routine_logs) == 1
        assert report.segments[0].routine_logs[0].id == "rlog_y"

    def test_segment_attaches_ajustes_finos(self) -> None:
        ajuste = _make_ajuste(
            "aju_1", Period.MANHA, 5, "Extended break",
        )
        journal = _make_journal("Manhã: x", {Period.MANHA})
        report = segment_journal_by_period(journal, ajustes_finos=[ajuste])
        assert len(report.segments[0].ajustes_finos) == 1
        assert report.segments[0].ajustes_finos[0].minutos == 5

    def test_segment_combines_routine_logs_and_ajustes(self) -> None:
        log = _make_routine_log(
            "rlog_1", "rou_acordar", Period.MANHA, RoutineType.ENTRY,
            "Acordei",
        )
        ajuste = _make_ajuste("aju_1", Period.MANHA, 10, "Extra break")
        journal = _make_journal("Manhã: x", {Period.MANHA})
        report = segment_journal_by_period(
            journal, routine_logs=[log], ajustes_finos=[ajuste],
        )
        seg = report.segments[0]
        assert len(seg.routine_logs) == 1
        assert len(seg.ajustes_finos) == 1


# ---------------------------------------------------------------------------
# render_period_summary with NL data
# ---------------------------------------------------------------------------


class TestRenderPeriodSummaryWithNL:
    """Tests for render_period_summary with NL data."""

    def test_summary_includes_routine_logs_count(self) -> None:
        seg = _make_segment_with(
            period=Period.MANHA,
            text="x",
            routine_logs=[
                _make_routine_log("r1", "r1", Period.MANHA, RoutineType.ENTRY, "a"),
                _make_routine_log("r2", "r2", Period.MANHA, RoutineType.CORE, "b"),
            ],
        )
        summary = render_period_summary(seg)
        assert "2 log(s) de rotina" in summary

    def test_summary_includes_ajustes_minutes(self) -> None:
        seg = _make_segment_with(
            period=Period.TARDE,
            text="x",
            ajustes_finos=[
                _make_ajuste("a1", Period.TARDE, 10, "extra"),
                _make_ajuste("a2", Period.TARDE, -5, "reduced"),
            ],
        )
        summary = render_period_summary(seg)
        assert "+5min ajustes" in summary

    def test_summary_negative_ajustes(self) -> None:
        seg = _make_segment_with(
            period=Period.MANHA,
            text="x",
            ajustes_finos=[_make_ajuste("a1", Period.MANHA, -10, "skip")],
        )
        summary = render_period_summary(seg)
        assert "-10min ajustes" in summary


def _make_segment_with(
    period: Period,
    text: str = "",
    routine_logs: list[RoutineLog] | None = None,
    ajustes_finos: list[AjusteFino] | None = None,
) -> object:
    """Helper to build a JournalSegment for testing."""
    from operational.core.journal_segmenter import JournalSegment

    return JournalSegment(
        period=period,
        text=text,
        energia_nivel=None,
        foco_nivel=None,
        pomodoros_completos=0,
        routine_logs=tuple(routine_logs or ()),
        ajustes_finos=tuple(ajustes_finos or ()),
    )


# ---------------------------------------------------------------------------
# render_natural_language_report with NL data
# ---------------------------------------------------------------------------


class TestRenderReportWithNL:
    """Tests for render_natural_language_report with NL data."""

    def test_report_includes_routine_logs_section(self) -> None:
        log = _make_routine_log(
            "rlog_1", "rou_acordar", Period.MANHA, RoutineType.ENTRY,
            "Acordei bem",
            energia=9, foco=8,
        )
        journal = _make_journal("Manhã: x", {Period.MANHA})
        report = segment_journal_by_period(journal, routine_logs=[log])
        md = render_natural_language_report(report)
        assert "### Logs de Rotina" in md
        assert "Acordei bem" in md
        assert "**ENTRY**" in md
        assert "Energia: 9/10" in md
        assert "Foco: 8/10" in md

    def test_report_includes_ajustes_section(self) -> None:
        ajuste = _make_ajuste("aju_1", Period.MANHA, 5, "Extended break")
        journal = _make_journal("Manhã: x", {Period.MANHA})
        report = segment_journal_by_period(journal, ajustes_finos=[ajuste])
        md = render_natural_language_report(report)
        assert "### Ajustes Finos" in md
        assert "+5min" in md
        assert "Extended break" in md

    def test_report_negative_ajuste(self) -> None:
        ajuste = _make_ajuste("aju_1", Period.TARDE, -30, "Reduced S3")
        journal = _make_journal("Tarde: x", {Period.TARDE})
        report = segment_journal_by_period(journal, ajustes_finos=[ajuste])
        md = render_natural_language_report(report)
        assert "-30min" in md
        assert "Reduced S3" in md

    def test_report_combines_text_logs_ajustes(self) -> None:
        log = _make_routine_log(
            "rlog_1", "rou_acordar", Period.MANHA, RoutineType.ENTRY,
            "Acordei bem",
        )
        ajuste = _make_ajuste("aju_1", Period.MANHA, 5, "extra")
        journal = _make_journal(
            "Manhã: rotina correu bem.",
            {Period.MANHA},
        )
        md = render_full_day_report(
            journal, routine_logs=[log], ajustes_finos=[ajuste],
        )
        # All three should appear
        assert "rotina correu bem" in md
        assert "Acordei bem" in md
        assert "extra" in md
        assert "### Logs de Rotina" in md
        assert "### Ajustes Finos" in md
