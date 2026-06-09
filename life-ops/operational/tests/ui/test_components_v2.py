"""Tests for PAV-OS v2 design system components.

These tests verify the components RENDER correctly and follow
the design tokens (no hardcoded colors/glyphs).
"""
from __future__ import annotations
import io
import os
import tempfile
from datetime import date
from pathlib import Path

import pytest
from rich.console import Console

# Set TIME_TASKER_STATE_DIR to a tmp dir BEFORE any operational import
_TMP_STATE = Path(tempfile.gettempdir()) / "time-tasker-v2-test-state"
_TMP_STATE.mkdir(parents=True, exist_ok=True)
os.environ["TIME_TASKER_STATE_DIR"] = str(_TMP_STATE)

import sys
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from operational.ui.tokens import (  # noqa: E402
    CONSOLE_WIDTH_V2, Glyph, PADDING, QUADRANT, REGIME, SEVERITY, STYLES,
)
from operational.ui.components_v2 import (  # noqa: E402
    cartesian_v2, header_v2, input_summary_v2, kpi_v2, metric_v2,
    next_step_v2, page, pomodoros_v2, progress_v2, regime_bar, section_v2,
    severity_text_v2, sparkline_v2, status_badge_v2, timeline_h_v2,
)
from operational.ui.mock_profiles import PROFILES, get_profile  # noqa: E402
from operational.ui.mock_snapshot import build_mock_snapshot  # noqa: E402


def _render(renderable) -> str:
    """Render a renderable to a string with no ANSI codes."""
    buf = io.StringIO()
    console = Console(file=buf, width=CONSOLE_WIDTH_V2, force_terminal=False, no_color=True, legacy_windows=False)
    console.print(renderable)
    return buf.getvalue()


# ===========================================================================
# Design tokens
# ===========================================================================

class TestTokens:
    def test_severity_has_8_keys(self) -> None:
        assert len(SEVERITY) == 8
        for k in ("primary", "success", "warning", "danger", "info", "muted", "accent", "inverse"):
            assert k in SEVERITY

    def test_regime_has_4_states(self) -> None:
        assert set(REGIME.keys()) == {"PUSH", "MAINTAIN", "REDUCE", "RECOVER"}
        for r in REGIME.values():
            assert r.glyph in ("▲", "◆", "▼", "✗")
            assert r.color in SEVERITY.values() or "bold" in r.color

    def test_quadrant_has_4_states(self) -> None:
        assert set(QUADRANT.keys()) == {"Q1", "Q2", "Q3", "Q4"}

    def test_console_width_is_128(self) -> None:
        assert CONSOLE_WIDTH_V2 == 128

    def test_glyph_constants(self) -> None:
        assert Glyph.POMO_DONE == "▣"
        assert Glyph.POMO_SKIP == "▢"
        assert Glyph.PT_EXCEL == "◆"
        assert Glyph.PT_CRIT == "✗"
        assert len(Glyph.SPARK_CHARS) == 8

    def test_padding_keys(self) -> None:
        assert set(PADDING.keys()) == {"xs", "sm", "md", "lg", "xl"}


# ===========================================================================
# Mock profiles
# ===========================================================================

class TestMockProfiles:
    def test_all_profiles_have_required_fields(self) -> None:
        for name, p in PROFILES.items():
            assert p.name == name
            assert p.tipo_dia is not None
            assert p.sleep_hours >= 0
            assert 0 <= p.energia <= 10
            assert 0 <= p.foco <= 10
            assert p.pomodoros_done >= 0
            assert p.pomodoros_meta >= 0

    def test_each_profile_has_distinct_quadrant(self) -> None:
        # q1=Q1, q2=Q2, q3=Q3, q4=Q4 at minimum
        assert PROFILES["q1"].quadrant == "Q1"
        assert PROFILES["q2"].quadrant == "Q2"
        assert PROFILES["q3"].quadrant == "Q3"
        assert PROFILES["q4"].quadrant == "Q4"

    def test_get_profile_raises_for_unknown(self) -> None:
        with pytest.raises(ValueError, match="Unknown mock profile"):
            get_profile("nope")

    def test_x_pct_capped_at_100(self) -> None:
        p = PROFILES["peak"]
        # peak has 600/240 = 250% but should cap at 100
        assert p.x_pct == 100.0

    def test_y_pct_capped_at_100(self) -> None:
        p = PROFILES["q1"]
        assert p.y_pct == 100.0

    def test_y_pct_uses_min_of_energia_and_foco(self) -> None:
        # q4: energia=8, foco=3 -> y=30
        assert PROFILES["q4"].y_pct == 30.0


# ===========================================================================
# Mock snapshot
# ===========================================================================

