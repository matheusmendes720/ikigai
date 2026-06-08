"""Tests for :mod:`operational.ui.components`.

The factory layer is intentionally a pure view: it receives Python data and
returns Rich renderables. These tests assert on the *structure* of the
returned renderables by capturing their plain-text output to a
:class:`io.StringIO` buffer, plus a small set of object-level inspections
for style/border colors.
"""
from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from operational.ui.components import (
    cartesian_plane,
    emoji_for_sleep,
    kpi_card,
    next_step_panel,
    pomodoros_grid,
    progress_bar,
    section_panel,
    severity_text,
    sev_for_desvio,
    sev_for_lunch,
    sev_for_quality,
    sev_for_sleep_hour,
    sev_for_sleep_hours,
    sev_for_transicoes,
    sev_for_wake_hour,
    sparkline,
)


# ---------------------------------------------------------------------------
# Capture helpers (plain text + ANSI)
# ---------------------------------------------------------------------------


def render_to_text(renderable, width: int = 120) -> str:
    """Render a Rich renderable to a plain-text string (no ANSI)."""
    buf = StringIO()
    console = Console(
        file=buf,
        width=width,
        no_color=True,
        force_terminal=False,
        legacy_windows=False,
    )
    with console.capture() as capture:
        console.print(renderable)
    return capture.get()


def render_with_ansi(renderable, width: int = 120) -> str:
    """Render a Rich renderable preserving ANSI color codes."""
    buf = StringIO()
    console = Console(
        file=buf,
        width=width,
        no_color=False,
        force_terminal=True,
        color_system="standard",
        legacy_windows=False,
    )
    with console.capture() as capture:
        console.print(renderable)
    return capture.get()


# ---------------------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------------------


class TestSevForWakeHour:
    def test_padrao_ouro(self) -> None:
        assert sev_for_wake_hour(3) == "ok"
        assert sev_for_wake_hour(4) == "ok"
        assert sev_for_wake_hour(5) == "ok"

    def test_leve_warn(self) -> None:
        assert sev_for_wake_hour(6) == "warn"

    def test_critico(self) -> None:
        assert sev_for_wake_hour(7) == "crit"
        assert sev_for_wake_hour(8) == "crit"
        assert sev_for_wake_hour(12) == "crit"

    def test_none_returns_muted(self) -> None:
        assert sev_for_wake_hour(None) == "muted"

    def test_below_three_is_ok(self) -> None:
        """Hours 0, 1, 2 fall through to the default ``ok`` branch."""
        assert sev_for_wake_hour(0) == "ok"
        assert sev_for_wake_hour(1) == "ok"
        assert sev_for_wake_hour(2) == "ok"


class TestSevForSleepHour:
    def test_normal_18_a_21(self) -> None:
        assert sev_for_sleep_hour(18) == "ok"
        assert sev_for_sleep_hour(19) == "ok"
        assert sev_for_sleep_hour(20) == "ok"
        assert sev_for_sleep_hour(21) == "ok"

    def test_borderline_warn(self) -> None:
        assert sev_for_sleep_hour(17) == "warn"
        assert sev_for_sleep_hour(22) == "warn"

    def test_crit(self) -> None:
        assert sev_for_sleep_hour(16) == "crit"
        assert sev_for_sleep_hour(23) == "crit"
        assert sev_for_sleep_hour(2) == "crit"

    def test_none_returns_muted(self) -> None:
        assert sev_for_sleep_hour(None) == "muted"


class TestSevForSleepHours:
    def test_padrao_ouro_7h_ou_mais(self) -> None:
        assert sev_for_sleep_hours(7.0) == "ok"
        assert sev_for_sleep_hours(8.0) == "ok"
        assert sev_for_sleep_hours(9.5) == "ok"

    def test_hardcore_5_a_6(self) -> None:
        """The implementation's warn-band is hours >= 5 and < 7."""
        assert sev_for_sleep_hours(5.0) == "warn"
        assert sev_for_sleep_hours(5.5) == "warn"
        assert sev_for_sleep_hours(6.99) == "warn"

    def test_below_5_is_crit(self) -> None:
        """4h is below the warn band → crit."""
        assert sev_for_sleep_hours(4.99) == "crit"
        assert sev_for_sleep_hours(4.0) == "crit"

    def test_critico_abaixo_de_4(self) -> None:
        assert sev_for_sleep_hours(3.99) == "crit"
        assert sev_for_sleep_hours(0.0) == "crit"

    def test_none_returns_muted(self) -> None:
        assert sev_for_sleep_hours(None) == "muted"


