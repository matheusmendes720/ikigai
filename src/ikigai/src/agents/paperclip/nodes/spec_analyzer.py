"""``spec_analyzer`` node — extract gaps from the spec via Claude.

Subprocess to the Claude adapter inside the REPO ROOT (not the worktree —
there's no worktree at this stage). The prompt is a structured request for
gaps; we parse ``AgentResult.output`` as JSON if it looks like JSON, else
fall back to a single-string gap list.

The analyzer is the only HIL trigger source in MVP (see plan §"HIL
triggers"). Iteration is capped via ``MAX_GAP_LOOPS`` to prevent the
graph looping forever on irreconcilably ambiguous specs.

On stub-adapter errors (``NotImplementedError``) the graph reports
``error_type=AnalyzerUnavailable`` and routes to END.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from src.ikigai.src.agents.paperclip.agents.base import AgentResult
from src.ikigai.src.agents.paperclip.state import PaperclipStateDict

log = logging.getLogger(__name__)

# Cap on analyzer iterations (gap → HIL → merge → analyzer loop). After cap,
# we surface ``error_message="spec_ambiguous: please rewrite"`` so the
# user knows to fix the spec text instead of answering forever.
MAX_GAP_LOOPS = 5

# Loose JSON detector — a string that starts with ``[`` or ``{`` and ends
# with the matching bracket is treated as JSON for parsing. Anything else
# becomes a single-string gap list.
_JSON_HEAD = re.compile(r"^\s*[\[\{]")


def _extract_gaps(output: str) -> list[str]:
    """Parse the agent output into a list of gap strings.

    Tries, in order:
    1. Whole-output JSON parse.
    2. Last JSON block in the output (some CLIs prefix with prose).
    3. Newline-split (each non-empty line = one gap).

    Returns an empty list when nothing useful is found (clean spec).
    """
    text = output.strip()
    if not text:
        return []
    # 1. Whole JSON
    if _JSON_HEAD.match(text):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
            if isinstance(parsed, dict) and "gaps" in parsed:
                gaps = parsed["gaps"]
                if isinstance(gaps, list):
                    return [str(x).strip() for x in gaps if str(x).strip()]
        except json.JSONDecodeError:
            pass
    # 2. Last JSON block
    last_bracket_start = max(text.rfind("["), text.rfind("{"))
    if last_bracket_start >= 0:
        candidate = text[last_bracket_start:]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            pass
    # 3. Newline-split fallback — only treat as gaps if every line looks
    # gap-like (starts with - or number+dot, OR is plain text <200 chars).
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if lines and all(len(ln) < 200 for ln in lines):
        return [ln.lstrip("- ").lstrip("0123456789. ") for ln in lines]
    return []


def spec_analyzer_node(
    state: PaperclipStateDict,
    *,
    claude_adapter: Any = None,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Run the Claude adapter in repo-root to extract spec gaps.

    Args:
        state: PaperclipStateDict. Reads ``spec_text`` + ``implement_iteration``.
        claude_adapter: optional adapter override (used by tests to mock
            Claude). Defaults to ``ClaudeAdapter()``.
        repo_root: optional repo root override (tests use a tmp dir).

    Returns:
        Partial state with ``spec_gaps`` populated (possibly empty).
        On Claude failure: error channel populated, downstream routes to END.
    """
    if claude_adapter is None:
        from src.ikigai.src.agents.paperclip.agents.claude import ClaudeAdapter

        claude_adapter = ClaudeAdapter()

    if repo_root is None:
        # Resolve repo root via the canonical pattern from drift tests
        # (walk up until we find ``.git``)
        here = Path(__file__).resolve()
        for parent in here.parents:
            if (parent / ".git").is_dir():
                repo_root = parent
                break
        if repo_root is None:
            repo_root = Path.cwd()

    iteration = int(state.get("gap_iteration") or 0) + 1
    if iteration > MAX_GAP_LOOPS:
        return {
            "originating_node": "spec_analyzer",
            "error_type": "SpecAmbiguousError",
            "error_message": (
                f"spec_ambiguous: more than {MAX_GAP_LOOPS} gap rounds — please rewrite the spec"
            ),
            "gap_iteration": iteration,
            "last_step": "spec_analyzer",
        }

    spec_text = state.get("spec_text") or ""
    prompt = (
        "Analyze the following spec for gaps, ambiguities, or missing "
        "decisions. Reply ONLY with a JSON array of gap strings (or [] if "
        "the spec is complete and unambiguous). No prose, no preamble.\n\n"
        "SPEC:\n"
        f"{spec_text}\n\n"
        "JSON:"
    )

    try:
        result: AgentResult = claude_adapter.run(prompt, repo_root)
    except NotImplementedError as exc:
        return {
            "originating_node": "spec_analyzer",
            "error_type": "AnalyzerUnavailable",
            "error_message": str(exc),
            "gap_iteration": iteration,
            "last_step": "spec_analyzer",
        }

    if not result.success:
        # Adapter itself failed (CLI missing, timeout, etc.). Don't crash —
        # report failure and let downstream route to END.
        return {
            "originating_node": "spec_analyzer",
            "error_type": "AnalyzerFailed",
            "error_message": result.error or "claude analyzer returned failure",
            "gap_iteration": iteration,
            "last_step": "spec_analyzer",
        }

    gaps = _extract_gaps(result.output)
    log.debug("paperclip spec_analyzer: %d gap(s) found (iter=%d)", len(gaps), iteration)
    return {
        "spec_gaps": gaps,
        "gap_iteration": iteration,
        "last_step": "spec_analyzer",
    }
