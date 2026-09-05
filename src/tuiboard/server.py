"""tuiboard MCP server entry point.

Transport-only scaffold (Phase A1). Tools (tuiboard_diff, tuiboard_snapshot,
tuiboard_render) are added in A2-A3.
"""
from __future__ import annotations

import logging
import os

from sys_ikigai.gateway.stdio_server_base import StdioServerBase

logger = logging.getLogger(__name__)


def _build_server() -> StdioServerBase:
    snapshots_dir = os.environ.get("TUIBOARD_SNAPSHOTS_DIR", "data/tuiboard/snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)
    server = StdioServerBase(name="tuiboard", version="0.1.0")
    # A2: read tools
    from tuiboard.tools.tuiboard_diff import handle as tb_diff
    from tuiboard.models import TuiboardDiffInput
    server.register_tool(
        name="tuiboard_diff",
        handler=tb_diff,
        schema=TuiboardDiffInput.model_json_schema(),
    )
    # A3: write tools (tuiboard_snapshot) - stub added in A2.6 for E2E
    from tuiboard.tools.tuiboard_snapshot import handle as tb_snapshot
    from tuiboard.models import TuiboardSnapshotInput
    server.register_tool(
        name="tuiboard_snapshot",
        handler=tb_snapshot,
        schema=TuiboardSnapshotInput.model_json_schema(),
    )
    # A3.4: render tool (4 layouts)
    from tuiboard.tools.tuiboard_render import handle as tb_render
    from tuiboard.models import TuiboardRenderInput
    server.register_tool(
        name="tuiboard_render",
        handler=tb_render,
        schema=TuiboardRenderInput.model_json_schema(),
    )
    # A4.3: aggregator-driven tool (multi-fork read)
    from tuiboard.tools.tuiboard_aggregate import handle as tb_aggregate
    from tuiboard.models import TuiboardAggregateInput
    server.register_tool(
        name="tuiboard_aggregate",
        handler=tb_aggregate,
        schema=TuiboardAggregateInput.model_json_schema(),
    )
    return server


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=__import__("sys").stderr)
    server = _build_server()
    # Tools registered in A2 (tuiboard_diff), A3 (tuiboard_snapshot, tuiboard_render),
    # A4.3 (tuiboard_aggregate)
    server.serve_forever()


if __name__ == "__main__":
    main()
