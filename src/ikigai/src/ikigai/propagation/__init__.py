"""Propagation: markdown DB (canonical), SQLite adapter, triagem, frontmatter."""

from ikigai.propagation.markdown_db import MarkdownDB
from ikigai.propagation.frontmatter import (
    frontmatter_to_dict,
    dict_to_frontmatter,
    serialize_to_markdown,
    parse_from_markdown,
)
from ikigai.propagation.triagem import Triagem, DriftEntry
from ikigai.propagation.sqlite_adapter import SQLiteAdapter

__all__ = [
    "MarkdownDB",
    "frontmatter_to_dict",
    "dict_to_frontmatter",
    "serialize_to_markdown",
    "parse_from_markdown",
    "Triagem",
    "DriftEntry",
    "SQLiteAdapter",
]