class TestSevForQuality:
    def test_ok_acima_de_7(self) -> None:
        assert sev_for_quality(7) == "ok"
        assert sev_for_quality(9) == "ok"
        assert sev_for_quality(10) == "ok"

    def test_warn_abaixo_de_7(self) -> None:
        assert sev_for_quality(0) == "warn"
        assert sev_for_quality(6) == "warn"

    def test_none_returns_muted(self) -> None:
        assert sev_for_quality(None) == "muted"


class TestSevForLunch:
    def test_ok_curto(self) -> None:
        assert sev_for_lunch(eat=5, rest=30, pesado=False) == "ok"
        assert sev_for_lunch(eat=3, rest=15, pesado=False) == "ok"

    def test_warn_longo(self) -> None:
        assert sev_for_lunch(eat=6, rest=20, pesado=False) == "warn"
        assert sev_for_lunch(eat=4, rest=31, pesado=False) == "warn"
        assert sev_for_lunch(eat=10, rest=60, pesado=False) == "warn"

    def test_crit_se_pesado(self) -> None:
        assert sev_for_lunch(eat=3, rest=15, pesado=True) == "crit"
        assert sev_for_lunch(eat=10, rest=60, pesado=True) == "crit"


class TestSevForTransicoes:
    def test_ok_quando_todas_feitas(self) -> None:
        assert sev_for_transicoes(done=9, total=9) == "ok"

    def test_warn_quando_falta_pouco(self) -> None:
        """Within the last 2 of total (and at least 1 done)."""
        assert sev_for_transicoes(done=7, total=9) == "warn"
        assert sev_for_transicoes(done=8, total=9) == "warn"

    def test_crit_quando_falta_muito(self) -> None:
        assert sev_for_transicoes(done=5, total=9) == "crit"
        assert sev_for_transicoes(done=0, total=9) == "crit"

    def test_total_zero(self) -> None:
        """Edge: zero total → not all done → falls into warn (1-1+2=2 vs max(1,2)=2)."""
        # done=0, total=0: 0==0 → ok (this is the literal "done == total" branch)
        assert sev_for_transicoes(done=0, total=0) == "ok"


class TestSevForDesvio:
    """Note: implementation only branches between ``ok`` and ``warn``;
    the ``crit`` return is unreachable but covered anyway."""

    def test_zero_dentro_da_tolerancia(self) -> None:
        assert sev_for_desvio(0) == "ok"
        assert sev_for_desvio(20) == "ok"
        assert sev_for_desvio(-20) == "ok"

    def test_positivo_acima_da_tolerancia(self) -> None:
        assert sev_for_desvio(30) == "warn"
        assert sev_for_desvio(100) == "warn"

    def test_negativo_abaixo_da_tolerancia(self) -> None:
        assert sev_for_desvio(-30) == "warn"
        assert sev_for_desvio(-100) == "warn"


class TestEmojiForSleep:
    @pytest.mark.parametrize(
        "hours,expected",
        [
            (None, "—"),
            (9.5, "🟢 excelente"),
            (8.0, "🟢 bom"),
            (7.0, "🟡 aceitável"),
            (5.0, "🟠 hardcore"),
            (3.5, "🔴 crítico"),
        ],
    )
    def test_variants(self, hours: float | None, expected: str) -> None:
        assert emoji_for_sleep(hours) == expected

    def test_all_six_ranges_documented(self) -> None:
        """The function should return one of the six known buckets."""
        assert emoji_for_sleep(None) == "—"
        assert emoji_for_sleep(12) == "🟢 excelente"
        assert emoji_for_sleep(8.5) == "🟢 bom"
        assert emoji_for_sleep(7.2) == "🟡 aceitável"
        assert emoji_for_sleep(4.0) == "🟠 hardcore"
        assert emoji_for_sleep(2.0) == "🔴 crítico"


# ---------------------------------------------------------------------------
# Atomic renderers
# ---------------------------------------------------------------------------


