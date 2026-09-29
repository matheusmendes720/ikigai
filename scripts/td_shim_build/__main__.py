#!/usr/bin/env python3
"""td shim — minimal Python launcher for the life-oss taskdog CLI.

Hardcoded repo path (this machine only).

Build with:
    python -m zipapp . -o td.exe -p "C:\\Python314\\python.exe"

Path strategy:
- sys.path naturally includes stdlib + Python 3.14 site-packages (which has
  pydantic, opentelemetry, langchain, etc). Keep those.
- Prepend REPO_ROOT paths so our src/mesh/taskdog_cli.py wins over any
  conflicting same-name module in site-packages.
- Filter out ONLY paths that contain 'installs' (Hermes venv injection)
  to avoid mixing incompatible OTEL versions across venvs.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(r'C:\Users\mathe\code_space\life-oss\life')
if not (REPO_ROOT / 'src' / 'mesh' / 'taskdog_cli.py').exists():
    sys.stderr.write('error: life-oss repo not found at ' + str(REPO_ROOT) + '\n')
    sys.exit(2)

# Drop any path that points into another app's installs/venv (Hermes)
def _is_safe(p: str) -> bool:
    if not p:
        return False
    p_norm = p.replace('\\', '/').lower()
    # Hermes injects venvs under Local/hermes/installs/<id>/environments/...
    if '/hermes/installs/' in p_norm:
        return False
    # Drop our own paths from sys.path (we'll re-add at the front)
    p_path = Path(p)
    try:
        if p_path.is_relative_to(REPO_ROOT):
            return False
    except (AttributeError, ValueError):  # python<3.9 compat
        pass
    return True

# Build a clean sys.path: only stdlib + Python's own site-packages,
# then prepend REPO_ROOT paths so our src/ wins.
clean = [p for p in sys.path if _is_safe(p)]
prepend = [
    str(REPO_ROOT / 'src'),
    str(REPO_ROOT),
    str(REPO_ROOT / 'src' / 'ikigai' / 'src'),
]
sys.path = prepend + clean

# Map any available token env-var to ANTHROPIC_API_KEY so langchain-anthropic
# picks it up. The MiniMax provider reuses ANTHROPIC_API_KEY (the chat session
# uses ANTHROPIC_AUTH_TOKEN via Claude Code, but langchain_anthropic only
# reads ANTHROPIC_API_KEY).
import os as _os
if "ANTHROPIC_API_KEY" not in _os.environ:
    for _alt in ("ANTHROPIC_AUTH_TOKEN", "MINIMAX_API_KEY"):
        if _alt in _os.environ:
            _os.environ["ANTHROPIC_API_KEY"] = _os.environ[_alt]
            break
if "ANTHROPIC_BASE_URL" not in _os.environ:
    _os.environ["ANTHROPIC_BASE_URL"] = "https://api.minimax.io/anthropic"
# Default IKIGAI_MODEL for v2 graph nodes
_os.environ.setdefault("IKIGAI_MODEL", "MiniMax-M2.7-highspeed")

from src.mesh.taskdog_cli import main

sys.exit(main(sys.argv[1:]))
