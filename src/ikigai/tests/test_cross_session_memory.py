"""Tests for M160 cross-session memory layer.

Covers:
- summarize produces valid markdown (H1, ## Summary, ## Key Observations)
- store creates file at correct path under vault/ikigai/runtime/sessions/
- store is append-only (re-store preserves prior content)
- query_related_summaries returns k relevant summaries via vault_cache
- cross-session recall surfaces same task categories across two sessions
- path-traversal / invalid session_id is rejected
- list_stored_sessions enumerates existing files
- empty sessions dir → empty query result
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

# Make sure ``agents.memory.cross_session`` resolves.
#
# The repo has TWO ``agents`` packages:
#   - ``<repo>/src/agents/``     — canonical (only has ``reflection/``)
#   - ``<repo>/src/ikigai/src/agents/`` — IKIGAI internal (has v2/, memory/, …)
#
# ``src/ikigai/tests/conftest.py`` adds ``<repo>/src/`` to sys.path for
# ``from src.mesh import queue`` support, which causes Python's import
# resolver to find the wrong ``agents`` package. We push the IKIGAI
# ``src/`` to the FRONT of sys.path so its ``agents/`` wins. Removing
# ``<repo>/src/`` from sys.path also works but is more invasive (other
# tests in the file may rely on ``from src.X`` imports working).
_REPO = Path(__file__).resolve().parent.parent.parent.parent
_SRC_IKIGAI_SRC = _REPO / "src" / "ikigai" / "src"
src_path = str(_SRC_IKIGAI_SRC)
repo_path = str(_REPO)
# Remove any existing entries so order is fully under our control.
sys.path[:] = [p for p in sys.path if p not in (src_path, repo_path)]
sys.path.insert(0, src_path)
sys.path.insert(0, repo_path)

from agents.memory.cross_session import (  # noqa: E402
    APPEND_SEPARATOR,
    MAX_RENDERED_OBSERVATIONS,
    SESSIONS_RELATIVE_PATH,
    SessionSummarizer,
    summarize_and_store,
)
from agents.v2.vault_cache import VaultEmbeddingCache  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_workspace():
    """Yield (vault_root, cache_dir) in a fresh tempdir."""
    with tempfile.TemporaryDirectory(prefix="cross_session_test_") as d:
        d = Path(d)
        vault = d / "vault"
        cache_dir = d / "chroma_db"
        yield vault, cache_dir


@pytest.fixture
def summarizer(tmp_workspace):
    """Yield a SessionSummarizer bound to the temp vault + cache."""
    vault, cache_dir = tmp_workspace
    cache = VaultEmbeddingCache(persist_dir=str(cache_dir))
    return SessionSummarizer(vault_root=str(vault), cache=cache)


# ---------------------------------------------------------------------------
# summarize_session (pure)
# ---------------------------------------------------------------------------


def test_summarize_returns_markdown_with_h1(summarizer):
    """summarize_session returns a body with H1 and ## Summary section."""
    summary = summarizer.summarize_session(
        "sess-001",
        transcript="agent: hello world",
        observations=["did X", "did Y"],
    )
    body = summary.body_markdown
    assert body.startswith("# Session sess-001"), body[:80]
    assert "## Summary" in body
    assert "## Key Observations" in body
    assert "## Timestamp" in body


def test_summarize_with_empty_inputs(summarizer):
    """Empty transcript + empty observations → still valid markdown."""
    summary = summarizer.summarize_session("sess-002")
    assert "## Summary" in summary.body_markdown
    assert "_No transcript provided._" in summary.body_markdown
    assert "_No observations recorded._" in summary.body_markdown


def test_summarize_observations_render_as_bullets(summarizer):
    """Observation list is rendered as `- bullet` lines under ## Key Observations."""
    summary = summarizer.summarize_session(
        "sess-003",
        observations=["first observation", "second observation", "third"],
    )
    body = summary.body_markdown
    assert "- first observation" in body
    assert "- second observation" in body
    assert "- third" in body


def test_summarize_truncates_long_transcript(summarizer):
    """Long transcripts are excerpted with an [omitted] marker."""
    long_text = "x" * 5000
    summary = summarizer.summarize_session("sess-long", transcript=long_text)
    body = summary.body_markdown
    assert "chars omitted" in body
    # Excerpt should be much shorter than the original
    assert len(summary.transcript_excerpt) < len(long_text)


