"""Tests for UEID primitive type — 5-part format per SPEC D10 + §3.1."""
from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from ikigai.entities.ueid import UEID


class TestUEIDValidator:
    def test_valid_ueid_parses(self) -> None:
        class M(BaseModel):
            id: UEID

        m = M(id="ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609")
        assert m.id == "ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609"

    def test_wrong_namespace_rejected(self) -> None:
        class M(BaseModel):
            id: UEID

        with pytest.raises(ValidationError):
            M(id="other:dream:slug:4f6a202a:2cb24609")

    def test_uppercase_uuid_rejected(self) -> None:
        class M(BaseModel):
            id: UEID

        with pytest.raises(ValidationError):
            M(id="ikigai:dream:slug:4F6A202A:2cb24609")

    def test_short_uuid_rejected(self) -> None:
        class M(BaseModel):
            id: UEID

        with pytest.raises(ValidationError):
            M(id="ikigai:dream:slug:4f6a202:2cb24609")

    def test_extra_colons_rejected(self) -> None:
        class M(BaseModel):
            id: UEID

        with pytest.raises(ValidationError):
            M(id="ikigai:dream:slug:more:4f6a202a:2cb24609")
