"""IKIGAi exceptions — 11 PAV error codes + custom.

PAV error code format: ERR_<CATEGORY>_<NNN>
Categories: ID (identity), SCORE, REGIME, PHASE, STATE, SYNC, DRIFT, OVERRIDE, IO, VAL, MIGRATE
"""

from __future__ import annotations


class IKIGAiError(Exception):
    """Base exception for all IKIGAi errors."""

    code: str = "ERR_IKIGAI_000"

    def __init__(self, message: str, *, code: str | None = None, context: dict | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code
        self.context = context or {}


# ─────────────────────────────────────────────────────────────────────────────
# Identity errors (ERR_ID_xxx)
# ─────────────────────────────────────────────────────────────────────────────


class InvalidUEIDError(IKIGAiError):
    code = "ERR_ID_001"


class UEIDCollisionError(IKIGAiError):
    code = "ERR_ID_002"


class SlugImmutableError(IKIGAiError):
    code = "ERR_ID_003"


# ─────────────────────────────────────────────────────────────────────────────
# Score errors (ERR_SCORE_xxx)
# ─────────────────────────────────────────────────────────────────────────────


class ScoreRangeError(IKIGAiError):
    code = "ERR_SCORE_001"


class ScoreUnitMismatchError(IKIGAiError):
    code = "ERR_SCORE_002"


# ─────────────────────────────────────────────────────────────────────────────
# Regime / Phase errors (ERR_REGIME_xxx, ERR_PHASE_xxx)
# ─────────────────────────────────────────────────────────────────────────────


class RegimeHysteresisViolationError(IKIGAiError):
    code = "ERR_REGIME_001"


class PhaseConvergenceError(IKIGAiError):
    code = "ERR_PHASE_001"


# ─────────────────────────────────────────────────────────────────────────────
# State machine errors (ERR_STATE_xxx)
# ─────────────────────────────────────────────────────────────────────────────


class InvalidStateTransitionError(IKIGAiError):
    code = "ERR_STATE_001"


class GuardConditionFailedError(IKIGAiError):
    code = "ERR_STATE_002"


# ─────────────────────────────────────────────────────────────────────────────
# Sync / drift errors (ERR_SYNC_xxx, ERR_DRIFT_xxx)
# ─────────────────────────────────────────────────────────────────────────────


class SyncError(IKIGAiError):
    code = "ERR_SYNC_001"


class DriftDetectedError(IKIGAiError):
    code = "ERR_DRIFT_001"


# ─────────────────────────────────────────────────────────────────────────────
# Override errors (ERR_OVERRIDE_xxx)
# ─────────────────────────────────────────────────────────────────────────────


class OverrideRejectedError(IKIGAiError):
    code = "ERR_OVERRIDE_001"


# ─────────────────────────────────────────────────────────────────────────────
# IO / validation errors (ERR_IO_xxx, ERR_VAL_xxx)
# ─────────────────────────────────────────────────────────────────────────────


class MarkdownParseError(IKIGAiError):
    code = "ERR_IO_001"


class MarkdownWriteError(IKIGAiError):
    code = "ERR_IO_002"


class ValidationError(IKIGAiError):
    code = "ERR_VAL_001"


class MigrationError(IKIGAiError):
    code = "ERR_MIGRATE_001"


__all__ = [
    "IKIGAiError",
    "InvalidUEIDError",
    "UEIDCollisionError",
    "SlugImmutableError",
    "ScoreRangeError",
    "ScoreUnitMismatchError",
    "RegimeHysteresisViolationError",
    "PhaseConvergenceError",
    "InvalidStateTransitionError",
    "GuardConditionFailedError",
    "SyncError",
    "DriftDetectedError",
    "OverrideRejectedError",
    "MarkdownParseError",
    "MarkdownWriteError",
    "ValidationError",
    "MigrationError",
]
