"""``classify`` node — naive slash-command router.

Maps a raw ``user_query`` to one of three ``command`` buckets:
``"research"``, ``"audit"``, or ``"fix"``. Anything that doesn't match
a known keyword falls through to ``"research"`` (the default branch).

Per ``deep-dive-dynamic-workflows.md`` §6, Ronald's classify node is
"the mass branch is naive keyword" — he admits this is partial and
"true routing would use an LLM-based classifier". We keep the same
discipline: keyword match, no LLM call.

Keyword prefixes (case-insensitive):

* ``/research``, ``/pesquisar`` → ``"research"``
* ``/audit``, ``/auditar`` → ``"audit"``
* ``/fix``, ``/corrigir`` → ``"fix"``
* (anything else) → ``"research"``
"""

from __future__ import annotations

from src.ikigai.src.agents.paperclip_dynamic.state import DynamicWorkflowState

# Keyword → command mapping. Order matters: first match wins.
# Keywords are matched as case-insensitive prefixes against the raw query.
_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("/research", "research"),
    ("/pesquisar", "research"),
    ("/audit", "audit"),
    ("/auditar", "audit"),
    ("/fix", "fix"),
    ("/corrigir", "fix"),
)

DEFAULT_COMMAND = "research"


def _classify_command(user_query: str) -> str:
    """Return one of ``research`` / ``audit`` / ``fix``.

    Keyword scan against ``user_query`` (case-insensitive). Falls
    through to ``DEFAULT_COMMAND`` if no keyword prefix is present.
    """
    q = (user_query or "").lower().lstrip()
    for prefix, command in _KEYWORDS:
        if q.startswith(prefix):
            return command
    return DEFAULT_COMMAND


def classify_node(state: DynamicWorkflowState) -> dict[str, object]:
    """Route the user query into one of three buckets.

    Reads ``state["user_query"]`` (with empty-string safety via
    ``.get(...)``), writes ``state["command"]`` and a trace entry.

    Returns a partial state dict (LangGraph convention). Routing after
    this node is unconditional — every command path goes to the planner.

    Never raises: missing / empty ``user_query`` is treated as an empty
    string (handled downstream by the planner with a default workload).
    """
    user_query = (state.get("user_query") or "").strip()
    command = state.get("command") or _classify_command(user_query)

    return {
        "command": command,
        "trace": [
            {
                "node": "classify",
                "command": command,
                "query_len": len(user_query),
            }
        ],
        "last_step": "classify",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"paperclip_dynamic: classify command={command!r} query_len={len(user_query)}"
                ),
            }
        ],
    }
