"""IKIGAI view renderers — ASCII visualizations of data/matheus/.

Read-only renderers for the 4 IKIGAI views (per matheus request 2026-07-09):
- breakdown-files: hierarchical tree via parent_ueid links
- gantt: horizontal bars per horizon_days
- kanban: columns by status (draft|planned|active|in_progress|done|...)
- calendar: dates per entity (start=created_at, end=created_at+horizon_days)

**No src/ikigai/ imports** — data-first methodology keeps src/ untouched
until 5+ SONHO logs exist. Pure stdlib + YAML frontmatter parsing.

Usage:
    python -m tools.ikigai_views breakdown [--persona matheus]
    python -m tools.ikigai_views gantt [--persona matheus]
    python -m tools.ikigai_views kanban [--persona matheus]
    python -m tools.ikigai_views calendar [--persona matheus]
    python -m tools.ikigai_views all [--persona matheus]

Stdlib only: yaml (PyYAML), pathlib, datetime, argparse.
External deps: PyYAML (already in life-ops/ikigai/pyproject.toml).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import yaml


# ──────────────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Entity:
    """Lightweight entity from YAML frontmatter (no Pydantic, no src/ import)."""

    ueid: str
    entity_type: str
    slug: str
    title: str
    status: str
    parent_ueid: str | None
    horizon_days: int
    created_at: datetime
    tags: tuple[str, ...]
    file_path: Path

    @property
    def end_date(self) -> datetime:
        return self.created_at + timedelta(days=self.horizon_days)


# ──────────────────────────────────────────────────────────────────────────────
# Loader
# ──────────────────────────────────────────────────────────────────────────────


def _parse_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file."""
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def load_entities(vault_root: Path) -> list[Entity]:
    """Load all entities from a persona vault."""
    entities: list[Entity] = []
    for md_path in vault_root.rglob("*.md"):
        meta = _parse_frontmatter(md_path)
        if not meta or "entity_type" not in meta:
            continue
        # Skip artifact-* (D1 outputs, etc.) — only load plan hierarchy + profiles
        if meta["entity_type"] == "artifact":
            continue
        created_at_raw = meta.get("created_at", "2026-01-01T00:00:00Z")
        if isinstance(created_at_raw, datetime):
            # YAML auto-parsed ISO 8601 as datetime
            created_at = created_at_raw if created_at_raw.tzinfo else created_at_raw.replace(tzinfo=timezone.utc)
        else:
            # String form — handle Z suffix
            created_at_str = str(created_at_raw).replace("Z", "+00:00")
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except ValueError:
                created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        entities.append(
            Entity(
                ueid=meta["ueid"],
                entity_type=meta["entity_type"],
                slug=meta.get("slug", ""),
                title=meta.get("title", ""),
                status=meta.get("status", "draft"),
                parent_ueid=meta.get("parent_ueid"),
                horizon_days=int(meta.get("horizon_days", 0)),
                created_at=created_at,
                tags=tuple(meta.get("tags", [])),
                file_path=md_path,
            )
        )
    return entities


# ──────────────────────────────────────────────────────────────────────────────
# View 1: breakdown-files (hierarchical tree via parent_ueid)
# ──────────────────────────────────────────────────────────────────────────────


def render_breakdown(entities: list[Entity]) -> str:
    """Hierarchical tree: DREAM → GOAL → OBJECTIVE → PROJECT → DELIVERABLE."""
    by_ueid = {e.ueid: e for e in entities}
    children: dict[str, list[Entity]] = {}
    roots = [e for e in entities if not e.parent_ueid]
    for e in entities:
        if e.parent_ueid:
            children.setdefault(e.parent_ueid, []).append(e)

    type_order = {"dream": 0, "goal": 1, "objective": 2, "project": 3, "deliverable": 4, "profile": 5}
    for parent_ueid in children:
        children[parent_ueid].sort(key=lambda e: (type_order.get(e.entity_type, 99), e.slug))

    lines = ["# Breakdown (parent_ueid tree)", ""]

    def walk(e: Entity, depth: int = 0) -> None:
        icon = {"dream": "🌙", "objective": "🎯", "project": "🛠 ", "deliverable": "📦", "profile": "👤"}.get(
            e.entity_type, "·"
        )
        indent = "  " * depth
        lines.append(f"{indent}{icon} **{e.entity_type.upper()}** `{e.slug}` — {e.title} [{e.status}, {e.horizon_days}d]")
        for child in children.get(e.ueid, []):
            walk(child, depth + 1)

    # DREAM first, then others without parent
    dreams = [e for e in roots if e.entity_type == "dream"]
    non_dream_roots = [e for e in roots if e.entity_type != "dream"]
    for e in dreams + non_dream_roots:
        walk(e)
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# View 2: gantt (horizontal bars per horizon_days)
# ──────────────────────────────────────────────────────────────────────────────


