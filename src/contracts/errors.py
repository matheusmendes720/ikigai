"""The typed error surface of the data layer (SPEC-03 D4).

The distinction matters to the agent on the other end of the transport: a
conflict means "reread and reapply", a validation failure means "fix the
payload", a forbidden means "stop" and a missing artifact means "check the UID".
A single opaque exception would collapse all four into one behaviour.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "ConflictError",
    "DataLayerError",
    "ErrorCode",
    "ForbiddenError",
    "InvalidPayloadError",
    "NotFoundError",
]


class ErrorCode(StrEnum):
    """Machine-readable error identity. This is what the transport surfaces."""

    CONFLICT = "conflict"
    VALIDATION = "validation"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"


class DataLayerError(Exception):
    """Base for every error the data layer raises deliberately."""

    code: ErrorCode = ErrorCode.VALIDATION

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def to_dict(self) -> dict[str, str | None]:
        return {"code": str(self.code), "message": self.message, "detail": self.detail}


class ConflictError(DataLayerError):
    """The optimistic revision guard rejected the write. Nothing was overwritten."""

    code = ErrorCode.CONFLICT


class InvalidPayloadError(DataLayerError):
    """The payload failed validation.

    Deliberately not named `ValidationError`: that name belongs to pydantic, and
    having both in scope in the same module is a reliable source of a caught
    exception meaning the wrong thing.
    """

    code = ErrorCode.VALIDATION


class ForbiddenError(DataLayerError):
    """Row-level security denied the operation. Never worked around."""

    code = ErrorCode.FORBIDDEN


class NotFoundError(DataLayerError):
    """No artifact carries that UID."""

    code = ErrorCode.NOT_FOUND
