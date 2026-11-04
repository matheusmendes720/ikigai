"""frontmatter_compat — the python-frontmatter 1.x API, reimplemented on PyYAML.

The `frontmatter` package dropped its ``loads()``/``dumps()``/``Post`` API in
3.x (the only 3.x public surface is ``Frontmatter.read_file(...)``, which
returns a plain dict). This module provides the 1.x callable API using PyYAML
directly.

Why not just use the `frontmatter` package directly?
- The vault layer needs both write AND read of frontmatter blocks.
  3.x's read_file API is sufficient for read but does not compose
  frontmatter + body for write.

This module:
  - `loads(text: str) -> SimpleNamespace(content, metadata)` —
    parses `---\n<yaml>\n---\n<body>` into a result object that
    has both `.content` (body string) and `.metadata` (frontmatter dict).
  - `dumps(post) -> str` — composes `---\n<yaml>\n---\n<body>` from
    the post object's `.content` and `.metadata`.
  - `Post(content, **fields)` — convenience constructor returning
    a SimpleNamespace with `.content` and `.metadata`.
  - `dump(post, file)` and `load(file)` — file-based counterparts.

This is a STRAIGHTFORWARD reimplementation, not a perfect 1.x match.
It implements the *minimum* surface the codebase actually uses.

Moved here from `sys_ikigai/vault/frontmatter_compat.py` (2026-11-02,
ADR-037 unpublishing). The shim was self-contained — it imported only
`re`, `pathlib`, `types`, `typing` and `yaml` — but its *location* inside
`sys_ikigai/` made the published `strategics` package depend on the
legacy tree, which in turn forced `sys_ikigai` into the wheel
(`pyproject.toml`: `{include = "sys_ikigai", from = "../.."}`).
That was the coupling that kept 91 legacy files on the remote branch.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml


# `---\n<yaml>\n---\n<body>` is the canonical markdown frontmatter block.
# We use a non-greedy match for the yaml body so subsequent `---` lines
# (in the markdown body itself, e.g. horizontal rules) don't accidentally
# truncate the frontmatter section.
_FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(?P<fm>.*?)\n---\s*\n?(?P<body>.*)$",
    re.DOTALL,
)


def loads(text: str) -> SimpleNamespace:
    """Parse `---\n<yaml>\n---\n<body>` into `.content` + `.metadata`.

    Mirrors python-frontmatter 1.x behavior:
      - empty / no frontmatter → .content = text, .metadata = {}
      - YAML errors → .metadata = {} (lenient) or raises (strict). We
        raise on invalid YAML to surface drift early.
      - `None` values in YAML → preserved as Python None (RT-03 invariant).
    """
    text = text or ""
    match = _FRONTMATTER_PATTERN.match(text)
    if match is None:
        # No frontmatter block → entire text is body
        return SimpleNamespace(content=text, metadata={})

    fm_block = match.group("fm")
    body = match.group("body")

    if fm_block.strip():
        # yaml.safe_load preserves None values as-is in the resulting dict
        metadata: dict[str, Any] = yaml.safe_load(fm_block) or {}
        if not isinstance(metadata, dict):
            # top-level yaml is not a mapping (e.g. just a list or scalar)
            # — preserve the text raw under a special key for visibility
            metadata = {"_raw": fm_block}
    else:
        metadata = {}

    return SimpleNamespace(content=body, metadata=metadata)


def dumps(post: Any) -> str:
    """Compose `---\n<yaml>\n---\n<body>` from `.content` + `.metadata`.

    Mirrors python-frontmatter 1.x behavior:
      - Uses yaml.safe_dump with default_flow_style=False (block style).
      - sort_keys=False (preserve dict insertion order).
      - trailing newline on body (POSIX text-file canonical form).
    """
    metadata: dict[str, Any] = getattr(post, "metadata", None) or {}
    content: str = (getattr(post, "content", None) or "").rstrip()

    fm_block = yaml.safe_dump(
        metadata,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        explicit_start=False,
    ).strip()

    parts = ["---", fm_block, "---", ""]
    if content:
        parts.append(content)
    parts.append("")
    return "\n".join(parts)


def Post(content: str = "", **fields: Any) -> SimpleNamespace:
    """Construct a post-like object with `.content` + `.metadata`.

    Mirrors python-frontmatter 1.x Post class.
    """
    return SimpleNamespace(content=content, metadata=dict(fields))


def load(file: Any) -> SimpleNamespace:
    """Load frontmatter from a file object (text mode)."""
    return loads(file.read())


def dump(post: Any, file: Any) -> None:
    """Write frontmatter to a file object (text mode)."""
    file.write(dumps(post))


__all__ = ["loads", "dumps", "Post", "load", "dump"]
