"""Paperclip — RiskGate unit tests (M176-paperclip-risk-gate).

Five focused tests covering the risk auto-throttle gate's contract:

* ``test_risk_gate_allows_clean_text`` — ``"hello world"`` → ``allowed=True``.
* ``test_risk_gate_blocks_dangerous_keyword`` — ``"please rm -rf /tmp/foo"``
  → blocked, reason contains the matched keyword.
* ``test_risk_gate_blocks_case_insensitive`` — ``"DROP DATABASE mydb"`` →
  blocked (case-insensitive substring match).
* ``test_risk_gate_blocks_multiple_matches`` — text containing both
  ``rm -rf`` and ``git push --force`` → blocked, reason lists both.
* ``test_risk_gate_keywords_from_env`` —
  ``monkeypatch.setenv("PAPERCLIP_RISK_KEYWORDS", "rm -rf,drop database")`` →
  only those 2 keywords are active (overrides defaults).

The risk gate is **fail-CLOSED** (unlike :class:`CostGate` /
:class:`WallClockGate` which are fail-open). The tests confirm that any
non-empty text containing a default keyword is refused.

Companion to ``policy.py`` and the wire-up in ``nodes/implement.py``.
"""

from __future__ import annotations

import pytest
from src.ikigai.src.agents.paperclip.policy import (
    DEFAULT_RISK_KEYWORDS,
    ENV_RISK_KEYWORDS,
    RiskGate,
)


def test_risk_gate_allows_clean_text() -> None:
    """A benign spec + prompt combination is allowed.

    Sanity check that the gate does not over-trigger. Clean text with
    no dangerous-keyword substrings should pass through.
    """
    gate = RiskGate(text_to_check="hello world, please implement a new function")
    allowed, reason = gate.check()

    assert allowed is True, f"expected allowance on clean text, got reason: {reason}"
    assert "no dangerous keyword match" in reason.lower() or "allowing" in reason.lower()


def test_risk_gate_blocks_dangerous_keyword() -> None:
    """``rm -rf /tmp/foo`` triggers the gate; reason echoes the match.

    The reason string MUST include the matched keyword (``rm -rf``) so
    downstream log scrapers / TUI can surface the operator what to
    rewrite. Per design: fail-CLOSED — any match refuses the call.
    """
    gate = RiskGate(text_to_check="please rm -rf /tmp/foo before continuing")
    allowed, reason = gate.check()

    assert allowed is False, f"expected block on dangerous keyword, got reason: {reason}"
    assert "rm -rf" in reason, f"reason should contain matched keyword 'rm -rf', got: {reason}"
    assert "dangerous keyword" in reason.lower(), (
        f"reason should mention 'dangerous keyword', got: {reason}"
    )


def test_risk_gate_blocks_case_insensitive() -> None:
    """``DROP DATABASE mydb`` is matched case-insensitively.

    The gate lowercases the haystack; default keywords are tested as
    lowercased substrings. This catches an upper-case spec that
    otherwise would slip through.
    """
    gate = RiskGate(text_to_check="DROP DATABASE mydb;")
    allowed, reason = gate.check()

    assert allowed is False, f"expected block on case-insensitive match, got reason: {reason}"
    assert "drop database" in reason.lower(), (
        f"reason should mention matched keyword (lowercased), got: {reason}"
    )


def test_risk_gate_blocks_multiple_matches() -> None:
    """Multiple dangerous keywords in the same text are all listed in the reason.

    The reason MUST list ALL matched keywords — not just the first — so
    the operator can see the full picture when triaging. Per the design
    note in the spec: "Reason string MUST list ALL matched keywords".
    """
    text = "first run: rm -rf /tmp/x; then: git push --force origin master"
    gate = RiskGate(text_to_check=text)
    allowed, reason = gate.check()

    assert allowed is False, f"expected block on multiple matches, got reason: {reason}"
    assert "rm -rf" in reason, f"reason should list 'rm -rf' match, got: {reason}"
    assert "git push --force" in reason, (
        f"reason should list 'git push --force' match, got: {reason}"
    )


def test_risk_gate_keywords_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """``PAPERCLIP_RISK_KEYWORDS`` env var overrides the default keyword list.

    Setting it to ``"rm -rf,drop database"`` should narrow the active
    keywords to just those two. The fixture text contains ``api_key=``
    (in the default list, but NOT in the env override) — under the env
    override, the gate is OPEN; with the default keywords, it would
    be CLOSED. This proves the env var was actually consulted and the
    default list is fully replaced (not extended).
    """
    monkeypatch.setenv(ENV_RISK_KEYWORDS, "rm -rf,drop database")

    # Sanity: gate picks up the env override (only 2 active keywords).
    gate = RiskGate(text_to_check="placeholder")
    assert gate.keywords == ("rm -rf", "drop database"), (
        f"expected 2 keywords from env, got {gate.keywords!r}"
    )
    # Default list has way more than 2 entries; this proves the override
    # replaced (not extended) the default.
    assert len(DEFAULT_RISK_KEYWORDS) > 2

    # A text with `api_key=` (default keyword) but NOT in env override:
    # the gate is OPEN because the env override removed it from the
    # active set.
    allowed_api, _ = RiskGate(text_to_check="set the api_key= here").check()
    assert allowed_api is True, (
        "expected allowance on api_key= when env override removed it from active keywords"
    )

    # Sanity: the env-overridden keywords DO trigger.
    allowed_rm, reason_rm = RiskGate(text_to_check="rm -rf /tmp/x").check()
    assert allowed_rm is False, f"expected block on env-override 'rm -rf', got: {reason_rm}"
    assert "rm -rf" in reason_rm
