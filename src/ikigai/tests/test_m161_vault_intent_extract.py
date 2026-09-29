"""Tests for M161 — vault-intent-extract skill."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from agents.v2.skills import vault_intent_extract


# ---------------------------------------------------------------------------
# Pattern matching — individual patterns
# ---------------------------------------------------------------------------


def test_amanha_pattern_creates_tomorrow_due():
    """'amanhã eu vou X' creates a candidate due tomorrow."""
    today = date(2026, 9, 29)
    md = "Amanhã eu vou revisar o vault cache"
    candidates = vault_intent_extract.extract_candidates(md, today=today)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["action"] == "CREATE"
    assert "revisar o vault cache" in c["fields"]["title"]
    assert c["fields"]["due"] == (today + timedelta(days=1)).isoformat()
    assert c["fields"]["priority"] == 3


def test_proxima_semana_pattern_creates_next_week_due():
    """'próxima semana X' creates a candidate due in 7 days."""
    today = date(2026, 9, 29)
    md = "Próxima semana vou planejar Q4 com cuidado"
    candidates = vault_intent_extract.extract_candidates(md, today=today)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["fields"]["due"] == (today + timedelta(days=7)).isoformat()


def test_deadline_with_explicit_date():
    """'deadline 2026-10-15 X' uses the explicit date."""
    today = date(2026, 9, 29)
    md = "Deadline 2026-10-15 entregar proposta da consultoria"
    candidates = vault_intent_extract.extract_candidates(md, today=today)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["fields"]["due"] == "2026-10-15"


def test_todo_pattern_no_due():
    """'TODO: X' creates a candidate with no due date."""
    today = date(2026, 9, 29)
    md = "TODO: implementar M161 skills"
    candidates = vault_intent_extract.extract_candidates(md, today=today)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["fields"]["due"] is None
    assert "implementar M161" in c["fields"]["title"]


def test_fixme_pattern_works():
    """FIXME works the same as TODO."""
    today = date(2026, 9, 29)
    md = "FIXME consertar bug de import"
    candidates = vault_intent_extract.extract_candidates(md, today=today)
    assert len(candidates) == 1


def test_lembrar_pattern_no_due():
    """'lembrar de X' creates a candidate with no due."""
    today = date(2026, 9, 29)
    md = "Lembrar de responder o email da Roberta"
    candidates = vault_intent_extract.extract_candidates(md, today=today)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["fields"]["due"] is None
    assert "Roberta" in c["fields"]["title"]


# ---------------------------------------------------------------------------
# Pattern matching — combined
# ---------------------------------------------------------------------------


def test_multiple_patterns_create_multiple_candidates():
    """Markdown with 5 different patterns → 5 candidates."""
    today = date(2026, 9, 29)
    md = """
Hoje eu trabalhei em várias coisas.
Amanhã eu vou revisar o vault cache.
TODO: implementar M161.
Próxima semana vou planejar Q4.
Lembrar de responder email.
Deadline 2026-10-15 proposta final.
"""
    candidates = vault_intent_extract.extract_candidates(md, today=today)
    assert len(candidates) == 5


def test_empty_markdown_no_candidates():
    """Empty markdown → no candidates."""
    today = date(2026, 9, 29)
    assert vault_intent_extract.extract_candidates("", today=today) == []


def test_markdown_without_patterns_no_candidates():
    """Markdown with no intent patterns → no candidates."""
    today = date(2026, 9, 29)
    md = "Hoje o dia foi tranquilo. Nada de especial pra fazer."
    assert vault_intent_extract.extract_candidates(md, today=today) == []


def test_duplicate_task_deduplicated():
    """Same task mentioned twice with different patterns → only once."""
    today = date(2026, 9, 29)
    md = """
Amanhã vou revisar vault.
TODO: revisar vault.
"""
    candidates = vault_intent_extract.extract_candidates(md, today=today)
    # Both match different patterns but same task → dedupe
    assert len(candidates) == 1


# ---------------------------------------------------------------------------
# UEID generation
# ---------------------------------------------------------------------------


def test_each_candidate_has_unique_ueid():
    """Every candidate has a distinct UEID."""
    today = date(2026, 9, 29)
    md = """
Amanhã task A
Amanhã task B
TODO task C
"""
    candidates = vault_intent_extract.extract_candidates(md, today=today)
    ueids = [c["ueid"] for c in candidates]
    assert len(ueids) == len(set(ueids))


def test_ueid_has_5_parts_format():
    """UEIDs follow 5-part lowercase format."""
    today = date(2026, 9, 29)
    md = "Amanhã vou fazer alguma coisa"
    candidates = vault_intent_extract.extract_candidates(md, today=today)
    ueid = candidates[0]["ueid"]
    parts = ueid.split(":")
    assert len(parts) == 5
    assert parts[0] == "tsk"
    assert parts[1] == "intention"


def test_ueid_is_deterministic_for_same_task():
    """Same task text → same UEID (so re-extracting is idempotent)."""
    today = date(2026, 9, 29)
    md1 = "Amanhã revisar vault"
    md2 = "Amanhã revisar vault"  # same content
    c1 = vault_intent_extract.extract_candidates(md1, today=today)
    c2 = vault_intent_extract.extract_candidates(md2, today=today)
    assert c1[0]["ueid"] == c2[0]["ueid"]


# ---------------------------------------------------------------------------
# Task text cleaning
# ---------------------------------------------------------------------------


def test_short_matches_filtered_out():
    """Matches shorter than 5 chars are filtered."""
    today = date(2026, 9, 29)
    md = "Amanhã a"  # task too short
    candidates = vault_intent_extract.extract_candidates(md, today=today)
    assert candidates == []


def test_long_task_truncated_to_80_chars():
    """Tasks longer than 80 chars are truncated with '...'."""
    today = date(2026, 9, 29)
    long_task = "x" * 100
    md = f"Amanhã {long_task}"
    candidates = vault_intent_extract.extract_candidates(md, today=today)
    assert len(candidates) == 1
    assert len(candidates[0]["fields"]["title"]) <= 80


# ---------------------------------------------------------------------------
# propose / propose_from_file
# ---------------------------------------------------------------------------


def test_propose_returns_pending_proposal():
    """propose() returns a Proposal with state='pending' and the right skill."""
    today = date(2026, 9, 29)
    p = vault_intent_extract.propose("Amanhã vou fazer X", today=today)
    assert p.approval_state == "pending"
    assert p.skill == "vault-intent-extract"
    assert len(p.changes) == 1
    assert p.proposal_id
    assert p.created_at


def test_propose_from_existing_file(tmp_path):
    """propose_from_file reads a real file."""
    today = date(2026, 9, 29)
    note = tmp_path / "2026-09-29.md"
    note.write_text("Amanhã vou testar M161\nTODO: validar skill\n", encoding="utf-8")
    p = vault_intent_extract.propose_from_file(note, today=today)
    assert len(p.changes) == 2


def test_propose_from_missing_file_returns_empty():
    """propose_from_file on missing path → empty proposal (no crash)."""
    p = vault_intent_extract.propose_from_file("/nonexistent/path.md")
    assert p.changes == []
    assert "not found" in p.reasoning


def test_run_skill_with_empty_string():
    """run_skill('') → empty proposal."""
    p = vault_intent_extract.run_skill("")
    assert p.changes == []


# ---------------------------------------------------------------------------
# Skill registry integration
# ---------------------------------------------------------------------------


def test_skill_registered_in_registry():
    """vault_intent-extract is registered in the skills registry."""
    from agents.v2.skills import list_skills
    assert "vault-intent-extract" in list_skills()
    assert "taskdog-triage" in list_skills()
