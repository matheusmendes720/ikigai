"""Unit tests for :mod:`operational.core.journal_segmenter`."""
from __future__ import annotations

from datetime import date, datetime

import pytest

from operational.core.journal_segmenter import (
    JournalReport,
    JournalSegment,
    render_natural_language_report,
    render_period_summary,
    segment_journal_by_period,
)
from operational.entities.journal import JournalEntry
from operational.enums import Period


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


# ---------------------------------------------------------------------------
# segment_journal_by_period
# ---------------------------------------------------------------------------


class TestSegmentJournalByPeriod:
    """Tests for the segmentation logic."""

    def test_empty_text_empty_periods(self) -> None:
        journal = _make_journal()
        report = segment_journal_by_period(journal)
        assert isinstance(report, JournalReport)
        assert report.segments == ()
        assert report.full_text == ""

    def test_single_period_manha(self) -> None:
        journal = _make_journal(
            "Manhã: Acordei 4h. Hidratação OK.",
            periods_covered={Period.MANHA},
        )
        report = segment_journal_by_period(journal)
        assert len(report.segments) == 1
        assert report.segments[0].period == Period.MANHA
        assert "Acordei 4h" in report.segments[0].text
        assert "Hidratação OK" in report.segments[0].text

    def test_three_periods(self) -> None:
        text = """Manhã: acordei 4h, ritual matinal.
Tarde: 4 rounds de foco no projeto X.
Noite: arrumação da casa, leitura."""
        journal = _make_journal(text, periods_covered={Period.MANHA, Period.TARDE, Period.NOITE})
        report = segment_journal_by_period(journal)
        assert len(report.segments) == 3
        assert [s.period for s in report.segments] == [Period.MANHA, Period.TARDE, Period.NOITE]
        assert "acordei 4h" in report.segments[0].text
        assert "4 rounds" in report.segments[1].text
        assert "arrumação" in report.segments[2].text

    def test_segments_ordered_by_period_start_hour(self) -> None:
        # If user writes out of order, segments are still ordered canonically
        text = """Noite: arrumação.
Manhã: acordei 4h.
Tarde: foco no projeto."""
        journal = _make_journal(text, periods_covered={Period.MANHA, Period.TARDE, Period.NOITE})
        report = segment_journal_by_period(journal)
        assert [s.period for s in report.segments] == [Period.MANHA, Period.TARDE, Period.NOITE]

    def test_text_without_markers_defaults_to_manha(self) -> None:
        journal = _make_journal(
            "Acordei 4h. Hidratação. Ritual matinal.",
            periods_covered={Period.MANHA},
        )
        report = segment_journal_by_period(journal)
        assert len(report.segments) == 1
        assert report.segments[0].period == Period.MANHA
        assert "Acordei 4h" in report.segments[0].text

    def test_only_emits_periods_in_periods_covered(self) -> None:
        # If journal says periods_covered={MANHA} but text mentions all 3,
        # only MANHA segment is emitted.
        text = """Manhã: acordei.
Tarde: foco.
Noite: arrumação."""
        journal = _make_journal(text, periods_covered={Period.MANHA})
        report = segment_journal_by_period(journal)
        assert len(report.segments) == 1
        assert report.segments[0].period == Period.MANHA

    def test_inherits_global_fields(self) -> None:
        journal = _make_journal(
            "Manhã: acordei 4h.",
            periods_covered={Period.MANHA},
            energia_nivel=8,
            foco_nivel=7,
            pomodoros=4,
        )
        report = segment_journal_by_period(journal)
        seg = report.segments[0]
        assert seg.energia_nivel == 8
        assert seg.foco_nivel == 7
        assert seg.pomodoros_completos == 4

    def test_frozen_dataclass(self) -> None:
        journal = _make_journal("Manhã: x", {Period.MANHA})
        report = segment_journal_by_period(journal)
        seg = report.segments[0]
        with pytest.raises((AttributeError, TypeError)):
            seg.text = "y"  # type: ignore[misc]

    def test_alternative_period_markers_english(self) -> None:
        text = """morning: woke up at 4am.
afternoon: deep work.
evening: shutdown."""
        journal = _make_journal(text, {Period.MANHA, Period.TARDE, Period.NOITE})
        report = segment_journal_by_period(journal)
        assert len(report.segments) == 3
        assert "woke up" in report.segments[0].text
        assert "deep work" in report.segments[1].text
        assert "shutdown" in report.segments[2].text

    def test_alternative_pt_marker_manha_no_accent(self) -> None:
        text = "Manha: acordou 4h."
        journal = _make_journal(text, {Period.MANHA})
        report = segment_journal_by_period(journal)
        assert "acordou 4h" in report.segments[0].text


