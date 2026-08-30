"""tuiboard MCP server entry point.

Transport-only scaffold (Phase A1). Tools (tuiboard_diff, tuiboard_snapshot,
tuiboard_render) are added in A2-A3.
"""
from __future__ import annotations

import logging
import os

from ikigai.gateway.stdio_server_base import StdioServerBase

logger = logging.getLogger(__name__)


def _build_server() -> StdioServerBase:
    snapshots_dir = os.environ.get("TUIBOARD_SNAPSHOTS_DIR", "data/tuiboard/snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)
    return StdioServerBase(name="tuiboard", version="0.1.0")


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=__import__("sys").stderr)
    server = _build_server()
    # Tools registered in A2 (tuiboard_diff), A3 (tuiboard_snapshot, tuiboard_render)
    server.serve_forever()


if __name__ == "__main__":
    main()
