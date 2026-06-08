"""Composite report renderers — receives DaySnapshot, returns Rich renderable.

Each function here is a factory that takes pure data and returns a
single Rich component (Panel, Group). NO data fetching, NO
console.print() calls.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from operational.core.services import DaySnapshot, compute_day_quadrant
from operational.enums import TipoDia
from operational.ui.components import (
    COLORS,
    PERIOD_ICON,
    QUADRANT_ACTION,
    QUADRANT_COLOR,
    QUADRANT_EMOJI,
    QUADRANT_LABEL,
    TIPO_DIA_COLOR,
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
)


# ---------------------------------------------------------------------------
# Daily report
# ---------------------------------------------------------------------------


def build_header_table(snap: DaySnapshot) -> Table:
    """Cinematic header: date · tipo · quadrant emoji · pomodoros."""
    q_code, x, y = compute_day_quadrant(snap)
    tipo_color = TIPO_DIA_COLOR.get(snap.tipo_dia.value, "white")
    q_color = QUADRANT_COLOR.get(q_code, "white")
    q_emoji = QUADRANT_EMOJI.get(q_code, "·")

    grid = Table.grid(expand=False, padding=(0, 1))
    grid.add_column(justify="left", min_width=4)
    grid.add_column(justify="left", min_width=12)
    grid.add_column(justify="left", min_width=4)
    grid.add_column(justify="left", min_width=14)
    grid.add_column(justify="left", min_width=4)
    grid.add_column(justify="left", min_width=12)
    if snap.pomodoros_meta:
        grid.add_column(justify="left", min_width=4)
        grid.add_column(justify="left", min_width=8)

    row: list[RenderableType] = [
        Text("  📅  ", style="dim"),
        Text(snap.date.isoformat(), style="bold white"),
        Text("  ", style="dim"),
        Text(f"◆ {snap.tipo_dia.value.upper()}", style=f"bold {tipo_color}"),
        Text("  ", style="dim"),
        Text(f"{q_emoji} {q_code}", style=f"bold {q_color}"),
    ]
    if snap.pomodoros_meta:
        row.extend([
            Text("  ", style="dim"),
            Text(f"🍅 {snap.n_pomodoros}/{snap.pomodoros_meta}", style="bold green3"),
        ])
    grid.add_row(*row)
    return grid


def build_ease_table(snap: DaySnapshot) -> Table:
    """EASE table — 9 rows of sleep + lifestyle metrics."""
    grid = Table.grid(expand=False, padding=(0, 1))
    grid.add_column(min_width=22, justify="left")
    grid.add_column(min_width=24, justify="left")

    def row(label: str, value: str, sev: str | None) -> None:
        grid.add_row(
            Text(label, style="bold white"),
            severity_text(value, sev),
        )

    row("⏰ Acordou",
        f"{snap.wake_hour:02d}:{snap.sleep.wake_time.minute:02d}" if snap.sleep.wake_time else "—",
        sev_for_wake_hour(snap.wake_hour))
    row("🌙 Dormiu",
        f"{snap.sleep_hour:02d}:{snap.sleep.bedtime.minute:02d}" if snap.sleep.bedtime else "—",
        sev_for_sleep_hour(snap.sleep_hour))
    row("😴 Sono",
        f"{snap.sleep.duration_hours:.1f}h {emoji_for_sleep(snap.sleep.duration_hours)}" if snap.sleep.duration_hours else "—",
        sev_for_sleep_hours(snap.sleep.duration_hours))
    row("⭐ Qualidade",
        f"{snap.sleep.quality}/10" if snap.sleep.quality else "—",
        sev_for_quality(snap.sleep.quality))
    row("💪 Workout",
        f"{snap.workout_minutes}min ✓" if snap.workout_done else "não feito",
        "ok" if snap.workout_done else "warn")
    row("🧘 Meditação",
        f"{snap.meditacao_minutes}min ✓" if snap.meditacao_done else "não feita",
        "ok" if snap.meditacao_done else "warn")

    lunch_total = snap.lunch_eat_min + snap.lunch_rest_min
    lunch_marker = " ⚠️ PESADO" if snap.lunch_pesado else ""
    row("🍽️  Lunch",
        f"{snap.lunch_eat_min}min eat + {snap.lunch_rest_min}min rest = {lunch_total}min{lunch_marker}",
        sev_for_lunch(snap.lunch_eat_min, snap.lunch_rest_min, snap.lunch_pesado))
    row("🌆 Jantar < 18h",
        "sim ✓" if snap.jantar_antes_18 else "tarde (luz azul)",
        "ok" if snap.jantar_antes_18 else "warn")
    row("📱 Luz azul",
        "cortada ✓" if not snap.luz_azul_apos_18 else "exposição após 18h",
        "ok" if not snap.luz_azul_apos_18 else "warn")
    row("🔄 Transições",
        f"{snap.n_transicoes_completas}/{snap.n_transicoes_total}",
        sev_for_transicoes(snap.n_transicoes_completas, snap.n_transicoes_total))
    return grid


def build_hardwork_table(snap: DaySnapshot) -> Table:
    """HARDWORK table — tipo, orçado, realizado, desvio, pomodoros."""
    grid = Table.grid(expand=False, padding=(0, 1))
    grid.add_column(min_width=22, justify="left")
    grid.add_column(min_width=22, justify="left")

    delta = snap.hardwork_realizado_min - snap.hardwork_orcado_min
    delta_str = f"+{delta}" if delta > 0 else str(delta)
    # Classify severity
    if -20 <= delta <= 20:
        desvio_sev = "ok"
        desvio_label = "DENTRO"
    elif delta > 20:
        desvio_sev = "warn"
        desvio_label = "ACIMA" if delta <= 60 else "MUITO_ACIMA"
    else:
        desvio_sev = "crit"
        desvio_label = "ABAIXO" if delta >= -60 else "MUITO_ABAIXO"

    def row(label: str, value: str, sev: str | None) -> None:
        grid.add_row(
            Text(label, style="bold white"),
            severity_text(value, sev),
        )

    row("Tipo de Dia", snap.tipo_dia.value.upper(), None)
    row("📊 Orçado",
        f"{snap.hardwork_orcado_min}min ({snap.hardwork_orcado_min // 60}h{snap.hardwork_orcado_min % 60:02d}m)",
        None)
    row("⏱️  Realizado",
        f"{snap.hardwork_realizado_min}min ({snap.hardwork_realizado_min // 60}h{snap.hardwork_realizado_min % 60:02d}m)",
        None)
    row("Δ Desvio", f"{delta_str}min ({desvio_label})", desvio_sev)
    if snap.pomodoros_meta:
        sev = "ok" if snap.n_pomodoros >= snap.pomodoros_meta else "warn"
        row("🍅 Pomodoros",
            f"{snap.n_pomodoros}/{snap.pomodoros_meta} rounds", sev)
    return grid


def build_energia_foco_table(snap: DaySnapshot) -> Table | None:
    """Energy/Focus progress bars."""
    if not snap.energia and not snap.foco:
        return None
    grid = Table.grid(expand=False, padding=(0, 1))
    grid.add_column(min_width=12, justify="left")
    grid.add_column(justify="left")
    if snap.energia:
        grid.add_row(
            Text("⚡ Energia  ", style="bold"),
            progress_bar(snap.energia, 10, severity="ok", label=f"{snap.energia}/10"),
        )
    if snap.foco:
        grid.add_row(
            Text("🎯 Foco  ", style="bold"),
            progress_bar(snap.foco, 10, severity="ok", label=f"{snap.foco}/10"),
        )
    return grid


def build_quadrant_caption(snap: DaySnapshot) -> Text:
    """Quadrant classification + action."""
    q_code, x, y = compute_day_quadrant(snap)
    q_color = QUADRANT_COLOR.get(q_code, "white")
    caption = Text()
    caption.append(f"  {q_code}  ", style=f"bold {q_color}")
    caption.append(f"  —  {QUADRANT_LABEL.get(q_code, '—')}\n", style="white")
    caption.append(f"  Ação: {QUADRANT_ACTION.get(q_code, '—')}", style="grey58 italic")
    return caption


def build_cartesian_panel(snap: DaySnapshot) -> Panel:
    """Cartesian panel — clean plane + quadrant caption."""
    q_code, x, y = compute_day_quadrant(snap)
    plane = cartesian_plane(x, y, width=18, height=7)
    caption = build_quadrant_caption(snap)
    body = Table.grid(expand=False, padding=(0, 0))
    body.add_column(justify="left")
    body.add_row(plane)
    body.add_row(Text(" "))
    body.add_row(caption)
    return section_panel(
        f"📈 Plano Cartesiano — X: Produtividade · Y: Eficiência · Point: ({x:.0f}%, {y:.0f}%)",
        body,
        color="primary",
    )


def build_desvios_ajustes_panel(snap: DaySnapshot) -> Panel | None:
    """Combined panel: desvios + ajustes + lições."""
    if not (snap.desvios or snap.ajustes or snap.licoes):
        return None
    grid = Table.grid(expand=False, padding=(0, 1))
    grid.add_column(min_width=12, justify="left")
    grid.add_column(justify="left", min_width=80)
    for d in snap.desvios:
        grid.add_row(Text("⚠️  Desvio", style="bold yellow1"), Text(d, style="white"))
    for a in snap.ajustes:
        grid.add_row(Text("🔧 Ajuste", style="bold deep_sky_blue1"), Text(a, style="white"))
    for l in snap.licoes:
        grid.add_row(Text("📚 Lição", style="bold green3"), Text(l, style="white"))
    return section_panel("⚠️  Desvios · 🔧 Ajustes · 📚 Lições", grid, color="warn")


def build_okrs_panel(snap: DaySnapshot) -> Panel | None:
    """OKRs V3 panel — Big-Win, Parar, Repetir, Deu certo/errado, Aprendizado."""
    if not any([snap.big_win, snap.parar_de_fazer, snap.repetir,
                snap.maior_aprendizado, snap.deu_certo, snap.deu_errado]):
        return None
    grid = Table.grid(expand=False, padding=(0, 1))
    grid.add_column(min_width=20, justify="left")
    grid.add_column(justify="left", min_width=60)
    if snap.big_win:
        grid.add_row(Text("🏆 Big-Win", style="bold magenta"), Text(snap.big_win, style="white"))
    for p in snap.parar_de_fazer:
        grid.add_row(Text("❌ Parar de fazer", style="bold red"), Text(p, style="white"))
    for r in snap.repetir:
        grid.add_row(Text("✅ Repetir", style="bold green"), Text(r, style="white"))
    for c in snap.deu_certo:
        grid.add_row(Text("✅ Deu certo", style="bold green"), Text(c, style="white"))
    for e in snap.deu_errado:
        grid.add_row(Text("❌ Deu errado", style="bold red"), Text(e, style="white"))
    if snap.maior_aprendizado:
        grid.add_row(Text("💡 Maior aprendizado", style="bold cyan"), Text(snap.maior_aprendizado, style="white"))
    return section_panel("🎯 OKRs V3 — Reflexão do dia", grid, color="ease")


def build_next_step_panel(snap: DaySnapshot) -> Panel:
    """Contextual recommendation."""
    q_code, _, _ = compute_day_quadrant(snap)
    if q_code == "Q3" or (snap.sleep.duration_hours is not None and snap.sleep.duration_hours < 6):
        return next_step_panel(
            "Aplicar plano de recuperação antes de continuar. Sono < 6h ou Q3 detectado.",
            severity="crit", icon="!",
        )
    if (snap.pomodoros_meta and
        snap.hardwork_realizado_min >= snap.hardwork_orcado_min and
        snap.n_pomodoros >= snap.pomodoros_meta):
        return next_step_panel(
            "Dia dentro do padrão ouro. Manter ritmo, monitorar fadiga.",
            severity="ok", icon="✓",
        )
    return next_step_panel(
        "Ajustar próximo dia: revisar desvios e aplicar ajustes finos.",
        severity="info", icon="→",
    )


def render_daily_report(snap: DaySnapshot) -> RenderableType:
    """Build the complete daily V3 report as a single Group."""
    parts: list[RenderableType] = []
    # Header panel
    header = section_panel("⚡ DAILY REPORT", build_header_table(snap), color="primary")
    parts.append(header)
    # EASE + HARDWORK + Pomodoros Grid + Estado Subjetivo (consolidated)
    ease_panel = section_panel("😴 EASE", build_ease_table(snap), color="sleep")
    hardwork_panel = section_panel("💻 HARDWORK", build_hardwork_table(snap), color="hardwork")
    pom_grid = build_pomodoros_grid_section(snap)
    ef_panel = build_energia_foco_section(snap)

    consolidated = Table.grid(expand=False, padding=(0, 0))
    consolidated.add_column(justify="left")
    consolidated.add_row(ease_panel)
    consolidated.add_row(Text(" "))
    consolidated.add_row(hardwork_panel)
    consolidated.add_row(Text(" "))
    consolidated.add_row(pom_grid)
    if ef_panel:
        consolidated.add_row(Text(" "))
        consolidated.add_row(ef_panel)
    parts.append(consolidated)
    # Cartesian
    parts.append(build_cartesian_panel(snap))
    # Deviation/Adjustments/Lessons
    dal = build_desvios_ajustes_panel(snap)
    if dal:
        parts.append(dal)
    # OKRs
    okrs = build_okrs_panel(snap)
    if okrs:
        parts.append(okrs)
    # Next step
    parts.append(build_next_step_panel(snap))
    return Group(*parts)


def build_pomodoros_grid_section(snap: DaySnapshot) -> Panel:
    """Pomodoros grid (S1/S2/S3)."""
    from operational.core.services import distribute_pomodoros_across_sessions
    s1, s2, s3 = distribute_pomodoros_across_sessions(snap.n_pomodoros)
    grid = pomodoros_grid(s1, s2, s3)
    return section_panel(
        f"🍅 Pomodoros Grid — S1 manhã · S2 tarde · S3 noite",
        grid, color="hardwork",
    )


def build_energia_foco_section(snap: DaySnapshot) -> Panel | None:
    """Energy/Focus section panel."""
    ef_table = build_energia_foco_table(snap)
    if ef_table is None:
        return None
    return section_panel("⚡ Estado Subjetivo", ef_table, color="energy")


__all__ = [
    "render_daily_report",
]
