"""Core types: UEID (tri-key), ScoreValue (with unit), Path utilities.

Anti-fragile identity: UEID = namespace:entity_type:slug:uuid_short:content_hash_short
- slug: human-readable, immutable
- uuid_short: 8-char UUID, immutable
- content_hash_short: 8-char SHA-256, detects drift

ScoreValue explicitly carries unit to avoid 0-100 vs 0-1 vs RICE 1-10 confusion.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, GetCoreSchemaHandler
from pydantic_core import core_schema


# ─────────────────────────────────────────────────────────────────────────────
# UEID — Tri-key Universal Entity Identifier
# ─────────────────────────────────────────────────────────────────────────────


class UEID(str):
    """Tri-key Universal Entity Identifier (anti-fragile).

    Format: `<namespace>:<entity_type>:<slug>:<uuid_short>:<content_hash_short>`

    Components:
    - `namespace`: ikigai | tw | obsidian | external
    - `entity_type`: dream | goal | objective | project | task | deliverable | ...
    - `slug`: human-readable, immutable post-creation
    - `uuid_short`: 8-char UUID (system-generated, immutable)
    - `content_hash_short`: 8-char SHA-256 of canonical form (drift detection)
    """

    _PATTERN = re.compile(
        r"^(?P<namespace>[a-z]+):(?P<entity_type>[a-z_]+):"
        r"(?P<slug>[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]):"
        r"(?P<uuid_short>[a-f0-9]{8}):"
        r"(?P<content_hash_short>[a-f0-9]{8})$"
    )

    def __new__(cls, value: str) -> "UEID":
        if not cls._PATTERN.match(value):
            raise ValueError(
                f"Invalid UEID format: {value!r}. "
                f"Expected: <namespace>:<entity_type>:<slug>:<uuid_short>:<content_hash_short>"
            )
        return super().__new__(cls, value)

    @property
    def namespace(self) -> str:
        return self._PATTERN.match(self).group("namespace")  # type: ignore[union-attr]

    @property
    def entity_type(self) -> str:
        return self._PATTERN.match(self).group("entity_type")  # type: ignore[union-attr]

    @property
    def slug(self) -> str:
        return self._PATTERN.match(self).group("slug")  # type: ignore[union-attr]

    @property
    def uuid_short(self) -> str:
        return self._PATTERN.match(self).group("uuid_short")  # type: ignore[union-attr]

    @property
    def content_hash_short(self) -> str:
        return self._PATTERN.match(self).group("content_hash_short")  # type: ignore[union-attr]

    @classmethod
    def generate(
        cls,
        namespace: str,
        entity_type: str,
        slug: str,
        canonical_content: str = "",
    ) -> "UEID":
        """Generate a new UEID.

        Args:
            namespace: e.g., 'ikigai', 'tw', 'obsidian'
            entity_type: e.g., 'dream', 'goal', 'project'
            slug: human-readable identifier
            canonical_content: optional content for hash (e.g., JSON frontmatter)
        """
        # Validate components
        if not re.match(r"^[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]$", slug):
            raise ValueError(f"Invalid slug: {slug!r}. Must be lowercase, 2-64 chars, [a-z0-9_-]")
        if not re.match(r"^[a-z_]+$", entity_type):
            raise ValueError(f"Invalid entity_type: {entity_type!r}. Must be lowercase [a-z_]")
        if not re.match(r"^[a-z]+$", namespace):
            raise ValueError(f"Invalid namespace: {namespace!r}. Must be lowercase [a-z]+")

        uuid_short = uuid.uuid4().hex[:8]
        content_hash = hashlib.sha256(canonical_content.encode("utf-8")).hexdigest()[:8]
        ueid_str = f"{namespace}:{entity_type}:{slug}:{uuid_short}:{content_hash}"
        return cls(ueid_str)

    def with_new_content_hash(self, new_content: str) -> "UEID":
        """Return a new UEID with updated content_hash (slug + uuid unchanged)."""
        new_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()[:8]
        return UEID(f"{self.namespace}:{self.entity_type}:{self.slug}:{self.uuid_short}:{new_hash}")

    def short(self) -> str:
        """Return a shortened display form: namespace:entity_type:slug."""
        return f"{self.namespace}:{self.entity_type}:{self.slug}"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# ScoreValue — score with explicit unit
# ─────────────────────────────────────────────────────────────────────────────


ScoreUnit = Literal["percent", "ratio", "raw", "index", "currency_brl", "hours"]


class ScoreValue(BaseModel):
    """Score value with explicit unit (avoids 0-100 vs 0-1 confusion).

    Units:
    - percent: 0-100
    - ratio: 0-1
    - raw: arbitrary (e.g., RICE reach 1-10)
    - index: composite (e.g., Q_HE 0-1, alignment 0-100)
    - currency_brl: BRL amount
    - hours: time duration in hours
    """

    value: float
    unit: ScoreUnit = "percent"

    @classmethod
    def percent(cls, value: float) -> "ScoreValue":
        if not 0 <= value <= 100:
            raise ValueError(f"percent must be in [0, 100], got {value}")
        return cls(value=value, unit="percent")

    @classmethod
    def ratio(cls, value: float) -> "ScoreValue":
        if not 0 <= value <= 1:
            raise ValueError(f"ratio must be in [0, 1], got {value}")
        return cls(value=value, unit="ratio")

    @classmethod
    def raw(cls, value: float, max_value: float = 10.0) -> "ScoreValue":
        if not 0 <= value <= max_value:
            raise ValueError(f"raw must be in [0, {max_value}], got {value}")
        return cls(value=value, unit="raw")

    def to_percent(self) -> "ScoreValue":
        """Convert to percent unit."""
        if self.unit == "percent":
            return self
        if self.unit == "ratio":
            return ScoreValue(value=self.value * 100, unit="percent")
        if self.unit == "index":
            return ScoreValue(value=self.value * 100, unit="percent")
        raise ValueError(f"Cannot convert {self.unit} to percent")

    def to_ratio(self) -> "ScoreValue":
        """Convert to ratio unit."""
        if self.unit == "ratio":
            return self
        if self.unit == "percent":
            return ScoreValue(value=self.value / 100, unit="ratio")
        if self.unit == "index":
            return ScoreValue(value=self.value, unit="ratio")
        raise ValueError(f"Cannot convert {self.unit} to ratio")

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ScoreValue):
            return self.value == other.value and self.unit == other.unit
        if isinstance(other, (int, float)):
            return self.value == other
        return NotImplemented

    def __lt__(self, other: "ScoreValue | float") -> bool:
        if isinstance(other, ScoreValue):
            return self.value < other.value
        return self.value < other

    def __le__(self, other: "ScoreValue | float") -> bool:
        if isinstance(other, ScoreValue):
            return self.value <= other.value
        return self.value <= other

    def __gt__(self, other: "ScoreValue | float") -> bool:
        if isinstance(other, ScoreValue):
            return self.value > other.value
        return self.value > other

    def __ge__(self, other: "ScoreValue | float") -> bool:
        if isinstance(other, ScoreValue):
            return self.value >= other.value
        return self.value >= other

    def __hash__(self) -> int:
        return hash((self.value, self.unit))


# ─────────────────────────────────────────────────────────────────────────────
# Path utilities
# ─────────────────────────────────────────────────────────────────────────────


def vault_path_for(entity_type_slug: str, slug: str) -> Path:
    """Return canonical markdown path for an entity in the vault.

    Layout:
        vault_root/<entity_type_plural>/<slug>.md
    """
    type_to_dir = {
        "dream": "dreams",
        "goal": "goals",
        "objective": "objectives",
        "project": "projects",
        "task": "tasks",
        "deliverable": "deliverables",
        "routine": "routines",
        "block": "blocks",
        "ritual": "rituals",
        "habit": "habits",
        "skill": "skills",
        "topic": "topics",
        "material": "materials",
        "session": "sessions",
        "vector": "ikigai_state",
        "profile": "ikigai_state",
    }
    subdir = type_to_dir.get(entity_type_slug, entity_type_slug + "s")
    return Path(subdir) / f"{slug}.md"


# ─────────────────────────────────────────────────────────────────────────────
# Re-exports
# ─────────────────────────────────────────────────────────────────────────────


__all__ = [
    "UEID",
    "ScoreUnit",
    "ScoreValue",
    "vault_path_for",
]
