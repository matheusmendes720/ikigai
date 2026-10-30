"""Paperclip Dynamic graph nodes.

Each node is a plain ``def(state: DynamicWorkflowState) -> dict[str, Any]``
function. ``graph.py`` wraps them in ``_safe_node`` so exceptions
populate the error channel instead of crashing the graph.

Implemented per ``deep-dive-dynamic-workflows.md`` §3 + §6:

* ``classify`` (entry) — naive slash-command router
* ``planner`` (LLM-A) — emit sub-agent task list
* ``harness_builder`` (LLM-B) — emit ``workflow_spec.md`` + parse
* ``subagent`` (LLM-C) — dynamic node factory, one per task
* ``per_subagent_verifier`` (LLM-D) — cheap retry gate
* ``global_evaluator`` (LLM-E) — cross-check findings
* ``synthesizer`` (LLM-F) — aggregate to final ``report.md``

For MVP all LLM calls are MOCKS — the real LLM wiring is a follow-up.
"""
