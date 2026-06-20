"""Enable ``python -m operational`` entry point.

Launches the interactive home menu by default.
Run ``python -m operational --help`` for all CLI commands.
"""
from __future__ import annotations

from operational.cli.app import app

if __name__ == "__main__":
    app()
