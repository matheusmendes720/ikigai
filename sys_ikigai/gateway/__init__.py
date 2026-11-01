"""Gateway layer — Tasks 13 + 14.

Serverless scope (ADR-037, 2026-11-01): the stdio MCP clients (taskdog-mcp,
tuiboard, solverforge-calendar) were PC-only surfaces and are no longer
published. The gateway now exposes only the cloud-safe HTTP/data-mesh
adapters.
"""

from .client_adapter import MCPClientAdapter
from .downstream import (
    CliAdapter,
    TaskdogAdapter,
    register_default_adapters,
)
from .gateway import GatewayConfig, UnifiedMCPGateway

__all__ = [
    "CliAdapter",
    "GatewayConfig",
    "MCPClientAdapter",
    "TaskdogAdapter",
    "UnifiedMCPGateway",
    "register_default_adapters",
]
