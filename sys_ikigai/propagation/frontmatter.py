"""Frontmatter serialization (Pydantic ↔ YAML)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from sys_ikigai.enums import EntityType, Phase, RegimeType, StatusType, VectorType
from sys_ikigai.exceptions import MarkdownParseError
from sys_ikigai.types import UEID

# ─────────────────────────────────────────────────────────────────────────────
# YAML representers (clean output)
# ─────────────────────────────────────────────────────────────────────────────


class _LiteralStr(str):
    """Marker for literal block scalar in YAML output."""


def _str_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    if len(data) > 80:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, _str_representer)


# ─────────────────────────────────────────────────────────────────────────────
# Frontmatter ↔ dict
# ─────────────────────────────────────────────────────────────────────────────


def _normalize_for_yaml(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize a frontmatter dict for YAML serialization."""
    out: dict[str, Any] = {}
    for k, v in data.items():
        if v is None:
            continue
        if isinstance(v, UEID):
            out[k] = str(v)
        elif isinstance(v, Path):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, Enum):
            out[k] = v.value
        elif isinstance(v, (set, frozenset)):
            out[k] = sorted(v)
        elif isinstance(v, dict):
            out[k] = {str(kk): vv for kk, vv in v.items()}
        else:
            out[k] = v
    return out


def coerce_typed_values(data: dict[str, Any]) -> dict[str, Any]:
    """Deserialize a frontmatter dict into typed values where possible.

    Strings → UEID / EntityType / StatusType / Phase / RegimeType / VectorType
    where parseable; otherwise left as strings for Pydantic to validate.
    """
    out: dict[str, Any] = dict(data)
    if "ueid" in out and isinstance(out["ueid"], str):
        try:
            out["ueid"] = UEID(out["ueid"])
        except ValueError:
            pass  # keep as string; will be validated by Pydantic
    if "entity_type" in out and isinstance(out["entity_type"], str):
        try:
            out["entity_type"] = EntityType(out["entity_type"])
        except ValueError:
            pass
    if "status" in out and isinstance(out["status"], str):
        try:
            out["status"] = StatusType(out["status"])
        except ValueError:
            pass
    if out.get("phase_at_creation"):
        try:
            out["phase_at_creation"] = Phase(out["phase_at_creation"])
        except (ValueError, KeyError):
            pass
    if out.get("regime_at_creation"):
        try:
            out["regime_at_creation"] = RegimeType(out["regime_at_creation"])
        except (ValueError, KeyError):
            pass
    if "ikigai_vectors" in out and isinstance(out["ikigai_vectors"], list):
        out["ikigai_vectors"] = [
            VectorType(v.split(".", 1)[0])
            if isinstance(v, str) and "." in v
            else (VectorType(v) if isinstance(v, str) else v)
            for v in out["ikigai_vectors"]
        ]
    if out.get("source_md_path"):
        out["source_md_path"] = Path(out["source_md_path"])
    return out


def frontmatter_to_dict(data: str | dict[str, Any]) -> dict[str, Any]:
    """Parse markdown OR normalize a dict → dict.

    Overloaded for ergonomics:
      - str input: parse markdown and return the frontmatter dict (body dropped).
      - dict input: normalize values for YAML serialization.
    """
    if isinstance(data, str):
        fm, _ = parse_from_markdown(data)
        return fm
    return _normalize_for_yaml(data)


def dict_to_frontmatter(data: dict[str, Any], body: str = "") -> str:
    """Serialize a dict + body → markdown string with frontmatter delimiters.

    Thin wrapper over `serialize_to_markdown` for callers that don't need a
    title heading.
    """
    return serialize_to_markdown(data, title="", body=body)


# ─────────────────────────────────────────────────────────────────────────────
# Markdown serialization
# ─────────────────────────────────────────────────────────────────────────────


_FRONTMATTER_DELIMITER = "---"


def serialize_to_markdown(
    frontmatter: dict[str, Any],
    title: str = "",
    body: str | None = "",
) -> str:
    """Serialize frontmatter + optional title heading + body to markdown.

    Args:
        frontmatter: dict to serialize as YAML between `---` delimiters.
        title: optional H1 heading inserted after the frontmatter block.
        body: optional markdown body. Pass `None` for no body.
    """
    normalized = _normalize_for_yaml(frontmatter)
    yaml_str = yaml.safe_dump(
        normalized,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )
    parts = [_FRONTMATTER_DELIMITER, yaml_str.rstrip("\n"), _FRONTMATTER_DELIMITER, ""]
    if title:
        parts.append(f"# {title}")
        parts.append("")
    if body:
        parts.append(body)
    return "\n".join(parts).rstrip("\n") + "\n"


def parse_from_markdown(content: str) -> tuple[dict[str, Any], str]:
    """Parse markdown into (frontmatter, body).

    Raises MarkdownParseError on malformed frontmatter.
    """
    if not content.startswith(_FRONTMATTER_DELIMITER + "\n"):
        return {}, content

    # Find closing delimiter
    lines = content.split("\n")
    if lines[0].strip() != _FRONTMATTER_DELIMITER:
        return {}, content

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _FRONTMATTER_DELIMITER:
            end_idx = i
            break

    if end_idx is None:
        raise MarkdownParseError(
            "Markdown frontmatter missing closing '---'",
            context={"line_count": len(lines)},
        )

    yaml_content = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :]).strip()

    try:
        data = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError as e:
        raise MarkdownParseError(
            f"Failed to parse YAML frontmatter: {e}",
            context={"yaml_content_preview": yaml_content[:200]},
        ) from e

    if not isinstance(data, dict):
        raise MarkdownParseError(
            "Frontmatter must be a YAML mapping",
            context={"type": type(data).__name__},
        )

    return data, body


# ─────────────────────────────────────────────────────────────────────────────
# Enum import shim (avoid circular)
# ─────────────────────────────────────────────────────────────────────────────


from enum import Enum  # noqa: E402

__all__ = [
    "coerce_typed_values",
    "dict_to_frontmatter",
    "frontmatter_to_dict",
    "parse_from_markdown",
    "serialize_to_markdown",
]