# ---------------------------------------------------------------------------
# render_period_summary
# ---------------------------------------------------------------------------


class TestRenderPeriodSummary:
    """Tests for single-period summary rendering."""

    def test_basic_summary(self) -> None:
        seg = JournalSegment(
            period=Period.MANHA,
            text="Acordei 4h, ritual matinal completo",
            energia_nivel=None,
            foco_nivel=None,
            pomodoros_completos=0,
        )
        summary = render_period_summary(seg)
        assert "**Manhã**" in summary
        assert "(3h)" in summary
        assert "Acordei 4h" in summary

    def test_summary_with_metrics(self) -> None:
        seg = JournalSegment(
            period=Period.TARDE,
            text="Foco no projeto X",
            energia_nivel=8,
            foco_nivel=9,
            pomodoros_completos=4,
        )
        summary = render_period_summary(seg)
        assert "**Tarde**" in summary
        assert "(8h)" in summary
        assert "Energia 8/10" in summary
        assert "Foco 9/10" in summary
        assert "4 pomodoros" in summary

    def test_summary_truncates_long_text(self) -> None:
        long_text = "a" * 500
        seg = JournalSegment(
            period=Period.NOITE,
            text=long_text,
            energia_nivel=None,
            foco_nivel=None,
            pomodoros_completos=0,
        )
        summary = render_period_summary(seg)
        assert "..." in summary
        assert len(summary) < 200

    def test_empty_text(self) -> None:
        seg = JournalSegment(
            period=Period.MANHA,
            text="",
            energia_nivel=None,
            foco_nivel=None,
            pomodoros_completos=0,
        )
        summary = render_period_summary(seg)
        assert "(sem registros)" in summary


# ---------------------------------------------------------------------------
# render_natural_language_report
# ---------------------------------------------------------------------------


class TestRenderNaturalLanguageReport:
    """Tests for the full markdown report generator."""

    def test_empty_report(self) -> None:
        journal = _make_journal()
        report = segment_journal_by_period(journal)
        output = render_natural_language_report(report)
        assert "# Relatório de 2026-06-07" in output
        assert "Journal vazio" in output

    def test_full_report_with_three_periods(self) -> None:
        text = """Manhã: acordei 4h, hidratação OK.
Tarde: 4 rounds de foco, 1h almoço.
Noite: arrumação da casa."""
        journal = _make_journal(
            text,
            periods_covered={Period.MANHA, Period.TARDE, Period.NOITE},
            energia_nivel=8,
            foco_nivel=7,
            pomodoros=4,
        )
        report = segment_journal_by_period(journal)
        output = render_natural_language_report(report)
        assert "# Relatório de 2026-06-07" in output
        assert "## Manhã (a partir de 3h)" in output
        assert "## Tarde (a partir de 8h)" in output
        assert "## Noite (a partir de 18h)" in output
        assert "acordei 4h" in output
        assert "**Energia:** 8/10" in output
        assert "**Foco:** 7/10" in output
        assert "**Pomodoros:** 4" in output

    def test_period_with_no_text_uses_placeholder(self) -> None:
        # Period in periods_covered but no text for it
        journal = _make_journal("", periods_covered={Period.MANHA})
        report = segment_journal_by_period(journal)
        output = render_natural_language_report(report)
        assert "_(sem registros para este período)_" in output
