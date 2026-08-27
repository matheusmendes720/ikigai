#!/usr/bin/env python3
"""Reproducer — trigger the same FileNotFoundError dcode hit on entities/ops/.

In the real session the agent invented a path
``src/ikigai/entities/ops/__init__.py`` against an empty scaffold directory
visible to ``ls`` but not to ``glob``. We simulate the equivalent
``open(..., "r")`` call and assert the OTel ``observed_tool`` decorator
records the exception class on the active span.

Run from the ikigai project root::

    python scripts/repro_ops_dir_error.py

Expected::

    Reproduced: [Errno 2] No such file or directory: ...

Then run ``scripts/verify_traces.py`` within 5 minutes to confirm both
backends received the span.
"""
import sys
from pathlib import Path

# Allow `from observability import ...` from src/observability/ without install.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from observability import init_tracing, observed_tool, shutdown_tracing  # noqa: E402

init_tracing()

# Path the agent tried to read in the real session — the entities/ops/
# scaffold is empty in this repo, so the file genuinely does not exist.
MISSING = ROOT / "src" / "ikigai" / "entities" / "ops" / "__init__.py"


@observed_tool("ikigai.read_file")
def read_file(path: str) -> str:
    """Simulates a tool call that opens the given path."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    try:
        read_file(str(MISSING))
    except FileNotFoundError as e:
        print(f"Reproduced: {e}")
    finally:
        shutdown_tracing()