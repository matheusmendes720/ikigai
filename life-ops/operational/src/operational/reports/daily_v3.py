"""Daily V3 report — Cinematic Rich-rendered, fully TTY.

Story structure (5 panels total — no more 11-panel mess):
1. Cinematic header (date + scenario + tipo_dia + emoji narrative)
2. EASE + HARDWORK consolidated (single panel, two tables)
3. Plano Cartesiano (clean, big point, no grid noise)
4. Deviations / Adjustments / Lessons (single panel, sections)
5. OKRs V3 (single panel)
6. Next step (single line)
"""
from __future__ import annotations

from datetime import date

from rich.box import SIMPLE, SIMPLE_HEAD
from rich.console import Console, Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from operational.cli.renderers import (
    COLORS,
    TIPO_DIA_COLOR,
    cartesian_plane,
    kpi_card,
    make_console,
    metric_table,
    next_step,
    pomodoros_grid,
    progress_bar,
    section_header,
)
from operational.core.budget import (
    classify_infracao,
    classify_quadrant,
    productivity_pct,
    efficiency_pct,
)
from operational.enums import TipoDia

__all__ = ["generate_daily_v3_rich", "generate_daily_v3_markdown"]


def generate_daily_v3_rich(
    *,
    report_date: date,
    tipo_dia: TipoDia,
    wake_hour: int | None,
    wake_minute: int | None,
    sleep_hour: int | None,
    sleep_minute: int | None,
    sleep_hours: float | None,
    sleep_quality: int | None,
    energia: int | None,
    foco: int | None,
    workout_done: bool = False,
    workout_minutes: int = 0,
    meditacao_done: bool = False,
    meditacao_minutes: int = 0,
    lunch_eat_min: int = 5,
    lunch_rest_min: int = 30,
    lunch_pesado: bool = False,
    jantar_antes_18: bool = False,
    luz_azul_apos_18: bool = False,
    n_transicoes_completas: int = 0,
    n_transicoes_total: int = 9,
    pomodoros_s1: int = 0,
    pomodoros_s2: int = 0,
    pomodoros_s3: int = 0,
    pomodoros_meta: int = 0,
    hardwork_orcado_min: int,
    hardwork_realizado_min: int,
    n_blocks: int = 0,
    desvios: list[str] | None = None,
    licoes: list[str] | None = None,
    ajustes: list[str] | None = None,
    big_win: str = "",
    parar_de_fazer: list[str] | None = None,
    repetir: list[str] | None = None,
    maior_aprendizado: str = "",
    deu_certo: list[str] | None = None,
    deu_errado: list[str] | None = None,
) -> RenderableType:
    """Build the full Rich report as a single Group renderable."""
    console = make_console(width=120)
    console_width = 120

    desvios = desvios or []
    licoes = licoes or []
    ajustes = ajustes or []
    parar_de_fazer = parar_de_fazer or []
    repetir = repetir or []
    deu_certo = deu_certo or []
    deu_errado = deu_errado or []

    sections: list[RenderableType] = []

    # Compute quadrant in advance for header narrative
    x_preview = productivity_pct(hardwork_realizado_min, hardwork_orcado_min)
    y_preview = efficiency_pct(hardwork_realizado_min, hardwork_realizado_min + 60)
    q_preview, _, _ = classify_quadrant(x_preview, y_preview)
    tipo_color = TIPO_DIA_COLOR.get(tipo_dia.value, "white")
    q_color = COLORS.get(q_preview.lower(), "white")
    q_emoji = {"Q1": "🏆", "Q2": "🟢", "Q3": "🚨", "Q4": "⚠️"}.get(q_preview, "·")

    # ====== 1. CINEMATIC HEADER ======
    header = Text()
    header.append("\n")
    header.append("  📅  ", style="dim")
    header.append(f"{report_date.isoformat()}", style="bold white")
    header.append("    ", style="dim")
    header.append(f"◆ {tipo_dia.value.upper()}", style=f"bold {tipo_color}")
    header.append("    ", style="dim")
    header.append(f"{q_emoji} {q_preview}", style=f"bold {q_color}")
    if pomodoros_meta:
        total = pomodoros_s1 + pomodoros_s2 + pomodoros_s3
        header.append("    ", style="dim")
        header.append(f"🍅 {total}/{pomodoros_meta}", style="bold green3")
    sections.append(Panel(header, border_style="cyan", box=SIMPLE_HEAD, padding=(0, 1)))

    # ====== 2. EASE TABLE ======
    ease_rows: list[tuple[str, str, str | None]] = []
    if wake_hour is not None:
        ease_rows.append(("⏰ Acordou", f"{wake_hour:02d}:{wake_minute or 0:02d}", _severity_for_wake(wake_hour)))
    if sleep_hour is not None:
        ease_rows.append(("🌙 Dormiu", f"{sleep_hour:02d}:{sleep_minute or 0:02d}", _severity_for_sleep_hour(sleep_hour)))
    if sleep_hours is not None:
        sev = "ok" if sleep_hours >= 7 else "warn" if sleep_hours >= 5 else "crit"
        ease_rows.append(("😴 Sono", f"{sleep_hours:.1f}h {emoji_for_sleep(sleep_hours)}", sev))
    if sleep_quality is not None:
        ease_rows.append(("⭐ Qualidade", f"{sleep_quality}/10", "ok" if sleep_quality >= 7 else "warn"))
    ease_rows.append((
        "💪 Workout",
        f"{workout_minutes}min ✓" if workout_done else "não feito",
        "ok" if workout_done else "warn",
    ))
    ease_rows.append((
        "🧘 Meditação",
        f"{meditacao_minutes}min ✓" if meditacao_done else "não feita",
        "ok" if meditacao_done else "warn",
    ))
    lunch_sev = "ok" if (lunch_eat_min <= 5 and lunch_rest_min <= 30) else "warn"
    if lunch_pesado:
        lunch_sev = "crit"
    lunch_marker = " ⚠️ PESADO" if lunch_pesado else ""
    ease_rows.append((
        "🍽️  Lunch",
        f"{lunch_eat_min}min eat + {lunch_rest_min}min rest = {lunch_eat_min + lunch_rest_min}min{lunch_marker}",
        lunch_sev,
    ))
    ease_rows.append((
        "🌆 Jantar < 18h",
        "sim ✓" if jantar_antes_18 else "tarde (luz azul)",
        "ok" if jantar_antes_18 else "warn",
    ))
    ease_rows.append((
        "📱 Luz azul",
        "cortada ✓" if not luz_azul_apos_18 else "exposição após 18h",
        "ok" if not luz_azul_apos_18 else "warn",
    ))
    ease_rows.append((
        "🔄 Transições",
        f"{n_transicoes_completas}/{n_transicoes_total}",
        "ok" if n_transicoes_completas == n_transicoes_total else "warn" if n_transicoes_completas >= 6 else "crit",
    ))

    # ====== 3. HARDWORK TABLE ======
    label, delta = classify_infracao(hardwork_realizado_min, hardwork_orcado_min)
    delta_str = f"+{delta}" if delta > 0 else str(delta)
    hardwork_rows: list[tuple[str, str, str | None]] = [
        ("Tipo de Dia", tipo_dia.value.upper(), None),
        ("📊 Orçado", f"{hardwork_orcado_min}min ({hardwork_orcado_min // 60}h{hardwork_orcado_min % 60:02d}m)", None),
        ("⏱️  Realizado", f"{hardwork_realizado_min}min ({hardwork_realizado_min // 60}h{hardwork_realizado_min % 60:02d}m)", None),
        ("Δ Desvio", f"{delta_str}min ({label})",
         "ok" if "DENTRO" in label else "warn" if "ACIMA" in label or "ABAIXO" in label else "crit"),
    ]
    if pomodoros_meta:
        total_pom = pomodoros_s1 + pomodoros_s2 + pomodoros_s3
        hardwork_rows.append(("🍅 Pomodoros", f"{total_pom}/{pomodoros_meta} rounds", "ok" if total_pom >= pomodoros_meta else "warn"))

    # Pomodoros grid (inline text, not boxed)
    grid_text = pomodoros_grid(pomodoros_s1, pomodoros_s2, pomodoros_s3)
    grid_panel = Panel(
        grid_text,
        title="[bold green3]🍅 Pomodoros Grid[/bold green3]",
        border_style="green3",
        box=SIMPLE_HEAD,
        padding=(0, 1),
    )

    # Consolidate EASE + HARDWORK into a single 2-column layout
    ease_table = metric_table("😴 EASE", ease_rows, title_color="sleep")
    hardwork_table = metric_table("💻 HARDWORK", hardwork_rows, title_color="hardwork")

    # Energy/Focus bars
    ef_panel: RenderableType | None = None
    if energia or foco:
        ef = Table.grid(padding=(0, 2))
        ef.add_column()
        ef.add_column()
        if energia:
            ef.add_row(
                Text("  ⚡ Energia  ", style="bold"),
                progress_bar(energia, 10, color="energy", label=f"{energia}/10"),
            )
        if foco:
            ef.add_row(
                Text("  🎯 Foco  ", style="bold"),
                progress_bar(foco, 10, color="focus", label=f"{foco}/10"),
            )
        ef_panel = Panel(ef, title="[bold yellow1]⚡ Estado Subjetivo[/bold yellow1]", border_style="yellow1", box=SIMPLE_HEAD, padding=(0, 1))

    # Combined EASE + HARDWORK + grid + energy/focus
    combined_metrics: list[RenderableType] = [
        ease_table,
        Text(" "),
        hardwork_table,
        Text(" "),
        grid_panel,
    ]
    if ef_panel:
        combined_metrics.append(Text(" "))
        combined_metrics.append(ef_panel)
    sections.append(Group(*combined_metrics))

    # ====== 4. CARTESIAN PLANE ======
    cart_text = cartesian_plane(x_preview, y_preview)
    q_text = Text()
    q_text.append(f"  {q_preview}  ", style=f"bold {q_color}")
    q_text.append(f"  —  {_label_for_quadrant(q_preview)}\n", style="white")
    q_text.append(f"  Ação: {_action_for_quadrant(q_preview)}", style="dim italic")
    cart_table = Table.grid(padding=(0, 1))
    cart_table.add_column()
    cart_table.add_row(cart_text)
    cart_table.add_row(Text(" "))
    cart_table.add_row(q_text)
    sections.append(Panel(
        cart_table,
        title=f"[bold cyan]📈 Plano Cartesiano — X: Produtividade · Y: Eficiência · Point: ({x_preview:.0f}%, {y_preview:.0f}%)[/bold cyan]",
        border_style="cyan",
        box=SIMPLE_HEAD,
        padding=(0, 1),
    ))

    # ====== 5. DESVIOS + AJUSTES + LIÇÕES (single panel) ======
    if desvios or ajustes or licoes:
        notes_table = Table(show_header=False, box=None, padding=(0, 1))
        notes_table.add_column("Tipo", style="bold", min_width=12)
        notes_table.add_column("Conteúdo", style="white")
        for d in desvios:
            notes_table.add_row("⚠️  Desvio", d)
        for a in ajustes:
            notes_table.add_row("🔧 Ajuste", a)
        for l in licoes:
            notes_table.add_row("📚 Lição", l)
        sections.append(Panel(
            notes_table,
            title="[bold yellow1]⚠️  Desvios · 🔧 Ajustes · 📚 Lições[/bold yellow1]",
            border_style="yellow1",
            box=SIMPLE_HEAD,
            padding=(0, 1),
        ))

    # ====== 6. OKRs V3 ======
    if any([big_win, parar_de_fazer, repetir, maior_aprendizado, deu_certo, deu_errado]):
        okr_table = Table(show_header=False, box=None, padding=(0, 1))
        okr_table.add_column(style="bold magenta", min_width=20)
        okr_table.add_column(style="white")
        if big_win:
            okr_table.add_row("🏆 Big-Win", big_win)
        for p in parar_de_fazer:
            okr_table.add_row("❌ Parar de fazer", p)
        for r in repetir:
            okr_table.add_row("✅ Repetir", r)
        for c in deu_certo:
            okr_table.add_row("✅ Deu certo", c)
        for e in deu_errado:
            okr_table.add_row("❌ Deu errado", e)
        if maior_aprendizado:
            okr_table.add_row("💡 Maior aprendizado", maior_aprendizado)
        sections.append(Panel(
            okr_table,
            title="[bold magenta]🎯 OKRs V3 — Reflexão do dia[/bold magenta]",
            border_style="magenta",
            box=SIMPLE_HEAD,
            padding=(0, 1),
        ))

    # ====== 7. NEXT STEP (single line) =====
    if _is_recovery_needed(sleep_hours, label, q_preview):
        sections.append(next_step("Aplicar plano de recuperação antes de continuar. Sono < 6h ou Q3 detectado.", color="crit", icon="!"))
    elif hardwork_realizado_min >= hardwork_orcado_min and (pomodoros_s1 + pomodoros_s2 + pomodoros_s3) >= pomodoros_meta and pomodoros_meta > 0:
        sections.append(next_step("Dia dentro do padrão ouro. Manter ritmo, monitorar fadiga.", color="ok", icon="✓"))
    else:
        sections.append(next_step("Ajustar próximo dia: revisar desvios e aplicar ajustes finos.", color="info", icon="→"))

    return Group(*sections)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _label_for_quadrant(q: str) -> str:
    mapping = {
        "Q1": "Excelente — manter ritmo",
        "Q2": "Otimizado mas pouco output",
        "Q3": "Crítico — revisar sistema, identificar bloqueios",
        "Q4": "Produtivo mas precisa otimizar",
    }
    return mapping.get(q, "—")


