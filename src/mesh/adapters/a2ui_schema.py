"""A2UI — Agent-to-UI Standard Protocol — wire schemas.

This module defines the JSON-RPC 2.0 message envelopes and parameter shapes
for the A2UI protocol. See `docs/superpowers/specs/2026-08-28-a2ui-protocol-design.md`
for the full spec.

v1 scope: schema only. No A2uiAdapter class yet (deferred per user decision 2026-08-28).
The transport (stdio canonical, HTTP+SSE future) and concrete UI implementations
(chat, TUI, web) consume these schemas.

Schemas:
- A2UIRequest / A2UIResponse / A2UIError / A2UINotification: JSON-RPC 2.0 envelopes
- MeshReadParams / TaskWriteParams / MeshSubscribeParams: typed method params
- A2UIAction: literal for task.write action field
- A2UIStatus: literal for event status

Pydantic v2 strict: frozen=True, extra="forbid". Aligns with src/contracts/ invariant.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.contracts.common import UEID


# === Literal type aliases (used by both spec and tests) ===

A2UIAction = Literal["create", "update", "delete", "done"]
A2UIMethod = Literal["mesh.read", "task.write", "mesh.subscribe"]
A2UINotificationMethod = Literal["mesh.event"]
A2UIProtocolVersion = Literal["2.0"]


# === JSON-RPC 2.0 envelopes ===

class A2UIError(BaseModel):
    """JSON-RPC 2.0 error object.

    Standard codes:
      -32700 Parse error (invalid JSON)
      -32600 Invalid Request
      -32601 Method not found
      -32602 Invalid params
      -32603 Internal error
    """
    model_config = ConfigDict(frozen=True, extra="forbid")
    code: int = Field(ge=-32799, le=-32000)  # JSON-RPC reserved range
    message: str = Field(min_length=1, max_length=512)
    data: dict | None = None


class A2UIRequest(BaseModel):
    """JSON-RPC 2.0 request envelope (client → server)."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    jsonrpc: A2UIProtocolVersion = "2.0"
    id: str = Field(min_length=1, max_length=64)
    method: A2UIMethod
    params: dict = Field(default_factory=dict)


class A2UIResponse(BaseModel):
    """JSON-RPC 2.0 response envelope (server → client).

    Exactly one of `result` or `error` must be set.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")
    jsonrpc: A2UIProtocolVersion = "2.0"
    id: str = Field(min_length=1, max_length=64)
    result: dict | None = None
    error: A2UIError | None = None


class A2UINotification(BaseModel):
    """JSON-RPC 2.0 server-pushed notification (no id, no response expected)."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    jsonrpc: A2UIProtocolVersion = "2.0"
    method: A2UINotificationMethod = "mesh.event"
    params: dict = Field(default_factory=dict)


# === Typed params for the 3 top-level methods ===

class MeshReadParams(BaseModel):
    """Params for `mesh.read`: cross-fork view for one UEID."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    ueid: UEID


class TaskWriteParams(BaseModel):
    """Params for `task.write`: emit TaskChange to review queue.

    v1: only `action="create"` is fully implemented. Other actions return
    -32601 Method not found (deferred to v1.2-v1.4).
    """
    model_config = ConfigDict(frozen=True, extra="forbid")
    action: A2UIAction
    ueid: UEID
    fields: dict = Field(default_factory=dict)
    source_fork: str = Field(min_length=2, max_length=64)


class MeshSubscribeParams(BaseModel):
    """Params for `mesh.subscribe`: open push stream of new events."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    filters: dict = Field(default_factory=dict)


__all__ = [
    "A2UIAction",
    "A2UIMethod",
    "A2UINotificationMethod",
    "A2UIProtocolVersion",
    "A2UIError",
    "A2UIRequest",
    "A2UIResponse",
    "A2UINotification",
    "MeshReadParams",
    "TaskWriteParams",
    "MeshSubscribeParams",
]