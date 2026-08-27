"""Gateway layer — Tasks 13 + 14."""

from .client_adapter import MCPClientAdapter
from .downstream import (
    SolverforgeCalendarAdapter,
    TaskdogAdapter,
    TuiboardAdapter,
    register_default_adapters,
)
from .gateway import GatewayConfig, UnifiedMCPGateway
from .stdio_adapter import StdioAdapter, StdioAdapterConfig, StdioAdapterError

__all__ = [
    "GatewayConfig",
    "MCPClientAdapter",
    "SolverforgeCalendarAdapter",
    "StdioAdapter",
    "StdioAdapterConfig",
    "StdioAdapterError",
    "TaskdogAdapter",
    "TuiboardAdapter",
    "UnifiedMCPGateway",
    "register_default_adapters",
]
