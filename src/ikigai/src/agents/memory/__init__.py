"""Cross-session memory module for the IKIGAI agent layer.

Exposes the SessionSummarizer primitive that records session-end
summaries under ``vault/ikigai/runtime/sessions/`` and lets future sessions
recover them via the M159 vault embeddings cache.
"""

from __future__ import annotations

from .cross_session import (
    SESSIONS_RELATIVE_PATH,
    SessionSummarizer,
    SessionSummary,
    summarize_and_store,
)

__all__ = [
    "SESSIONS_RELATIVE_PATH",
    "SessionSummarizer",
    "SessionSummary",
    "summarize_and_store",
]
