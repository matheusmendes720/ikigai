"""YAML frontmatter parser — convert markdown journal files to Pydantic entities.

The canonical daily journal format is a markdown file with YAML frontmatter:

.. code-block:: markdown

    ---
    id: day_2026_06_07
    date: 2026-06-07
    periods_covered: [MANHA, TARDE, NOITE]
    energia_nivel: 8
    foco_nivel: 7
    pomodoros_completos: 8
    humor_morning: 4
    humor_evening: 3
    routines_completed: [rou_acordar, rou_meditar, rou_hardwork_s1]
    desvios:
      - "Acordei 30min atrasado"
    licoes_aprendidas:
      - "Preparar café na noite anterior economiza 10min"
    ajustes_finos:
      - periodo: MANHA
        minutos: 5
        razao: "Pausa extra para alongamento"
    ---

    Corpo do diário — narrativa livre do dia...
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import yaml

from operational.entities.ajuste_fino import AjusteFino
from operational.entities.journal import JournalEntry
from operational.enums import Period

__all__ = [
    "parse_journal_frontmatter",
    "serialize_journal_to_markdown",
]


def _coerce_date(raw: Any) -> date:
    """Parse a date from string or datetime."""
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        return date.fromisoformat(raw)
    raise TypeError("Cannot coerce %s to date: %r" % (type(raw).__name__, raw))


def _parse_ajuste_fino(raw: dict[str, Any]) -> AjusteFino:
    """Convert a raw dict from YAML into an AjusteFino entity."""
    return AjusteFino(
        id=raw.get("id", f"aju_{hash(str(raw)) & 0xFFFFFFFF:08x}"),
        date=_coerce_date(raw.get("data", raw.get("date", datetime.now(UTC).date()))),
        period=Period(raw.get("periodo", raw.get("period", Period.MANHA.value))),
        minutos=int(raw.get("minutos", 0)),
        reason=raw.get("razao", raw.get("reason", "")),
        block_id_before=raw.get("block_id_before", raw.get("bloco_antes")),
        block_id_after=raw.get("block_id_after", raw.get("bloco_depois")),
        created_at=datetime.now(UTC),
    )


def parse_journal_frontmatter(
    markdown_text: str,
    default_id: str | None = None,
) -> JournalEntry:
    """Parse a markdown text with YAML frontmatter into a JournalEntry.

    Args:
        markdown_text: Full markdown text, optionally starting with
            ``---`` frontmatter delimiters.
        default_id: Fallback UEID if frontmatter has no ``id`` field.

    Returns:
        A :class:`JournalEntry` populated from the frontmatter.

    Raises:
        ValueError: If the frontmatter is malformed or required fields
            are missing.
        yaml.YAMLError: If the YAML block is syntactically invalid.
    """
    # Split frontmatter from body
    body_start = 0
    frontmatter_raw: dict[str, Any] = {}

    lines = markdown_text.splitlines()
    if lines and lines[0].strip() == "---":
        end_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break
        if end_idx == -1:
            msg = "Unclosed frontmatter block (no closing '---')"
            raise ValueError(msg)
        fm_block = "\n".join(lines[1:end_idx])
        frontmatter_raw = yaml.safe_load(fm_block) or {}
        body_start = end_idx + 1

    body = "\n".join(lines[body_start:]).strip()

    # Build the JournalEntry
    entry_id = frontmatter_raw.get("id") or default_id or f"day_{date.today().isoformat()}"
    entry_date = _coerce_date(frontmatter_raw.get("date", date.today()))

    # Parse periods_covered
    periods_raw = frontmatter_raw.get("periods_covered") or frontmatter_raw.get("periodos")
    periods_covered: set[Period] = set()
    if periods_raw:
        for p in periods_raw:
            periods_covered.add(Period(p.upper() if isinstance(p, str) else p))

    # Parse ajustes_finos
    ajustes_raw = frontmatter_raw.get("ajustes_finos") or frontmatter_raw.get("ajusteFinos") or []
    ajustes_finos = [_parse_ajuste_fino(a) for a in ajustes_raw]

    # Parse routine UEIDs
    routines_raw = frontmatter_raw.get("routines_completed") or frontmatter_raw.get("rotinas") or []

    return JournalEntry(
        id=entry_id,
        date=entry_date,
        entry_text=body,
        periods_covered=periods_covered,
        routines_completed=list(routines_raw),
        desvios=frontmatter_raw.get("desvios", []),
        ajustes_finos=ajustes_finos,
        rotinas_logs=list(frontmatter_raw.get("rotinas_logs", [])),
        licoes_aprendidas=frontmatter_raw.get("licoes_aprendidas", frontmatter_raw.get("licoes", [])),
        energia_nivel=frontmatter_raw.get("energia_nivel") or frontmatter_raw.get("energia"),
        foco_nivel=frontmatter_raw.get("foco_nivel") or frontmatter_raw.get("foco"),
        pomodoros_completos=frontmatter_raw.get("pomodoros_completos", 0),
        humor_morning=frontmatter_raw.get("humor_morning") or frontmatter_raw.get("humor_manha"),
        humor_evening=frontmatter_raw.get("humor_evening") or frontmatter_raw.get("humor_noite"),
        created_at=datetime.now(UTC),
    )


def _yaml_dump_ajuste(ajuste: AjusteFino) -> dict[str, Any]:
    """Serialize an AjusteFino to a YAML-friendly dict."""
    d: dict[str, Any] = {
        "periodo": ajuste.period.value,
        "minutos": ajuste.minutos,
        "razao": ajuste.reason,
    }
    if ajuste.block_id_before:
        d["bloco_antes"] = ajuste.block_id_before
    if ajuste.block_id_after:
        d["bloco_depois"] = ajuste.block_id_after
    return d


def serialize_journal_to_markdown(entry: JournalEntry) -> str:
    """Serialize a JournalEntry to markdown with YAML frontmatter.

    Args:
        entry: The journal entry to serialize.

    Returns:
        A markdown string with YAML frontmatter followed by the body.
    """
    front: dict[str, Any] = {
        "id": entry.id,
        "date": entry.date.isoformat(),
        "periods_covered": [p.value for p in sorted(entry.periods_covered)],
        "energia_nivel": entry.energia_nivel,
        "foco_nivel": entry.foco_nivel,
        "pomodoros_completos": entry.pomodoros_completos,
    }
    if entry.humor_morning is not None:
        front["humor_morning"] = entry.humor_morning
    if entry.humor_evening is not None:
        front["humor_evening"] = entry.humor_evening
    if entry.routines_completed:
        front["routines_completed"] = list(entry.routines_completed)
    if entry.desvios:
        front["desvios"] = list(entry.desvios)
    if entry.licoes_aprendidas:
        front["licoes_aprendidas"] = list(entry.licoes_aprendidas)
    if entry.ajustes_finos:
        front["ajustes_finos"] = [_yaml_dump_ajuste(a) for a in entry.ajustes_finos]
    if entry.rotinas_logs:
        front["rotinas_logs"] = list(entry.rotinas_logs)

    fm = yaml.safe_dump(front, allow_unicode=True, sort_keys=False, default_flow_style=False).strip()
    body = entry.entry_text.strip() or ""
    return f"---\n{fm}\n---\n\n{body}\n"
