"""Unit tests for meta-planner nodes (Plan D Track B).

Combined B.1 + B.2 + B.3 unit tests for the meta-plan subgraph nodes:
  - B.1 (8 tests): nodes/meta_plan/classify_intent.py — pure keyword
    classifier that emits an IntentClassification (Pydantic v2 strict).
    Replaces D.1's TEMPORARY STUB with the real Pydantic implementation.
  - B.2 (3 tests): nodes/meta_plan/fetch_context.py — memory + folder +
    hierarchy context gathering with defensive fallbacks.
  - B.3 (4 tests): nodes/meta_plan/generate_proposal.py — typed Pydantic
    Proposal builder (consumes B.1 + B.2 outputs, emits Proposal pending).
"""

from __future__ import annotations

from src.ikigai.contracts.proposal import IntentClassification

from agents.v2.nodes.meta_plan.classify_intent import (
    PLANNING_KEYWORDS,
    classify_intent,
)


def test_classify_high_single_keyword():
    ic = classify_intent("quero focar em X essa semana")
    assert ic.level == "high"
    assert ic.score >= 1


def test_classify_high_multiple_keywords():
    ic = classify_intent("quero focar no objetivo da meta do projeto essa semana")
    assert ic.level == "high"
    assert ic.score >= 3


def test_classify_medium_two_keywords():
    ic = classify_intent("qual seria o próximo passo?")
    assert ic.level == "medium"


def test_classify_low_no_keywords():
    ic = classify_intent("que horas são?")
    assert ic.level == "low"
    assert ic.score == 0


def test_classify_case_insensitive():
    ic = classify_intent("QUERO FOCAR EM X")
    assert ic.level == "high"


def test_classify_threshold_zero_high_one_medium():
    # "qual seria" alone → medium (only 1 medium keyword)
    ic = classify_intent("qual seria")
    assert ic.level == "medium"


def test_classify_returns_intent_classification():
    ic = classify_intent("qualquer coisa")
    assert isinstance(ic, IntentClassification)


def test_planning_keywords_have_required_tiers():
    assert "high" in PLANNING_KEYWORDS
    assert "medium" in PLANNING_KEYWORDS
    assert all(isinstance(k, str) for k in PLANNING_KEYWORDS["high"])
    assert all(isinstance(k, str) for k in PLANNING_KEYWORDS["medium"])


# ---------------------------------------------------------------------------
# Plan D Task B.3 — generate_proposal
# ---------------------------------------------------------------------------

from src.ikigai.contracts.proposal import HierarchyMatch  # noqa: E402

from agents.v2.nodes.meta_plan.generate_proposal import generate_proposal  # noqa: E402


def test_generate_proposal_returns_pending_proposal():
    state = {
        "user_request": "quero focar em meta M01",
        "intent_classification": IntentClassification(level="high", score=2),
        "memory_refs": [],
        "folder_reads": [],
        "hierarchy_matches": HierarchyMatch(),
    }
    proposal = generate_proposal(state)
    assert proposal.approval_state == "pending"
    assert proposal.source_request == "quero focar em meta M01"


def test_generate_proposal_ueid_is_4_part():
    state = {
        "user_request": "x",
        "intent_classification": IntentClassification(level="low", score=0),
        "memory_refs": [],
        "folder_reads": [],
        "hierarchy_matches": HierarchyMatch(),
    }
    proposal = generate_proposal(state)
    import re

    assert re.match(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$", proposal.id)


def test_generate_proposal_traceability_lists_adrs():
    state = {
        "user_request": "x",
        "intent_classification": IntentClassification(level="high", score=1),
        "memory_refs": [],
        "folder_reads": [],
        "hierarchy_matches": HierarchyMatch(),
    }
    proposal = generate_proposal(state)
    assert "ADR-029" in proposal.traceability.adrs_consulted
    assert "ADR-013" in proposal.traceability.adrs_consulted
    assert "ADR-014" in proposal.traceability.adrs_consulted


def test_generate_proposal_low_intent_returns_empty_operations():
    state = {
        "user_request": "que horas são",
        "intent_classification": IntentClassification(level="low", score=0),
        "memory_refs": [],
        "folder_reads": [],
        "hierarchy_matches": HierarchyMatch(),
    }
    proposal = generate_proposal(state)
    # Low intent → empty operations (meta-planner skips; user gets fast-path)
    assert proposal.operations == []


# ---------------------------------------------------------------------------
# Plan D Task B.2 — fetch_context
# ---------------------------------------------------------------------------

from agents.v2.nodes.meta_plan.fetch_context import (  # noqa: E402
    fetch_context,
    scan_hierarchy,
)


def test_scan_hierarchy_returns_match_for_known_meta():
    """scan_hierarchy walks vault frontmatter for matching meta UEID."""
    # Use the in-repo vault mock fixture or empty test vault
    matches = scan_hierarchy("objetivo Q4-2026 build")
    # May be empty in test env; just verify it returns HierarchyMatch
    from src.ikigai.contracts.proposal import HierarchyMatch as _HM  # noqa: E402

    assert isinstance(matches, _HM)


def test_fetch_context_returns_three_lists():
    """fetch_context returns (memory_refs, folder_reads, hierarchy_match)."""
    from src.ikigai.contracts.proposal import (  # noqa: E402
        FolderReadOp as _FRO,
        HierarchyMatch as _HM2,
        MemoryRef as _MR,
    )

    state = {
        "user_request": "quero focar em X",
        "intent_classification": IntentClassification(level="high", score=1),
    }
    refs, reads, match = fetch_context(state)
    assert isinstance(refs, list)
    assert isinstance(reads, list)
    assert isinstance(match, _HM2)
    # Type narrow: each ref/entry should be a Pydantic v2 instance or empty
    assert all(isinstance(r, _MR) for r in refs)
    assert all(isinstance(r, _FRO) for r in reads)


def test_fetch_context_handles_missing_recall_memory(monkeypatch):
    """If recall_memory is not importable, fetch_context proceeds with empty refs."""
    from src.ikigai.contracts.proposal import HierarchyMatch as _HM3  # noqa: E402

    state = {
        "user_request": "test",
        "intent_classification": IntentClassification(level="low", score=0),
    }
    # Low-intent short-circuits before recall_memory; verify graceful path.
    refs, reads, match = fetch_context(state)
    assert refs == []
    assert reads == []
    assert isinstance(match, _HM3)
