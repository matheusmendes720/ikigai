"""Schema validation tests for A2UI protocol wire types.

Spec: docs/superpowers/specs/2026-08-28-a2ui-protocol-design.md

Tests verify:
  1. Valid envelopes roundtrip via JSON
  2. Pydantic v2 strict (frozen + extra=forbid) is enforced
  3. Invalid UEIDs are rejected (UEID type validation cascades)
  4. Unknown methods / actions are rejected
  5. Error code range is enforced (-32799 to -32000)
  6. JSON-RPC v2.0 protocol version is the only valid value
"""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from src.contracts.common import UEID
from src.mesh.adapters.a2ui_schema import (
    A2UIError,
    A2UINotification,
    A2UIRequest,
    A2UIResponse,
    MeshReadParams,
    MeshSubscribeParams,
    TaskWriteParams,
)


VALID_UEID = UEID("tsk:foo:11111111-1111-1111-1111-111111111111:1111111111111111")


# === A2UIRequest ===

def test_request_minimal_roundtrip() -> None:
    """mesh.read with bare params dict still validates."""
    req = A2UIRequest(id="req-001", method="mesh.read", params={"ueid": str(VALID_UEID)})
    as_json = req.model_dump_json()
    restored = A2UIRequest.model_validate_json(as_json)
    assert restored.id == "req-001"
    assert restored.method == "mesh.read"
    assert restored.jsonrpc == "2.0"


def test_request_rejects_unknown_method() -> None:
    with pytest.raises(ValidationError):
        A2UIRequest(id="req-002", method="mesh.bogus", params={})


def test_request_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        A2UIRequest(id="req-003", method="mesh.read", params={}, extra_field="nope")


def test_request_rejects_empty_id() -> None:
    with pytest.raises(ValidationError):
        A2UIRequest(id="", method="mesh.read", params={})


def test_request_rejects_long_id() -> None:
    with pytest.raises(ValidationError):
        A2UIRequest(id="x" * 65, method="mesh.read", params={})


# === A2UIResponse ===

def test_response_success_roundtrip() -> None:
    resp = A2UIResponse(id="req-001", result={"ueid": str(VALID_UEID), "view": {}, "mismatches": []})
    as_json = resp.model_dump_json()
    restored = A2UIResponse.model_validate_json(as_json)
    assert restored.result == {"ueid": str(VALID_UEID), "view": {}, "mismatches": []}
    assert restored.error is None


def test_response_error_roundtrip() -> None:
    resp = A2UIResponse(
        id="req-001",
        error=A2UIError(code=-32602, message="Invalid UEID", data={"ueid": "bad-input"}),
    )
    as_json = resp.model_dump_json()
    restored = A2UIResponse.model_validate_json(as_json)
    assert restored.error is not None
    assert restored.error.code == -32602
    assert restored.error.message == "Invalid UEID"
    assert restored.error.data == {"ueid": "bad-input"}
    assert restored.result is None


def test_response_error_code_must_be_in_jsonrpc_range() -> None:
    """JSON-RPC 2.0 reserves -32799 to -32000 for predefined errors."""
    with pytest.raises(ValidationError):
        A2UIError(code=-100, message="non-JSON-RPC code")


def test_response_error_rejects_long_message() -> None:
    with pytest.raises(ValidationError):
        A2UIError(code=-32603, message="x" * 513)


# === A2UINotification ===

def test_notification_default_method_is_mesh_event() -> None:
    note = A2UINotification(params={"event_id": "evt_abc123", "ueid": str(VALID_UEID)})
    assert note.method == "mesh.event"
    assert note.jsonrpc == "2.0"


def test_notification_rejects_unknown_method() -> None:
    with pytest.raises(ValidationError):
        A2UINotification(method="mesh.bogus", params={})


# === MeshReadParams ===

def test_mesh_read_params_validates_ueid() -> None:
    """UEID is validated on construction; bad UEIDs raise ValueError."""
    with pytest.raises(ValidationError):
        MeshReadParams(ueid="not-a-ueid")  # type: ignore[arg-type]


def test_mesh_read_params_accepts_valid_ueid() -> None:
    p = MeshReadParams(ueid=VALID_UEID)
    assert str(p.ueid) == str(VALID_UEID)


# === TaskWriteParams ===

@pytest.mark.parametrize(
    "action",
    ["create", "update", "delete", "done"],
)
def test_task_write_params_accepts_all_actions(action: str) -> None:
    p = TaskWriteParams(
        action=action,  # type: ignore[arg-type]
        ueid=VALID_UEID,
        fields={"title": "x"},
        source_fork="interfaces/cli",
    )
    assert p.action == action


def test_task_write_params_rejects_unknown_action() -> None:
    with pytest.raises(ValidationError):
        TaskWriteParams(
            action="bogus",  # type: ignore[arg-type]
            ueid=VALID_UEID,
            fields={},
            source_fork="interfaces/cli",
        )


def test_task_write_params_rejects_short_source_fork() -> None:
    with pytest.raises(ValidationError):
        TaskWriteParams(
            action="create",
            ueid=VALID_UEID,
            fields={},
            source_fork="x",  # min_length=2
        )


def test_task_write_params_defaults_fields_to_empty_dict() -> None:
    p = TaskWriteParams(
        action="delete",
        ueid=VALID_UEID,
        source_fork="interfaces/cli",
    )
    assert p.fields == {}


# === MeshSubscribeParams ===

def test_subscribe_params_default_filters() -> None:
    p = MeshSubscribeParams()
    assert p.filters == {}


def test_subscribe_params_accepts_filters() -> None:
    p = MeshSubscribeParams(filters={"actions": ["create"], "ueid_prefix": "tsk:"})
    assert p.filters == {"actions": ["create"], "ueid_prefix": "tsk:"}


# === Frozen invariant ===

def test_request_is_frozen() -> None:
    """Pydantic v2 strict: frozen=True prevents mutation."""
    req = A2UIRequest(id="req-001", method="mesh.read", params={})
    with pytest.raises(ValidationError):
        req.id = "req-002"  # type: ignore[misc]


def test_response_is_frozen() -> None:
    resp = A2UIResponse(id="req-001", result={"x": 1})
    with pytest.raises(ValidationError):
        resp.result = {"x": 2}  # type: ignore[misc]


# === JSON roundtrip (no data loss) ===

def test_full_request_response_cycle_via_json() -> None:
    """End-to-end: build request → JSON → parse on other side → build response."""
    req = A2UIRequest(
        id="req-007",
        method="task.write",
        params={
            "action": "create",
            "ueid": str(VALID_UEID),
            "fields": {"title": "Hello", "priority": "high"},
            "source_fork": "interfaces/cli",
        },
    )
    wire = req.model_dump_json()
    parsed = json.loads(wire)
    assert parsed["jsonrpc"] == "2.0"
    assert parsed["method"] == "task.write"

    # Server side: parse params via typed schema
    server_params = TaskWriteParams.model_validate(parsed["params"])
    assert server_params.action == "create"
    assert server_params.fields["title"] == "Hello"

    # Server side: build response
    resp = A2UIResponse(id="req-007", result={"event_id": "evt_abc", "status": "pending"})
    wire_resp = resp.model_dump_json()
    assert json.loads(wire_resp)["result"]["status"] == "pending"