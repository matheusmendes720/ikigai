"""Strategics loader — pulls ./strategics/*.md (PT-BR) into agent context.

Per attribution report §1 (2026-08-29), ./strategics/ PT-BR markdown is the
single source of truth for IKIGAI agent instructions. This module loads them
into a Pydantic v2 frozen model for downstream tools.

Append-only invariant: this loader NEVER writes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import frontmatter
from pydantic import BaseModel, ConfigDict, Field


class StrategicDoc(BaseModel):
    """Single strategic document."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: Path
    title: str
    tags: list[str]
    body: str
    sha256: str


class StrategicsContext(BaseModel):
    """Loaded strategic context, ready for prompt injection."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    documents: list[StrategicDoc]
    by_tag: dict[str, list[StrategicDoc]]
    index: str = Field(default="")


def load_strategics(vault_root: Path) -> StrategicsContext:
    """Load all strategic docs from vault_root/strategics/.

    Filters: only files with `tags: [strategic]` (or any tag containing
    "strategic") in frontmatter.

    Args:
        vault_root: vault root directory

    Returns:
        StrategicsContext with documents, by_tag dict, and concatenated index
    """
    strategics_dir = vault_root / "strategics"
    if not strategics_dir.exists():
        return StrategicsContext(documents=[], by_tag={}, index="")

    documents: list[StrategicDoc] = []
    by_tag: dict[str, list[StrategicDoc]] = {}

    for md_path in sorted(strategics_dir.glob("*.md")):
        post = frontmatter.loads(md_path.read_text(encoding="utf-8"))
        tags = post.metadata.get("tags", [])

        # Filter: must have at least one tag containing "strategic"
        if not any("strategic" in str(t) for t in tags):
            continue

        sha256 = hashlib.sha256(md_path.read_bytes()).hexdigest()
        title = post.metadata.get("title", md_path.stem)
        tags_list = [str(t) for t in tags]

        doc = StrategicDoc(
            path=md_path,
            title=title,
            tags=tags_list,
            body=post.content,
            sha256=sha256,
        )
        documents.append(doc)

        for tag in tags_list:
            by_tag.setdefault(tag, []).append(doc)

    # Build index: concatenate titles + bodies
    parts = []
    for doc in documents:
        parts.append(f"## {doc.title}\n\n{doc.body}\n")
    index = "\n".join(parts)

    return StrategicsContext(documents=documents, by_tag=by_tag, index=index)