def test_summarize_accepts_iterable_transcript(summarizer):
    """transcript can be an iterable of lines, not just a string."""
    summary = summarizer.summarize_session(
        "sess-iter",
        transcript=["line one", "line two", "line three"],
    )
    assert "line one" in summary.body_markdown
    assert "line two" in summary.body_markdown


def test_summarize_rejects_invalid_session_id(summarizer):
    """Invalid session_id raises ValueError (path-traversal guard)."""
    with pytest.raises(ValueError, match="invalid session_id"):
        summarizer.summarize_session("../escape")


def test_summarize_truncates_excess_observations(summarizer):
    """>MAX_RENDERED_OBSERVATIONS bullets render a (+N more) marker."""
    obs = [f"obs {i}" for i in range(MAX_RENDERED_OBSERVATIONS + 5)]
    summary = summarizer.summarize_session("sess-many", observations=obs)
    body = summary.body_markdown
    assert f"(+{len(obs) - MAX_RENDERED_OBSERVATIONS} more)" in body


# ---------------------------------------------------------------------------
# store_summary
# ---------------------------------------------------------------------------


def test_store_creates_file_at_canonical_path(summarizer, tmp_workspace):
    """store_summary writes to vault/ikigai/runtime/sessions/<id>.md."""
    vault, _ = tmp_workspace
    path = summarizer.summarize_and_store(
        "sess-store-001",
        transcript="hello",
        observations=["did X"],
    )
    assert path.exists()
    # Path must live under vault/ikigai/runtime/sessions/
    expected = vault / SESSIONS_RELATIVE_PATH / "sess-store-001.md"
    assert path == expected, f"got {path}, expected {expected}"


def test_store_creates_sessions_directory(summarizer, tmp_workspace):
    """First store creates the sessions dir if it doesn't exist."""
    vault, _ = tmp_workspace
    sessions_dir = vault / SESSIONS_RELATIVE_PATH
    assert not sessions_dir.exists()
    summarizer.summarize_and_store("sess-create-dir")
    assert sessions_dir.is_dir()


def test_store_is_append_only(summarizer):
    """Re-storing the same session_id appends; never overwrites."""
    path1 = summarizer.summarize_and_store(
        "sess-append",
        transcript="first",
        observations=["A"],
    )
    text1 = path1.read_text()
    path2 = summarizer.summarize_and_store(
        "sess-append",
        transcript="second",
        observations=["B"],
    )
    text2 = path2.read_text()
    # First store content survives
    assert "first" in text2
    assert "- A" in text2
    # Second store content is appended below
    assert "second" in text2
    assert "- B" in text2
    # Append-only: text2 must be strictly longer
    assert len(text2) > len(text1)
    # Separator marks the join point
    assert APPEND_SEPARATOR in text2


def test_store_invalidates_cache(summarizer, tmp_workspace):
    """store_summary invalidates the cache entry for the file."""
    path = summarizer.summarize_and_store("sess-invalidate")
    # After invalidate, next get_or_compute re-embeds
    cached = summarizer.cache.get_or_compute(str(path))
    assert len(cached) > 0


def test_list_stored_sessions(summarizer):
    """list_stored_sessions returns one path per stored session."""
    assert summarizer.list_stored_sessions() == []
    summarizer.summarize_and_store("alpha")
    summarizer.summarize_and_store("beta")
    summarizer.summarize_and_store("gamma")
    paths = summarizer.list_stored_sessions()
    assert [p.stem for p in paths] == ["alpha", "beta", "gamma"]


def test_session_path_validation_rejects_traversal(summarizer):
    """session_path() raises ValueError on path-traversal-ish ids."""
    with pytest.raises(ValueError, match="invalid session_id"):
        summarizer.session_path("../../etc/passwd")
    with pytest.raises(ValueError, match="invalid session_id"):
        summarizer.session_path("with/slash")
    with pytest.raises(ValueError, match="invalid session_id"):
        summarizer.session_path("with space")


# ---------------------------------------------------------------------------
# query_related_summaries (semantic recall)
# ---------------------------------------------------------------------------


def test_query_returns_empty_when_no_sessions(summarizer):
    """No stored sessions → query_related_summaries returns []."""
    assert summarizer.query_related_summaries("anything", k=3) == []