class TestMockSnapshot:
    def test_snapshot_has_all_required_fields(self) -> None:
        snap = build_mock_snapshot(PROFILES["q1"])
        assert snap.tipo_dia is not None
        assert snap.hardwork_orcado_min > 0
        assert snap.pomodoros_meta > 0

    def test_snapshot_notes_contains_mock_marker(self) -> None:
        snap = build_mock_snapshot(PROFILES["q3"])
        assert "MOCK" in snap.sleep.notes
        assert "q3" in snap.sleep.notes

    def test_empty_snapshot_has_zeros(self) -> None:
        snap = build_mock_snapshot(PROFILES["empty"])
        assert snap.hardwork_realizado_min == 0
        assert snap.n_pomodoros == 0


# ===========================================================================
# Components render without errors
# ===========================================================================

class TestComponentsRender:
    def test_kpi_v2(self) -> None:
        out = _render(kpi_v2("Sono", "8.0h", "ok", icon="😴"))
        assert "Sono" in out
        assert "8.0h" in out
        assert "😴" in out

    def test_kpi_v2_with_delta(self) -> None:
        out = _render(kpi_v2("Sono", "8.0h", "ok", delta="+0.5h 7d"))
        assert "+0.5h 7d" in out

    def test_header_v2(self) -> None:
        out = _render(header_v2("Daily Report", "2026-06-08"))
        assert "DAILY REPORT" in out
        assert "2026-06-08" in out

    def test_section_v2(self) -> None:
        out = _render(section_v2("HARDWORK", icon="💻", subtitle="Cartesian"))
        assert "HARDWORK" in out
        assert "Cartesian" in out

    def test_pomodoros_v2(self) -> None:
        out = _render(pomodoros_v2(s1_done=3, s1_focus=8.0, s2_done=2, s2_focus=6.0, s3_done=0, s3_focus=0.0))
        assert "S1 manha" in out
        assert "S2 tarde" in out
        assert "S3 noite" in out
        assert "75%" in out
        assert "50%" in out

    def test_pomodoros_v2_shows_focus_score(self) -> None:
        out = _render(pomodoros_v2(s1_done=4, s1_focus=9.0))
        assert "9/10" in out

    def test_pomodoros_v2_total(self) -> None:
        out = _render(pomodoros_v2(s1_done=4, s2_done=2, s3_done=1))
        assert "Total: 7/12" in out

    def test_sparkline_v2(self) -> None:
        out = _render(sparkline_v2([1, 2, 3, 4, 5, 6, 7, 8], "Sono"))
        assert "Sono" in out
        assert "8" in out  # current value

    def test_sparkline_v2_empty(self) -> None:
        out = _render(sparkline_v2([], "Sono"))
        assert "no data" in out

    def test_regime_bar(self) -> None:
        out = _render(regime_bar("PUSH"))
        assert "PUSH" in out
        assert "MAINTAIN" in out
        assert "RECOVER" in out

    def test_next_step_v2(self) -> None:
        out = _render(next_step_v2("Q1 mantido", "Manter ritmo", severity="success"))
        assert "OBSERVACAO" in out
        assert "Q1 mantido" in out
        assert "ACAO" in out
        assert "Manter ritmo" in out


class TestCartesian:
    def test_q1_renders(self) -> None:
        out = _render(cartesian_v2(80, 80, "Q1"))
        assert "Q1" in out
        assert "Excelente" in out

    def test_q3_renders(self) -> None:
        out = _render(cartesian_v2(20, 20, "Q3"))
        assert "Q3" in out
        assert "Critico" in out

    def test_with_history_renders_sparkline(self) -> None:
        history = [(50, 50), (60, 60), (70, 70), (80, 80), (90, 90), (85, 85), (95, 95)]
        out = _render(cartesian_v2(95, 95, "Q1", historical=history))
        assert "historico" in out

    def test_with_equation_renders(self) -> None:
        out = _render(cartesian_v2(50, 50, "Q2", show_equation=True))
        assert "realizado" in out
        assert "foco" in out


# ===========================================================================
# Page composition
# ===========================================================================

class TestPage:
    def test_page_renders_full(self) -> None:
        k1 = kpi_v2("Sono", "8.0h", "ok")
        k2 = kpi_v2("Pomodoros", "12/12", "success")
        body = section_v2("Test", content=k1)
        footer = next_step_v2("obs", "act")
        out = _render(page("Daily Report", "2026-06-08", body, footer=footer))
        assert "DAILY REPORT" in out
        assert "TEST" in out  # section_v2 uppercases
        assert "OBSERVACAO" in out


# ===========================================================================
# No ANSI leak (consistency with v1 contract)
# ===========================================================================

class TestNoAnsiLeak:
    def test_all_components_no_ansi_when_no_color(self) -> None:
        for profile_name in PROFILES:
            snap = build_mock_snapshot(PROFILES[profile_name])
            # Render a small subset to confirm
            k = kpi_v2("X", "1", "ok")
            out = _render(k)
            assert "\x1b" not in out
            assert "\x1b[" not in out


# ===========================================================================
# v1 ports — widgets added in this batch
# ===========================================================================

