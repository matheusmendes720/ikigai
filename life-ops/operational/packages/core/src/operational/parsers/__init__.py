"""Parsers — convert structured text (YAML frontmatter, CSV, etc.) to Pydantic entities.

Public API
----------
- :func:`parse_journal_frontmatter` — YAML frontmatter → JournalEntry
- :func:`parse_time_block_line` — CSV line → TimeBlock
- :func:`serialize_journal_to_markdown` — JournalEntry → YAML frontmatter + body
"""
from __future__ import annotations

from operational.parsers.frontmatter import (
    parse_journal_frontmatter,
    serialize_journal_to_markdown,
)
from operational.parsers.time_block_parser import (
    parse_time_block_dict,
    parse_time_block_line,
    serialize_time_block_line,
)

__all__ = [
    "parse_journal_frontmatter",
    "parse_time_block_dict",
    "parse_time_block_line",
    "serialize_journal_to_markdown",
    "serialize_time_block_line",
]