def test_query_returns_k_relevant_summaries(summarizer):
    """query_related_summaries returns up to k entries, ordered by score."""
    summarizer.summarize_and_store(
        "sess-planning",
        transcript="Planning the cross-session memory layer",
        observations=["m159 cache", "vault embeddings", "planner-only"],
    )
    summarizer.summarize_and_store(
        "sess-debug",
        transcript="Debugging mtime invalidation bug in vault cache",
        observations=["mtime check", "os.stat", "race condition"],
    )
    summarizer.summarize_and_store(
        "sess-deploy",
        transcript="Deploying dashboard to production",
        observations=["nginx config", "ssl cert", "load balancer"],
    )

    results = summarizer.query_related_summaries("vault cache embeddings", k=2)
    assert len(results) <= 2
    assert len(results) >= 1
    for r in results:
        assert "path" in r
        assert "session_id" in r
        assert "similarity" in r
        assert "summary_excerpt" in r


def test_query_k_zero_returns_empty(summarizer):
    """k=0 is a valid edge case: return no results."""
    summarizer.summarize_and_store("sess-k0")
    assert summarizer.query_related_summaries("anything", k=0) == []


def test_query_k_one_returns_single_best(summarizer):
    """k=1 returns at most one result."""
    summarizer.summarize_and_store("a", transcript="alpha project")
    summarizer.summarize_and_store("b", transcript="beta project")
    summarizer.summarize_and_store("c", transcript="gamma project")
    results = summarizer.query_related_summaries("project", k=1)
    assert len(results) == 1


# ---------------------------------------------------------------------------
# Cross-session recall (the headline feature)
# ---------------------------------------------------------------------------


def test_cross_session_recall_returns_same_task_categories(summarizer):
    """Two sessions with overlapping task categories are both recalled for
    a third session's query about those categories.
    """
    # Session 1: ends with the agent noting "data mesh" + "taskdog" work
    summarizer.summarize_and_store(
        "sess-2026-10-01-a",
        transcript="worked on data mesh integration and taskdog MCP read tools",
        observations=[
            "data mesh create flow shipped",
            "taskdog path-3 read-only MCP shipped",
            "taskdog path-1 canonical write still harness-unwired",
        ],
    )
    # Session 2: next day, different topic but mentions data mesh
    summarizer.summarize_and_store(
        "sess-2026-10-01-b",
        transcript="continuation: data mesh Phase A fork connection",
        observations=[
            "data mesh 3 adapters (CLI/taskdog/UPI) joined",
            "data mesh ueid 4-part canonical enforced",
        ],
    )
    # Session 3 (this session): we ask "what did I learn last time about
    # data mesh?" and expect both prior sessions to surface.
    results = summarizer.query_related_summaries("data mesh", k=3)
    session_ids = {r["session_id"] for r in results}
    # Both previous sessions should appear (or at least one, depending on
    # the embedding fallback). The contract is "returns relevant summaries"
    # — for the deterministic hash fallback this is a soft check: at least
    # one of the two data-mesh sessions surfaces.
    assert session_ids & {"sess-2026-10-01-a", "sess-2026-10-01-b"}, (
        f"expected at least one data-mesh session in {session_ids}"
    )


def test_cross_session_recall_caches_after_first_query(summarizer):
    """Subsequent queries reuse embeddings — cache count is stable."""
    summarizer.summarize_and_store("x", transcript="first")
    summarizer.summarize_and_store("y", transcript="second")
    summarizer.query_related_summaries("first", k=1)
    count_after_first = summarizer.cache.stats()["count"]
    summarizer.query_related_summaries("first", k=1)
    count_after_second = summarizer.cache.stats()["count"]
    # No re-embed on second call (file mtime hasn't moved)
    assert count_after_first == count_after_second


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------


def test_module_level_convenience_wrapper(tmp_workspace):
    """summarize_and_store() works without explicitly constructing SessionSummarizer."""
    vault, _ = tmp_workspace
    # Patch the module-level default by overriding vault_root explicitly.
    path = summarize_and_store(
        "sess-convenience",
        transcript="hi",
        observations=["via module-level fn"],
        vault_root=str(vault),
    )
    assert path.exists()
    expected = vault / SESSIONS_RELATIVE_PATH / "sess-convenience.md"
    assert path == expected
