"""fetch_context node — gather memory + folder + hierarchy context (Plan D Task B.2).

Reuses shipped infrastructure:
- recall_memory (ADR-028, B-N12) — graceful fallback if unavailable
- external_folder_read (Plan B, src/ikigai/security/external_folder_read.py)
- scan_hierarchy (local helper, walks vault frontmatter)

All three fetches are read-only. No writes here.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from src.ikigai.contracts.proposal import (
    FolderReadOp,
    HierarchyMatch,
    IntentClassification,
    MemoryRef,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 4-part UEID canonical regex (ADR-014)
# ---------------------------------------------------------------------------
# Reused for scan_hierarchy validation when bucketing matched vault entries.
# Plan A naming convention: sonho:/objetivo:/meta:/projeto:/ prefix names.
_PLAN_A_UEID_PREFIXES: tuple[str, ...] = (
    "sonho:",
    "objetivo:",
    "meta:",
    "projeto:",
)


def recall_memory(query: str, top_k: int = 5) -> list[MemoryRef]:
    """Wrapper around B-N12 memory recall (ADR-028).

    Defensive: returns ``[]`` on ``ImportError`` so the meta-planner can
    still proceed when the memory layer is missing or unshipped. Production
    callers should expect this fallback to fire only in test environments.
    """
    try:
        from src.ikigai.agents.v2.memory_read import query_memory  # type: ignore[import-not-found]

        results = query_memory(query=query, top_k=top_k)
        return [
            MemoryRef(
                id=r.get("id", "mem:unknown:00:0000"),
                vault_path=r.get("vault_path"),
                relevance_score=float(r.get("score", 0.0)),
            )
            for r in results
        ]
    except (ImportError, AttributeError, KeyError) as exc:
        log.warning("recall_memory fallback (no memory layer): %s", exc)
        return []


def external_folder_read(path: str, reason: str) -> FolderReadOp:
    """Wrapper around Plan B external_folder_read.

    Defensive: returns a stub ``FolderReadOp`` with an "[access denied or
    file missing]" excerpt on ``ImportError`` / ``PermissionError`` /
    ``FileNotFoundError``. The orchestrator filters out fallback entries
    before passing them downstream (see ``fetch_context``).
    """
    try:
        from src.ikigai.security.external_folder_read import (  # type: ignore[import-not-found]
            external_folder_read as _read,
        )

        content = _read(path=path, reason=reason)
        excerpt = content[:500] if content else ""
        return FolderReadOp(path=path, excerpt=excerpt, reason=reason)
    except (ImportError, PermissionError, FileNotFoundError) as exc:
        log.warning("external_folder_read fallback for %s: %s", path, exc)
        return FolderReadOp(
            path=path,
            excerpt="[access denied or file missing]",
            reason=f"FALLBACK: {reason}",
        )


def scan_hierarchy(
    user_request: str,
    memory_refs: list[MemoryRef] | None = None,
) -> HierarchyMatch:
    """Walk vault frontmatter for SONHO/OBJETIVO/META/PROJETO matches.

    Lightweight keyword-only implementation: scans ``vault/`` for ``*.md``
    files with a top-level ``ueid:`` line and requires >=2 shared words
    with the (lowercased) user request before counting a match. Matched
    files are bucketed by their 4-part UEID prefix (Plan A naming).

    Production-grade hierarchy matching (graph traversal, semantic
    similarity, time-window filtering) is out of scope for Plan D v1.

    Args:
        user_request: Free-text user request used as the keyword probe.
        memory_refs: Currently unused; reserved for future use where
            memory recall hints bias the walk.

    Returns:
        ``HierarchyMatch`` populated with the first matched UEID per
        bucket (sonho/objetivo/meta/projeto). Empty when no matches.
    """
    text = user_request.lower().strip()
    matches = HierarchyMatch()

    # Best-effort vault walk; fail-safe to all-None if vault not found.
    # We probe relative to CWD so tests can chdir into a fixture root.
    vault_root = Path("vault")
    if not vault_root.exists():
        return matches

    request_tokens = set(text.split())

    for md_file in vault_root.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        # Crude frontmatter parse: look for top-level `ueid: <value>`.
        ueid_match = re.search(r"^ueid:\s*(\S+)", content, re.MULTILINE)
        if not ueid_match:
            continue
        ueid = ueid_match.group(1)

        # Reject non-canonical (5+ part) UEIDs to keep buckets clean.
        if ueid.count(":") != 3:
            continue

        # Require >=2 shared tokens between user_request and file content.
        content_tokens = set(content.lower().split())
        if len(request_tokens & content_tokens) < 2:
            continue

        # Bucket by 4-part UEID prefix (Plan A naming convention).
        if ueid.startswith(_PLAN_A_UEID_PREFIXES):
            if ueid.startswith("sonho:") and matches.sonho is None:
                matches.sonho = ueid
            elif ueid.startswith("objetivo:") and matches.objetivo is None:
                matches.objetivo = ueid
            elif ueid.startswith("meta:") and matches.meta is None:
                matches.meta = ueid
            elif ueid.startswith("projeto:") and matches.projeto is None:
                matches.projeto = ueid

    return matches


def fetch_context(
    state: dict[str, Any],
) -> tuple[list[MemoryRef], list[FolderReadOp], HierarchyMatch]:
    """Fetch memory + folder + hierarchy context for user_request.

    State keys consumed:
      - ``user_request``: ``str`` — natural-language planning request.
      - ``intent_classification``: ``IntentClassification`` — output of
        the upstream ``classify_intent`` node.

    Behaviour:
      - Short-circuits to ``([], [], HierarchyMatch())`` when intent is
        ``low`` (avoids noise; matches B.3 fast-path contract).
      - Memory recall uses ``recall_memory`` with ``top_k=5``; failures
        fall back to ``[]``.
      - Folder reads iterate memory refs that carry a ``vault_path``;
        denied reads are filtered out so downstream consumers see only
        successful reads.
      - Hierarchy scan is local + read-only; runs after memory + folder
        fetches so the final state contains all three slices.

    Returns:
        3-tuple ``(memory_refs, folder_reads, hierarchy_match)`` ready
        to be merged into the meta-plan subgraph state for ``generate_proposal``.
    """
    user_request: str = state.get("user_request", "")
    intent: IntentClassification | None = state.get("intent_classification")

    # Skip fetches for low intent (avoid noise — matches generate_proposal contract).
    if intent is not None and intent.level == "low":
        return [], [], HierarchyMatch()

    # 1. Memory recall — defensive fallback handled inside recall_memory.
    memory_refs = recall_memory(user_request, top_k=5)

    # 2. Folder reads — for each memory ref with a vault_path, attempt read.
    #    Denied / missing reads return a stub excerpt; filter those out so
    #    downstream consumers see only successful reads.
    folder_reads: list[FolderReadOp] = []
    for ref in memory_refs:
        if not ref.vault_path:
            continue
        op = external_folder_read(ref.vault_path, reason=f"context for: {user_request[:50]}")
        if "[access denied" not in op.excerpt:
            folder_reads.append(op)

    # 3. Hierarchy scan — local keyword walk over vault/ frontmatter.
    hierarchy_match = scan_hierarchy(user_request, memory_refs)

    return memory_refs, folder_reads, hierarchy_match
