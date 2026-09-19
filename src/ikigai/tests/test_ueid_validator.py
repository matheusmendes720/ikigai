"""Tests for UEID primitive type — 5-part format per SPEC D10 + §3.1."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from sys_ikigai.entities.ueid import UEID


class TestUEIDValidator:
    def test_valid_ueid_parses(self) -> None:
        class M(BaseModel):
            id: UEID

        m = M(id="ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609")
        assert m.id == "ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609"

    @pytest.mark.skip(reason="M73.1 dropped namespace allowlist; 2-8 lowercase range accepts any. Test no longer applies.")
    def test_wrong_namespace_rejected(self) -> None:
        """M73.1 widened namespace from {2,5}→{2,8}. Any 2-8 char lowercase string
        is a valid namespace. The strict allowlist test was rolled back to keep
        SONHO `sn:` and other production namespaces compatible."""
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
        """M73.2 relaxed UUID/hash minimum to {4,8} for solverforge fixture compat
        (solverforge calendar uses 5-char hashes like `cccc3`).
        Therefore 4-char hex is now the minimum; 3-char is rejected."""
        class M(BaseModel):
            id: UEID

        with pytest.raises(ValidationError):
            M(id="ikigai:dream:slug:abc:def4567")

    def test_extra_colons_rejected(self) -> None:
        class M(BaseModel):
            id: UEID

        with pytest.raises(ValidationError):
            M(id="ikigai:dream:slug:more:4f6a202a:2cb24609")
