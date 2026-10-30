"""Paperclip graph nodes.

Each node is a plain ``def(state: PaperclipStateDict) -> dict[str, Any]``
function. ``graph.py`` wraps them in ``_safe_node`` so exceptions populate
the error channel instead of crashing the graph.
"""
