"""Paperclip Dynamic — implements Anthropic's "Dynamic Workflows" pattern.

A second LangGraph graph alongside ``ikigai_paperclip`` (which is the
fixed-topology, single-purpose meta-orchestrator). The dynamic workflow
graph is a **meta-orchestrator**: classify → planner → harness builder
→ N sub-agents → per-sub-agent verifier → global evaluator → synthesizer.

Unlike Paperclip (which executes a single static pipeline), the dynamic
graph materialises its own sub-agents per run — the planner emits a task
list, the harness builder emits a ``workflow_spec.md``, and the runtime
fans out to N sub-agent nodes with isolated contexts.

Per ``deep-dive-dynamic-workflows.md`` §3 (graph) + §4 (state model).
"""

__version__ = "0.1.0"
