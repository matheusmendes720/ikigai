"""Tests for the M161 vault-intent-extract skill.

The skill ships in two layers:
  - `agents.v2.skills.vault_intent_extract` — pure-Python regex extractor + proposal builder
  - `.claude/skills/vault-intent-extract/SKILL.md` — Claude Code skill description

These tests cover the pure-Python layer (pattern coverage, dedup, idempotency,
proposal shape) and the review-queue integration (approved proposal →
TaskChange lands in `data/review_queue/`).

Run::

    cd src/ikigai && uv run pytest tests/skills/test_vault_intent_extract.py -v
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


_FIXED_TODAY = date(2026, 10, 1)


@pytest.fixture
def skill():
    from agents.v2.skills import vault_intent_extract

    return vault_intent_extract


@pytest.fixture
def proposal_cls():
    from agents.v2.proposals import Proposal

    return Proposal


# ---------------------------------------------------------------------------
# extract_candidates: per-pattern coverage
# ---------------------------------------------------------------------------


class TestAmanhaPattern:
    def test_amanha_eu_faco_x(self, skill: Any) -> None:
        md = "amanhã eu faço o relatório semanal"
        cands = skill.extract_candidates(md, today=_FIXED_TODAY)
        assert len(cands) == 1
        c = cands[0]
        assert c["fields"]["title"] == "o relatório semanal"
        assert c["fields"]["due"] == (_FIXED_TODAY + timedelta(days=1)).isoformat()

    def test_amanha_x_no_verb(self, skill: Any) -> None:
        md = "amanhã comprar leite"
        cands = skill.extract_candidates(md, today=_FIXED_TODAY)
        assert len(cands) == 1
        assert cands[0]["fields"]["title"] == "comprar leite"

    def test_amanha_uppercase(self, skill: Any) -> None:
        """Case-insensitive matching is part of the SKILL.md contract."""
        md = "AMANHÃ EU VOU revisar docs"
        cands = skill.extract_candidates(md, today=_FIXED_TODAY)
        assert len(cands) == 1
        assert cands[0]["fields"]["due"] == (_FIXED_TODAY + timedelta(days=1)).isoformat()


class TestProximaSemanaPattern:
    def test_proxima_semana_x(self, skill: Any) -> None:
        md = "próxima semana vou revisar docs antigos"
        cands = skill.extract_candidates(md, today=_FIXED_TODAY)
        assert len(cands) == 1
        assert cands[0]["fields"]["due"] == (_FIXED_TODAY + timedelta(days=7)).isoformat()

    def test_proxima_semana_no_accent(self, skill: Any) -> None:
        md = "proxima semana fazer migration"
        cands = skill.extract_candidates(md, today=_FIXED_TODAY)
        assert len(cands) == 1


class TestExplicitDeadlinePattern:
    def test_deadline_explicit_date(self, skill: Any) -> None:
        md = "deadline 2026-10-15 fechar Q3 retro"
        cands = skill.extract_candidates(md, today=_FIXED_TODAY)
        assert len(cands) == 1
        c = cands[0]
        assert c["fields"]["title"] == "fechar Q3 retro"
        assert c["fields"]["due"] == "2026-10-15"

    def test_deadline_e_date_pt_br(self, skill: Any) -> None:
        md = "deadline é 2026-11-01 pagar boleto"
        cands = skill.extract_candidates(md, today=_FIXED_TODAY)
        assert len(cands) == 1
        assert cands[0]["fields"]["due"] == "2026-11-01"


class TestTodoPattern:
    def test_todo(self, skill: Any) -> None:
        md = "TODO: limpar inbox de email"
        cands = skill.extract_candidates(md, today=_FIXED_TODAY)
        assert len(cands) == 1
        assert cands[0]["fields"]["title"] == "limpar inbox de email"
        assert cands[0]["fields"]["due"] is None

    def test_fixme(self, skill: Any) -> None:
        md = "FIXME: rebuild cache"
        cands = skill.extract_candidates(md, today=_FIXED_TODAY)
        assert len(cands) == 1
        assert cands[0]["fields"]["title"] == "rebuild cache"


class TestLembrarPattern:
    def test_lembrar_de_x(self, skill: Any) -> None:
        md = "lembrar de pagar conta de luz"
        cands = skill.extract_candidates(md, today=_FIXED_TODAY)
        assert len(cands) == 1
        assert cands[0]["fields"]["title"] == "pagar conta de luz"
        assert cands[0]["fields"]["due"] is None


# ---------------------------------------------------------------------------
# Dedup and idempotency
# ---------------------------------------------------------------------------


class TestDedup:
    def test_duplicate_within_note_dedupes(self, skill: Any) -> None:
        # Same captured task text twice → deduped to 1 candidate.
        md = (
            "amanhã eu faço o relatório\n"
            "amanhã eu faço o relatório\n"
        )
        cands = skill.extract_candidates(md, today=_FIXED_TODAY)
        assert len(cands) == 1

    def test_case_insensitive_dedup(self, skill: Any) -> None:
        md = "TODO: limpar inbox\ntodo: limpar inbox"
        cands = skill.extract_candidates(md, today=_FIXED_TODAY)
        assert len(cands) == 1


class TestIdempotency:
    def test_ueids_deterministic(self, skill: Any) -> None:
        """Same task text → same UEID across runs (idempotency contract)."""
        md = "amanhã eu faço o relatório semanal"
        c1 = skill.extract_candidates(md, today=_FIXED_TODAY)
        c2 = skill.extract_candidates(md, today=_FIXED_TODAY)
        assert c1[0]["ueid"] == c2[0]["ueid"]

    def test_propose_idempotent(self, skill: Any) -> None:
        md = "TODO: rebuild cache\namanhã eu faço o relatório"
        p1 = skill.propose(md, today=_FIXED_TODAY)
        p2 = skill.propose(md, today=_FIXED_TODAY)
        # Compare deterministic content (ignoring timestamp / proposal_id)
        assert p1.skill == p2.skill
        assert p1.changes == p2.changes
        assert p1.reasoning == p2.reasoning


# ---------------------------------------------------------------------------
# propose / propose_from_file: shape and edge cases
# ---------------------------------------------------------------------------


class TestPropose:
    def test_builds_valid_proposal(self, skill: Any, proposal_cls: Any) -> None:
        md = "TODO: rebuild cache"
        proposal = skill.propose(md, today=_FIXED_TODAY)
        assert isinstance(proposal, proposal_cls)
        assert proposal.skill == "vault-intent-extract"
        assert proposal.approval_state == "pending"
        errors = proposal.validate()
        assert errors == [], f"unexpected validation errors: {errors}"

    def test_each_change_has_required_fields(self, skill: Any) -> None:
        md = "TODO: rebuild cache\namanhã eu faço X"
        proposal = skill.propose(md, today=_FIXED_TODAY)
        for c in proposal.changes:
            # Implementation emits uppercase "CREATE" — part of the contract.
            assert c["action"] == "CREATE"
            assert "ueid" in c
            assert "fields" in c
            assert "title" in c["fields"]
            assert "priority" in c["fields"]
            # rationale + ueid are the audit trail
            assert "rationale" in c

    def test_empty_markdown_empty_proposal(self, skill: Any) -> None:
        proposal = skill.propose("", today=_FIXED_TODAY)
        assert proposal.changes == []

    def test_run_skill_entry_point(self, skill: Any) -> None:
        proposal = skill.run_skill(markdown="TODO: rebuild cache")
        assert proposal.skill == "vault-intent-extract"
        assert len(proposal.changes) == 1


class TestProposeFromFile:
    def test_reads_existing_file(self, skill: Any, tmp_path: Path) -> None:
        note = tmp_path / "2026-10-01.md"
        note.write_text("TODO: rebuild cache\n", encoding="utf-8")
        proposal = skill.propose_from_file(note, today=_FIXED_TODAY)
        assert len(proposal.changes) == 1
        assert proposal.changes[0]["fields"]["title"] == "rebuild cache"

    def test_missing_file_returns_empty(self, skill: Any, tmp_path: Path) -> None:
        proposal = skill.propose_from_file(
            tmp_path / "does-not-exist.md", today=_FIXED_TODAY
        )
        assert proposal.changes == []
        assert "not found" in proposal.reasoning

    def test_empty_file_returns_empty(self, skill: Any, tmp_path: Path) -> None:
        note = tmp_path / "empty.md"
        note.write_text("", encoding="utf-8")
        proposal = skill.propose_from_file(note, today=_FIXED_TODAY)
        assert proposal.changes == []


# ---------------------------------------------------------------------------
# Review-queue integration
# ---------------------------------------------------------------------------


class TestReviewQueueIntegration:
    def test_approved_proposal_creates_taskchange(
        self, skill: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Approved proposal → TaskChange lands in data/review_queue/."""
        from src.mesh import queue as queue_mod

        monkeypatch.setattr(queue_mod, "QUEUE_DIR", tmp_path)

        from contracts.task_change import TaskAction, TaskChange

        md = "TODO: rebuild cache"
        proposal = skill.propose(md, today=_FIXED_TODAY)
        assert proposal.approval_state == "pending"
        proposal.approval_state = "approved"

        for c in proposal.changes:
            tc = TaskChange(
                event_id=uuid.uuid4().hex,
                ueid=c["ueid"],
                action=TaskAction.CREATE,
                fields=c["fields"],
                source_fork=f"td_chat:{skill.SKILL_NAME}",
                timestamp=datetime.now(timezone.utc),
            )
            queue_mod.enqueue(tc)

        queue_files = list(tmp_path.glob("*.json"))
        assert len(queue_files) == len(proposal.changes) == 1
        payload = json.loads(queue_files[0].read_text(encoding="utf-8"))
        assert payload["action"] == "create"
        assert payload["source_fork"] == f"td_chat:{skill.SKILL_NAME}"

    def test_meta_plan_format_for_audit(self, skill: Any) -> None:
        md = "TODO: rebuild cache\namanhã eu faço o relatório"
        proposal = skill.propose(md, today=_FIXED_TODAY)
        for c in proposal.changes:
            assert "rationale" in c
            assert isinstance(c["rationale"], str)
            assert len(c["rationale"]) > 0


