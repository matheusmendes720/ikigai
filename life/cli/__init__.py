"""
Algorithmic Life OS — integrated CLI multi-systems for produtividade.

Centrals: task, finance, knowledge, research.
Handlers: daily, weekly (orchestrate centrals).
Plugins, test runner, structured logging.
"""

__version__ = "0.1.0"

import sys
from pathlib import Path


def _bootstrap_repo_paths() -> None:
    """Ensure repo root and src/ are on sys.path for the console script.

    When invoked via `pip install -e .` (i.e. `life` on PATH), the `life`
    package is installed but `src/contracts`, `src/mesh`, `interfaces/cli`,
    etc. are not. This adds them so the top-level imports in cli.py
    (e.g. `from interfaces.cli.notify_cli import ...`) resolve.

    The repo root is found by:
      1. Walking up from this file (case: this file lives in <repo>/life/cli/).
      2. Walking up from CWD looking for a pyproject.toml (case: installed
         via pip with a non-relative layout, e.g. uv tool install).
    """
    # Already bootstrapped? (avoid duplicate work).
    marker = "_LIFE_REPO_BOOTSTRAPPED"
    if getattr(sys, marker, False):
        return
    setattr(sys, marker, True)

    candidate_roots: list[Path] = []

    # Case 1: editable install — file is at <repo>/life/cli/__init__.py.
    # Repo root = parents[2] = <repo>.
    try:
        here = Path(__file__).resolve()
        candidate_roots.append(here.parents[2])
    except IndexError:
        pass

    # Case 2: walking up from CWD looking for pyproject.toml.
    cwd = Path.cwd()
    for p in [cwd, *cwd.parents]:
        if (p / "pyproject.toml").exists() and (p / "life").is_dir():
            candidate_roots.append(p)
            break

    for root in candidate_roots:
        for sub in (root, root / "src", root / "interfaces"):
            sp = str(sub)
            if sp not in sys.path:
                sys.path.insert(0, sp)


def _main_console() -> None:
    """Console-script entry point declared in pyproject.toml.

    `pip install -e .` then `life --help` invokes this. We bootstrap
    repo paths first so `src/*` and `interfaces/*` resolve, then
    delegate to the Typer app defined in `cli.cli`. This gives one CLI
    surface regardless of whether you launch via `python -m life.cli`,
    `python cli/cli.py`, or `life` (after install).
    """
    _bootstrap_repo_paths()
    from life.cli.cli import app

    app()
