"""PASS 2 — the default search renderer emits no UEID.

The owner's default view names the title and the strategic level; the UEID is
the technical receipt, fetched with /detalhe. The pattern is the ONE canonical
source (src.contracts.common._UEID_PATTERN), never re-typed.

Falsification: re-add the uid line to _render_search and this fails.
"""

from __future__ import annotations

from src.bot.main import _render_search
from src.contracts.common import _UEID_PATTERN


def test_the_search_render_leaks_no_ueid() -> None:
    result = {
        "artifacts": [
            {
                "uid": "not:2026-11-24:a1b2c3d4:0123456789abcdef",
                "title": "Relatório Diário — 2026-11-24",
                "kind": "nota",
            },
            {
                "uid": "rev:2026-w47:957fb44a:65c78f0a53baec51",
                "title": "Revisão W47",
                "kind": "revisao",
            },
        ]
    }
    out = _render_search(result)
    assert "Relatório Diário" in out
    assert "Atividade" in out
    leaked = [token for token in out.split() if _UEID_PATTERN.match(token)]
    assert not leaked, f"the default search render leaked a UEID: {leaked}"
