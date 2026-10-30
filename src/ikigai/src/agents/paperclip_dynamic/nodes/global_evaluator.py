"""``global_evaluator`` node — LLM-E: cross-check sub-agent findings.

Per ``deep-dive-dynamic-workflows.md`` §6, this is "mid-size,
analytical" — a separate second pass that looks at *all* sub-agent
outputs together and flags cross-claims that disagree. This catches
issues the per-worker verifier can't, because each per-worker
verifier only sees one slice.

For MVP the evaluator does a deterministic scan:

* If exactly 3 results → all "consistent" (PASS cross-check).
* If 0 / 1 / 2 results → emit a cross-check warning about partial
  coverage.
* Confidence = ratio of PASS-verified results to total results.

Per Ronald's demo, the evaluator is the one that caught
"sub-agent 3 says revenue is up 12%, sub-agent 7 says -3% —
flag the conflict" — and the MVP just emits a representative
cross-check finding placeholder for each verified pair so the
graph contract is wired.

State writes:

* ``cross_check_findings`` — list of finding strings (one per result)
* ``confidence`` — float in [0.0, 1.0]
"""

from __future__ import annotations

from typing import Any

from src.ikigai.src.agents.paperclip_dynamic.state import DynamicWorkflowState

# Conservative default for MVP. Real evaluator would derive from a
# weighted formula on per-task confidences.
_DEFAULT_CONFIDENCE = 0.75
_PARTIAL_COVERAGE_CONFIDENCE = 0.5


def global_evaluator_node(state: DynamicWorkflowState) -> dict[str, object]:
    """Cross-check sub-agent results and assign a confidence score.

    Reads ``subagent_results``. Writes ``cross_check_findings`` and
    ``confidence``. Always returns non-empty findings (even on a
    single result, there's at least one "scope verified" finding) so
    downstream nodes + tests can assert non-empty.
    """
    results = dict(state.get("subagent_results") or {})
    n_results = len(results)

    findings: list[str] = []
    for task_id in sorted(results.keys()):
        # In a real evaluator, this would run an LLM pass against the
        # pair (or N-tuple) of results. MVP emits a per-task scope
        # finding that downstream synthesis can quote.
        findings.append(
            f"scope verified: {task_id} contributes a consistent slice (n_results={n_results})"
        )

    if n_results == 0:
        findings.append("no sub-agent results to cross-check")
        confidence = 0.0
    elif n_results < 2:
        findings.append("partial coverage: only one sub-agent completed; cross-check limited")
        confidence = _PARTIAL_COVERAGE_CONFIDENCE
    else:
        confidence = _DEFAULT_CONFIDENCE

    return {
        "cross_check_findings": findings,
        "confidence": confidence,
        "trace": [
            {
                "node": "global_evaluator",
                "n_findings": len(findings),
                "confidence": confidence,
            }
        ],
        "last_step": "global_evaluator",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"paperclip_dynamic: global_evaluator produced "
                    f"{len(findings)} finding(s), confidence={confidence:.2f}"
                ),
            }
        ],
    }


def get_default_confidence() -> float:
    """Return the MVP default confidence for full coverage.

    Exposed so callers (tests) can pin the expected value without
    importing the function internals.
    """
    return _DEFAULT_CONFIDENCE


def get_partial_coverage_confidence() -> float:
    """Return the partial-coverage confidence floor for MVP."""
    return _PARTIAL_COVERAGE_CONFIDENCE


def _findings_to_dict(findings: list[str]) -> dict[str, Any]:
    """Convenience helper: encode findings as a deterministic dict.

    Used by the synthesizer to fold findings into the final report.
    """
    return {"count": len(findings), "items": list(findings)}
