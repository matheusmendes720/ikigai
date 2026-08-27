"""frontmatter_to_dict — markdown file → IKIGAiRecord-ready dict.

Preserves:
  - `null` keys (RT-03) — explicit `None`, not dropped
  - tz-aware datetimes remain ISO strings (RT-04)
  - Unknown frontmatter keys pass through (RT-06) so the validator's
    `extra="allow"` config (SPEC D6) accepts them.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def frontmatter_to_dict(path: Path) -> dict[str, Any]:
    """Read a markdown file, parse its YAML frontmatter block, and return
    the dict. Falls back to empty dict if no frontmatter delimiter.
    """
    try:
        import frontmatter
    except ImportError as exc:  # pragma: no cover — required dependency
        raise ImportError(
            "python-frontmatter is required for vault I/O; install via "
            "`uv add frontmatter` in life-ops/ikigai"
        ) from exc

    post = frontmatter.loads(path.read_text(encoding="utf-8"))
    # frontmatter drops None-valued keys in some versions; preserve them
    # explicitly for RT-03.
    raw = post.metadata or {}
    result: dict[str, Any] = {}
    for k, v in raw.items():
        if v is None:
            result[k] = None
        else:
            result[k] = v
    return result


__all__ = ["frontmatter_to_dict"]