def _action_for_quadrant(q: str) -> str:
    mapping = {
        "Q1": "Manter",
        "Q2": "Aumentar volume de trabalho",
        "Q3": "Revisão urgente",
        "Q4": "Reduzir distrações",
    }
    return mapping.get(q, "—")


def _is_recovery_needed(sleep_hours, infracao_label, q_code) -> bool:
    return (
        q_code == "Q3"
        or (sleep_hours is not None and sleep_hours < 6)
        or infracao_label in ("MUITO_ABAIXO", "ABAIXO")
    )


def _severity_for_wake(hour: int) -> str:
    if 3 <= hour <= 5:
        return "ok"
    if hour == 6:
        return "warn"
    if hour >= 7:
        return "crit"
    return "ok"


def _severity_for_sleep_hour(hour: int) -> str:
    if 18 <= hour <= 21:
        return "ok"
    if hour == 22 or hour == 17:
        return "warn"
    return "crit"


def emoji_for_sleep(hours: float) -> str:
    if hours >= 9:
        return "🟢 excelente"
    if hours >= 8:
        return "🟢 bom"
    if hours >= 7:
        return "🟡 aceitável"
    if hours >= 4:
        return "🟠 hardcore"
    return "🔴 crítico"


# ---------------------------------------------------------------------------
# Markdown fallback for --json
# ---------------------------------------------------------------------------