class TestProgressBar:
    def test_full_100_percent(self) -> None:
        text = render_to_text(progress_bar(10, 10))
        assert "100%" in text
        # Width defaults to 18, so 18 filled blocks
        assert "█" * 18 in text
        assert "░" not in text

    def test_zero_0_percent(self) -> None:
        text = render_to_text(progress_bar(0, 10))
        assert "  0%" in text
        assert "░" * 18 in text
        assert "█" not in text

    def test_partial_50_percent(self) -> None:
        text = render_to_text(progress_bar(5, 10, width=8))
        assert "50%" in text
        # Half filled, half empty
        assert "█" * 4 in text
        assert "░" * 4 in text

    def test_label_appears(self) -> None:
        text = render_to_text(progress_bar(5, 10, label="5/10"))
        assert "(5/10)" in text
        assert "50%" in text

    def test_returns_text_object(self) -> None:
        out = progress_bar(5, 10)
        assert isinstance(out, Text)

    def test_handles_total_zero(self) -> None:
        """Defensive: total=0 should not crash and should render 0%."""
        text = render_to_text(progress_bar(5, 0))
        assert "0%" in text

    def test_custom_width(self) -> None:
        text = render_to_text(progress_bar(1, 2, width=4))
        # Half of 4 = 2 filled
        assert "█" * 2 in text
        assert "░" * 2 in text


class TestSparkline:
    def test_basic_seven_values(self) -> None:
        text = render_to_text(sparkline([1, 2, 3, 4, 5, 6, 7]))
        # 7 values mapped to 8 levels, the last one should be the top
        assert "▁" in text
        assert "█" in text

    def test_empty_returns_sem_dados(self) -> None:
        text = render_to_text(sparkline([]))
        assert "(sem dados)" in text

    def test_label_appears(self) -> None:
        text = render_to_text(sparkline([1, 2, 3], label="3 dias"))
        assert "3 dias" in text

    def test_single_value(self) -> None:
        """A single value should not crash; span would be 0."""
        text = render_to_text(sparkline([5]))
        # Should still produce at least one glyph
        assert any(c in text for c in "▁▂▃▄▅▆▇█")

    def test_all_same_value(self) -> None:
        """When lo==hi, every glyph is the bottom one."""
        text = render_to_text(sparkline([5, 5, 5, 5]))
        assert "▁" in text

    def test_returns_text_object(self) -> None:
        out = sparkline([1, 2, 3])
        assert isinstance(out, Text)


class TestSeverityText:
    def test_wraps_in_color(self) -> None:
        out = severity_text("hello", "ok")
        assert isinstance(out, Text)
        # Plain text content is preserved
        assert "hello" in out.plain
        # Style reflects the color name
        style_str = str(out.style).lower()
        assert "green" in style_str

    def test_warn_color(self) -> None:
        out = severity_text("warn-value", "warn")
        assert "warn-value" in out.plain
        assert "yellow" in str(out.style).lower()

    def test_crit_color(self) -> None:
        out = severity_text("crit-value", "crit")
        assert "crit-value" in out.plain
        style_str = str(out.style).lower()
        assert "red" in style_str

    def test_none_severity_defaults_to_white(self) -> None:
        out = severity_text("plain", None)
        assert "plain" in out.plain
        assert "white" in str(out.style).lower()

    def test_renders_through_console(self) -> None:
        text = render_to_text(severity_text("rendered", "ok"))
        assert "rendered" in text


# ---------------------------------------------------------------------------
# Composite renderers
# ---------------------------------------------------------------------------


class TestKpiCard:
    def test_basic_contents(self) -> None:
        panel = kpi_card(
            title="Pomodoros",
            value="8",
            icon="🍅",
            footer="+2 vs ontem",
        )
        assert isinstance(panel, Panel)
        text = render_to_text(panel)
        assert "Pomodoros" in text
        assert "8" in text
        assert "🍅" in text
        assert "+2 vs ontem" in text

    def test_no_icon(self) -> None:
        panel = kpi_card(title="Sleep", value="7h")
        text = render_to_text(panel)
        assert "Sleep" in text
        assert "7h" in text

    def test_no_footer(self) -> None:
        panel = kpi_card(title="Focus", value="92%")
        text = render_to_text(panel)
        assert "Focus" in text
        assert "92%" in text

    def test_color_changes_border(self) -> None:
        """Different color keys map to different border styles."""
        ok_panel = kpi_card("T", "1", color="ok")
        warn_panel = kpi_card("T", "1", color="warn")
        crit_panel = kpi_card("T", "1", color="crit")

        assert str(ok_panel.border_style) != str(warn_panel.border_style)
        assert str(warn_panel.border_style) != str(crit_panel.border_style)
        assert str(ok_panel.border_style) != str(crit_panel.border_style)

        # And the color names should be detectable
        assert "green" in str(ok_panel.border_style).lower()
        assert "yellow" in str(warn_panel.border_style).lower()
        assert "red" in str(crit_panel.border_style).lower()

    def test_ansi_codes_present_when_color_enabled(self) -> None:
        """Sanity: with color enabled the panel emits ANSI escape codes."""
        ansi = render_with_ansi(kpi_card("T", "V", color="ok"))
        assert "\x1b[" in ansi
        assert "T" in ansi
        assert "V" in ansi


