"""Drift test — observe.py must not re-introduce QHE constants.

R1.4 from ``vault/run-continuation/2026-09-21-master-review-revisited.json``.
Pins the W3.2 / M12 resolution: ``DEFAULT_QHE_PUSH = 0.85`` and
``DEFAULT_QHE_RECOVER = 0.60`` were stripped from ``state.py`` on
2026-09-04 and live ONLY in ``prompts/algorithm_constants.json`` (loaded
via ``prompts/load_constants.py``).

This guard prevents the constants from leaking back into the v2 agent
node layer through ``observe.py``. The tiebreaker verdict in the master
review JSON (``conflicts_resolved.conflicts[0]``) confirmed that
``observe.py`` is now an intent classifier
(``_classify_plan_intent`` + ``PLAN_INTENT_KEYWORDS``) — not a math
executor.

Invariants enforced:

1. No ``DEFAULT_``-prefixed module-level assignments in observe.py.
2. No raw QHE magic numbers (``0.85`` / ``0.60``) appear in observe.py.
3. observe.py does NOT import ``prompts.load_constants`` — it has no
   math/algorithm work to do, so a load_constants import is a smell.

If any of these is violated, the test FAILS. Drift net guard runs in CI.

Run::

    pytest src/ikigai/tests/test_observe_node_no_qhe_constants.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path resolution — mirror test_drift_extended_invariants.py
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
IKIGAI_TESTS = THIS_FILE.parent
IKIGAI_PKG = IKIGAI_TESTS.parent
IKIGAI_SRC = IKIGAI_PKG / "src"
OBSERVE_PY = IKIGAI_SRC / "agents" / "v2" / "nodes" / "observe.py"


@pytest.fixture(scope="module")
def observe_source() -> str:
    """Read observe.py once per module — it's small and stable."""
    return OBSERVE_PY.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Invariant 1 — no DEFAULT_ module-level assignments
# ---------------------------------------------------------------------------
# Matches `NAME = ...` at module scope (zero-indent). Allows the names
# in docstrings/comments (those have leading whitespace).
DEFAULT_ASSIGNMENT_RE = re.compile(
    r"^DEFAULT_[A-Z_][A-Z0-9_]*\s*=",
    re.MULTILINE,
)


def test_observe_node_has_no_default_module_assignments(observe_source: str) -> None:
    """observe.py must not declare any DEFAULT_* module-level variable.

    W3.2 (2026-09-04) stripped all DEFAULT_* algorithm constants from
    ``state.py``. observe.py is an intent classifier and must not
    re-introduce this anti-pattern.
    """
    matches = DEFAULT_ASSIGNMENT_RE.findall(observe_source)
    assert matches == [], (
        f"observe.py contains DEFAULT_* module-level assignment(s): {matches}. "
        "Algorithm tuning constants must live ONLY in "
        "src/ikigai/src/agents/v2/prompts/algorithm_constants.json "
        "(see load_constants.py). Re-introducing DEFAULT_* in observe.py "
        "violates W3.2 / ADR-019."
    )


# ---------------------------------------------------------------------------
# Invariant 2 — no raw QHE magic numbers (0.85 / 0.60)
# ---------------------------------------------------------------------------
# Strict word-boundary regex on the bare literals. Excludes comments
# (lines starting with #) by stripping them first.
QHE_PUSH_LITERAL = "0.85"
QHE_RECOVER_LITERAL = "0.60"


def _strip_python_comments(source: str) -> str:
    """Drop ``# ...`` line-comments so we only scan real code."""
    return "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))


def test_observe_node_has_no_qhe_push_literal(observe_source: str) -> None:
    """observe.py must not contain the raw ``0.85`` literal.

    ``0.85`` is the QHE_PUSH_THRESHOLD (formerly DEFAULT_QHE_PUSH). Its
    presence in observe.py signals that the intent classifier has
    accidentally been re-coupled to algorithm math.
    """
    code = _strip_python_comments(observe_source)
    assert QHE_PUSH_LITERAL not in code, (
        "observe.py contains the literal '0.85' — this is the "
        "QHE_PUSH_THRESHOLD value. Algorithm constants belong in "
        "prompts/algorithm_constants.json, not in node code."
    )


def test_observe_node_has_no_qhe_recover_literal(observe_source: str) -> None:
    """observe.py must not contain the raw ``0.60`` literal.

    ``0.60`` is the QHE_RECOVER_THRESHOLD (formerly DEFAULT_QHE_RECOVER).
    """
    code = _strip_python_comments(observe_source)
    assert QHE_RECOVER_LITERAL not in code, (
        "observe.py contains the literal '0.60' — this is the "
        "QHE_RECOVER_THRESHOLD value. Algorithm constants belong in "
        "prompts/algorithm_constants.json, not in node code."
    )


# ---------------------------------------------------------------------------
# Invariant 3 — observe.py must not import prompts.load_constants
# ---------------------------------------------------------------------------
# observe.py is an intent classifier. It has no need to consume algorithm
# tuning constants. If a future contributor wires observe.py to math,
# they should be forced to justify it via a code review (and probably
# add the import back intentionally with a drift-test update).
LOAD_CONSTANTS_IMPORT_PATTERNS = (
    "from ..prompts.load_constants",
    "from agents.v2.prompts.load_constants",
    "import load_constants",
    "from ...prompts.load_constants",
)


def test_observe_node_does_not_import_load_constants(observe_source: str) -> None:
    """observe.py must not import prompts.load_constants.

    observe.py's job is plan-intent classification, not algorithm
    math. A load_constants import here would mean someone re-coupled
    the intent classifier to PAE/QHE math — exactly what W3.2 stripped.
    """
    for pattern in LOAD_CONSTANTS_IMPORT_PATTERNS:
        assert pattern not in observe_source, (
            f"observe.py imports load_constants via '{pattern}'. "
            "observe.py is an intent classifier; it should not consume "
            "algorithm tuning constants. If you genuinely need them, "
            "update this drift test with rationale."
        )


# ---------------------------------------------------------------------------
# Invariant 4 — observe.py must not reference QHE identifiers
# ---------------------------------------------------------------------------
# Catches future `qhe_score`, `QHE_THRESHOLD`, `compute_qhe`, etc.
QHE_IDENTIFIER_RE = re.compile(r"\bQHE\b", re.IGNORECASE)


def test_observe_node_has_no_qhe_identifier(observe_source: str) -> None:
    """observe.py must not reference any ``QHE`` identifier.

    observe.py reads ``user_input`` and emits ``plan_intent_hint``. It
    has no business talking about Q_HE (Quality-of-Health-Energy).
    """
    matches = QHE_IDENTIFIER_RE.findall(observe_source)
    assert matches == [], (
        f"observe.py references QHE identifier(s): {matches}. "
        "Q_HE is an algorithm concept (PAE math) and must not appear in "
        "the intent-classifier node layer."
    )
