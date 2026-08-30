"""solverforge-calendar MCP server entry point.

Transport-only scaffold (Phase A1). Tools (sf_availability, sf_schedule,
sf_replan) are added in A2-A4.
"""
from __future__ import annotations

import logging
import os

from ikigai.gateway.stdio_server_base import StdioServerBase

logger = logging.getLogger(__name__)


def _build_server() -> StdioServerBase:
    data_dir = os.environ.get("SOLVERFORGE_DATA_DIR", "data/solverforge_calendar")
    os.makedirs(data_dir, exist_ok=True)
    return StdioServerBase(name="solverforge-calendar", version="0.1.0")


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=__import__("sys").stderr)
    server = _build_server()
    # Tools registered in A2 (sf_availability), A3 (sf_schedule), A4 (sf_replan)
    server.serve_forever()


if __name__ == "__main__":
    main()
