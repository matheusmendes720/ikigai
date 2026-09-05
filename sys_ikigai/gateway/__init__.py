"""Gateway layer — Tasks 13 + 14."""

from .client_adapter import MCPClientAdapter
from .downstream import (
    cli_adapter,
    register_default_adapters,
    solverforge_calendar_adapter,
    taskdog_adapter,
    tuiboard_adapter,
)
from .gateway import GatewayConfig, UnifiedMCPGateway
from .stdio_adapter import StdioAdapter, StdioAdapterConfig, StdioAdapterError

__all__ = [
    "GatewayConfig",
    "MCPClientAdapter",
    "StdioAdapter",
    "StdioAdapterConfig",
    "StdioAdapterError",
    "UnifiedMCPGateway",
    "cli_adapter",
    "register_default_adapters",
    "solverforge_calendar_adapter",
    "taskdog_adapter",
    "tuiboard_adapter",
]
