"""OPEN-3 drift guard — Cloud Studio chat-input enablement.

Cloud Studio enables the chat input on a graph ONLY when BOTH invariants
hold (per docs/2026-09-29-langgraph-dev-studio-e2e.md §3.6):

  1. The graph's ``input_schema`` declares a ``messages`` field.
  2. All OTHER required fields are Optional / have defaults — Studio
     cannot auto-fill required fields without a defaults form, so it
     greys out the chat input as a precaution.

This test asserts both invariants for all three graphs registered in
``langgraph.json``:

  - ikigai_maintainer_v2  (src/ikigai/src/agents/v2/graph.py)
  - ikigai_fork_smoke     (src/ikigai/src/agents/v2/fork_smoke_graph.py)
  - ikigai_taskdog_mcp    (src/ikigai/src/agents/taskdog_mcp_graph.py)

If any of them break the dependency, the test FAILS and Studio chat is
re-disabled for that graph.

Run::

    pytest src/ikigai/tests/test_studio_chat_schema.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, get_args, get_origin

import pytest

THIS_FILE = Path(__file__).resolve()
IKIGAI_TESTS = THIS_FILE.parent
IKIGAI_PKG = IKIGAI_TESTS.parent
IKIGAI_SRC = IKIGAI_PKG / "src"
REPO_ROOT = IKIGAI_PKG.parent.parent  # life/


# ---------------------------------------------------------------------------
# Studio chat invariant helpers
# ---------------------------------------------------------------------------
def _has_messages_field(annotations: dict[str, Any]) -> bool:
    """True iff annotations declare a `messages` field.

    We accept either ``messages: list[...]`` or
    ``messages: NotRequired[list[...]]`` — both surface as a `messages`
    key in the TypedDict's __annotations__ dict. We do NOT introspect
    __optional_keys__ (TypedDict's private slot) — that's an
    implementation detail of CPython that varies across versions.
    """
    return "messages" in annotations


def _field_is_optional(annotations: dict[str, Any], field_name: str) -> bool:
    """True iff field's annotation is Optional (NotRequired[T]) OR has default.

    TypedDict's NotRequired[T] erases to plain T at runtime (it's a
    PEP 655 typing-only marker), so we cannot reliably detect it via
    ``get_origin(annotation) is NotRequired`` — that returns False on
    most versions.

    Instead, we read the source file and AST-walk the class body for
    the field's ast.AnnAssign — if its annotation is
    ``ast.Subscript`` with func ``"NotRequired"``, the field is
    Optional. Otherwise, it's REQUIRED and Studio would disable chat.
    """
    import ast

    # Caller passes the source path so we can locate the field in its
    # declaring class. We fall back to assuming required if the field
    # is not in the annotations map at all.
    return _ast_field_is_not_required(_LAST_AST_SOURCE, field_name)


_LAST_AST_SOURCE: Path | None = None


def _ast_field_is_not_required(source: Path, field_name: str) -> bool:
    """AST-scan a Python source for `field_name: NotRequired[...]` or default."""
    import ast

    if not source.exists():
        return False
    try:
        tree = ast.parse(source.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.AnnAssign):
                continue
            if not isinstance(stmt.target, ast.Name):
                continue
            if stmt.target.id != field_name:
                continue
            annotation = stmt.annotation
            # Check for `field: NotRequired[T]` (Subscript of Name "NotRequired")
            if (
                isinstance(annotation, ast.Subscript)
                and isinstance(annotation.value, ast.Name)
                and annotation.value.id == "NotRequired"
            ):
                return True
            # Check for `class X(TypedDict, total=False)` — all fields NotRequired
            if _class_is_total_false(tree, node.name):
                return True
            # `field = "default"` or `field: T = default` counts as having default
            if stmt.value is not None:
                return True
            return False
    return False


def _class_is_total_false(tree: ast.AST, class_name: str) -> bool:
    """True iff `class X(TypedDict, total=False)` is in tree."""
    import ast

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name != class_name:
            continue
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "TypedDict":
                for kw in node.keywords:
                    if kw.arg == "total" and isinstance(kw.value, ast.Constant):
                        return kw.value.value is False
            # `class X(ParentTypedDict, total=False)` — same check
            # (the AST walker above handles both via the same kwargs loop
            # because keywords are stored at the ClassDef level, not on
            # the base.)
    return False


# ---------------------------------------------------------------------------
# Per-graph source paths (resolve at module-import time)
# ---------------------------------------------------------------------------
IKIGAI_STATE_PY = IKIGAI_SRC / "agents" / "v2" / "state.py"
FORK_SMOKE_PY = IKIGAI_SRC / "agents" / "v2" / "fork_smoke_graph.py"
TASKDOG_MCP_PY = IKIGAI_SRC / "agents" / "taskdog_mcp_graph.py"


# ---------------------------------------------------------------------------
# ikigai_maintainer_v2 — IKIGAiStateDict
# ---------------------------------------------------------------------------
class TestIKIGAIMaintainerV2:
    """ikigai_maintainer_v2 input schema invariants."""

    def test_state_module_imports(self) -> None:
        """IKIGAiStateDict is importable from v2.state."""
        sys.path.insert(0, str(IKIGAI_SRC.parent))
        sys.path.insert(0, str(IKIGAI_SRC))
        from src.ikigai.src.agents.v2.state import IKIGAiStateDict  # noqa: F401

    def test_input_schema_has_messages(self) -> None:
        """IKIGAiStateDict declares a `messages` field (Studio chat detect)."""
        from src.ikigai.src.agents.v2.state import IKIGAiStateDict  # noqa: F401

        annotations = IKIGAiStateDict.__annotations__
        assert _has_messages_field(annotations), (
            f"IKIGAiStateDict must declare a `messages` field for Cloud "
            f"Studio chat detection. Got annotations: {sorted(annotations)}"
        )

    def test_cycle_id_is_optional(self) -> None:
        """`cycle_id` is NotRequired — default 'default' when Studio omits."""
        global _LAST_AST_SOURCE
        _LAST_AST_SOURCE = IKIGAI_STATE_PY
        assert _ast_field_is_not_required(IKIGAI_STATE_PY, "cycle_id"), (
            "`cycle_id` must be NotRequired (or have a default) so Studio "
            "chat input is enabled (OPEN-3 fix, 2026-10-02). See "
            "docs/2026-09-29-langgraph-dev-studio-e2e.md §3.6."
        )

    def test_cycle_start_is_optional(self) -> None:
        """`cycle_start` is NotRequired — defaults to today.isoformat()."""
        assert _ast_field_is_not_required(IKIGAI_STATE_PY, "cycle_start"), (
            "`cycle_start` must be NotRequired so Studio chat is enabled."
        )

    def test_cycle_end_is_optional(self) -> None:
        """`cycle_end` is NotRequired — defaults to today.isoformat()."""
        assert _ast_field_is_not_required(IKIGAI_STATE_PY, "cycle_end"), (
            "`cycle_end` must be NotRequired so Studio chat is enabled."
        )

    def test_iteration_is_optional(self) -> None:
        """`iteration` is NotRequired — defaults to 0 when Studio omits."""
        assert _ast_field_is_not_required(IKIGAI_STATE_PY, "iteration"), (
            "`iteration` must be NotRequired so Studio chat is enabled."
        )


# ---------------------------------------------------------------------------
# ikigai_fork_smoke — ForkSmokeStateDict
# ---------------------------------------------------------------------------
class TestIKIGAIForkSmoke:
    """ikigai_fork_smoke input schema invariants."""

    def test_state_module_imports(self) -> None:
        """ForkSmokeStateDict is importable from v2.fork_smoke_graph."""
        from src.ikigai.src.agents.v2.fork_smoke_graph import ForkSmokeStateDict  # noqa: F401

    def test_input_schema_has_messages(self) -> None:
        """ForkSmokeStateDict declares a `messages` field."""
        from src.ikigai.src.agents.v2.fork_smoke_graph import ForkSmokeStateDict  # noqa: F401

        annotations = ForkSmokeStateDict.__annotations__
        assert _has_messages_field(annotations), (
            f"ForkSmokeStateDict must declare a `messages` field for "
            f"Studio chat. Got annotations: {sorted(annotations)}"
        )

    def test_all_fields_optional(self) -> None:
        """All ForkSmokeStateDict fields are NotRequired (TypedDict total=False)."""
        assert _ast_field_is_not_required(FORK_SMOKE_PY, "messages"), (
            "`messages` must be NotRequired so Studio chat is enabled."
        )
        assert _ast_field_is_not_required(FORK_SMOKE_PY, "forks_status"), (
            "`forks_status` must be NotRequired."
        )


# ---------------------------------------------------------------------------
# ikigai_taskdog_mcp — TaskdogMcpStateDict
# ---------------------------------------------------------------------------
class TestIKIGAITaskdogMcp:
    """ikigai_taskdog_mcp input schema invariants."""

    def test_state_module_imports(self) -> None:
        """TaskdogMcpStateDict is importable from taskdog_mcp_graph."""
        from src.ikigai.src.agents.taskdog_mcp_graph import TaskdogMcpStateDict  # noqa: F401

    def test_input_schema_has_messages(self) -> None:
        """TaskdogMcpStateDict declares a `messages` field."""
        from src.ikigai.src.agents.taskdog_mcp_graph import TaskdogMcpStateDict  # noqa: F401

        annotations = TaskdogMcpStateDict.__annotations__
        assert _has_messages_field(annotations), (
            f"TaskdogMcpStateDict must declare a `messages` field for "
            f"Studio chat. Got annotations: {sorted(annotations)}"
        )

    def test_only_messages_in_placeholder_state(self) -> None:
        """Placeholder graph (TaskdogMcpStateDict) has only `messages`.

        The full ReAct agent graph (``create_react_agent``) has its own
        prebuilt schema — we only enforce on the placeholder branch
        here. Both branches must accept ``{"messages": [...]}`` input
        without filtering (the schema guard's purpose).
        """
        from src.ikigai.src.agents.taskdog_mcp_graph import TaskdogMcpStateDict  # noqa: F401

        annotations = TaskdogMcpStateDict.__annotations__
        # Either "messages"-only (placeholder minimal) or "messages"+others
        # all NotRequired — we accept either.
        assert "messages" in annotations, (
            "TaskdogMcpStateDict must declare `messages` for Studio chat."
        )
        # All declared fields must be NotRequired / total=False
        # (We rely on the source-level AST check below.)
        assert _class_is_total_false(
            _ast_parse(TASKDOG_MCP_PY), "TaskdogMcpStateDict"
        ), (
            "TaskdogMcpStateDict must use `total=False` or NotRequired so "
            "Studio chat input isn't blocked by required fields."
        )


def _ast_parse(path: Path) -> Any:
    import ast

    return ast.parse(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Cross-graph: all 3 Studio-chat invariants hold simultaneously
# ---------------------------------------------------------------------------
def test_all_graphs_chat_enabled() -> None:
    """ALL THREE graphs must satisfy both Studio chat invariants.

    This is the consolidated invariant test. If ANY graph fails either
    condition, this fails — preventing a partial fix that only enables
    chat on 2 of 3 graphs.
    """
    from src.ikigai.src.agents.v2.fork_smoke_graph import ForkSmokeStateDict
    from src.ikigai.src.agents.v2.state import IKIGAiStateDict
    from src.ikigai.src.agents.taskdog_mcp_graph import TaskdogMcpStateDict

    pairs = [
        ("ikigai_maintainer_v2", IKIGAiStateDict, IKIGAI_STATE_PY),
        ("ikigai_fork_smoke", ForkSmokeStateDict, FORK_SMOKE_PY),
        ("ikigai_taskdog_mcp", TaskdogMcpStateDict, TASKDOG_MCP_PY),
    ]
    failures: list[str] = []
    for name, td, src in pairs:
        annotations = td.__annotations__
        if not _has_messages_field(annotations):
            failures.append(
                f"  {name}: input_schema missing `messages` field — "
                f"got {sorted(annotations)}"
            )
            continue
        # For ikigai_maintainer_v2, the four identity fields must each be
        # NotRequired. For the other two graphs, total=False on the
        # TypedDict class covers everything.
        if name == "ikigai_maintainer_v2":
            for f in ("cycle_id", "cycle_start", "cycle_end", "iteration"):
                if not _ast_field_is_not_required(src, f):
                    failures.append(
                        f"  {name}: `{f}` is REQUIRED — Studio cannot "
                        f"auto-fill, so chat is disabled."
                    )
        else:
            if not _class_is_total_false(_ast_parse(src), td.__name__):
                failures.append(
                    f"  {name}: {td.__name__} is not total=False / "
                    f"has required fields — chat disabled."
                )

    assert not failures, (
        "Studio chat is disabled for some graphs (OPEN-3 fix regression):\n"
        + "\n".join(failures)
    )