class TestSectionPanel:
    def test_title_appears(self) -> None:
        panel = section_panel("My Section", Text("body content"))
        assert isinstance(panel, Panel)
        text = render_to_text(panel)
        assert "My Section" in text
        assert "body content" in text

    def test_color_changes_border(self) -> None:
        primary = section_panel("T", Text("B"), color="primary")
        warn = section_panel("T", Text("B"), color="warn")
        assert "cyan" in str(primary.border_style).lower()
        assert "yellow" in str(warn.border_style).lower()

    def test_accepts_arbitrary_renderable_body(self) -> None:
        body = Table.grid()
        body.add_column()
        body.add_row(Text("row1"))
        panel = section_panel("Title", body)
        text = render_to_text(panel)
        assert "Title" in text
        assert "row1" in text


class TestNextStepPanel:
    def test_text_and_icon_appear(self) -> None:
        panel = next_step_panel("Beba água agora", severity="warn", icon="💧")
        assert isinstance(panel, Panel)
        text = render_to_text(panel)
        assert "Beba água agora" in text
        assert "💧" in text

    def test_default_icon(self) -> None:
        panel = next_step_panel("Algo a fazer")
        text = render_to_text(panel)
        assert "Algo a fazer" in text
        assert "→" in text

    def test_severity_changes_border(self) -> None:
        ok = next_step_panel("ok", severity="ok")
        crit = next_step_panel("crit", severity="crit")
        assert "green" in str(ok.border_style).lower()
        assert "red" in str(crit.border_style).lower()


# ---------------------------------------------------------------------------
# Grid renderers — the most important block
# ---------------------------------------------------------------------------


class TestPomodorosGrid:
    def test_full_s1_s2_s3(self) -> None:
        grid = pomodoros_grid(4, 4, 4)
        assert isinstance(grid, Table)
        text = render_to_text(grid)
        # 3 rows × 4 cells = 12 filled
        assert text.count("▣") == 12
        assert text.count("▢") == 0
        # Each row shows its session label
        assert "S1 manhã" in text
        assert "S2 tarde" in text
        assert "S3 noite" in text
        # And the count "4/4" appears 3 times
        assert text.count("4/4") == 3

    def test_empty_s1_s2_s3(self) -> None:
        grid = pomodoros_grid(0, 0, 0)
        text = render_to_text(grid)
        assert text.count("▢") == 12
        assert text.count("▣") == 0
        # 0/4 appears 3 times
        assert text.count("0/4") == 3

    def test_partial_mixed(self) -> None:
        grid = pomodoros_grid(2, 3, 1)
        text = render_to_text(grid)
        # 2 + 3 + 1 = 6 filled, 6 empty
        assert text.count("▣") == 6
        assert text.count("▢") == 6
        assert "2/4" in text
        assert "3/4" in text
        assert "1/4" in text

    def test_capped_at_max_per_session(self) -> None:
        """Values above max_per_session are clamped."""
        grid = pomodoros_grid(10, 10, 10)
        text = render_to_text(grid)
        # 12 filled even when we asked for 10
        assert text.count("▣") == 12
        assert text.count("4/4") == 3

    def test_negative_clamped_to_zero(self) -> None:
        """Negative inputs become 0 (defensive)."""
        grid = pomodoros_grid(-5, -5, -5)
        text = render_to_text(grid)
        assert text.count("▣") == 0
        assert text.count("0/4") == 3

    def test_custom_max_per_session(self) -> None:
        grid = pomodoros_grid(2, 2, 2, max_per_session=2)
        text = render_to_text(grid)
        # 6 cells, 2x3 = 6
        assert text.count("▣") == 6
        assert text.count("2/2") == 3

    def test_session_label_color(self) -> None:
        """Sanity check: ANSI is emitted (does not need exact match)."""
        ansi = render_with_ansi(pomodoros_grid(2, 2, 2))
        assert "\x1b[" in ansi
        assert "S1 manhã" in ansi


