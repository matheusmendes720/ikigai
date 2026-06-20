"""Output formatters for CLI commands."""
from __future__ import annotations

from operational.cli.formatters.base import (
    format_as_json,
    format_as_markdown,
    format_as_table,
)

__all__ = ["format_as_json", "format_as_markdown", "format_as_table"]
