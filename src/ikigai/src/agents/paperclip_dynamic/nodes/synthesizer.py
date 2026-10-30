"""``synthesizer`` node — LLM-F: aggregate to final report.

Per ``deep-dive-dynamic-workflows.md`` §6, the synthesizer is the
"best prose model he has" (Qwen 3.7 Max in the demo). It aggregates
all sub-agent results + cross-check findings into one user-facing
markdown report.

In production this is the largest / most-expensive model because
the report is the user-facing artifact and its prose quality
determines perceived value.

For MVP the synthesizer is a deterministic markdown builder that:

1. Pulls every entry from ``subagent_results``.
2. Pulls every entry from ``cross_check_findings``.
3. Pulls the ``confidence`` score.
4. Renders a markdown report with a header, per-task body section,
   cross-check findings list, and a confidence footer.

Determinism matters here so tests can assert exact substrings without
brittleness from incidental LLM prose.

State writes:

* ``final_report_md`` — the markdown report
* ``trace`` — appended (one entry: synthesiser ran)
"""

from __future__ import annotations

from typing import Any

from src.ikigai.src.agents.paperclip_dynamic.state import DynamicWorkflowState

# Report header convention — pinned so tests can match against it.
REPORT_HEADER = "# ikigai_dynamic_report"
REPORT_FOOTER_PREFIX = "## Confidence"


def _render_report(
    user_query: str,
    command: str,
    subagent_results: dict[str, Any],
    cross_check_findings: list[str],
    confidence: float,
) -> str:
    """Render the final markdown report.

    Deterministic: same inputs → same output. No LLM call.
    """
    lines: list[str] = []
    lines.append(REPORT_HEADER)
    lines.append("")
    lines.append("## Query")
    lines.append((user_query or "").strip() or "(no query)")
    lines.append("")
    lines.append(f"## Command: {command}")
    lines.append("")
    lines.append("## Sub-agent findings")
    if not subagent_results:
        lines.append("- (no sub-agent results)")
    else:
        for task_id in sorted(subagent_results.keys()):
            result = subagent_results[task_id]
            lines.append("")
            lines.append(f"### {task_id} ({result.get('role', 'unknown')})")
            lines.append("")
            lines.append(result.get("markdown") or "(empty)")

    lines.append("")
    lines.append("## Cross-check findings")
    if not cross_check_findings:
        lines.append("- (none)")
    else:
        for finding in cross_check_findings:
            lines.append(f"- {finding}")

    lines.append("")
    lines.append(f"{REPORT_FOOTER_PREFIX}: {confidence:.2f}")
    lines.append("")
    return "\n".join(lines)


def synthesizer_node(state: DynamicWorkflowState) -> dict[str, object]:
    """Aggregate sub-agent results + findings into the final report.

    Reads ``user_query``, ``command``, ``subagent_results``,
    ``cross_check_findings``, ``confidence``. Writes
    ``final_report_md`` (the markdown report) and a trace entry.

    The body section is deterministic — no LLM call. The report is
    suitable for direct user delivery.
    """
    user_query = (state.get("user_query") or "").strip()
    command = state.get("command") or "research"
    results = dict(state.get("subagent_results") or {})
    findings = list(state.get("cross_check_findings") or [])
    confidence = float(state.get("confidence") or 0.0)

    report_md = _render_report(
        user_query=user_query,
        command=command,
        subagent_results=results,
        cross_check_findings=findings,
        confidence=confidence,
    )

    return {
        "final_report_md": report_md,
        "trace": [
            {
                "node": "synthesizer",
                "report_chars": len(report_md),
                "n_results_used": len(results),
                "n_findings_used": len(findings),
            }
        ],
        "last_step": "synthesizer",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"paperclip_dynamic: synthesizer produced "
                    f"{len(report_md)} chars from {len(results)} result(s) "
                    f"and {len(findings)} finding(s)"
                ),
            }
        ],
    }
