"""Journal segmenter — natural language reports by period.

The JournalEntry is a free-form text narrative of the day. This
module:

1. **Segments** a JournalEntry by the periods it covers (e.g.
   MANHÃ / TARDE / NOITE).
2. **Renders** a natural-language summary per period (e.g.
   "Manhã (3-5am): acordou 4h, hidratação OK, ritual matinal
   completo, 4 rounds de foco").

The segmenter does **not** replace the user's journal — it is a
*reflection helper* that turns a journal into per-period summaries
for the daily/weekly reports. The journal remains the source of
truth; the segmenter is a pure function over it.

**Integrates with RoutineLog + AjusteFino** (PAV §2/§3/§10). The
user captures both numerical records (TimeBlock, break_minutes,
AjusteFino) and natural language (RoutineLog, JournalEntry.text,
desvios). The segmenter can pull in per-period RoutineLogs and
AjusteFinos to enrich the per-period NL report.

**No pomodoro in this layer.** Journal entries are free-form text;
the segmenter extracts period-coverage and tags but does not assume
any sub-block time tracking.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from operational.enums import Period

if TYPE_CHECKING:
    from datetime import date

    from operational.entities.ajuste_fino import AjusteFino
    from operational.entities.journal import JournalEntry
    from operational.entities.routine import RoutineLog

__all__ = [
    "JournalReport",
    "JournalSegment",
    "render_full_day_report",
    "render_natural_language_report",
    "render_period_summary",
    "segment_journal_by_period",
]


# Canonical period labels (PT-BR) for natural-language output
_PERIOD_LABELS_PT: Final[dict[Period, str]] = {
    Period.MANHA: "Manhã",
    Period.TARDE: "Tarde",
    Period.NOITE: "Noite",
}

# Canonical period start hours (PAV §3)
_PERIOD_START_HOURS: Final[dict[Period, int]] = {
    Period.MANHA: 3,
    Period.TARDE: 8,
    Period.NOITE: 18,
}


@dataclass(frozen=True, slots=True)
class JournalSegment:
    """A single period's segment of a journal entry.

    Field names mirror :class:`operational.entities.journal.JournalEntry`
    (PT-BR) for consistency.

    Attributes:
        period: Which period this segment covers.
        text: The text of the journal that was assigned to this period.
        energia_nivel: Energy level at this period, if reported.
        foco_nivel: Focus level at this period, if reported.
        pomodoros_completos: Pomodoros completed in this period, if reported.
        routine_logs: NL descriptions of routine executions in this period.
        ajustes_finos: Fine-grained adjustments in this period.
    """
    period: Period
    text: str
    energia_nivel: int | None
    foco_nivel: int | None
    pomodoros_completos: int
    routine_logs: tuple[RoutineLog, ...] = ()
    ajustes_finos: tuple[AjusteFino, ...] = ()


@dataclass(frozen=True, slots=True)
class JournalReport:
    """A natural-language report of a journal entry, segmented by period.

    Attributes:
        date: The date of the journal.
        segments: Ordered list of per-period segments (by period start hour).
        full_text: The original journal text.
    """
    date: date
    segments: tuple[JournalSegment, ...]
    full_text: str


def _split_text_by_period_markers(text: str) -> dict[Period, list[str]]:
    """Split journal text by explicit period markers.

    Recognises PT-BR markers like 'Manhã:', 'Tarde:', 'Noite:' as line
    prefixes (e.g. "Manhã: acordei 4h"). Text without any marker is
    associated with MANHÃ by default.
    """
    if not text:
        return {}
    sections: dict[Period, list[str]] = {p: [] for p in Period}
    current_period: Period = Period.MANHA  # default bucket
    current_lines: list[str] = []
    period_markers = {
        "manhã": Period.MANHA,
        "manha": Period.MANHA,
        "morning": Period.MANHA,
        "tarde": Period.TARDE,
        "afternoon": Period.TARDE,
        "noite": Period.NOITE,
        "evening": Period.NOITE,
        "night": Period.NOITE,
    }
    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        # Check if the line starts with a period marker (with or without colon)
        # e.g., "Manhã: acordei 4h" → marker "manhã:", content "acordei 4h"
        matched_marker: Period | None = None
        content_after_marker: str | None = None
        for marker, period in period_markers.items():
            # Match "marker:" or "marker " or "marker" at the start
            for suffix in (":", " ", ""):
                if lowered.startswith(marker + suffix) and (
                    len(lowered) == len(marker) + len(suffix) or
                    lowered[len(marker) + len(suffix):].strip() == ""
                ):
                    continue
                if lowered.startswith(marker + suffix):
                    matched_marker = period
                    # Strip the marker prefix from the original line
                    content_after_marker = stripped[len(marker) + len(suffix):].lstrip(": ").strip()
                    break
            if matched_marker is not None:
                break
        if matched_marker is not None:
            # Flush current buffer
            if current_lines:
                sections[current_period].append("\n".join(current_lines).strip())
                current_lines = []
            current_period = matched_marker
            if content_after_marker:
                current_lines.append(content_after_marker)
        else:
            current_lines.append(line)
    if current_lines:
        sections[current_period].append("\n".join(current_lines).strip())
    return sections


def segment_journal_by_period(
    journal: JournalEntry,
    routine_logs: tuple[RoutineLog, ...] | list[RoutineLog] = (),
    ajustes_finos: tuple[AjusteFino, ...] | list[AjusteFino] = (),
) -> JournalReport:
    """Segment a JournalEntry by period.

    Strategy:
    1. If the journal's ``periods_covered`` set is non-empty, only emit
       those periods.
    2. Within those periods, split the text by PT-BR period markers
       ('Manhã:', 'Tarde:', 'Noite:'). Text without a marker goes
       to MANHÃ by default.
    3. Each segment carries the energy/focus/pomodoros from the
       parent journal (they are global fields).
    4. Per-period RoutineLogs and AjusteFinos (if provided) are
       attached to their respective segment.

    Args:
        journal: The source journal entry.
        routine_logs: Optional NL logs to attach to per-period segments.
        ajustes_finos: Optional structured adjustments to attach.

    Returns:
        A JournalReport with ordered segments.
    """
    if not journal.entry_text and not journal.periods_covered:
        return JournalReport(
            date=journal.date,
            segments=(),
            full_text=journal.entry_text,
        )
    sections = _split_text_by_period_markers(journal.entry_text)
    target_periods: list[Period] = sorted(
        journal.periods_covered or set(sections.keys()),
        key=lambda p: _PERIOD_START_HOURS[p],
    )
    # Pre-index routine_logs and ajustes by period for O(1) lookup
    logs_by_period: dict[Period, list[RoutineLog]] = {}
    for log in routine_logs:
        if log.date == journal.date:
            logs_by_period.setdefault(log.period, []).append(log)
    ajustes_by_period: dict[Period, list[AjusteFino]] = {}
    for ajuste in ajustes_finos:
        if ajuste.date == journal.date:
            ajustes_by_period.setdefault(ajuste.period, []).append(ajuste)
    segments = [
        JournalSegment(
            period=p,
            text="\n".join(sections[p]).strip() if sections.get(p) else "",
            energia_nivel=journal.energia_nivel,
            foco_nivel=journal.foco_nivel,
            pomodoros_completos=journal.pomodoros_completos,
            routine_logs=tuple(logs_by_period.get(p, ())),
            ajustes_finos=tuple(ajustes_by_period.get(p, ())),
        )
        for p in target_periods
        if sections.get(p) or p in journal.periods_covered
    ]
    return JournalReport(
        date=journal.date,
        segments=tuple(segments),
        full_text=journal.entry_text,
    )


def render_period_summary(segment: JournalSegment) -> str:
    """Render a single period segment as a one-line natural-language summary.

    Format: "{Period} ({start_hour}h): {text_or_summary}"
    Plus optional energy/focus/pomodoros info if present.
    Plus optional NL routine logs and ajustes finos (counts only —
    detailed view is in :func:`render_natural_language_report`).
    """
    period_label = _PERIOD_LABELS_PT.get(segment.period, segment.period.value)
    start_hour = _PERIOD_START_HOURS.get(segment.period, 0)
    text = segment.text or "(sem registros)"
    # Collapse to a single line for the summary
    one_line = " ".join(text.split())
    if len(one_line) > 120:
        one_line = one_line[:117] + "..."
    parts = [f"**{period_label}** ({start_hour}h): {one_line}"]
    if segment.energia_nivel is not None:
        parts.append(f"Energia {segment.energia_nivel}/10")
    if segment.foco_nivel is not None:
        parts.append(f"Foco {segment.foco_nivel}/10")
    if segment.pomodoros_completos > 0:
        parts.append(f"{segment.pomodoros_completos} pomodoros")
    if segment.routine_logs:
        parts.append(f"{len(segment.routine_logs)} log(s) de rotina")
    if segment.ajustes_finos:
        total_min = sum(a.minutos for a in segment.ajustes_finos)
        sign = "+" if total_min > 0 else ""
        parts.append(f"{sign}{total_min}min ajustes")
    return " | ".join(parts)


def render_natural_language_report(report: JournalReport) -> str:
    """Render a full JournalReport as a natural-language markdown report.

    Includes:
    * Per-period journal text
    * Per-period energy/focus/pomodoros metrics
    * Per-period RoutineLogs (NL descriptions of routine executions)
    * Per-period AjusteFinos (structured fine-grained adjustments)
    """
    if not report.segments:
        return f"# Relatório de {report.date.isoformat()}\n\n_(Journal vazio)_"
    lines: list[str] = [
        f"# Relatório de {report.date.isoformat()}",
        "",
        f"Períodos cobertos: {len(report.segments)}",
        "",
    ]
    for segment in report.segments:
        period_label = _PERIOD_LABELS_PT.get(segment.period, segment.period.value)
        start_hour = _PERIOD_START_HOURS.get(segment.period, 0)
        lines.append(f"## {period_label} (a partir de {start_hour}h)")
        lines.append("")
        if segment.text:
            lines.append(segment.text)
        else:
            lines.append("_(sem registros para este período)_")
        lines.append("")
        if segment.energia_nivel is not None:
            lines.append(f"- **Energia:** {segment.energia_nivel}/10")
        if segment.foco_nivel is not None:
            lines.append(f"- **Foco:** {segment.foco_nivel}/10")
        if segment.pomodoros_completos > 0:
            lines.append(f"- **Pomodoros:** {segment.pomodoros_completos}")
        if segment.routine_logs:
            lines.append("")
            lines.append(f"### Logs de Rotina ({len(segment.routine_logs)})")
            for log in segment.routine_logs:
                type_emoji = {
                    "ENTRY": "🌅",
                    "EXIT": "🌙",
                    "CORE": "🎯",
                    "TRANSITION": "🔄",
                }.get(log.routine_type.value, "•")
                lines.append(f"- {type_emoji} **{log.routine_type.value}**: {log.text}")
                if log.energia_nivel is not None:
                    lines.append(f"  - Energia: {log.energia_nivel}/10")
                if log.foco_nivel is not None:
                    lines.append(f"  - Foco: {log.foco_nivel}/10")
        if segment.ajustes_finos:
            lines.append("")
            lines.append(f"### Ajustes Finos ({len(segment.ajustes_finos)})")
            for ajuste in segment.ajustes_finos:
                sign = "+" if ajuste.minutos > 0 else ""
                lines.append(f"- {sign}{ajuste.minutos}min — {ajuste.reason}")
        lines.append("")
    return "\n".join(lines)


def render_full_day_report(
    journal: JournalEntry,
    routine_logs: tuple[RoutineLog, ...] | list[RoutineLog] = (),
    ajustes_finos: tuple[AjusteFino, ...] | list[AjusteFino] = (),
) -> str:
    """One-shot helper: segment + render the full markdown report.

    Combines :func:`segment_journal_by_period` and
    :func:`render_natural_language_report` for convenience.
    """
    report = segment_journal_by_period(
        journal,
        routine_logs=routine_logs,
        ajustes_finos=ajustes_finos,
    )
    return render_natural_language_report(report)