def generate_daily_v3_markdown(
    *,
    report_date: date,
    tipo_dia: TipoDia,
    **kwargs,
) -> str:
    from datetime import datetime
    lines: list[str] = [
        "---",
        "type: daily_v3",
        f"date: {report_date.isoformat()}",
        f"tipo_dia: {tipo_dia.value}",
        f"generated_at: {datetime.now().isoformat()}",
        "---",
        "",
        f"# 📈 Daily V3 — {report_date.isoformat()}",
        "",
    ]
    sleep_hours = kwargs.get("sleep_hours")
    energia = kwargs.get("energia")
    foco = kwargs.get("foco")
    pomodoros_s1 = kwargs.get("pomodoros_s1", 0)
    pomodoros_s2 = kwargs.get("pomodoros_s2", 0)
    pomodoros_s3 = kwargs.get("pomodoros_s3", 0)
    pomodoros_meta = kwargs.get("pomodoros_meta", 0)
    orcado = kwargs.get("hardwork_orcado_min", 0)
    realizado = kwargs.get("hardwork_realizado_min", 0)

    if sleep_hours is not None:
        lines.append(f"## 😴 EASE — Sono {sleep_hours:.1f}h {emoji_for_sleep(sleep_hours)}")
    lines.append(f"\n**Tipo de Dia:** {tipo_dia.value.upper()}")
    lines.append(f"**Orçado vs Realizado:** {realizado}/{orcado}min")

    x = productivity_pct(realizado, orcado)
    y = efficiency_pct(realizado, realizado + 60)
    q_code, q_label, q_action = classify_quadrant(x, y)
    lines.append(f"\n**Plano Cartesiano:** X={x:.0f}%, Y={y:.0f}% → {q_code} {q_label}")
    lines.append(f"**Ação:** {q_action}\n")
    return "\n".join(lines)