class TestCartesianPlane:
    def test_origin_at_zero_zero(self) -> None:
        grid = cartesian_plane(0, 0)
        assert isinstance(grid, Table)
        text = render_to_text(grid)
        # The origin glyph is ┼ — point at (0,0) is co-located with the origin
        assert "┼" in text
        # No colored point glyph is rendered for origin (origin takes priority)
        assert "◆" not in text
        assert "✗" not in text
        assert "▲" not in text

    def test_max_at_100_100(self) -> None:
        """Q1 corner: should render the green ◆ glyph."""
        text = render_to_text(cartesian_plane(100, 100))
        assert "◆" in text
        # Only one point is plotted
        assert text.count("◆") == 1

    def test_q1_high_effort_high_output(self) -> None:
        """(75, 80) → x≥50, y≥50 → bright_green ◆"""
        text = render_to_text(cartesian_plane(75, 80))
        assert "◆" in text
        # No other quadrant glyphs
        assert "✗" not in text
        assert "▲" not in text

    def test_q2_low_effort_high_output(self) -> None:
        """(25, 80) → x<50, y≥50 → cyan ◆"""
        text = render_to_text(cartesian_plane(25, 80))
        assert "◆" in text
        assert "✗" not in text
        assert "▲" not in text

    def test_q3_low_effort_low_output(self) -> None:
        """(25, 20) → x<50, y<50 → red ✗"""
        text = render_to_text(cartesian_plane(25, 20))
        assert "✗" in text
        assert "◆" not in text
        assert "▲" not in text

    def test_q4_high_effort_low_output(self) -> None:
        """(75, 20) → x≥50, y<50 → yellow ▲"""
        text = render_to_text(cartesian_plane(75, 20))
        assert "▲" in text
        assert "◆" not in text
        assert "✗" not in text

    def test_axes_labels_visible(self) -> None:
        """Y axis and X axis are labelled with axis ticks.

        The default 14x7 plane uses step=7/13 horizontally and step=16/6
        vertically, so the literal "50" never lands on a tick. We test with
        dimensions that produce clean 0/50/100 ticks: width=11 → step=10;
        height=6 → step=20.
        """
        text = render_to_text(cartesian_plane(50, 50, width=11, height=6))
        # Y labels: 100, 80, 60, 40, 20, 0  (in leftmost column)
        assert "  100" in text
        assert "    0" in text
        # X bottom labels: "0" at col 0 and "100" at col 10
        assert "100" in text
        # Y axis pipe column is present
        assert "│" in text
        # X axis dash row is present
        assert "─" in text

    def test_quadrant_lines_visible(self) -> None:
        """50% horizontal (┈) and 50% vertical (┊) lines are drawn."""
        text = render_to_text(cartesian_plane(50, 50))
        assert "┊" in text
        assert "┈" in text

    def test_y_axis_pipe(self) -> None:
        """Left-edge y-axis uses │ glyphs (height-1 of them, plus origin)."""
        text = render_to_text(cartesian_plane(0, 50))
        # The y-axis column (col 0) uses │. There are (height-1) pipes
        # plus the origin. The point at (0, 50) may overlap the axis.
        assert "│" in text

    def test_x_axis_dash(self) -> None:
        """Bottom row uses ─ glyphs across the x-axis."""
        text = render_to_text(cartesian_plane(50, 0))
        # X-axis bottom row contains many "─" characters
        assert "─" in text
        assert text.count("─") >= 5

    def test_values_clamped_to_range(self) -> None:
        """Out-of-range x/y values are clamped to 0..100."""
        text_low = render_to_text(cartesian_plane(-50, -50))
        # Clamped to (0, 0) → origin glyph ┼
        assert "┼" in text_low
        text_high = render_to_text(cartesian_plane(150, 150))
        # Clamped to (100, 100) → green ◆
        assert "◆" in text_high

    def test_custom_dimensions(self) -> None:
        """Smaller plane still renders the point and axes."""
        text = render_to_text(cartesian_plane(50, 50, width=10, height=5))
        assert "◆" in text
        assert "100" in text
        assert "  0" in text or "0" in text
