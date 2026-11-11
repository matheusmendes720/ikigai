"""The published surfaces: where the panel is, and how it is reached.

The deployment carries the route in the repository — `deploy/surfaces.json`,
mounted read-only at `/etc/ikigai/surfaces.json` (ADR-045) — and this module
is the only thing that reads it. The environment is the FALLBACK, not the
truth: an address that lives in the box's `.env` is a second truth, and a
second truth is one that gets edited by hand and never reviewed.

Everything here FAILS CLOSED. A table that is missing, malformed, or that
declares a surface whose data door is not the Telegram signature produces no
address at all: the bot then behaves exactly as it did before the panel
existed — the chat keeps working, and the panel button is simply not sent.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

#: Where the table is mounted. The default is the mount's path, and the
#: variable can still point somewhere else — what changes is the default, not
#: the capability (ADR-042 D2).
SURFACES_FILE_ENV = "IKIGAI_SURFACES_FILE"
DEFAULT_SURFACES_FILE = "/etc/ikigai/surfaces.json"

#: The Mini App's key in the table.
MINIAPP = "miniapp"

#: The only credential model a surface may declare. The panel's identity is
#: Telegram's signature: a surface whose data endpoints are open is not a
#: surface of ours (ADR-044).
AUTH_TELEGRAM_INITDATA = "telegram-initdata"
ALLOWED_AUTH = frozenset({AUTH_TELEGRAM_INITDATA})

#: `pending` is declared but not published; `published` is published to the
#: internet. The word is the owner's decision, not a derived fact.
STATE_PENDING = "pending"
STATE_PUBLISHED = "published"
ALLOWED_STATES = frozenset({STATE_PENDING, STATE_PUBLISHED})

#: The publication modes. `tailnet` is reachable inside the tailnet only;
#: `funnel` is a surface that MAY be published — and only when the state says
#: so.
MODE_TAILNET = "tailnet"
MODE_FUNNEL = "funnel"
ALLOWED_MODES = frozenset({MODE_TAILNET, MODE_FUNNEL})


def surfaces_path() -> Path:
    """The table's path: the environment's, or the mount's default."""
    raw = (os.environ.get(SURFACES_FILE_ENV) or "").strip()
    return Path(raw or DEFAULT_SURFACES_FILE)


def load_surfaces(path: Path | str | None = None) -> dict[str, Any]:
    """The table's surfaces, or an empty mapping.

    A table that cannot be read is a table that does not exist: the surfaces
    are then the ones from before, which is none of them.
    """
    target = Path(path) if path is not None else surfaces_path()
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(document, dict):
        return {}
    surfaces = document.get("surfaces")
    if not isinstance(surfaces, dict):
        return {}
    return {str(name): value for name, value in surfaces.items() if isinstance(value, dict)}


def surface(name: str, path: Path | str | None = None) -> dict[str, Any] | None:
    """One surface, or None — and None means "no address".

    A surface is refused — and therefore has no address — when it declares a
    credential model we do not implement, a state we do not know, a mode we
    do not know, or a host we cannot read. Refusing is the honest answer: a
    published surface with an open data door is worse than no surface.
    """
    candidate = load_surfaces(path).get(name)
    if candidate is None:
        return None
    if str(candidate.get("auth") or "") not in ALLOWED_AUTH:
        return None
    if str(candidate.get("state") or "") not in ALLOWED_STATES:
        return None
    if str(candidate.get("mode") or "") not in ALLOWED_MODES:
        return None
    if not str(candidate.get("host") or "").strip():
        return None
    try:
        port = int(candidate.get("https_port") or 0)
    except (TypeError, ValueError):
        return None
    if not 1 <= port <= 65535:
        return None
    return candidate


def surface_url(name: str, path: Path | str | None = None) -> str:
    """The address a client reaches the surface at.

    The same address in both states: the funnel does not change the URL, it
    removes the tailnet-only restriction. A surface that is declared but not
    published is still reachable — inside the tailnet, which is where the
    owner is.
    """
    declared = surface(name, path)
    if declared is None:
        return ""
    host = str(declared["host"]).strip()
    port = int(declared["https_port"])
    route = str(declared.get("path") or "/")
    if not route.startswith("/"):
        route = "/" + route
    authority = host if port == 443 else f"{host}:{port}"
    return f"https://{authority}{route}"


def miniapp_url(path: Path | str | None = None) -> str:
    """The address the panel's button points at."""
    return surface_url(MINIAPP, path)
