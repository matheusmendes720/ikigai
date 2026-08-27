"""IKIGAiAgenticWriter — sole canonical vault writer.

Replaces f-string writer at src/agents/tools.py:350-385.
Sole authority for IKIGAiRecord → markdown round-trip.
"""
from __future__ import annotations

from pathlib import Path

import frontmatter

from ikigai.entities.ikigai_record import IKIGAiRecord
from ikigai.vault.dict_to_frontmatter import dict_to_frontmatter
from ikigai.vault.lock import VaultLock


class IKIGAiAgenticWriter:
    def __init__(
        self,
        vault_dir: Path,
        lock_path: Path | None = None,
    ) -> None:
        self.vault_dir = Path(vault_dir)
        self.lock_path = lock_path or (self.vault_dir / ".vault.lock")

    def write(self, record: IKIGAiRecord) -> Path:
        """Write record to its source_md_path; acquire file lock."""
        target = self._resolve_path(record.source_md_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        body = self._render_body(record)
        metadata = dict_to_frontmatter(record)

        with VaultLock(self.lock_path):
            frontmatter.dump(
                frontmatter.Post(content=body, **metadata),
                str(target),
            )
        return target

    def _resolve_path(self, source_md_path: Path) -> Path:
        if source_md_path.is_absolute():
            return source_md_path
        return self.vault_dir.parent / source_md_path

    @staticmethod
    def _render_body(record: IKIGAiRecord) -> str:
        """Render the markdown body below frontmatter.

        Default: brief title + status block. Entity-specific rendering
        can override in subclass.
        """
        return f"# {record.title}\n\nStatus: `{record.status.value}`\n"


__all__ = ["IKIGAiAgenticWriter"]