class TestProgressV2:
    def test_progress_v2_renders(self) -> None:
        out = _render(progress_v2(50, 100, "Hardwork", severity="success"))
        assert "Hardwork" in out
        assert "50%" in out
        assert "(50/100)" in out

    def test_progress_v2_uses_tokens(self) -> None:
        out = _render(progress_v2(10, 20, severity="success"))
        assert Glyph.BAR_FULL in out
        assert Glyph.BAR_EMPTY in out

    def test_progress_v2_zero_max_no_crash(self) -> None:
        out = _render(progress_v2(0, 0, "x", severity="warning"))
        assert "0%" in out
        assert "\x1b[" not in out

    def test_progress_v2_full_bar(self) -> None:
        out = _render(progress_v2(100, 100, "Done", severity="success"))
        assert "100%" in out
        assert Glyph.BAR_EMPTY not in out


class TestMetricV2:
    def test_metric_v2_renders(self) -> None:
        rows = [("Sono", "8.0h", "ok"), ("Pomodoros", "12/12", "ok"), ("Energia", "10/10", "ok")]
        out = _render(metric_v2(rows))
        assert "Sono" in out
        assert "8.0h" in out
        assert "Pomodoros" in out
        assert "Energia" in out

    def test_metric_v2_severity_optional(self) -> None:
        rows = [("Sono", "8.0h", None), ("Energia", "3", "warn")]
        out = _render(metric_v2(rows))
        assert "Sono" in out
        assert "Energia" in out
        assert "3" in out

    def test_metric_v2_custom_headers(self) -> None:
        rows = [("a", "1", "ok")]
        out = _render(metric_v2(rows, headers=["Key", "Value"]))
        assert "Key" in out
        assert "Value" in out

    def test_metric_v2_no_ansi_leak(self) -> None:
        rows = [("x", "1", "ok"), ("y", "2", "warn"), ("z", "3", "crit")]
        out = _render(metric_v2(rows))
        assert "\x1b[" not in out


class TestSeverityTextV2:
    def test_severity_text_v2_renders(self) -> None:
        out = _render(severity_text_v2("OK", "success"))
        assert "OK" in out

    def test_severity_text_v2_danger(self) -> None:
        out = _render(severity_text_v2("FAIL", "danger"))
        assert "FAIL" in out
        assert "\x1b[" not in out

    def test_severity_text_v2_default_info(self) -> None:
        out = _render(severity_text_v2("hi"))
        assert "hi" in out


class TestTimelineHV2:
    def test_timeline_h_v2_renders(self) -> None:
        events = [
            ("06:00", "wake", "done"),
            ("07:00", "coffee", "done"),
            ("09:00", "class", "active"),
            ("12:00", "lunch", "warning"),
            ("18:00", "dinner", "pending"),
        ]
        out = _render(timeline_h_v2(events))
        assert "06:00" in out
        assert "wake" in out
        assert "12:00" in out
        assert "lunch" in out
        assert Glyph.CHECK in out
        assert Glyph.ACTIVE in out
        assert Glyph.PENDING in out

    def test_timeline_h_v2_empty(self) -> None:
        out = _render(timeline_h_v2([]))
        assert "no events" in out

    def test_timeline_h_v2_no_ansi_leak(self) -> None:
        events = [("06:00", "a", "done"), ("12:00", "b", "warning")]
        out = _render(timeline_h_v2(events))
        assert "\x1b[" not in out


class TestStatusBadgeV2:
    def test_status_badge_v2_renders(self) -> None:
        out = _render(status_badge_v2("active", "success"))
        assert "ACTIVE" in out
        assert Glyph.ACTIVE in out

    def test_status_badge_v2_muted_uses_dot(self) -> None:
        out = _render(status_badge_v2("paused", "muted"))
        assert "PAUSED" in out
        assert Glyph.MUTED_DOT in out

    def test_status_badge_v2_no_ansi_leak(self) -> None:
        out = _render(status_badge_v2("ok", "info"))
        assert "\x1b[" not in out


class TestInputSummaryV2:
    def test_input_summary_v2_renders(self) -> None:
        items = [
            ("Nome", "Morning workout"),
            ("Período", "MANHA"),
            ("Tipo", "CORE"),
            ("Início", "06:00"),
        ]
        out = _render(input_summary_v2(items))
        assert "Nome" in out
        assert "Morning workout" in out
        assert "Período" in out
        assert "MANHA" in out
        assert "Tipo" in out
        assert "CORE" in out
        assert "Início" in out
        assert "06:00" in out

    def test_input_summary_v2_custom_title(self) -> None:
        items = [("x", "1")]
        out = _render(input_summary_v2(items, title="Echo"))
        assert "Echo" in out

    def test_input_summary_v2_empty(self) -> None:
        out = _render(input_summary_v2([]))
        assert "Você digitou" in out  # default title still in the panel
        assert "\x1b[" not in out

    def test_input_summary_v2_no_ansi_leak(self) -> None:
        items = [("a", "1"), ("b", "2")]
        out = _render(input_summary_v2(items))
        assert "\x1b[" not in out
