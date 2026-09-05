"""solverforge-calendar MCP server entry point.

Transport-only scaffold (Phase A1). Tools (sf_availability, sf_schedule,
sf_replan) are added in A2-A4.
"""

from __future__ import annotations

import logging
import os

from sys_ikigai.gateway.stdio_server_base import StdioServerBase

logger = logging.getLogger(__name__)


def _build_server() -> StdioServerBase:
    data_dir = os.environ.get("SOLVERFORGE_DATA_DIR", "data/solverforge_calendar")
    os.makedirs(data_dir, exist_ok=True)
    server = StdioServerBase(name="solverforge-calendar", version="0.1.0")
    # A2: read tools
    from solverforge_calendar.tools.sf_availability import handle as sf_avail
    from solverforge_calendar.models import SfAvailabilityInput

    server.register_tool(
        name="sf_availability",
        handler=sf_avail,
        schema=SfAvailabilityInput.model_json_schema(),
    )
    # A3: write tools
    from solverforge_calendar.tools.sf_schedule import handle as sf_sched
    from solverforge_calendar.models import SfScheduleInput

    server.register_tool(
        name="sf_schedule",
        handler=sf_sched,
        schema=SfScheduleInput.model_json_schema(),
    )
    # A4: advanced tools
    from solverforge_calendar.tools.sf_replan import handle as sf_replan
    from solverforge_calendar.models import SfReplanInput

    server.register_tool(
        name="sf_replan",
        handler=sf_replan,
        schema=SfReplanInput.model_json_schema(),
    )
    return server


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=__import__("sys").stderr)
    server = _build_server()
    # Tools registered in A2 (sf_availability), A3 (sf_schedule), A4 (sf_replan)
    server.serve_forever()


if __name__ == "__main__":
    main()
