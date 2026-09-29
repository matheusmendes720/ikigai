"""M161 — Shared Proposal dataclass.

Skills (taskdog-triage, vault-intent-extract, meta_plan, etc) emit
Proposals instead of executing changes directly. The user approves
via `--approve` and only then are changes applied via review_queue.

Constitutional references:
- reversibility_over_cleverness: nothing happens without explicit approval
- state_on_disk_not_conversation: Proposal is persisted to vault_log
- tests_are_the_contract: Proposal.validate() catches malformed inputs
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Proposal:
    """A pending set of changes proposed by a skill.

    Approval states:
        pending  — emitted by skill, awaiting user
        approved — user said --approve, will be applied
        rejected — user said --reject, discarded
        applied  — changes have been queued via review_queue
    """

    skill: str
    reasoning: str
    changes: list[dict[str, Any]]
    approval_state: str = "pending"
    created_at: str = ""
    applied_at: str = ""
    proposal_id: str = ""
    vault_log_path: str = ""

    def __post_init__(self) -> None:
        if not self.proposal_id:
            self.proposal_id = f"prop-{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.approval_state not in ("pending", "approved", "rejected", "applied"):
            raise ValueError(f"invalid approval_state: {self.approval_state}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def summary(self) -> str:
        """One-line human summary for display."""
        n = len(self.changes)
        word = "change" if n == 1 else "changes"
        return f"{self.skill}: {n} {word} (state={self.approval_state})"

    def validate(self) -> list[str]:
        """Return list of validation errors (empty if valid)."""
        errors: list[str] = []
        if not self.skill:
            errors.append("skill name is required")
        if not self.changes:
            errors.append("proposal has no changes")
        for i, c in enumerate(self.changes):
            if "action" not in c:
                errors.append(f"change #{i} missing 'action'")
            if "ueid" not in c:
                errors.append(f"change #{i} missing 'ueid'")
        return errors

    def write_to_vault(self, vault_dir: str = "vault/proposals") -> str:
        """Persist the proposal to disk as a JSON file. Returns path."""
        path = Path(vault_dir)
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / f"{self.proposal_id}.json"
        file_path.write_text(self.to_json(), encoding="utf-8")
        self.vault_log_path = str(file_path)
        return str(file_path)
