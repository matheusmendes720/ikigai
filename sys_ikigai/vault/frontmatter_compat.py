"""frontmatter_compat — backward-compat shim for upstream frontmatter 3.x.

The `frontmatter` package dropped its loads()/dumps()/Post API in 3.x
(the only 3.x public surface is `Frontmatter.read_file(...)` which
returns a dict). This shim provides the old 1.x callable API using
PyYAML directly.

Why not just `import frontmatter` and use it directly?
- Tests fail at master HEAD with `"frontmatter has no attribute Post"`
  or `"frontmatter has no attribute loads"` because the system has
  3.0.8 installed.
- The vault layer needs both write AND read of frontmatter blocks.
  3.x's read_file API is sufficient for read but doesn't compose
  frontmatter + body for write.

This shim:
  - `loads(text: str) -> SimpleNamespace(content, metadata)` —
    parses `---\n<yaml>\n---\n<body>` into a result object that
    has both `.content` (body string) and `.metadata` (frontmatter dict).
  - `dumps(post) -> str` — composes `---\n<yaml>\n---\n<body>` from
    the post object's `.content` and `.metadata`.
  - `Post(content, **fields)` — convenience constructor returning
    a SimpleNamespace with `.content` and `.metadata`.
  - `dump(post, file)` and `load(file)` — file-based counterparts,
    not yet exercised by tests but provided for forward compat.

This is a STRAIGHTFORWARD shim, not a perfect 1.x re-implementation.
It implements the *minimum* surface the codebase actually uses:
- `frontmatter.loads(text)` from:
    sys_ikigai/vault/frontmatter_to_dict.py
    sys_ikigai/vault/vault_read.py
    src/ikigai/src/mcp_server/handlers.py
    src/ikigai/src/strategics/loader.py
- `frontmatter.dumps(post)` and `frontmatter.Post(...)` from:
    sys_ikigai/vault/vault_write.py (M72 already migrated this one
    but kept the shim for cross-system symmetry)

M72.1 (2026-09-19): replaces `import frontmatter` calls in
5 files with this shim. Keeps `frontmatter` package installable
for any forward compat that depends on 3.x directly.
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
