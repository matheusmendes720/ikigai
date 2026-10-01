"""Cross-session memory — session-end summary persistence + recall (M160).

Goal: when a new Claude session starts, the agent's recall_node can answer
"What did I learn last time about X?" by searching past session summaries.

Flow:
    1. SessionEnd hook → ``summarize_and_store(session_id, transcript, observations)``
       returns markdown summary.
    2. Summary written to ``vault/ikigai/runtime/sessions/<session_id>.md``.
       Existing files are appended to (append-only per CLAUDE.md invariant).
    3. New summary automatically enters the M159 ``VaultEmbeddingCache`` on
       next ``get_or_compute`` call — the cache is mtime-driven, so just
       touching the file is enough.
    4. Next session's ``query_related_summaries(query, k=3)`` does a cosine
       similarity search over the cache and returns the top-k paths.

Why not LLM-summarize? Two reasons:
    (a) Cost / latency. SessionEnd must be fast (<2s) and free.
    (b) Determinism. Tests must reproduce the same summary from the same
        transcript without network access.
The summary is a structural extraction of the transcript (first/last
utterance, observation bullets, token counts). When a real LLM is wired
into SessionEnd, replace ``summarize_session`` body but keep the same
return contract.

Append-only invariant (CLAUDE.md §"Refactor Protocol"): the sessions
directory MUST NOT delete entries. Re-writing a session_id appends a new
section with a timestamp marker. A monotonic header counter protects
against accidental rewrite.

Drift invariants enforced in tests/test_cross_session_memory.py:
    - ``summarize_session`` returns valid markdown (has H1, has ## Summary)
    - ``store_summary`` writes to vault/ikigai/runtime/sessions/<id>.md
    - ``query_related_summaries`` returns <=k items, ordered by score desc
    - Re-store of the same session_id appends; never overwrites
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Logger
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Canonical relative path under <vault_root/> for stored session summaries.
#: Suffix matches CLAUDE.md: "vault/ikigai/runtime/sessions/<session_id>.md".
SESSIONS_RELATIVE_PATH: str = "ikigai/runtime/sessions"

#: Frontmatter delimiter used to separate session entries on re-store.
APPEND_SEPARATOR: str = "\n\n---\n\n"

#: Maximum number of observation bullets rendered in the markdown summary.
#: Beyond this, observations are truncated with a "(+N more)" marker.
MAX_RENDERED_OBSERVATIONS: int = 20

#: Rough char budget for transcript excerpts in the summary.
TRANSCRIPT_EXCERPT_CHARS: int = 800

#: Regex for safe session_id chars (no path traversal).
#: Allows alnum + dash + underscore + dot. Length 1-128.
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


# ---------------------------------------------------------------------------
# Resolve defaults — anchored to repo layout
# ---------------------------------------------------------------------------


def _resolve_repo_root() -> Path:
    """Locate the repo root (parent of ``vault/``).

    Walks up from this file's location until it sees a sibling ``vault/``
    directory. Falls back to cwd. This module lives at
    ``<repo>/src/ikigai/src/agents/memory/cross_session.py`` so the
    resolved root is 5 parents up.
    """
    here = Path(__file__).resolve()
    for ancestor in [here, *here.parents]:
        if (ancestor / "vault").is_dir():
            return ancestor
    return Path.cwd()


def _default_vault_root() -> Path:
    """Return ``<repo>/vault`` — the canonical vault location."""
    return _resolve_repo_root() / "vault"


def _default_sessions_dir(vault_root: Path) -> Path:
    return vault_root / SESSIONS_RELATIVE_PATH


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionSummary:
    """Structured form of a session-end summary.

    The dataclass is the canonical in-memory representation. The markdown
    form is the persistence format (write to disk + indexable by the M159
    vault cache).
    """

    session_id: str
    body_markdown: str
    observations: tuple[str, ...] = ()
    transcript_excerpt: str = ""
    created_at: float = field(default_factory=time.time)
    summary_path: Path | None = None


# ---------------------------------------------------------------------------
# SessionSummarizer
# ---------------------------------------------------------------------------


class SessionSummarizer:
    """Produce, persist, and recall session-end summaries.

    Two collaborators:
      * the sessions directory on disk (``vault/ikigai/runtime/sessions/``)
      * the M159 ``VaultEmbeddingCache`` (for semantic recall)

    Both are injectable so tests can use a temp dir + a fresh cache.
    """

    def __init__(
        self,
        vault_root: str | Path | None = None,
        cache: Any | None = None,
    ) -> None:
        self._vault_root = Path(vault_root) if vault_root else _default_vault_root()
        self._sessions_dir = _default_sessions_dir(self._vault_root)
        # Lazy import to keep this module importable without v2 deps in CI.
        if cache is None:
            from agents.v2.vault_cache import default_cache

            cache = default_cache()
        self._cache = cache

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def vault_root(self) -> Path:
        return self._vault_root

    @property
    def sessions_dir(self) -> Path:
        return self._sessions_dir

    @property
    def cache(self) -> Any:
        return self._cache

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def session_path(self, session_id: str) -> Path:
        """Resolve the on-disk path for a session_id (no I/O).

        Raises ``ValueError`` if session_id contains path-traversal chars.
        """
        if not _SESSION_ID_RE.match(session_id):
            raise ValueError(
                f"invalid session_id {session_id!r}: must match {_SESSION_ID_RE.pattern}"
            )
        return self._sessions_dir / f"{session_id}.md"

    def list_stored_sessions(self) -> list[Path]:
        """Return all session summary paths currently on disk, sorted."""
        if not self._sessions_dir.exists():
            return []
        return sorted(self._sessions_dir.glob("*.md"))

    # ------------------------------------------------------------------
    # Summarize (no I/O)
    # ------------------------------------------------------------------

    def summarize_session(
        self,
        session_id: str,
        transcript: str | Iterable[str] | None = None,
        observations: Iterable[str] | None = None,
    ) -> SessionSummary:
        """Produce a ``SessionSummary`` for ``session_id``.

        ``transcript`` is the raw session log (free text or iterable of
        lines/utterances). ``observations`` is a list of short bullet
        strings the caller wants recorded (typically from the agent's
        last ``recall_node`` output, or from the orchestrator's
        per-tick observations).

        The function is pure: no disk writes, no cache reads. ``store_summary``
        does the write and the cache index happens lazily on the next
        ``get_or_compute`` call.
        """
        if not _SESSION_ID_RE.match(session_id):
            raise ValueError(
                f"invalid session_id {session_id!r}: must match {_SESSION_ID_RE.pattern}"
            )

        transcript_excerpt = self._extract_transcript_excerpt(transcript)
        obs_list = list(observations or [])

        body = self._render_markdown(
            session_id=session_id,
            transcript_excerpt=transcript_excerpt,
            observations=obs_list,
        )
        return SessionSummary(
            session_id=session_id,
            body_markdown=body,
            observations=tuple(obs_list),
            transcript_excerpt=transcript_excerpt,
        )

    # ------------------------------------------------------------------
    # Store (writes to disk)
    # ------------------------------------------------------------------

    def store_summary(
        self,
        session_id: str,
        summary: str | SessionSummary,
    ) -> Path:
        """Persist a summary to ``vault/ikigai/runtime/sessions/<id>.md``.

        Append-only: if the file already exists, the new content is
        appended below a separator. The existing content is never
        overwritten. This matches the CLAUDE.md append-only invariant
        on the vault.
        """
        path = self.session_path(session_id)
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

        body = summary if isinstance(summary, str) else summary.body_markdown

        if path.exists():
            existing = path.read_text(encoding="utf-8", errors="replace")
            # Increment counter so readers can tell the re-store count.
            new_body = (
                f"{existing.rstrip()}{APPEND_SEPARATOR}"
                f"<!-- re-store #{(existing.count('<!-- re-store') + 1)} "
                f"@ {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} -->\n\n"
                f"{body}"
            )
        else:
            new_body = body

        path.write_text(new_body, encoding="utf-8")
        # Invalidate cache so the next get_or_compute re-embeds.
        try:
            self._cache.invalidate(str(path))
        except Exception as exc:  # cache is best-effort, never block writes
            log.warning("cache invalidate failed for %s: %s", path, exc)
        return path

    def summarize_and_store(
        self,
        session_id: str,
        transcript: str | Iterable[str] | None = None,
        observations: Iterable[str] | None = None,
    ) -> Path:
        """Convenience: ``summarize_session`` + ``store_summary`` in one call."""
        summary = self.summarize_session(session_id, transcript, observations)
        return self.store_summary(session_id, summary)

    # ------------------------------------------------------------------
    # Recall (semantic search via M159 cache)
    # ------------------------------------------------------------------

    def query_related_summaries(
        self,
        query: str,
        k: int = 3,
    ) -> list[dict[str, Any]]:
        """Return top-k past session summaries most relevant to ``query``.

        Two-step process:
          1. Embed the query; score against every cached session summary.
          2. Return the top-k as ``{path, similarity, summary_excerpt}``.

        The M159 cache only knows about files that have been ``get_or_compute``-ed
        at least once. This method calls ``get_or_compute`` on every stored
        session first, so the index is up-to-date even if a previous session
        skipped the cache step.
        """
        if k <= 0:
            return []
        # Make sure the cache knows about every stored session.
        for path in self.list_stored_sessions():
            try:
                self._cache.get_or_compute(str(path))
            except Exception as exc:
                log.warning("cache get_or_compute failed for %s: %s", path, exc)

        scored = self._cache.similarity_to(query, top_k=k)
        results: list[dict[str, Any]] = []
        for path_str, sim in scored:
            p = Path(path_str)
            if not p.exists():
                continue
            excerpt = self._read_excerpt(p)
            results.append(
                {
                    "path": str(p),
                    "session_id": p.stem,
                    "similarity": sim,
                    "summary_excerpt": excerpt,
                }
            )
        return results

    # ------------------------------------------------------------------
    # Internal rendering
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_transcript_excerpt(transcript: str | Iterable[str] | None) -> str:
        if transcript is None:
            return ""
        if isinstance(transcript, str):
            text = transcript.strip()
        else:
            text = "\n".join(str(line) for line in transcript).strip()
        if len(text) <= TRANSCRIPT_EXCERPT_CHARS:
            return text
        # Keep first half + last half so callers see both intent + outcome.
        half = TRANSCRIPT_EXCERPT_CHARS // 2
        return f"{text[:half]}\n\n[...{len(text) - TRANSCRIPT_EXCERPT_CHARS} chars omitted...]\n\n{text[-half:]}"

    @staticmethod
    def _render_markdown(
        session_id: str,
        transcript_excerpt: str,
        observations: list[str],
    ) -> str:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        token_estimate = max(1, len(transcript_excerpt) // 4)
        lines: list[str] = []
        lines.append(f"# Session {session_id}")
        lines.append("")
        lines.append(
            f"<!-- generated {ts} • est_tokens={token_estimate} • summary_id={uuid.uuid4().hex[:8]} -->"
        )
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        if transcript_excerpt:
            lines.append("```text")
            lines.append(transcript_excerpt)
            lines.append("```")
        else:
            lines.append("_No transcript provided._")
        lines.append("")
        lines.append("## Key Observations")
        lines.append("")
        if observations:
            shown = observations[:MAX_RENDERED_OBSERVATIONS]
            for obs in shown:
                obs_clean = obs.strip().replace("\n", " ")
                if obs_clean:
                    lines.append(f"- {obs_clean}")
            if len(observations) > MAX_RENDERED_OBSERVATIONS:
                lines.append(f"- (+{len(observations) - MAX_RENDERED_OBSERVATIONS} more)")
        else:
            lines.append("_No observations recorded._")
        lines.append("")
        lines.append("## Timestamp")
        lines.append("")
        lines.append(f"- created_at: {ts}")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _read_excerpt(path: Path, max_chars: int = 500) -> str:
        try:
            text = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return ""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def summarize_and_store(
    session_id: str,
    transcript: str | Iterable[str] | None = None,
    observations: Iterable[str] | None = None,
    vault_root: str | Path | None = None,
) -> Path:
    """Convenience wrapper: build a default ``SessionSummarizer`` and run it."""
    summarizer = SessionSummarizer(vault_root=vault_root)
    return summarizer.summarize_and_store(
        session_id=session_id,
        transcript=transcript,
        observations=observations,
    )
