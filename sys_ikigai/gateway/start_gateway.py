"""UnifiedMCPGateway launcher — separates Layer 2 from Layer 1 FastMCP server.

Per spec §10 (decisions):
- Q3=a: no auth (localhost-only is sufficient)
- Q4=i: single JSONL event log at data/gateway/events.jsonl
- Wires register_default_adapters() so all 3 forks (taskdog, solverforge-calendar,
  tuiboard) are reachable via /call endpoint.

Boot:
    python -m ikigai.gateway.start_gateway
"""

from __future__ import annotations

import http.server
import logging
import os
import sys
from pathlib import Path

# EventLog is defined in ikigai.gateway.event_log but not re-exported by the
# package __init__; import directly to keep the fix inside start_gateway.py
# (per A1.7 brief AC#7: NO files outside the 2 listed paths).
from sys_ikigai.gateway import (
    GatewayConfig,
    UnifiedMCPGateway,
    register_default_adapters,
)
from sys_ikigai.gateway.event_log import EventLog

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    host = os.environ.get("IKIGAI_GATEWAY_HOST", "127.0.0.1")
    port = int(os.environ.get("IKIGAI_GATEWAY_PORT", "8765"))
    data_dir = Path(os.environ.get("IKIGAI_DATA_DIR", "data"))

    cfg = GatewayConfig(host=host, port=port)
    event_log = EventLog(data_dir / "gateway" / "events.jsonl")
    gateway = UnifiedMCPGateway(config=cfg, event_log=event_log)
    register_default_adapters(gateway, data_dir=data_dir)
    logger.info("gateway listening on %s:%d (adapters registered)", host, port)
    # Plan called gateway.serve_forever(), but the shipped UnifiedMCPGateway
    # class only exposes make_handler(); the HTTP server boot is owned here
    # so the A1.7 brief's "NO files outside 2 listed paths" constraint holds.
    server = http.server.ThreadingHTTPServer((cfg.host, cfg.port), gateway.make_handler())
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("gateway shutting down")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
