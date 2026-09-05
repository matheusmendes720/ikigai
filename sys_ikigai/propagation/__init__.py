"""Propagation: markdown DB (canonical), SQLite adapter, triagem, frontmatter."""

from sys_ikigai.propagation.frontmatter import (
    dict_to_frontmatter,
    frontmatter_to_dict,
    parse_from_markdown,
    serialize_to_markdown,
)
from sys_ikigai.propagation.markdown_db import MarkdownDB
from sys_ikigai.propagation.sqlite_adapter import SQLiteAdapter
from sys_ikigai.propagation.triagem import DriftEntry, Triagem

__all__ = [
    "DriftEntry",
    "MarkdownDB",
    "SQLiteAdapter",
    "Triagem",
    "dict_to_frontmatter",
    "frontmatter_to_dict",
    "parse_from_markdown",
    "serialize_to_markdown",
]
