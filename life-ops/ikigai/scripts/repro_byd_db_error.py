#!/usr/bin/env python3
"""Reproducer — trigger the same UnicodeDecodeError that dcode hit on byd-tracker.db.

In the real dcode session, deepagents' FilesystemBackend.read() fell through to
a UTF-8 text read because the file has no recognised extension in
``deepagents/backends/utils.py:_EXTENSION_TO_FILE_TYPE``. We simulate the
equivalent code path locally and assert that the OTel ``observed_tool``
decorator records the exception class + hint + stack trace on the active
span, so both LangSmith and Langfuse dashboards show the failure.

Run from the ikigai project root::

    python scripts/repro_byd_db_error.py

Expected::

    Reproduced: 'utf-8' codec can't decode byte ...
    [error_capture] span=tool.ikigai.read_sqlite_as_text error.class=UnicodeDecodeError

Then run ``scripts/verify_traces.py`` within 5 minutes to confirm both
backends received the span.
"""
import os
import sys
from pathlib import Path

# Allow `from observability import ...` from src/observability/ without install.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from observability import init_tracing, observed_tool, shutdown_tracing  # noqa: E402

init_tracing()

# Real path from the dcode session — adapt if your vault differs.
DB = ROOT / "data" / "matheus" / "deliverables" / "byd-d4-outputs" / "byd-tracker.db"


@observed_tool("ikigai.read_sqlite_as_text")
def read_db_as_text(path: str) -> str:
    """Simulates the deepagents fallback: open with utf-8 regardless of content."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    if not DB.exists():
        print(
            f"SKIP: {DB} not present. Drop a SQLite file at this path "
            "(or edit DB constant) and re-run.",
            file=sys.stderr,
        )
        sys.exit(0)

    try:
        read_db_as_text(str(DB))
    except UnicodeDecodeError as e:
        print(f"Reproduced: {e}")
    finally:
        shutdown_tracing()