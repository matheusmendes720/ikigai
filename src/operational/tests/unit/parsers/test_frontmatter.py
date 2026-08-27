"""Unit tests for :mod:`operational.parsers.frontmatter`."""
from __future__ import annotations

from datetime import date

import pytest

from operational.parsers.frontmatter import (
    parse_journal_frontmatter,
    serialize_journal_to_markdown,
)
from operational.enums import Period


# ---------------------------------------------------------------------------
# parse_journal_frontmatter
# ---------------------------------------------------------------------------


class TestParseJournalFrontmatter:
    def test_minimal_frontmatter(self) -> None:
        md = "---\nid: day_2026_06_07\ndate: 2026-06-07\n---\n\nBody text"
        entry = parse_journal_frontmatter(md)
        assert entry.id == "day_2026_06_07"
        assert entry.date == date(2026, 6, 7)
        assert entry.entry_text == "Body text"
        assert entry.periods_covered == set()
        assert entry.pomodoros_completos == 0

    def test_no_frontmatter(self) -> None:
        md = "Just body text, no frontmatter"
        entry = parse_journal_frontmatter(md, default_id="day_default")
        assert entry.id == "day_default"
        assert entry.date == date.today()
        assert entry.entry_text == "Just body text, no frontmatter"

    def test_full_frontmatter(self) -> None:
        md = """---
id: day_2026_06_07
date: 2026-06-07
periods_covered: [MANHA, TARDE]
energia_nivel: 8
foco_nivel: 7
pomodoros_completos: 10
humor_morning: 4
humor_evening: 3
routines_completed: [rou_acordar, rou_hardwork_s1]
desvios:
  - "Acordei 30min tarde"
licoes_aprendidas:
  - "Preparar café na noite anterior"
ajustes_finos:
  - periodo: MANHA
    minutos: 5
    razao: "Extra break"
---
Narrative body"""
        entry = parse_journal_frontmatter(md)
        assert entry.id == "day_2026_06_07"
        assert entry.date == date(2026, 6, 7)
        assert Period.MANHA in entry.periods_covered
        assert Period.TARDE in entry.periods_covered
        assert entry.energia_nivel == 8
        assert entry.foco_nivel == 7
        assert entry.pomodoros_completos == 10
        assert entry.humor_morning == 4
        assert entry.humor_evening == 3
        assert len(entry.routines_completed) == 2
        assert len(entry.desvios) == 1
        assert len(entry.licoes_aprendidas) == 1
        assert len(entry.ajustes_finos) == 1
        assert entry.ajustes_finos[0].minutos == 5
        assert entry.ajustes_finos[0].reason == "Extra break"
        assert entry.entry_text == "Narrative body"

    def test_unclosed_frontmatter_raises(self) -> None:
        md = "---\nid: x\n"
        with pytest.raises(ValueError, match="Unclosed"):
            parse_journal_frontmatter(md)

    def test_empty_text_returns_default(self) -> None:
        entry = parse_journal_frontmatter("", default_id="day_empty")
        assert entry.id == "day_empty"

    def test_frontmatter_only(self) -> None:
        md = "---\nid: day_001\ndate: 2026-06-07\n---"
        entry = parse_journal_frontmatter(md)
        assert entry.entry_text == ""

    def test_portuguese_field_names(self) -> None:
        md = """---
id: day_pt
date: 2026-06-07
periodos: [MANHA]
energia: 7
foco: 6
pomodoros_completos: 4
rotinas: [rou_x]
desvios: ["Teste"]
licoes: ["Licao"]
ajustes_finos:
  - periodo: TARDE
    minutos: -10
    razao: "Reduzido"
---
Corpo"""
        entry = parse_journal_frontmatter(md)
        assert entry.date == date(2026, 6, 7)
        assert Period.MANHA in entry.periods_covered
        assert entry.energia_nivel == 7
        assert entry.foco_nivel == 6
        assert len(entry.routines_completed) == 1
        assert len(entry.desvios) == 1
        assert len(entry.licoes_aprendidas) == 1
        assert len(entry.ajustes_finos) == 1
        assert entry.ajustes_finos[0].minutos == -10


# ---------------------------------------------------------------------------
# serialize_journal_to_markdown
# ---------------------------------------------------------------------------


class TestSerializeJournalToMarkdown:
    def test_roundtrip(self) -> None:
        md = """---
id: day_2026_06_07
date: 2026-06-07
periods_covered: [MANHA, TARDE]
energia_nivel: 8
foco_nivel: 7
pomodoros_completos: 10
humor_morning: 4
routines_completed:
- rou_acordar
desvios:
- Acordei 30min tarde
licoes_aprendidas:
- Preparar café na noite anterior
ajustes_finos:
- periodo: MANHA
  minutos: 5
  razao: Extra break
---

Narrative body"""
        entry = parse_journal_frontmatter(md)
        serialized = serialize_journal_to_markdown(entry)
        # Re-parse
        entry2 = parse_journal_frontmatter(serialized)
        assert entry2.id == entry.id
        assert entry2.date == entry.date
        assert entry2.periods_covered == entry.periods_covered
        assert entry2.energia_nivel == entry.energia_nivel
        assert entry2.foco_nivel == entry.foco_nivel
        assert entry2.pomodoros_completos == entry.pomodoros_completos

    def test_serialize_has_yaml_delimiters(self) -> None:
        entry = parse_journal_frontmatter(
            "---\nid: day_x\ndate: 2026-06-07\n---\n\nbody"
        )
        out = serialize_journal_to_markdown(entry)
        assert out.startswith("---")
        assert "---" in out[3:]
        assert out.strip().endswith("body")