def render_gantt(entities: list[Entity], total_days: int = 365) -> str:
    """ASCII gantt: each entity gets a horizontal bar of [start, start+horizon]."""
    if not entities:
        return "# Gantt (no entities)"

    # Find time range
    min_date = min(e.created_at for e in entities)
    max_date = max(e.end_date for e in entities)
    span_days = max((max_date - min_date).days, 30)
    bar_width = 60

    # Sort by entity_type then start
    type_order = {"dream": 0, "goal": 1, "objective": 2, "project": 3, "deliverable": 4, "profile": 5}
    sorted_entities = sorted(entities, key=lambda e: (type_order.get(e.entity_type, 99), e.created_at))

    lines = [f"# Gantt ({span_days}d span, {bar_width} cols)", ""]
    header = "       " + "·" * bar_width
    lines.append(header)

    icon_map = {"dream": "🌙", "objective": "🎯", "project": "🛠 ", "deliverable": "📦", "profile": "👤"}
    for e in sorted_entities:
        start_offset = (e.created_at - min_date).days
        end_offset = (e.end_date - min_date).days
        start_col = int(start_offset / span_days * bar_width)
        end_col = max(int(end_offset / span_days * bar_width), start_col + 1)
        bar = " " * start_col + "█" * (end_col - start_col)
        bar = bar[:bar_width].ljust(bar_width)
        icon = icon_map.get(e.entity_type, "·")
        lines.append(f"{icon} {e.slug[:18]:<18} |{bar}| {e.horizon_days}d [{e.status}]")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# View 3: kanban (columns by status)
# ──────────────────────────────────────────────────────────────────────────────


def render_kanban(entities: list[Entity]) -> str:
    """Kanban: columns by status."""
    by_status: dict[str, list[Entity]] = {}
    for e in entities:
        by_status.setdefault(e.status, []).append(e)

    # Fixed column order
    columns = ["draft", "planned", "active", "in_progress", "review", "done", "cancelled"]
    # Add any other statuses seen
    for s in by_status:
        if s not in columns:
            columns.append(s)

    lines = ["# Kanban (status columns)", ""]
    for status in columns:
        items = by_status.get(status, [])
        if not items:
            continue
        lines.append(f"## 📋 {status.upper()} ({len(items)})")
        for e in items:
            icon = {"dream": "🌙", "objective": "🎯", "project": "🛠 ", "deliverable": "📦", "profile": "👤"}.get(
                e.entity_type, "·"
            )
            lines.append(f"  - {icon} **{e.entity_type}** `{e.slug}` — {e.title} [{e.horizon_days}d]")
        lines.append("")
    return "\n".join(lines).rstrip()


# ──────────────────────────────────────────────────────────────────────────────
# View 4: calendar (dates per entity)
# ──────────────────────────────────────────────────────────────────────────────


def render_calendar(entities: list[Entity]) -> str:
    """Calendar: chronological list with start/end dates."""
    sorted_entities = sorted(entities, key=lambda e: e.created_at)
    lines = ["# Calendar (chronological)", ""]
    lines.append(f"{'Start':<12} {'End':<12} {'Span':<6} {'Type':<12} {'Slug':<35} Status")
    lines.append("─" * 100)
    for e in sorted_entities:
        start = e.created_at.strftime("%Y-%m-%d")
        end = e.end_date.strftime("%Y-%m-%d")
        span = f"{e.horizon_days}d"
        lines.append(f"{start:<12} {end:<12} {span:<6} {e.entity_type:<12} {e.slug[:33]:<35} {e.status}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────


def find_vault_root(persona: str, start: Path | None = None) -> Path:
    """Locate data/<persona>/ relative to repo root or CWD."""
    # Try relative to CWD first
    cwd_candidate = Path.cwd() / "life-ops" / "ikigai" / "data" / persona
    if cwd_candidate.exists():
        return cwd_candidate
    # Try relative to this file (life-ops/ikigai/tools/views.py)
    if start is None:
        start = Path(__file__).parent
    for ancestor in [start, *start.parents]:
        candidate = ancestor / "data" / persona
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not locate data/{persona}/ from {Path.cwd()}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IKIGAI view renderers (ASCII).")
    parser.add_argument(
        "view",
        choices=["breakdown", "gantt", "kanban", "calendar", "all"],
        help="View to render.",
    )
    parser.add_argument("--persona", default="matheus", help="Persona name (subdir of data/).")
    args = parser.parse_args(argv)

    vault_root = find_vault_root(args.persona)
    entities = load_entities(vault_root)
    if not entities:
        print(f"No entities found in {vault_root}", file=sys.stderr)
        return 1

    views = {
        "breakdown": render_breakdown,
        "gantt": render_gantt,
        "kanban": render_kanban,
        "calendar": render_calendar,
    }
    if args.view == "all":
        for name, fn in views.items():
            print(fn(entities))
            print()
    else:
        print(views[args.view](entities))
    return 0


if __name__ == "__main__":
    sys.exit(main())