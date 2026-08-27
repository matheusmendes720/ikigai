"""Triagem — drift detection + triagem.md generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class DriftEntry:
    """A single drift record."""

    timestamp: datetime
    entity_ueid: str
    entity_path: Path
    markdown_mtime: datetime
    sqlite_mtime: datetime | None
    drift_kind: str  # markdown_newer | sqlite_newer | both_modified | missing_sqlite
    decision: str  # markdown_wins | sqlite_wins | needs_merge
    resolution: str = ""


@dataclass
class Triagem:
    """Drift triage report generator."""

    entries: list[DriftEntry] = field(default_factory=list)
    vault_root: Path | None = None

    def add(self, entry: DriftEntry) -> None:
        self.entries.append(entry)

    def to_markdown(self) -> str:
        """Render triagem.md content."""
        lines: list[str] = [
            "# Triagem — Drift Detection Report",
            "",
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
            f"**Vault:** {self.vault_root or 'unknown'}",
            f"**Drift entries:** {len(self.entries)}",
            "",
        ]

        if not self.entries:
            lines.append("✅ No drift detected. Markdown and SQLite are in sync.")
            return "\n".join(lines) + "\n"

        # Group by kind
        by_kind: dict[str, list[DriftEntry]] = {}
        for entry in self.entries:
            by_kind.setdefault(entry.drift_kind, []).append(entry)

        for kind, entries in sorted(by_kind.items()):
            lines.append(f"## {kind} ({len(entries)} entries)")
            lines.append("")
            for e in entries:
                lines.append(f"### `{e.entity_path.name}` ({e.entity_ueid})")
                lines.append(f"- markdown mtime: `{e.markdown_mtime.isoformat()}`")
                lines.append(f"- sqlite mtime:   `{e.sqlite_mtime.isoformat() if e.sqlite_mtime else 'N/A'}`")
                lines.append(f"- decision: **{e.decision}**")
                if e.resolution:
                    lines.append(f"- resolution: {e.resolution}")
                lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## Resolution Commands",
                "",
                "```bash",
                "# Prefer markdown (rebuild SQLite from vault):",
                "ikigai sync --prefer markdown",
                "",
                "# Prefer SQLite (write back to markdown):",
                "ikigai sync --prefer sqlite",
                "",
                "# 3-way merge (resolve conflicts manually):",
                "ikigai sync --prefer merge",
                "```",
                "",
            ]
        )

        return "\n".join(lines)

    def write(self, path: Path | str | None = None) -> Path:
        """Write triagem.md to vault."""
        if path is None:
            assert self.vault_root is not None, "vault_root must be set"
            path = self.vault_root / "meta" / "triagem.md"
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(), encoding="utf-8")
        return path


__all__ = ["DriftEntry", "Triagem"]