# ---------------------------------------------------------------------------
# File-handling safety
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_propose_does_not_touch_filesystem(self, skill: Any, tmp_path: Path) -> None:
        """propose() is a pure function — it must NOT write to disk."""
        with patch.object(Path, "write_text") as mock_write:
            skill.propose("TODO: rebuild cache", today=_FIXED_TODAY)
            mock_write.assert_not_called()

    def test_propose_from_file_handles_missing_gracefully(
        self, skill: Any, tmp_path: Path
    ) -> None:
        proposal = skill.propose_from_file(
            tmp_path / "missing.md", today=_FIXED_TODAY
        )
        assert proposal.skill == "vault-intent-extract"
        assert proposal.changes == []


# ---------------------------------------------------------------------------
# Drift guards
# ---------------------------------------------------------------------------


def test_skill_name_is_stable(skill: Any) -> None:
    assert skill.SKILL_NAME == "vault-intent-extract"


def test_intent_patterns_shape(skill: Any) -> None:
    """INTENT_PATTERNS is a sequence of (regex, due_offset_days_or_None, due_explicit_group_or_None)
    triples. Drift guard against silent refactors that break the triple shape."""
    patterns = skill.INTENT_PATTERNS
    assert isinstance(patterns, (list, tuple))
    for entry in patterns:
        assert isinstance(entry, tuple)
        assert len(entry) == 3
        regex, due_offset, due_explicit = entry
        assert isinstance(regex, str)
        assert due_offset is None or isinstance(due_offset, int)
        assert due_explicit is None or isinstance(due_explicit, str)


def test_gen_ueid_format(skill: Any) -> None:
    """UEIDs follow 5-part format `tsk:intention:<h8>:<h8>:<h8>`. Drift guard
    against silent format changes that would break the cross-fork join."""
    md = "TODO: rebuild cache"
    cands = skill.extract_candidates(md, today=_FIXED_TODAY)
    ueid = cands[0]["ueid"]
    parts = ueid.split(":")
    assert len(parts) == 5
    assert parts[0] == "tsk"
    assert parts[1] == "intention"
