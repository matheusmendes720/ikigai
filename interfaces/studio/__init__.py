"""M168: Studio UI — local HTML dashboard served by FastAPI.

Backend FastAPI (uvicorn) for `td` operations + `deep agent` chat. The frontend
is a single-page vanilla-JS UI in `index.html`, styled by `styles.css`. All
state comes from the existing TaskdogAdapter (HTTP-first with SQLite fallback);
chat proxies through the LangGraph API (`/threads/<id>/runs`) when reachable.

Usage:
    python -m interfaces.studio.server
    # then open http://127.0.0.1:8765 in a browser
"""

__all__: list[str] = []