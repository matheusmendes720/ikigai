"""MarkdownDB — canonical source of truth for plan entities.

Layout:
    vault_root/
    ├── dreams/<slug>.md
    ├── goals/<slug>.md
    ├── objectives/<slug>.md
    ├── projects/<slug>.md
    ├── tasks/<slug>.md
    ├── deliverables/<slug>.md
    ├── routines/<slug>.md
    ├── habits/<slug>.md
    ├── ikigai_state/<slug>.md
    └── meta/<slug>.md

Atomic writes (write to .tmp, then rename).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ikigai.entities.base import PlanEntity
from ikigai.enums import EntityType
from ikigai.exceptions import MarkdownParseError, MarkdownWriteError
from ikigai.propagation.frontmatter import (
    dict_to_frontmatter,
    parse_from_markdown,
    serialize_to_markdown,
)


def _dir_for(entity_type: EntityType) -> str:
    """Map entity type to vault subdirectory."""
    mapping = {
        EntityType.DREAM: "dreams",
        EntityType.GOAL: "goals",
        EntityType.OBJECTIVE: "objectives",
        EntityType.PROJECT: "projects",
        EntityType.TASK: "tasks",
        EntityType.DELIVERABLE: "deliverables",
        EntityType.ROUTINE: "routines",
        EntityType.BLOCK: "blocks",
        EntityType.RITUAL: "rituals",
        EntityType.HABIT: "habits",
        EntityType.SKILL: "skills",
        EntityType.TOPIC: "topics",
        EntityType.MATERIAL: "materials",
        EntityType.SESSION: "sessions",
        EntityType.VECTOR: "ikigai_state",
        EntityType.PROFILE: "ikigai_state",
        EntityType.JOURNAL: "journal",
        EntityType.NOTE: "meta",
    }
    return mapping.get(entity_type, "meta")


class MarkdownDB:
    """Canonical markdown vault for plan entities."""

    def __init__(self, vault_root: Path | str) -> None:
        self.vault_root = Path(vault_root)
        self.vault_root.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Path resolution
    # ─────────────────────────────────────────────────────────────────────────

    def path_for(self, entity: PlanEntity) -> Path:
        """Resolve canonical path for a plan entity."""
        subdir = _dir_for(entity.entity_type)
        path = self.vault_root / subdir / f"{entity.slug}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def exists(self, entity: PlanEntity) -> bool:
        return self.path_for(entity).exists()

    # ─────────────────────────────────────────────────────────────────────────
    # CRUD operations
    # ─────────────────────────────────────────────────────────────────────────

    def write(self, entity: PlanEntity, body: str = "") -> Path:
        """Atomic write of entity to its canonical markdown file.

        Writes to .tmp then renames (atomic on POSIX and modern Windows).
        """
        path = self.path_for(entity)
        entity.source_md_path = path
        entity.updated_at = datetime.now(timezone.utc)

        frontmatter = entity.to_frontmatter_dict()
        md_content = serialize_to_markdown(frontmatter, body)

        tmp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp_path.write_text(md_content, encoding="utf-8")
            tmp_path.replace(path)
        except OSError as e:
            raise MarkdownWriteError(
                f"Failed to write markdown file: {e}",
                context={"path": str(path)},
            ) from e

        return path

    def read(self, path: Path) -> PlanEntity:
        """Read and parse a markdown file into a PlanEntity."""
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            raise MarkdownParseError(
                f"Failed to read markdown file: {e}",
                context={"path": str(path)},
            ) from e

        data, _ = parse_from_markdown(content)
        if not data:
            raise MarkdownParseError(
                "Empty or missing frontmatter",
                context={"path": str(path)},
            )

        data = dict_to_frontmatter(data)
        data["source_md_path"] = path

        # Discriminate by entity_type
        from ikigai.entities.plan.dream import DreamEntity
        from ikigai.entities.plan.goal import GoalEntity
        from ikigai.entities.plan.objective import ObjectiveEntity
        from ikigai.entities.plan.project import ProjectEntity
        from ikigai.entities.plan.task import TaskEntity
        from ikigai.entities.plan.deliverable import DeliverableEntity

        entity_type = data.get("entity_type")
        model_map = {
            EntityType.DREAM: DreamEntity,
            EntityType.GOAL: GoalEntity,
            EntityType.OBJECTIVE: ObjectiveEntity,
            EntityType.PROJECT: ProjectEntity,
            EntityType.TASK: TaskEntity,
            EntityType.DELIVERABLE: DeliverableEntity,
        }
        model_cls = model_map.get(entity_type, PlanEntity)
        return model_cls.model_validate(data)

    def delete(self, entity: PlanEntity) -> bool:
        """Delete the entity's markdown file. Returns True if deleted."""
        path = self.path_for(entity)
        if path.exists():
            path.unlink()
            return True
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Query operations
    # ─────────────────────────────────────────────────────────────────────────

    def list_all(self, entity_type: EntityType | None = None) -> list[Path]:
        """List all markdown paths for an entity type (or all)."""
        paths: list[Path] = []
        if entity_type is not None:
            subdir = self.vault_root / _dir_for(entity_type)
            if subdir.exists():
                paths = sorted(subdir.glob("*.md"))
        else:
            for sub in self.vault_root.iterdir():
                if sub.is_dir():
                    paths.extend(sorted(sub.glob("*.md")))
        return paths

    def find_by_slug(self, entity_type: EntityType, slug: str) -> Path | None:
        """Find a markdown file by type + slug."""
        subdir = self.vault_root / _dir_for(entity_type)
        candidate = subdir / f"{slug}.md"
        return candidate if candidate.exists() else None

    def query(
        self,
        entity_type: EntityType | None = None,
        status: str | None = None,
        ikigai_vector: str | None = None,
        needs_review_days: int | None = None,
    ) -> list[PlanEntity]:
        """Dynamic query across the vault."""
        paths = self.list_all(entity_type)
        results: list[PlanEntity] = []
        now = datetime.now(timezone.utc)

        for path in paths:
            try:
                entity = self.read(path)
            except MarkdownParseError:
                continue  # skip malformed files

            if status and entity.status.value != status:
                continue
            if ikigai_vector:
                root = ikigai_vector.split(".", 1)[0]
                if not any(v.value == root or v.value == ikigai_vector for v in entity.ikigai_vectors):
                    continue
            if needs_review_days is not None:
                if entity.last_reviewed_at is None:
                    continue
                age_days = (now - entity.last_reviewed_at).days
                if age_days < needs_review_days:
                    continue
            results.append(entity)

        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Index (for fast queries)
    # ─────────────────────────────────────────────────────────────────────────

    def index_dump(self) -> dict[str, Any]:
        """Build a JSON index of the vault (for cross-DB queries)."""
        index: dict[str, Any] = {
            "vault_root": str(self.vault_root),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "entities": [],
        }
        for path in self.list_all():
            try:
                entity = self.read(path)
                index["entities"].append(
                    {
                        "ueid": str(entity.ueid),
                        "entity_type": entity.entity_type.value,
                        "slug": entity.slug,
                        "status": entity.status.value,
                        "ikigai_vectors": [v.value for v in entity.ikigai_vectors],
                        "parent_ueid": str(entity.parent_ueid) if entity.parent_ueid else None,
                        "phase_at_creation": entity.phase_at_creation.value if entity.phase_at_creation else None,
                        "last_reviewed_at": (
                            entity.last_reviewed_at.isoformat() if entity.last_reviewed_at else None
                        ),
                        "path": str(path.relative_to(self.vault_root)),
                    }
                )
            except MarkdownParseError:
                continue
        return index

    def index_save(self, path: Path | str | None = None) -> Path:
        """Save index to disk."""
        if path is None:
            path = self.vault_root / "meta" / "vault_index.json"
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.index_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path


__all__ = ["MarkdownDB"]
