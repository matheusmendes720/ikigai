"""
enrichment_engine.py — Metadata Enrichment Engine v2
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def compute_upstream_id(entity_type: str, entity_id: str, title: str = "") -> str:
    """Gera SHA-256 de 12 chars para idempotência cross-system."""
    seed = f"{entity_type}:{entity_id}:{title}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:12]


TAG_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(bug|fix|erro|crash)\b", "bug"),
    (r"\b(refactor|cleanup|limpeza)\b", "refactor"),
    (r"\b(doc|readme|spec|prd)\b", "docs"),
    (r"\b(test|teste|tdd|pytest)\b", "test"),
    (r"\b(feat|feature|funcionalidade)\b", "feat"),
    (r"\b(infra|deploy|ci|cd|docker)\b", "infra"),
    (r"\b(study|estudo|aprender|learn)\b", "study"),
]


def infer_tags(text: str) -> List[str]:
    """Infere tags do conteúdo via heurísticas regex."""
    found: List[str] = []
    text_lower = text.lower()
    for pattern, tag in TAG_PATTERNS:
        if re.search(pattern, text_lower):
            found.append(tag)
    return list(dict.fromkeys(found))


def current_temporal_label(now: Optional[datetime] = None) -> Dict[str, str]:
    """Labels temporais (quarter, week) baseadas na data atual."""
    now = now or datetime.utcnow()
    quarter = f"Q{(now.month - 1) // 3 + 1}-{now.year}"
    iso_cal = now.isocalendar()
    return {
        "quarter": quarter,
        "week_label": f"W{iso_cal[1]:02d}-{iso_cal[0]}",
        "iso_week": f"{iso_cal[0]}-W{iso_cal[1]:02d}",
        "day_of_week": now.strftime("%A"),
    }


class EnrichmentEngine:
    """
    Pipeline de enriquecimento: upstream_id → temporal → auto_tags.
    Agora inclui métodos para chunking semântico de notas de estudo (Layer 2).
    """

    def __init__(self, inject_temporal: bool = True, infer_auto_tags: bool = True) -> None:
        self.inject_temporal = inject_temporal
        self.infer_auto_tags = infer_auto_tags

    def chunk_content(self, text: str, chunk_size: int = 1500, overlap: int = 100) -> List[str]:
        """Quebra conteúdo em chunks para indexação vetorial com overlap."""
        tokens = text.split()
        chunks, start = [], 0
        while start < len(tokens):
            end = start + chunk_size
            chunks.append(" ".join(tokens[start:end]))
            start = end - overlap
        return chunks

    def enrich_study_note(self, entity: BaseModel, content: str) -> Dict[str, Any]:
        """Enriquece especificamente notas de estudo com linhagem e chunks."""
        base_meta = self.enrich("study_note", entity)
        base_meta["semantic_lineage"] = {
            "source_type": "obsidian",
            "abstraction_level": getattr(entity, "abstraction_level", "practical"),
            "word_count": len(content.split())
        }
        return base_meta

    def enrich(self, entity_type: str, entity: BaseModel) -> Dict[str, Any]:
        meta: Dict[str, Any] = {}
        entity_id = str(getattr(entity, "id", ""))
        title = getattr(entity, "title", getattr(entity, "description", ""))

        meta["upstream_id"] = compute_upstream_id(entity_type, entity_id, title)
        if self.inject_temporal:
            meta["temporal"] = current_temporal_label()
        if self.infer_auto_tags and title:
            auto_tags = infer_tags(title)
            if auto_tags:
                meta["auto_tags"] = auto_tags
        
        meta["entity_type"] = entity_type
        meta["enriched_at"] = datetime.utcnow().isoformat()
        return meta
