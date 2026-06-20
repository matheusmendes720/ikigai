"""Base formatting helpers."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


def format_as_json(data: Any, *, indent: int = 2) -> str:
    """Dump data as JSON, handling Pydantic models and datetimes."""
    return json.dumps(data, indent=indent, default=_json_fallback)


def _json_fallback(obj: Any) -> Any:
    """Return a JSON-serializable dict for Pydantic models and datetimes."""
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Object of type %s is not JSON serializable" % type(obj).__name__)


def format_as_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    sep: str = " | ",
) -> str:
    """Format a simple text table.

    Args:
        headers: Column headers.
        rows: List of rows, each a list of cell strings.
        sep: Column separator.

    Returns:
        A string with header row, separator line, and data rows.
    """
    lines: list[str] = [sep.join(headers)]
    lines.append(sep.join(["-" * len(h) for h in headers]))
    for row in rows:
        lines.append(sep.join(str(c) if c is not None else "" for c in row))
    return "\n".join(lines)


def format_as_markdown(text: str) -> str:
    """Wrap text in a Markdown code block (for terminal output)."""
    return f"```\n{text}\n```"
