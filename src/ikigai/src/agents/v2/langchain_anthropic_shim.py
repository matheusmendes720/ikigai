"""M158e — Monkey-patch anthropic.OverloadedError for langchain_anthropic compat.

langchain_anthropic.chat_models:984 defines:

    class AnthropicOverloadedError(anthropic.OverloadedError, ModelAPIError):
        ...

This class definition fails at module-import time if anthropic<0.40
(no OverloadedError attribute). We work around by monkey-patching
the missing attribute before any langchain_anthropic import.

Import this module BEFORE any langchain_anthropic usage:

    import langchain_anthropic_shim  # noqa: F401
    from langchain_anthropic import ChatAnthropic
"""
from __future__ import annotations

import anthropic  # noqa: F401


def _ensure_overloaded_error() -> None:
    """Add a stub OverloadedError to anthropic if missing."""
    if not hasattr(anthropic, "OverloadedError"):
        class OverloadedError(anthropic.APIError):  # type: ignore[misc, valid-type]
            """Stub OverloadedError for anthropic<0.40 compatibility.

            Real anthropic>=0.40 has this. We provide a no-op subclass
            so langchain_anthropic can define its AnthropicOverloadedError
            without crashing the import chain.
            """

            def __init__(self, message: str = "API overloaded") -> None:
                super().__init__(message=message)

        anthropic.OverloadedError = OverloadedError  # type: ignore[attr-defined]


_ensure_overloaded_error()


def _extract_text(content) -> str:
    """M158e: Extract plain text from langchain-anthropic 1.x response.

    langchain-anthropic 1.x returns content as a LIST of blocks like:
        [{"type": "thinking", "thinking": "..."},
         {"type": "text", "text": "actual response"}]

    Older versions returned a plain string. This helper normalizes both.
    """
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if "text" in block:
                    parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


def _strip_markdown_fences(text: str) -> str:
    """Strip ```json or ``` fences from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


def install_response_normalizer() -> None:
    """Patch ChatAnthropic.invoke so response.content is always a string.

    This wraps the invoke method to:
    1. Call the original invoke
    2. Extract text from list-of-blocks if needed
    3. Strip markdown fences

    So callers can do: json.loads(response.content) without worrying
    about the content type.
    """
    from langchain_anthropic import ChatAnthropic  # noqa

    _original_invoke = ChatAnthropic.invoke

    def _patched_invoke(self, *args, **kwargs):
        response = _original_invoke(self, *args, **kwargs)
        try:
            text = _extract_text(response.content)
            response.content = _strip_markdown_fences(text)
        except Exception:  # noqa: BLE001
            pass
        return response

    ChatAnthropic.invoke = _patched_invoke