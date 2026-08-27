"""Tests for ikigai.exceptions — all error codes."""

from __future__ import annotations

import pytest
from ikigai.exceptions import (
    IKIGAiError,
    InvalidUEIDError,
    UEIDCollisionError,
    SlugImmutableError,
    ScoreRangeError,
    ScoreUnitMismatchError,
    RegimeHysteresisViolationError,
    PhaseConvergenceError,
    InvalidStateTransitionError,
    GuardConditionFailedError,
    SyncError,
    DriftDetectedError,
    OverrideRejectedError,
    MarkdownParseError,
    MarkdownWriteError,
    ValidationError,
    MigrationError,
)


class TestIKIGAiError:
    """Base IKIGAiError exception class."""

    def test_is_exception(self) -> None:
        """IKIGAiError must subclass Exception."""
        assert issubclass(IKIGAiError, Exception)

    def test_message_and_code(self) -> None:
        """Must accept message and code."""
        err = IKIGAiError("test message", code="ERR_TEST")
        assert str("test message") in str(err) or "ERR_TEST" in str(err)
        assert err.code == "ERR_TEST"

    def test_context_stored(self) -> None:
        """context dict must be stored."""
        err = IKIGAiError("test", context={"key": "value"})
        assert err.context["key"] == "value"


class TestInvalidUEIDError:
    def test_inheritance(self) -> None:
        assert issubclass(InvalidUEIDError, IKIGAiError)

    def test_code(self) -> None:
        assert InvalidUEIDError("bad ueid").code == "ERR_ID_001"


class TestUEIDCollisionError:
    def test_inheritance(self) -> None:
        assert issubclass(UEIDCollisionError, IKIGAiError)

    def test_code(self) -> None:
        assert UEIDCollisionError("collision").code == "ERR_ID_002"


class TestSlugImmutableError:
    def test_inheritance(self) -> None:
        assert issubclass(SlugImmutableError, IKIGAiError)

    def test_code(self) -> None:
        assert SlugImmutableError("immutable").code == "ERR_ID_003"


class TestScoreRangeError:
    def test_inheritance(self) -> None:
        assert issubclass(ScoreRangeError, IKIGAiError)

    def test_code(self) -> None:
        assert ScoreRangeError("range").code == "ERR_SCORE_001"


class TestScoreUnitMismatchError:
    def test_inheritance(self) -> None:
        assert issubclass(ScoreUnitMismatchError, IKIGAiError)

    def test_code(self) -> None:
        assert ScoreUnitMismatchError("unit").code == "ERR_SCORE_002"


class TestRegimeHysteresisViolationError:
    def test_inheritance(self) -> None:
        assert issubclass(RegimeHysteresisViolationError, IKIGAiError)

    def test_code(self) -> None:
        assert RegimeHysteresisViolationError("hyst").code == "ERR_REGIME_001"


class TestPhaseConvergenceError:
    def test_inheritance(self) -> None:
        assert issubclass(PhaseConvergenceError, IKIGAiError)

    def test_code(self) -> None:
        assert PhaseConvergenceError("conv").code == "ERR_PHASE_001"


class TestInvalidStateTransitionError:
    def test_inheritance(self) -> None:
        assert issubclass(InvalidStateTransitionError, IKIGAiError)

    def test_code(self) -> None:
        assert InvalidStateTransitionError("trans").code == "ERR_STATE_001"


class TestGuardConditionFailedError:
    def test_inheritance(self) -> None:
        assert issubclass(GuardConditionFailedError, IKIGAiError)

    def test_code(self) -> None:
        assert GuardConditionFailedError("guard").code == "ERR_STATE_002"


class TestSyncError:
    def test_inheritance(self) -> None:
        assert issubclass(SyncError, IKIGAiError)

    def test_code(self) -> None:
        assert SyncError("sync").code == "ERR_SYNC_001"


class TestDriftDetectedError:
    def test_inheritance(self) -> None:
        assert issubclass(DriftDetectedError, IKIGAiError)

    def test_code(self) -> None:
        assert DriftDetectedError("drift").code == "ERR_DRIFT_001"


class TestOverrideRejectedError:
    def test_inheritance(self) -> None:
        assert issubclass(OverrideRejectedError, IKIGAiError)

    def test_code(self) -> None:
        assert OverrideRejectedError("over").code == "ERR_OVERRIDE_001"


class TestMarkdownParseError:
    def test_inheritance(self) -> None:
        assert issubclass(MarkdownParseError, IKIGAiError)

    def test_code(self) -> None:
        assert MarkdownParseError("parse").code == "ERR_IO_001"


class TestMarkdownWriteError:
    def test_inheritance(self) -> None:
        assert issubclass(MarkdownWriteError, IKIGAiError)

    def test_code(self) -> None:
        assert MarkdownWriteError("write").code == "ERR_IO_002"


class TestValidationError:
    def test_inheritance(self) -> None:
        assert issubclass(ValidationError, IKIGAiError)

    def test_code(self) -> None:
        assert ValidationError("val").code == "ERR_VAL_001"


class TestMigrationError:
    def test_inheritance(self) -> None:
        assert issubclass(MigrationError, IKIGAiError)

    def test_code(self) -> None:
        assert MigrationError("mig").code == "ERR_MIGRATE_001"
